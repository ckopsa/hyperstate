"""Add recipes and ingredients tables

Revision ID: f3a9d2c6b1e8
Revises: 270b740e907c
Create Date: 2026-06-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a9d2c6b1e8'
down_revision: Union[str, Sequence[str], None] = '270b740e907c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'recipes',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('theme', sa.String(), nullable=False),
        sa.Column('uses_frozen_meat', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column('thaw_lead_hours', sa.Integer(), nullable=True),
        sa.Column('prep_minutes', sa.Integer(), nullable=True),
        sa.Column('state', sa.String(), server_default='active', nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_recipes_theme', 'recipes', ['theme'])
    op.create_index('ix_recipes_state', 'recipes', ['state'])

    op.create_table(
        'ingredients',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('recipe_id', sa.String(), nullable=False),
        sa.Column('position', sa.Integer(), server_default='0', nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('quantity', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_ingredients_recipe_id', 'ingredients', ['recipe_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_ingredients_recipe_id', table_name='ingredients')
    op.drop_table('ingredients')
    op.drop_index('ix_recipes_state', table_name='recipes')
    op.drop_index('ix_recipes_theme', table_name='recipes')
    op.drop_table('recipes')
