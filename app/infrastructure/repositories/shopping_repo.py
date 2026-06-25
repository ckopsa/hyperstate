from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.shopping.aggregate import ShoppingList
from app.domain.shopping.entities import ShoppingItem
from app.domain.shopping.states import ItemStatus
from app.domain.shopping.value_objects import Quantity
from app.infrastructure.models.shopping_model import ShoppingListRow, ShoppingItemRow


class ShoppingListRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, week_plan_id: str) -> ShoppingList | None:
        stmt = (
            select(ShoppingListRow)
            .where(ShoppingListRow.week_plan_id == week_plan_id)
            .options(selectinload(ShoppingListRow.items))
        )
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        return self._to_domain(row) if row is not None else None

    async def save(self, shopping_list: ShoppingList) -> None:
        stmt = (
            select(ShoppingListRow)
            .where(ShoppingListRow.week_plan_id == shopping_list.week_plan_id)
            .options(selectinload(ShoppingListRow.items))
        )
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row is None:
            row = ShoppingListRow(week_plan_id=shopping_list.week_plan_id)
            self.session.add(row)

        # Items are merged value lines with no identity: replace the whole
        # collection so build/mark round-trip deterministically. The
        # delete-orphan cascade removes the previous rows on flush.
        row.items = [
            ShoppingItemRow(
                week_plan_id=shopping_list.week_plan_id,
                position=i,
                name=item.name,
                amount=item.quantity.amount,
                unit=item.quantity.unit,
                status=item.status.value,
            )
            for i, item in enumerate(shopping_list.items)
        ]

        await self.session.flush()

    def _to_domain(self, row: ShoppingListRow) -> ShoppingList:
        items = [
            ShoppingItem(
                name=r.name,
                quantity=Quantity(amount=r.amount, unit=r.unit),
                status=ItemStatus(r.status),
            )
            for r in sorted(row.items, key=lambda x: x.position)
        ]
        return ShoppingList(week_plan_id=row.week_plan_id, items=items)
