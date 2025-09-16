"""add melange and conversion rate to deposits
Revision ID: a1db1fd306c3
Revises: a6fe5e68863a
Create Date: 2025-09-15 17:33:59.602297
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
# revision identifiers, used by Alembic.
revision: str = 'a1db1fd306c3'
down_revision: Union[str, Sequence[str], None] = 'a6fe5e68863a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('deposits', sa.Column('melange_amount', sa.Float(), nullable=True))
    op.add_column('deposits', sa.Column('conversion_rate', sa.Float(), nullable=True))
def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('deposits', 'conversion_rate')
    op.drop_column('deposits', 'melange_amount')
