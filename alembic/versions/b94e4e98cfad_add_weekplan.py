"""Add week_plans and dinner_slots tables

Revision ID: b94e4e98cfad
Revises: f3a9d2c6b1e8
Create Date: 2026-06-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b94e4e98cfad'
down_revision: Union[str, Sequence[str], None] = 'f3a9d2c6b1e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'week_plans',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('week_start', sa.Date(), nullable=False),
        sa.Column('state', sa.String(), server_default='planning', nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_week_plans_week_start', 'week_plans', ['week_start'], unique=True)
    op.create_index('ix_week_plans_state', 'week_plans', ['state'])

    op.create_table(
        'dinner_slots',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('week_plan_id', sa.String(), nullable=False),
        sa.Column('slot_date', sa.Date(), nullable=False),
        sa.Column('weekday', sa.Integer(), nullable=False),
        sa.Column('theme', sa.String(), nullable=False),
        sa.Column('recipe_id', sa.String(), nullable=True),
        sa.Column('target_time', sa.Time(), nullable=False),
        sa.ForeignKeyConstraint(['week_plan_id'], ['week_plans.id'], ),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_dinner_slots_week_plan_id', 'dinner_slots', ['week_plan_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_dinner_slots_week_plan_id', table_name='dinner_slots')
    op.drop_table('dinner_slots')
    op.drop_index('ix_week_plans_state', table_name='week_plans')
    op.drop_index('ix_week_plans_week_start', table_name='week_plans')
    op.drop_table('week_plans')
