from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.shopping.aggregate import ShoppingList
from app.domain.shopping.errors import ShoppingError, ShoppingListNotFound
from app.infrastructure.repositories.shopping_repo import ShoppingListRepository

# Each action maps 1:1 to a ``mark_<action>`` method on the aggregate, so the
# use case stays generic over the three free toggles.
_ACTIONS = {"have", "needed", "bought"}


class MarkItem:
    """Toggle one shopping-list line between needed / have / bought."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.lists = ShoppingListRepository(session)

    async def execute(
        self, week_plan_id: str, item_key: str, action: str
    ) -> ShoppingList:
        if action not in _ACTIONS:
            raise ShoppingError(f"Unknown shopping item action: {action}")
        shopping_list = await self.lists.get(week_plan_id)
        if shopping_list is None:
            raise ShoppingListNotFound(week_plan_id)
        getattr(shopping_list, f"mark_{action}")(item_key)
        await self.lists.save(shopping_list)
        await self.session.commit()
        return shopping_list
