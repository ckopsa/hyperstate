from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.recipes.aggregate import Recipe
from app.domain.recipes.errors import RecipeNotFound
from app.infrastructure.repositories.recipe_repo import RecipeRepository


class TransitionRecipe:
    """Generic use case for recipe state transitions (archive, restore)."""

    def __init__(self, session: AsyncSession):
        self.repo = RecipeRepository(session)
        self.session = session

    async def execute(self, recipe_id: str, action: str) -> Recipe:
        recipe = await self.repo.get(recipe_id)
        if recipe is None:
            raise RecipeNotFound(recipe_id)

        if action == "archive":
            recipe.archive()
        elif action == "restore":
            recipe.restore()
        else:
            raise ValueError(f"Unknown action: {action}")

        await self.repo.save(recipe)
        await self.session.commit()
        return recipe
