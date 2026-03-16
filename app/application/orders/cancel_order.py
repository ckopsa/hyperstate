# app/application/orders/cancel_order.py

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.orders.errors import OrderError
from app.domain.orders.states import InvalidTransition
from app.infrastructure.repositories.order_repo import OrderRepository
from app.hyperstate.response import HyperStateResponse, ActorContext
from app.hyperstate.flash import Flash
from app.projection.orders.detail import OrderDetailProjection


class CancelOrder:
    """Use case: attempt to cancel an order. Returns the next HyperState view."""

    def __init__(self, session: AsyncSession):
        self.repo = OrderRepository(session)
        self.session = session

    async def execute(self, order_id: str, actor: ActorContext) -> HyperStateResponse:
        order = await self.repo.get(order_id)
        if order is None:
            raise OrderNotFound(order_id)

        try:
            order.cancel()
        except InvalidTransition:
            # Domain rejected the command — return current view with error flash
            return OrderDetailProjection(order, actor).build(
                flash=Flash(
                    type="error",
                    title="Cannot Cancel",
                    body=f"Order is in '{order.state.value}' state and cannot be cancelled.",
                )
            )

        await self.repo.save(order)
        await self.session.commit()

        # Return the new view with success flash
        return OrderDetailProjection(order, actor).build(
            flash=Flash(
                type="success",
                title="Order Cancelled",
                body=f"A refund of ${order.total.display():.2f} will be processed within 3-5 business days.",
            )
        )


class OrderNotFound(Exception):
    def __init__(self, order_id: str):
        self.order_id = order_id
        super().__init__(f"Order {order_id} not found")
