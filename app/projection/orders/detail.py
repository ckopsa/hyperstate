# app/projection/orders/detail.py

from app.domain.orders.aggregate import Order
from app.domain.orders.states import OrderState
from app.hyperstate.response import HyperStateResponse, ViewContext, ActorContext
from app.hyperstate.flash import Flash
from app.hyperstate.nav import NavLink
from app.hyperstate.sections import (
    Section, PropertiesSection, ActionSection, ListSection,
    TimelineSection, TimelineEvent, ActionCondition, ActionAlternative,
    ColumnDef, ListItem,
)
from app.hyperstate.display import PropertyItem
from app.hyperstate.fields import (
    SelectField, TextField, BooleanField, FieldOption, DependsOn,
)


class OrderDetailProjection:
    """Projects an Order aggregate into a HyperState detail view.

    Each method maps to a BDD scenario:
    - _cancel_section() for "pending" returns an active action
    - _cancel_section() for "shipped" returns a disabled action with explanation
    - _cancel_section() for "delivered"/"cancelled" returns None (action doesn't exist)
    """

    def __init__(self, order: Order, actor: ActorContext):
        self.order = order
        self.actor = actor

    def build(self, flash: Flash | None = None) -> HyperStateResponse:
        sections: list[Section] = []

        sections.append(self._properties_section())

        if action := self._shipping_form_section():
            sections.append(action)

        if action := self._cancel_section():
            sections.append(action)

        sections.append(self._line_items_section())
        sections.append(self._timeline_section())

        return HyperStateResponse(
            view="detail",
            title=f"Order #{self.order.id}",
            self_=f"/orders/{self.order.id}",
            context=ViewContext(
                domain="orders",
                aggregate="order",
                state=self.order.state.value,
                actor=self.actor,
            ),
            flash=flash,
            nav=self._nav(),
            sections=sections,
        )

    # ── Section Builders (each maps to aggregate state) ──

    def _properties_section(self) -> PropertiesSection:
        o = self.order
        data = [
            PropertyItem(
                key="status", label="Status",
                value=o.state.value,
                display="badge",
                variant=self._state_variant(),
            ),
            PropertyItem(
                key="total", label="Total",
                value=o.total.display(),
                display="currency", currency=o.total.currency,
            ),
        ]
        if o.placed_at:
            data.append(PropertyItem(
                key="placed_at", label="Placed",
                value=o.placed_at.isoformat(), display="datetime",
            ))
        if o.cancelled_at:
            data.append(PropertyItem(
                key="cancelled_at", label="Cancelled",
                value=o.cancelled_at.isoformat(), display="datetime",
            ))
        if o.shipped_at:
            data.append(PropertyItem(
                key="shipped_at", label="Shipped",
                value=o.shipped_at.isoformat(), display="datetime",
            ))
        return PropertiesSection(title="Order Details", data=data)

    def _cancel_section(self) -> ActionSection | None:
        o = self.order
        match o.state:
            case OrderState.PENDING:
                return ActionSection(
                    key="cancel",
                    label="Cancel Order",
                    description="Cancel this order and initiate a full refund.",
                    method="POST",
                    href=f"/orders/{o.id}/cancel",
                    style="danger",
                    confirm=f"Are you sure? This will refund ${o.total.display():.2f}.",
                )
            case OrderState.SHIPPED:
                return ActionSection(
                    key="cancel",
                    label="Cancel Order",
                    method="POST",
                    href=f"/orders/{o.id}/cancel",
                    style="danger",
                    condition=ActionCondition(
                        met=False,
                        explain="This order has shipped. Cancellation is no longer available.",
                        alternative=ActionAlternative(
                            label="Request a Return",
                            href=f"/orders/{o.id}/return",
                        ),
                    ),
                )
            case _:
                return None  # cancelled, delivered — no cancel action at all

    def _shipping_form_section(self) -> ActionSection | None:
        if self.order.state != OrderState.PENDING:
            return None

        o = self.order
        addr = o.shipping_address

        return ActionSection(
            key="update_shipping",
            label="Update Shipping",
            method="PATCH",
            href=f"/orders/{o.id}",
            reload_href=f"/orders/{o.id}/_form/shipping",
            fields=[
                SelectField(
                    name="country",
                    label="Country",
                    required=True,
                    value=addr.country if addr else "US",
                    options=[
                        FieldOption(value="US", label="United States"),
                        FieldOption(value="CA", label="Canada"),
                        FieldOption(value="MX", label="Mexico"),
                    ],
                ),
                SelectField(
                    name="state",
                    label="State / Province",
                    required=True,
                    value=addr.state if addr else None,
                    depends_on=DependsOn(
                        fields=["country"],
                        behavior="reload_options",
                        options_href="/api/regions?country={country}",
                    ),
                    options=self._current_region_options(addr),
                ),
                TextField(
                    name="street",
                    label="Street Address",
                    required=True,
                    value=addr.street if addr else None,
                ),
                BooleanField(
                    name="expedited",
                    label="Expedited Shipping (+$15.00)",
                    value=o.expedited,
                ),
            ],
        )

    def _line_items_section(self) -> ListSection:
        o = self.order
        return ListSection(
            title="Line Items",
            columns=[
                ColumnDef(key="name", label="Product"),
                ColumnDef(key="qty", label="Qty", align="right"),
                ColumnDef(key="unit_price", label="Unit Price", display="currency", currency="USD", align="right"),
                ColumnDef(key="subtotal", label="Subtotal", display="currency", currency="USD", align="right"),
            ],
            items=[
                ListItem(
                    href=f"/products/{item.product_id}",
                    data={
                        "name": item.product_name,
                        "qty": item.quantity,
                        "unit_price": item.unit_price.display(),
                        "subtotal": item.subtotal.display(),
                    },
                )
                for item in o.line_items
            ],
        )

    def _timeline_section(self) -> TimelineSection:
        o = self.order
        events: list[TimelineEvent] = []
        if o.placed_at:
            events.append(TimelineEvent(timestamp=o.placed_at.isoformat(), label="Order placed"))
        if o.shipped_at:
            events.append(TimelineEvent(timestamp=o.shipped_at.isoformat(), label="Order shipped"))
        if o.cancelled_at:
            events.append(TimelineEvent(timestamp=o.cancelled_at.isoformat(), label="Order cancelled"))
        if o.delivered_at:
            events.append(TimelineEvent(timestamp=o.delivered_at.isoformat(), label="Order delivered"))
        return TimelineSection(title="History", events=events)

    # ── Helpers ───────────────────────────────

    def _state_variant(self) -> str:
        return {
            OrderState.DRAFT: "secondary",
            OrderState.PENDING: "warning",
            OrderState.SHIPPED: "info",
            OrderState.DELIVERED: "success",
            OrderState.CANCELLED: "danger",
        }.get(self.order.state, "secondary")

    def _nav(self) -> list[NavLink]:
        return [
            NavLink(label="All Orders", href="/orders", rel="collection"),
            NavLink(label="Customer", href=f"/customers/{self.order.customer_id}", rel="related"),
        ]

    def _current_region_options(self, addr) -> list[FieldOption]:
        # In practice, this would query the same data the options endpoint uses.
        # Pre-populating avoids a flash of empty dropdown on initial load.
        if addr and addr.country == "US":
            return [
                FieldOption(value="UT", label="Utah"),
                FieldOption(value="CA", label="California"),
                # ... server would include all US states
            ]
        return []
