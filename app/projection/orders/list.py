# app/projection/orders/list.py

from typing import Iterable
from app.domain.orders.aggregate import Order
from app.hyperstate.response import HyperStateResponse, ViewContext, ActorContext
from app.hyperstate.sections import ListSection, ColumnDef, ListItem


class OrderListProjection:
    """Projects a collection of orders into a HyperState list view."""

    def __init__(self, orders: Iterable[Order], actor: ActorContext):
        self.orders = orders
        self.actor = actor

    def build(self) -> HyperStateResponse:
        return HyperStateResponse(
            view="list",
            title="Order History",
            self_="/orders",
            context=ViewContext(
                domain="orders",
                aggregate="orders",
                state="collection",
                actor=self.actor,
            ),
            sections=[
                ListSection(
                    title="All Orders",
                    columns=[
                        ColumnDef(key="id", label="Order ID"),
                        ColumnDef(key="status", label="Status", display="badge"),
                        ColumnDef(key="total", label="Total", display="currency"),
                    ],
                    items=[
                        ListItem(
                            href=f"/orders/{o.id}",
                            data={
                                "id": o.id,
                                "status": o.state.value,
                                "total": o.total.display(),
                            }
                        )
                        for o in self.orders
                    ]
                )
            ]
        )
