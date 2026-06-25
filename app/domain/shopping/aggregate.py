from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Mapping

from app.domain.shared.aggregate import AggregateRoot
from .states import ItemStatus, ON_BUY_LIST
from .entities import ShoppingItem
from .errors import ShoppingError
from .events import (
    ShoppingListBuilt,
    ItemMarkedHave,
    ItemMarkedNeeded,
    ItemMarkedBought,
)
from .value_objects import Quantity

if TYPE_CHECKING:  # imported for typing only — the shopping domain stays decoupled
    from app.domain.weekplan.aggregate import WeekPlan
    from app.domain.recipes.aggregate import Recipe


@dataclass(kw_only=True)
class ShoppingList(AggregateRoot):
    """Aggregate root for one week's shopping, keyed one-per-WeekPlan.

    A list is *built from* a finalized plan: every decided slot's recipe
    contributes its ingredients, and lines sharing the same (name, unit) are
    merged into one, summing numeric amounts. Each line is then toggled through
    NEEDED / HAVE / BOUGHT as the cook shops.
    """

    week_plan_id: str
    items: list[ShoppingItem] = field(default_factory=list)

    @property
    def id(self) -> str:
        """The list's identity is its week plan — exposed as ``id`` for ergonomic
        parity with the other aggregates."""
        return self.week_plan_id

    @classmethod
    def build_from(
        cls, plan: "WeekPlan", recipes_by_id: "Mapping[str, Recipe]"
    ) -> "ShoppingList":
        """Roll up ingredients across the plan's decided slots into one list.

        ``recipes_by_id`` maps recipe id → Recipe; a decided slot whose recipe
        is absent from the mapping is skipped rather than failing the build. A
        recipe used in two slots contributes its ingredients twice (you cook it
        twice), so quantities scale accordingly.
        """
        merged: dict[tuple[str, str], ShoppingItem] = {}
        for slot in plan.slots:
            recipe_id = slot.recipe_id
            if recipe_id is None:  # an undecided slot contributes nothing
                continue
            recipe = recipes_by_id.get(recipe_id)
            if recipe is None:
                continue
            for ingredient in recipe.ingredients:
                quantity = Quantity.parse(ingredient.quantity)
                key = (ingredient.name.strip().lower(), quantity.unit.strip().lower())
                if key in merged:
                    existing = merged[key]
                    existing.quantity = existing.quantity.added_to(quantity)
                else:
                    merged[key] = ShoppingItem(
                        name=ingredient.name.strip(),
                        quantity=quantity,
                        status=ItemStatus.NEEDED,
                    )
        # dict preserves first-seen order, which is the order ingredients appear
        # across the week — a stable, readable list order.
        items = list(merged.values())
        shopping_list = cls(week_plan_id=plan.id, items=items)
        shopping_list._events.append(
            ShoppingListBuilt(week_plan_id=plan.id, item_count=len(items))
        )
        return shopping_list

    # -- item status toggles --------------------------------------------------

    def mark_have(self, item_key: str) -> None:
        """Drop a line off the buy list — we already have it on hand."""
        self.item_for(item_key).status = ItemStatus.HAVE
        self._events.append(ItemMarkedHave(week_plan_id=self.week_plan_id, item_key=item_key))

    def mark_needed(self, item_key: str) -> None:
        """Put a line back on the buy list."""
        self.item_for(item_key).status = ItemStatus.NEEDED
        self._events.append(ItemMarkedNeeded(week_plan_id=self.week_plan_id, item_key=item_key))

    def mark_bought(self, item_key: str) -> None:
        """Check a line off — purchased on this trip."""
        self.item_for(item_key).status = ItemStatus.BOUGHT
        self._events.append(ItemMarkedBought(week_plan_id=self.week_plan_id, item_key=item_key))

    # -- queries --------------------------------------------------------------

    def item_for(self, item_key: str) -> ShoppingItem:
        for item in self.items:
            if item.key == item_key:
                return item
        raise ShoppingError(f"No shopping item '{item_key}' on this list.")

    def with_status(self, status: ItemStatus) -> list[ShoppingItem]:
        return [item for item in self.items if item.status == status]

    def to_buy(self) -> list[ShoppingItem]:
        """The lines still outstanding — NEEDED, not yet HAVE or BOUGHT."""
        return [item for item in self.items if item.status in ON_BUY_LIST]

    def is_empty(self) -> bool:
        return not self.items
