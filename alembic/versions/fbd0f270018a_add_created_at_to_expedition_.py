"""add created_at to expedition_participants

Revision ID: fbd0f270018a
Revises: a1db1fd306c3
Create Date: 2025-09-15 18:25:37.812661

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fbd0f270018a'
down_revision: Union[str, Sequence[str], None] = 'a1db1fd306c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('expedition_participants', sa.Column('created_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('expedition_participants', 'created_at')
