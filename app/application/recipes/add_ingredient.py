from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.recipes.aggregate import Recipe
from app.domain.recipes.errors import RecipeNotFound
from app.infrastructure.repositories.recipe_repo import RecipeRepository


class AddIngredient:
    def __init__(self, session: AsyncSession):
        self.repo = RecipeRepository(session)
        self.session = session

    async def execute(
        self,
        recipe_id: str,
        name: str,
        quantity: str | None = None,
    ) -> Recipe:
        recipe = await self.repo.get(recipe_id)
        if recipe is None:
            raise RecipeNotFound(recipe_id)
        recipe.add_ingredient(name=name, quantity=quantity)
        await self.repo.save(recipe)
        await self.session.commit()
        return recipe
