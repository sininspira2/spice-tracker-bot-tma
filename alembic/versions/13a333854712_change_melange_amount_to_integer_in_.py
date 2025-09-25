"""Change melange_amount to Integer in deposits table

Revision ID: 13a333854712
Revises: a1db1fd306c3
Create Date: 2025-09-17 02:59:24.531099

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '13a333854712'
down_revision: Union[str, Sequence[str], None] = 'a1db1fd306c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.alter_column('deposits', 'melange_amount',
                   existing_type=sa.FLOAT(),
                   type_=sa.Integer(),
                   existing_nullable=True,
                   postgresql_using='melange_amount::integer')
    else:
        with op.batch_alter_table('deposits', schema=None) as batch_op:
            batch_op.alter_column('melange_amount',
                   existing_type=sa.FLOAT(),
                   type_=sa.Integer(),
                   existing_nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.alter_column('deposits', 'melange_amount',
                   existing_type=sa.Integer(),
                   type_=sa.FLOAT(),
                   existing_nullable=True)
    else:
        with op.batch_alter_table('deposits', schema=None) as batch_op:
            batch_op.alter_column('melange_amount',
                   existing_type=sa.Integer(),
                   type_=sa.FLOAT(),
                   existing_nullable=True)
