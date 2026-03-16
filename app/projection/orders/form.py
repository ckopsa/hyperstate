# app/projection/orders/form.py

from app.domain.orders.aggregate import Order
from app.hyperstate.response import ActorContext
from app.hyperstate.sections import ActionSection
from app.projection.orders.detail import OrderDetailProjection


class OrderFormProjection:
    """Specialized projection for form-only responses (e.g., reload_form)."""

    def __init__(self, order: Order, actor: ActorContext):
        self.order = order
        self.actor = actor

    def shipping_form(self, current_values: dict | None = None) -> ActionSection:
        """Builds the shipping form, optionally pre-populating with pending client data."""
        # Reuse logic from Detail projection
        detail_projection = OrderDetailProjection(self.order, self.actor)
        form = detail_projection._shipping_form_section()

        if form and current_values:
            for field in form.fields:
                if field.name in current_values:
                    field.value = current_values[field.name]

        return form
