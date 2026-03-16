from dataclasses import dataclass
from .value_objects import Money


@dataclass(frozen=True)
class DomainEvent:
    pass


@dataclass(frozen=True)
class OrderPlaced(DomainEvent):
    order_id: str
    total: Money


@dataclass(frozen=True)
class OrderCancelled(DomainEvent):
    order_id: str
    total: Money


@dataclass(frozen=True)
class ShippingUpdated(DomainEvent):
    order_id: str
