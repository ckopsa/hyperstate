from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.recipes.aggregate import Recipe
from app.domain.recipes.errors import RecipeNotFound
from app.domain.shared.themes import Theme
from app.infrastructure.repositories.recipe_repo import RecipeRepository


class EditRecipe:
    def __init__(self, session: AsyncSession):
        self.repo = RecipeRepository(session)
        self.session = session

    async def execute(
        self,
        recipe_id: str,
        name: str,
        theme: Theme,
        uses_frozen_meat: bool = False,
        thaw_lead_hours: int | None = None,
        prep_minutes: int | None = None,
    ) -> Recipe:
        recipe = await self.repo.get(recipe_id)
        if recipe is None:
            raise RecipeNotFound(recipe_id)
        recipe.edit(
            name=name,
            theme=theme,
            uses_frozen_meat=uses_frozen_meat,
            thaw_lead_hours=thaw_lead_hours,
            prep_minutes=prep_minutes,
        )
        await self.repo.save(recipe)
        await self.session.commit()
        return recipe
