"""Add curriculum tables

Revision ID: 270b740e907c
Revises:
Create Date: 2026-03-16 22:39:58.132660

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '270b740e907c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'curricula',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('grade_level', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'curriculum_items',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('curriculum_id', sa.String(), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('subject_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('day_offset', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['curriculum_id'], ['curricula.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'curriculum_item_resources',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('item_id', sa.String(), nullable=False),
        sa.Column('resource_type', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['item_id'], ['curriculum_items.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('curriculum_item_resources')
    op.drop_table('curriculum_items')
    op.drop_table('curricula')
