from dataclasses import dataclass


@dataclass(frozen=True)
class ShoppingListBuilt:
    week_plan_id: str
    item_count: int


@dataclass(frozen=True)
class ItemMarkedHave:
    week_plan_id: str
    item_key: str


@dataclass(frozen=True)
class ItemMarkedNeeded:
    week_plan_id: str
    item_key: str


@dataclass(frozen=True)
class ItemMarkedBought:
    week_plan_id: str
    item_key: str
