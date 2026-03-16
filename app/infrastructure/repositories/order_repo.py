# app/infrastructure/repositories/order_repo.py

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.orders.aggregate import Order, LineItem
from app.domain.orders.states import OrderState
from app.domain.orders.value_objects import Money, Address
from app.infrastructure.models.order_model import OrderRow, LineItemRow


class OrderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, order_id: str) -> Order | None:
        stmt = (
            select(OrderRow)
            .where(OrderRow.id == order_id)
            .options(selectinload(OrderRow.items))
        )
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return self._to_domain(row)

    async def save(self, order: Order) -> None:
        row = await self.session.get(OrderRow, order.id)
        if row is None:
            row = OrderRow(id=order.id)
            self.session.add(row)

        row.customer_id = order.customer_id
        row.state = order.state.value
        row.expedited = order.expedited
        row.placed_at = order.placed_at
        row.cancelled_at = order.cancelled_at
        row.shipped_at = order.shipped_at
        row.delivered_at = order.delivered_at

        if order.shipping_address:
            row.shipping_street = order.shipping_address.street
            row.shipping_city = order.shipping_address.city
            row.shipping_state = order.shipping_address.state
            row.shipping_country = order.shipping_address.country
            row.shipping_postal = order.shipping_address.postal_code

        # Save line items
        # For simplicity, we'll clear and recreate them or just ensure they are there
        # In a real app, you'd be more careful with identity
        # The relationship is set to cascade="all, delete-orphan"
        
        # Mapping domain line items to ORM models
        current_items = {item.product_id: item for item in row.items}
        new_items = []
        for item in order.line_items:
            new_items.append(
                LineItemRow(
                    product_id=item.product_id,
                    product_name=item.product_name,
                    quantity=item.quantity,
                    unit_price=item.unit_price.amount,
                    currency=item.unit_price.currency
                )
            )
        row.items = new_items

        await self.session.flush()

    def _to_domain(self, row: OrderRow) -> Order:
        address = None
        if row.shipping_street:
            address = Address(
                street=row.shipping_street,
                city=row.shipping_city or "",
                state=row.shipping_state or "",
                country=row.shipping_country or "",
                postal_code=row.shipping_postal or "",
            )

        return Order(
            id=row.id,
            customer_id=row.customer_id,
            state=OrderState(row.state),
            shipping_address=address,
            expedited=row.expedited,
            placed_at=row.placed_at,
            cancelled_at=row.cancelled_at,
            shipped_at=row.shipped_at,
            delivered_at=row.delivered_at,
            line_items=[
                LineItem(
                    product_id=item.product_id,
                    product_name=item.product_name,
                    quantity=item.quantity,
                    unit_price=Money(item.unit_price, item.currency),
                )
                for item in row.items
            ],
        )
