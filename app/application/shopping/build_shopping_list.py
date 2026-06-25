from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.shopping.aggregate import ShoppingList
from app.domain.shopping.errors import ShoppingError
from app.domain.weekplan.errors import WeekPlanNotFound
from app.domain.weekplan.states import WeekPlanState
from app.infrastructure.repositories.recipe_repo import RecipeRepository
from app.infrastructure.repositories.shopping_repo import ShoppingListRepository
from app.infrastructure.repositories.weekplan_repo import WeekPlanRepository


class BuildShoppingList:
    """Roll up a finalized week's recipes into a single shopping list.

    The list is built from the plan's decided slots, so the plan must be
    finalized (PLANNED or later) — there is nothing to shop for while dinners
    are still being decided. Re-running rebuilds from the current plan: the
    repository replaces the list's items wholesale, so any prior have/bought
    toggles are reset.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.plans = WeekPlanRepository(session)
        self.recipes = RecipeRepository(session)
        self.lists = ShoppingListRepository(session)

    async def execute(self, week_plan_id: str) -> ShoppingList:
        plan = await self.plans.get(week_plan_id)
        if plan is None:
            raise WeekPlanNotFound(week_plan_id)
        if plan.state == WeekPlanState.PLANNING:
            raise ShoppingError(
                "Finalize the plan before building its shopping list."
            )
        recipes = await self.recipes.list_all()
        shopping_list = ShoppingList.build_from(plan, {r.id: r for r in recipes})
        await self.lists.save(shopping_list)
        await self.session.commit()
        return shopping_list
