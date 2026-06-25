from dataclasses import dataclass


@dataclass(frozen=True)
class BuildShoppingList:
    week_plan_id: str


@dataclass(frozen=True)
class MarkItemHave:
    week_plan_id: str
    item_key: str


@dataclass(frozen=True)
class MarkItemNeeded:
    week_plan_id: str
    item_key: str


@dataclass(frozen=True)
class MarkItemBought:
    week_plan_id: str
    item_key: str
