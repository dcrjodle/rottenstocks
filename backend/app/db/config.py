"""
Database configuration for RottenStocks application.

This module provides database-specific configuration management that can be used
independently of the main application configuration.
"""

import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    
    # Connection settings
    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: str = "postgres"
    database: str = "rottenstocks"
    driver: str = "asyncpg"
    
    # Connection pool settings
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    pool_pre_ping: bool = True
    
    # Engine settings
    echo: bool = False
    echo_pool: bool = False
    future: bool = True
    
    # Additional engine options
    engine_options: Dict[str, Any] = field(default_factory=dict)
    
    # SSL settings
    ssl_mode: Optional[str] = None
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None
    ssl_ca: Optional[str] = None
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate configuration values."""
        if not self.host:
            raise ValueError("Database host cannot be empty")
        
        if not (1 <= self.port <= 65535):
            raise ValueError("Database port must be between 1 and 65535")
        
        if not self.user:
            raise ValueError("Database user cannot be empty")
        
        if not self.database:
            raise ValueError("Database name cannot be empty")
        
        if self.driver not in ["asyncpg", "psycopg2", "psycopg"]:
            raise ValueError(f"Unsupported database driver: {self.driver}")
        
        if self.pool_size < 1:
            raise ValueError("Pool size must be at least 1")
        
        if self.max_overflow < 0:
            raise ValueError("Max overflow cannot be negative")
        
        if self.pool_timeout < 0:
            raise ValueError("Pool timeout cannot be negative")
    
    @property
    def database_url(self) -> str:
        """Get complete database URL."""
        base_url = f"postgresql+{self.driver}://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        
        # Add SSL parameters if configured
        ssl_params = []
        if self.ssl_mode:
            ssl_params.append(f"sslmode={self.ssl_mode}")
        if self.ssl_cert:
            ssl_params.append(f"sslcert={self.ssl_cert}")
        if self.ssl_key:
            ssl_params.append(f"sslkey={self.ssl_key}")
        if self.ssl_ca:
            ssl_params.append(f"sslrootcert={self.ssl_ca}")
        
        if ssl_params:
            base_url += "?" + "&".join(ssl_params)
        
        return base_url
    
    @property
    def sync_database_url(self) -> str:
        """Get synchronous database URL (without async driver)."""
        return self.database_url.replace(f"+{self.driver}", "")
    
    def get_engine_kwargs(self) -> Dict[str, Any]:
        """Get engine keyword arguments."""
        kwargs = {
            "echo": self.echo,
            "echo_pool": self.echo_pool,
            "future": self.future,
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_timeout": self.pool_timeout,
            "pool_recycle": self.pool_recycle,
            "pool_pre_ping": self.pool_pre_ping,
            **self.engine_options
        }
        
        return kwargs
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "database": self.database,
            "driver": self.driver,
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_timeout": self.pool_timeout,
            "pool_recycle": self.pool_recycle,
            "pool_pre_ping": self.pool_pre_ping,
            "echo": self.echo,
            "echo_pool": self.echo_pool,
            "future": self.future,
            "ssl_mode": self.ssl_mode,
            "ssl_cert": self.ssl_cert,
            "ssl_key": self.ssl_key,
            "ssl_ca": self.ssl_ca,
        }
    
    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> "DatabaseConfig":
        """
        Create configuration from environment variables.
        
        Args:
            env_file: Path to .env file (optional)
        
        Returns:
            DatabaseConfig instance
        """
        # Load .env file if specified and dotenv is available
        if env_file and load_dotenv:
            env_path = Path(env_file)
            if env_path.exists():
                load_dotenv(env_path)
                logger.info(f"Loaded environment from {env_path}")
            else:
                logger.warning(f"Environment file not found: {env_path}")
        elif load_dotenv:
            # Try to load from default locations
            for env_path in [".env", "../.env", "../../.env"]:
                if Path(env_path).exists():
                    load_dotenv(env_path)
                    logger.info(f"Loaded environment from {env_path}")
                    break
        
        # Get configuration from environment variables
        config = cls(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "postgres"),
            database=os.getenv("DB_NAME", "rottenstocks"),
            driver=os.getenv("DB_DRIVER", "asyncpg"),
            
            # Pool settings
            pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
            pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
            pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "3600")),
            pool_pre_ping=os.getenv("DB_POOL_PRE_PING", "true").lower() == "true",
            
            # Engine settings
            echo=os.getenv("DB_ECHO", "false").lower() == "true",
            echo_pool=os.getenv("DB_ECHO_POOL", "false").lower() == "true",
            future=os.getenv("DB_FUTURE", "true").lower() == "true",
            
            # SSL settings
            ssl_mode=os.getenv("DB_SSL_MODE"),
            ssl_cert=os.getenv("DB_SSL_CERT"),
            ssl_key=os.getenv("DB_SSL_KEY"),
            ssl_ca=os.getenv("DB_SSL_CA"),
        )
        
        return config
    
    @classmethod
    def from_url(cls, database_url: str) -> "DatabaseConfig":
        """
        Create configuration from database URL.
        
        Args:
            database_url: Complete database URL
        
        Returns:
            DatabaseConfig instance
        """
        from urllib.parse import urlparse, parse_qs
        
        parsed = urlparse(database_url)
        
        # Extract driver from scheme
        scheme_parts = parsed.scheme.split("+")
        if len(scheme_parts) == 2:
            driver = scheme_parts[1]
        else:
            driver = "asyncpg"  # Default
        
        # Parse query parameters for SSL settings
        query_params = parse_qs(parsed.query) if parsed.query else {}
        
        config = cls(
            host=parsed.hostname or "localhost",
            port=parsed.port or 5432,
            user=parsed.username or "postgres",
            password=parsed.password or "",
            database=parsed.path.lstrip("/") or "rottenstocks",
            driver=driver,
            ssl_mode=query_params.get("sslmode", [None])[0],
            ssl_cert=query_params.get("sslcert", [None])[0],
            ssl_key=query_params.get("sslkey", [None])[0],
            ssl_ca=query_params.get("sslrootcert", [None])[0],
        )
        
        return config


@dataclass
class TestDatabaseConfig(DatabaseConfig):
    """Test database configuration with safe defaults."""
    
    database: str = "rottenstocks_test"
    echo: bool = False
    pool_size: int = 1
    max_overflow: int = 0
    
    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> "TestDatabaseConfig":
        """Create test configuration from environment variables."""
        # Get base config from environment
        base_config = super().from_env(env_file)
        
        # Override with test-specific settings
        return cls(
            host=os.getenv("TEST_DB_HOST", base_config.host),
            port=int(os.getenv("TEST_DB_PORT", str(base_config.port))),
            user=os.getenv("TEST_DB_USER", base_config.user),
            password=os.getenv("TEST_DB_PASSWORD", base_config.password),
            database=os.getenv("TEST_DB_NAME", "rottenstocks_test"),
            driver=os.getenv("TEST_DB_DRIVER", base_config.driver),
            echo=os.getenv("TEST_DB_ECHO", "false").lower() == "true",
            pool_size=1,  # Single connection for tests
            max_overflow=0,
        )


# Configuration factory functions

def get_database_config(
    database_url: Optional[str] = None,
    env_file: Optional[str] = None,
    **overrides
) -> DatabaseConfig:
    """
    Get database configuration.
    
    Args:
        database_url: Complete database URL (takes precedence)
        env_file: Path to .env file
        **overrides: Configuration overrides
    
    Returns:
        DatabaseConfig instance
    """
    if database_url:
        config = DatabaseConfig.from_url(database_url)
    else:
        config = DatabaseConfig.from_env(env_file)
    
    # Apply any overrides
    for key, value in overrides.items():
        if hasattr(config, key):
            setattr(config, key, value)
        else:
            logger.warning(f"Unknown configuration parameter: {key}")
    
    return config


def get_test_database_config(
    database_url: Optional[str] = None,
    env_file: Optional[str] = None,
    **overrides
) -> TestDatabaseConfig:
    """
    Get test database configuration.
    
    Args:
        database_url: Complete database URL (takes precedence)
        env_file: Path to .env file
        **overrides: Configuration overrides
    
    Returns:
        TestDatabaseConfig instance
    """
    if database_url:
        # Convert to test config
        base_config = DatabaseConfig.from_url(database_url)
        config = TestDatabaseConfig(
            host=base_config.host,
            port=base_config.port,
            user=base_config.user,
            password=base_config.password,
            database=f"{base_config.database}_test",
            driver=base_config.driver,
        )
    else:
        config = TestDatabaseConfig.from_env(env_file)
    
    # Apply any overrides
    for key, value in overrides.items():
        if hasattr(config, key):
            setattr(config, key, value)
        else:
            logger.warning(f"Unknown configuration parameter: {key}")
    
    return config


def validate_database_config(config: DatabaseConfig) -> bool:
    """
    Validate database configuration.
    
    Args:
        config: Database configuration to validate
    
    Returns:
        True if valid, raises exception if invalid
    """
    try:
        config._validate_config()
        return True
    except ValueError as e:
        logger.error(f"Database configuration validation failed: {e}")
        raise


# Environment variable reference for documentation
ENV_VAR_REFERENCE = {
    "DB_HOST": "Database host (default: localhost)",
    "DB_PORT": "Database port (default: 5432)",
    "DB_USER": "Database username (default: postgres)",
    "DB_PASSWORD": "Database password (default: postgres)",
    "DB_NAME": "Database name (default: rottenstocks)",
    "DB_DRIVER": "Database driver (default: asyncpg)",
    "DB_POOL_SIZE": "Connection pool size (default: 5)",
    "DB_MAX_OVERFLOW": "Maximum pool overflow (default: 10)",
    "DB_POOL_TIMEOUT": "Pool timeout in seconds (default: 30)",
    "DB_POOL_RECYCLE": "Pool recycle time in seconds (default: 3600)",
    "DB_POOL_PRE_PING": "Enable pool pre-ping (default: true)",
    "DB_ECHO": "Enable SQL query logging (default: false)",
    "DB_ECHO_POOL": "Enable pool logging (default: false)",
    "DB_FUTURE": "Enable SQLAlchemy 2.0 mode (default: true)",
    "DB_SSL_MODE": "SSL mode (optional)",
    "DB_SSL_CERT": "SSL certificate file path (optional)",
    "DB_SSL_KEY": "SSL key file path (optional)",
    "DB_SSL_CA": "SSL CA certificate file path (optional)",
    
    # Test database variables
    "TEST_DB_HOST": "Test database host (default: same as DB_HOST)",
    "TEST_DB_PORT": "Test database port (default: same as DB_PORT)",
    "TEST_DB_USER": "Test database username (default: same as DB_USER)",
    "TEST_DB_PASSWORD": "Test database password (default: same as DB_PASSWORD)",
    "TEST_DB_NAME": "Test database name (default: rottenstocks_test)",
    "TEST_DB_DRIVER": "Test database driver (default: same as DB_DRIVER)",
    "TEST_DB_ECHO": "Enable test SQL query logging (default: false)",
}