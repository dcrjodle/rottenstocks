"""
Migration testing utilities and safety procedures.

Provides tools for testing migrations, rollback procedures, and database
schema validation to ensure safe migration operations.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.core.config import get_settings


def get_alembic_config() -> Config:
    """Get configured Alembic config object."""
    backend_dir = Path(__file__).parent.parent.parent
    alembic_ini_path = backend_dir / "alembic.ini"
    
    config = Config(str(alembic_ini_path))
    return config


def create_backup_database(backup_name: Optional[str] = None) -> str:
    """
    Create a backup of the current database.
    
    Args:
        backup_name: Optional name for the backup. If None, uses timestamp.
        
    Returns:
        str: Name of the backup database created.
    """
    settings = get_settings()
    
    if backup_name is None:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"rottenstocks_backup_{timestamp}"
    
    # Extract database connection details
    db_url = settings.database_url_sync
    if "postgresql" in db_url:
        # Create PostgreSQL backup
        backup_cmd = [
            "pg_dump",
            "-h", settings.POSTGRES_SERVER,
            "-p", str(settings.POSTGRES_PORT),
            "-U", settings.POSTGRES_USER,
            "-d", settings.POSTGRES_DB,
            "-f", f"/tmp/{backup_name}.sql",
            "--no-password"
        ]
        
        env = os.environ.copy()
        env["PGPASSWORD"] = settings.POSTGRES_PASSWORD
        
        result = subprocess.run(backup_cmd, env=env, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Database backup failed: {result.stderr}")
        
        print(f"✅ Database backup created: /tmp/{backup_name}.sql")
        return backup_name
    
    raise NotImplementedError("Only PostgreSQL backups are currently supported")


def restore_from_backup(backup_name: str) -> None:
    """
    Restore database from a backup.
    
    Args:
        backup_name: Name of the backup to restore from.
    """
    settings = get_settings()
    backup_file = f"/tmp/{backup_name}.sql"
    
    if not os.path.exists(backup_file):
        raise FileNotFoundError(f"Backup file not found: {backup_file}")
    
    # Drop and recreate database
    admin_engine = create_engine(
        f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@"
        f"{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/postgres"
    )
    
    with admin_engine.connect() as conn:
        # Terminate existing connections
        conn.execute(text(f"""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = '{settings.POSTGRES_DB}'
            AND pid <> pg_backend_pid()
        """))
        
        # Drop and recreate database
        conn.execute(text(f"DROP DATABASE IF EXISTS {settings.POSTGRES_DB}"))
        conn.execute(text(f"CREATE DATABASE {settings.POSTGRES_DB}"))
    
    # Restore from backup
    restore_cmd = [
        "psql",
        "-h", settings.POSTGRES_SERVER,
        "-p", str(settings.POSTGRES_PORT),
        "-U", settings.POSTGRES_USER,
        "-d", settings.POSTGRES_DB,
        "-f", backup_file,
        "--quiet"
    ]
    
    env = os.environ.copy()
    env["PGPASSWORD"] = settings.POSTGRES_PASSWORD
    
    result = subprocess.run(restore_cmd, env=env, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"Database restore failed: {result.stderr}")
    
    print(f"✅ Database restored from backup: {backup_name}")


def test_migration_forward(target_revision: Optional[str] = None) -> bool:
    """
    Test migrating forward to a specific revision.
    
    Args:
        target_revision: Target revision to migrate to. If None, migrates to head.
        
    Returns:
        bool: True if migration succeeded, False otherwise.
    """
    try:
        config = get_alembic_config()
        
        if target_revision:
            command.upgrade(config, target_revision)
            print(f"✅ Forward migration to {target_revision} successful")
        else:
            command.upgrade(config, "head")
            print("✅ Forward migration to head successful")
        
        return True
    except Exception as e:
        print(f"❌ Forward migration failed: {e}")
        return False


def test_migration_backward(target_revision: str) -> bool:
    """
    Test migrating backward to a specific revision.
    
    Args:
        target_revision: Target revision to migrate to.
        
    Returns:
        bool: True if migration succeeded, False otherwise.
    """
    try:
        config = get_alembic_config()
        command.downgrade(config, target_revision)
        print(f"✅ Backward migration to {target_revision} successful")
        return True
    except Exception as e:
        print(f"❌ Backward migration failed: {e}")
        return False


def get_current_revision() -> str:
    """Get the current database revision."""
    config = get_alembic_config()
    
    # Capture the current revision
    from alembic.runtime.migration import MigrationContext
    from sqlalchemy import create_engine
    
    settings = get_settings()
    engine = create_engine(settings.database_url_sync)
    
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        current_rev = context.get_current_revision()
        return current_rev or "base"


def get_migration_history() -> List[Dict[str, str]]:
    """Get the migration history."""
    config = get_alembic_config()
    
    # Get revision history
    from alembic.script import ScriptDirectory
    
    script_dir = ScriptDirectory.from_config(config)
    history = []
    
    for revision in script_dir.walk_revisions():
        history.append({
            "revision": revision.revision,
            "down_revision": revision.down_revision,
            "branch_labels": revision.branch_labels,
            "message": revision.doc,
            "is_head": revision.is_head,
        })
    
    return history


def validate_migration_path(start_revision: str, end_revision: str) -> List[str]:
    """
    Validate that there's a migration path between two revisions.
    
    Args:
        start_revision: Starting revision
        end_revision: Ending revision
        
    Returns:
        List[str]: List of revisions in the migration path
    """
    config = get_alembic_config()
    from alembic.script import ScriptDirectory
    
    script_dir = ScriptDirectory.from_config(config)
    
    try:
        path = []
        for revision in script_dir.iterate_revisions(end_revision, start_revision):
            path.append(revision.revision)
        return path
    except Exception as e:
        raise ValueError(f"No migration path from {start_revision} to {end_revision}: {e}")


def test_full_migration_cycle(backup_before: bool = True) -> bool:
    """
    Test a full migration cycle: backup -> migrate up -> migrate down -> restore.
    
    Args:
        backup_before: Whether to create a backup before testing
        
    Returns:
        bool: True if all tests passed, False otherwise.
    """
    backup_name = None
    original_revision = get_current_revision()
    
    try:
        print("🧪 Starting full migration cycle test...")
        
        # Create backup if requested
        if backup_before:
            backup_name = create_backup_database()
        
        # Get migration history
        history = get_migration_history()
        if len(history) < 2:
            print("⚠️ Not enough migrations to test full cycle")
            return True
        
        # Test forward migration
        print("📈 Testing forward migration...")
        if not test_migration_forward():
            return False
        
        # Get the previous revision for testing backward migration
        current_rev = get_current_revision()
        previous_rev = None
        
        for revision in history:
            if revision["revision"] == current_rev:
                previous_rev = revision["down_revision"]
                break
        
        if previous_rev:
            # Test backward migration
            print("📉 Testing backward migration...")
            if not test_migration_backward(previous_rev):
                return False
            
            # Migrate back to head
            print("📈 Migrating back to head...")
            if not test_migration_forward():
                return False
        
        print("✅ Full migration cycle test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Migration cycle test failed: {e}")
        
        # Attempt to restore if we have a backup
        if backup_name and backup_before:
            print("🔄 Attempting to restore from backup...")
            try:
                restore_from_backup(backup_name)
            except Exception as restore_error:
                print(f"❌ Backup restore failed: {restore_error}")
        
        return False


if __name__ == "__main__":
    """CLI interface for migration testing utilities."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migration testing utilities")
    parser.add_argument("command", choices=[
        "backup", "restore", "test-forward", "test-backward", 
        "test-cycle", "current", "history"
    ])
    parser.add_argument("--revision", help="Target revision")
    parser.add_argument("--backup-name", help="Backup name")
    parser.add_argument("--no-backup", action="store_true", help="Skip backup creation")
    
    args = parser.parse_args()
    
    try:
        if args.command == "backup":
            backup_name = create_backup_database(args.backup_name)
            print(f"Backup created: {backup_name}")
        
        elif args.command == "restore":
            if not args.backup_name:
                print("❌ --backup-name required for restore command")
                sys.exit(1)
            restore_from_backup(args.backup_name)
        
        elif args.command == "test-forward":
            success = test_migration_forward(args.revision)
            sys.exit(0 if success else 1)
        
        elif args.command == "test-backward":
            if not args.revision:
                print("❌ --revision required for test-backward command")
                sys.exit(1)
            success = test_migration_backward(args.revision)
            sys.exit(0 if success else 1)
        
        elif args.command == "test-cycle":
            success = test_full_migration_cycle(not args.no_backup)
            sys.exit(0 if success else 1)
        
        elif args.command == "current":
            current_rev = get_current_revision()
            print(f"Current revision: {current_rev}")
        
        elif args.command == "history":
            history = get_migration_history()
            print("Migration History:")
            print("-" * 50)
            for rev in history:
                marker = " (HEAD)" if rev["is_head"] else ""
                print(f"📝 {rev['revision']}{marker}")
                print(f"   Message: {rev['message']}")
                print(f"   Down: {rev['down_revision']}")
                print()
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)