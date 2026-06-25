from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time

from app.domain.shared.themes import Theme

# Every dinner targets the same wall-clock serving time unless overridden.
DEFAULT_TARGET_TIME = time(16, 45)


@dataclass
class DinnerSlot:
    """One night's dinner within a WeekPlan.

    A slot has identity-by-date within its plan: there is exactly one slot per
    calendar day. ``theme`` is the soft suggestion derived from the weekday, but
    any recipe may be assigned. ``recipe_id`` is ``None`` until a dinner is
    decided. ``target_time`` is the time dinner should be ready (4:45pm).
    """

    date: date
    weekday: int
    theme: Theme
    recipe_id: str | None = None
    target_time: time = DEFAULT_TARGET_TIME

    @property
    def is_decided(self) -> bool:
        return self.recipe_id is not None
