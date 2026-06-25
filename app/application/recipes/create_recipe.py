import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.recipes.aggregate import Recipe
from app.domain.shared.themes import Theme
from app.infrastructure.repositories.recipe_repo import RecipeRepository


class CreateRecipe:
    def __init__(self, session: AsyncSession):
        self.repo = RecipeRepository(session)
        self.session = session

    async def execute(
        self,
        name: str,
        theme: Theme,
        uses_frozen_meat: bool = False,
        thaw_lead_hours: int | None = None,
        prep_minutes: int | None = None,
    ) -> Recipe:
        recipe_id = f"REC-{uuid.uuid4().hex[:6].upper()}"
        recipe = Recipe.create(
            id=recipe_id,
            name=name,
            theme=theme,
            uses_frozen_meat=uses_frozen_meat,
            thaw_lead_hours=thaw_lead_hours,
            prep_minutes=prep_minutes,
        )
        await self.repo.save(recipe)
        await self.session.commit()
        return recipe
