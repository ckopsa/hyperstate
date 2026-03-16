from __future__ import annotations
from dataclasses import dataclass
from .value_objects import Money


@dataclass
class LineItem:
    product_id: str
    product_name: str
    quantity: int
    unit_price: Money

    @property
    def subtotal(self) -> Money:
        return Money(self.unit_price.amount * self.quantity, self.unit_price.currency)


@dataclass
class ShippingInfo:
    address: Address
    expedited: bool = False
