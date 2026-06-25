from __future__ import annotations

import re
from dataclasses import dataclass, field

from .states import ItemStatus
from .value_objects import Quantity


@dataclass
class ShoppingItem:
    """One line on a shopping list: an ingredient rolled up across the week.

    A line's identity is its (name, unit) pair — that is what ingredients merge
    on — so ``key`` is a stable slug derived from both, suitable as a web handle
    for the mark actions. ``status`` starts NEEDED and is toggled directly.
    """

    name: str
    quantity: Quantity = field(default_factory=Quantity)
    status: ItemStatus = ItemStatus.NEEDED

    @property
    def key(self) -> str:
        base = f"{self.name} {self.quantity.unit}" if self.quantity.unit else self.name
        slug = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")
        return slug or "item"

    @property
    def merge_key(self) -> tuple[str, str]:
        """The (name, unit) pair, case-folded, that lines combine on."""
        return (self.name.strip().lower(), self.quantity.unit.strip().lower())

    @property
    def label(self) -> str | None:
        """Quantity rendered for display, e.g. ``"2 lb"`` or ``None``."""
        return self.quantity.label
