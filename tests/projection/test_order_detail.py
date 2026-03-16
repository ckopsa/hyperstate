import pytest
from decimal import Decimal
from datetime import datetime, UTC

from app.domain.orders.aggregate import Order, LineItem
from app.domain.orders.states import OrderState
from app.domain.orders.value_objects import Money
from app.hyperstate.response import ActorContext
from app.projection.orders.detail import OrderDetailProjection


@pytest.fixture
def actor():
    return ActorContext(id="user-7", roles=["manager"])


@pytest.fixture
def pending_order():
    return Order(
        id="42",
        customer_id="7",
        state=OrderState.PENDING,
        placed_at=datetime(2026, 3, 12, tzinfo=UTC),
        line_items=[
            LineItem(
                product_id="811",
                product_name="Blue Widget",
                quantity=2,
                unit_price=Money(Decimal("47.25")),
            ),
        ],
    )


class TestPendingOrderProjection:
    def test_includes_cancel_action(self, pending_order, actor):
        view = OrderDetailProjection(pending_order, actor).build()
        actions = [s for s in view.sections if s.kind == "action"]
        cancel = next((a for a in actions if a.key == "cancel"), None)

        assert cancel is not None
        assert cancel.condition is None
        assert cancel.style == "danger"
        assert "refund" in cancel.confirm.lower()

    def test_includes_shipping_form(self, pending_order, actor):
        view = OrderDetailProjection(pending_order, actor).build()
        actions = [s for s in view.sections if s.kind == "action"]
        shipping = next((a for a in actions if a.key == "update_shipping"), None)

        assert shipping is not None
        assert len(shipping.fields) == 4
        field_names = {f.name for f in shipping.fields}
        assert field_names == {"country", "state", "street", "expedited"}
