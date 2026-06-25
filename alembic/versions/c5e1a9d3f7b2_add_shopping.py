"""Add shopping_lists and shopping_items tables

Revision ID: c5e1a9d3f7b2
Revises: b94e4e98cfad
Create Date: 2026-06-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5e1a9d3f7b2'
down_revision: Union[str, Sequence[str], None] = 'b94e4e98cfad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'shopping_lists',
        sa.Column('week_plan_id', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['week_plan_id'], ['week_plans.id'], ),
        sa.PrimaryKeyConstraint('week_plan_id'),
    )

    op.create_table(
        'shopping_items',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('week_plan_id', sa.String(), nullable=False),
        sa.Column('position', sa.Integer(), server_default='0', nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=True),
        sa.Column('unit', sa.String(), server_default='', nullable=False),
        sa.Column('status', sa.String(), server_default='needed', nullable=False),
        sa.ForeignKeyConstraint(['week_plan_id'], ['shopping_lists.week_plan_id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_shopping_items_week_plan_id', 'shopping_items', ['week_plan_id'])
    op.create_index('ix_shopping_items_status', 'shopping_items', ['status'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_shopping_items_status', table_name='shopping_items')
    op.drop_index('ix_shopping_items_week_plan_id', table_name='shopping_items')
    op.drop_table('shopping_items')
    op.drop_table('shopping_lists')
