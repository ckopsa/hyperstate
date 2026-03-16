from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, UTC
from decimal import Decimal

from app.domain.shared.aggregate import AggregateRoot
from .states import OrderState, can_transition, next_state, InvalidTransition
from .value_objects import Money, Address
from .entities import LineItem
from .events import DomainEvent, OrderPlaced, OrderCancelled, ShippingUpdated
from .errors import OrderError


@dataclass(kw_only=True)
class Order(AggregateRoot):
    """Aggregate root. All mutations go through methods. All methods enforce invariants."""

    id: str
    customer_id: str
    state: OrderState = OrderState.DRAFT
    line_items: list[LineItem] = field(default_factory=list)
    shipping_address: Address | None = None
    expedited: bool = False
    placed_at: datetime | None = None
    cancelled_at: datetime | None = None
    shipped_at: datetime | None = None
    delivered_at: datetime | None = None

    @property
    def total(self) -> Money:
        if not self.line_items:
            return Money(Decimal("0"), "USD")
        result = Money(Decimal("0"), self.line_items[0].unit_price.currency)
        for item in self.line_items:
            result = result + item.subtotal
        return result

    # ── Commands ──────────────────────────────

    def place(self) -> None:
        """Transition draft → pending."""
        self._transition("place")
        self.placed_at = datetime.now(UTC)
        self._events.append(OrderPlaced(order_id=self.id, total=self.total))

    def cancel(self) -> None:
        """Transition pending → cancelled."""
        self._transition("cancel")
        self.cancelled_at = datetime.now(UTC)
        self._events.append(OrderCancelled(order_id=self.id, total=self.total))

    def ship(self) -> None:
        self._transition("ship")
        self.shipped_at = datetime.now(UTC)

    def deliver(self) -> None:
        self._transition("deliver")
        self.delivered_at = datetime.now(UTC)

    def update_shipping(self, address: Address, expedited: bool = False) -> None:
        if self.state != OrderState.PENDING:
            raise OrderError("Can only update shipping on pending orders.")
        self.shipping_address = address
        self.expedited = expedited
        self._events.append(ShippingUpdated(order_id=self.id))

    # ── Available actions (for projection layer) ──

    def available_actions(self) -> set[str]:
        """What can be done to this order right now?"""
        from .states import TRANSITIONS
        actions = set(TRANSITIONS.get(self.state, {}).keys())
        if self.state == OrderState.PENDING:
            actions.add("update_shipping")
        return actions

    # ── Private ───────────────────────────────

    def _transition(self, action: str) -> None:
        self.state = next_state(self.state, action)
