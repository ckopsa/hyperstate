# app/application/orders/place_order.py

from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.orders.states import InvalidTransition
from app.infrastructure.repositories.order_repo import OrderRepository
from app.hyperstate.response import HyperStateResponse, ActorContext
from app.hyperstate.flash import Flash
from app.projection.orders.detail import OrderDetailProjection
from .cancel_order import OrderNotFound


class PlaceOrder:
    """Use case: finalize a draft order."""

    def __init__(self, session: AsyncSession):
        self.repo = OrderRepository(session)
        self.session = session

    async def execute(self, order_id: str, actor: ActorContext) -> HyperStateResponse:
        order = await self.repo.get(order_id)
        if order is None:
            raise OrderNotFound(order_id)

        try:
            order.place()
        except InvalidTransition:
            return OrderDetailProjection(order, actor).build(
                flash=Flash(
                    type="error",
                    title="Placement Failed",
                    body=f"Cannot place order in '{order.state.value}' state."
                )
            )

        await self.repo.save(order)
        await self.session.commit()

        return OrderDetailProjection(order, actor).build(
            flash=Flash(type="success", title="Order Placed")
        )
