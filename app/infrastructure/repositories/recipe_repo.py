from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.recipes.aggregate import Recipe
from app.domain.recipes.entities import Ingredient
from app.domain.recipes.states import RecipeState
from app.domain.shared.themes import Theme
from app.infrastructure.models.recipe_model import RecipeRow, IngredientRow


class RecipeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, recipe_id: str) -> Recipe | None:
        stmt = (
            select(RecipeRow)
            .where(RecipeRow.id == recipe_id)
            .options(selectinload(RecipeRow.ingredients))
        )
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return self._to_domain(row)

    async def list_all(self, state: str | None = None) -> list[Recipe]:
        stmt = select(RecipeRow).options(selectinload(RecipeRow.ingredients))
        if state:
            stmt = stmt.where(RecipeRow.state == state)
        stmt = stmt.order_by(RecipeRow.name)
        rows = (await self.session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]

    async def list_by_theme(self, theme: Theme, state: str | None = None) -> list[Recipe]:
        stmt = (
            select(RecipeRow)
            .where(RecipeRow.theme == theme.value)
            .options(selectinload(RecipeRow.ingredients))
        )
        if state:
            stmt = stmt.where(RecipeRow.state == state)
        stmt = stmt.order_by(RecipeRow.name)
        rows = (await self.session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]

    async def save(self, recipe: Recipe) -> None:
        stmt = (
            select(RecipeRow)
            .where(RecipeRow.id == recipe.id)
            .options(selectinload(RecipeRow.ingredients))
        )
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row is None:
            row = RecipeRow(id=recipe.id)
            self.session.add(row)
        row.name = recipe.name
        row.theme = recipe.theme.value
        row.uses_frozen_meat = recipe.uses_frozen_meat
        row.thaw_lead_hours = recipe.thaw_lead_hours
        row.prep_minutes = recipe.prep_minutes
        row.state = recipe.state.value

        # Ingredients are value objects with no identity: replace the whole
        # collection so add/remove/reorder round-trip deterministically. The
        # delete-orphan cascade removes the previous rows on flush.
        row.ingredients = [
            IngredientRow(
                recipe_id=recipe.id,
                position=i,
                name=ingredient.name,
                quantity=ingredient.quantity,
            )
            for i, ingredient in enumerate(recipe.ingredients)
        ]

        await self.session.flush()

    def _to_domain(self, row: RecipeRow) -> Recipe:
        ingredients = [
            Ingredient(name=r.name, quantity=r.quantity)
            for r in sorted(row.ingredients, key=lambda x: x.position)
        ]
        return Recipe(
            id=row.id,
            name=row.name,
            theme=Theme(row.theme),
            uses_frozen_meat=row.uses_frozen_meat,
            thaw_lead_hours=row.thaw_lead_hours,
            prep_minutes=row.prep_minutes,
            state=RecipeState(row.state),
            ingredients=ingredients,
        )
