# app/application/orders/update_shipping.py

from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.orders.errors import OrderError
from app.domain.orders.value_objects import Address
from app.infrastructure.repositories.order_repo import OrderRepository
from app.hyperstate.response import HyperStateResponse, ActorContext
from app.hyperstate.flash import Flash
from app.projection.orders.detail import OrderDetailProjection
from .cancel_order import OrderNotFound


class UpdateShipping:
    """Use case: update shipping address and options."""

    def __init__(self, session: AsyncSession):
        self.repo = OrderRepository(session)
        self.session = session

    async def execute(
        self, 
        order_id: str, 
        address: Address, 
        expedited: bool, 
        actor: ActorContext
    ) -> HyperStateResponse:
        order = await self.repo.get(order_id)
        if order is None:
            raise OrderNotFound(order_id)

        try:
            order.update_shipping(address, expedited)
        except OrderError as e:
            return OrderDetailProjection(order, actor).build(
                flash=Flash(type="error", title="Update Failed", body=str(e))
            )

        await self.repo.save(order)
        await self.session.commit()

        return OrderDetailProjection(order, actor).build(
            flash=Flash(type="success", title="Shipping Updated")
        )
