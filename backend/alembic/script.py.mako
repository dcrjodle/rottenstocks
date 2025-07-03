"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, Sequence[str], None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """Upgrade database schema.
    
    Apply migration changes to upgrade the database schema.
    This function should contain all forward migration logic.
    
    Safety checks:
    - Always use transactions for schema changes
    - Test migrations on a copy of production data first
    - Ensure all constraints can be satisfied
    - Consider impact on large tables
    """
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Downgrade database schema.
    
    Revert migration changes to downgrade the database schema.
    This function should contain all backward migration logic.
    
    Safety checks:
    - Ensure downgrade doesn't cause data loss
    - Test downgrade path thoroughly
    - Consider if data migration is needed
    - Document any irreversible changes
    """
    ${downgrades if downgrades else "pass"}
