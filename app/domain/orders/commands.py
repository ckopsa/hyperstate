from dataclasses import dataclass
from .value_objects import Address


@dataclass(frozen=True)
class PlaceOrder:
    order_id: str
    customer_id: str


@dataclass(frozen=True)
class CancelOrder:
    order_id: str


@dataclass(frozen=True)
class UpdateShipping:
    order_id: str
    address: Address
    expedited: bool = False
