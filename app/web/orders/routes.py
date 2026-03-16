# app/web/orders/routes.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.hyperstate.response import HyperStateResponse, ActorContext
from app.infrastructure.database import get_db
from app.infrastructure.repositories.order_repo import OrderRepository
from app.projection.orders.detail import OrderDetailProjection
from app.application.orders.cancel_order import CancelOrder
from app.web.deps import get_current_actor

from pydantic import BaseModel
from app.hyperstate.sections import ActionSection
from app.projection.orders.form import OrderFormProjection

from app.projection.orders.list import OrderListProjection

router = APIRouter(prefix="/orders", tags=["orders"])

MEDIA_TYPE = "application/vnd.hyperstate+json"


@router.get(
    "",
    response_model=HyperStateResponse,
    responses={200: {"content": {MEDIA_TYPE: {}}}},
)
async def list_orders(
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.infrastructure.models.order_model import OrderRow
    from app.infrastructure.repositories.order_repo import OrderRepository
    
    stmt = select(OrderRow).options(selectinload(OrderRow.items))
    rows = (await db.execute(stmt)).scalars().all()
    
    repo = OrderRepository(db)
    orders = [repo._to_domain(row) for row in rows]
    
    return OrderListProjection(orders, actor).build()


class ShippingFormReload(BaseModel):
    """The client sends current field values; server returns rebuilt form."""
    _reload: bool = True
    country: str | None = None
    state: str | None = None
    street: str | None = None
    expedited: bool = False


@router.post(
    "/{order_id}/_form/shipping",
    response_model=ActionSection,
)
async def reload_shipping_form(
    order_id: str,
    body: ShippingFormReload,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """Returns a rebuilt action section with fields adjusted to current values."""
    repo = OrderRepository(db)
    order = await repo.get(order_id)
    if order is None:
        raise HTTPException(status_code=404)

    projection = OrderFormProjection(order, actor)
    return projection.shipping_form(current_values=body.model_dump())


@router.get(
    "/{order_id}",
    response_model=HyperStateResponse,
    responses={200: {"content": {MEDIA_TYPE: {}}}},
)
async def get_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    repo = OrderRepository(db)
    order = await repo.get(order_id)
    if order is None:
        raise HTTPException(status_code=404)
    return OrderDetailProjection(order, actor).build()


@router.post(
    "/{order_id}/cancel",
    response_model=HyperStateResponse,
    responses={200: {"content": {MEDIA_TYPE: {}}}},
)
async def cancel_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    use_case = CancelOrder(db)
    return await use_case.execute(order_id, actor)
