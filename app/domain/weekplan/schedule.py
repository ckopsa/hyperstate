"""Pure scheduling service for a week plan.

Given a plan and a lookup of the recipes its slots reference, compute the prep
timeline: when to pull frozen meat out to thaw, and when to start cooking so
dinner lands at each slot's target time. No I/O, no framework — just dates.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Mapping

from app.domain.recipes.aggregate import Recipe
from .aggregate import WeekPlan


class ScheduleEventKind(StrEnum):
    THAW = "thaw"
    COOK_START = "cook_start"


@dataclass(frozen=True)
class ScheduleEvent:
    """A single dated reminder on the week's prep timeline."""

    kind: ScheduleEventKind
    when: datetime
    slot_date: date
    recipe_id: str
    recipe_name: str


def compute_schedule(
    plan: WeekPlan, recipes_by_id: Mapping[str, Recipe]
) -> list[ScheduleEvent]:
    """Build the sorted prep timeline for a plan.

    For every decided slot whose recipe is known:
      * THAW at ``target − thaw_lead_hours`` — only for frozen-meat recipes that
        carry a thaw lead time.
      * COOK_START at ``target − prep_minutes`` — only when prep_minutes is set.

    ``target`` is the slot's date at its ``target_time`` (4:45pm by default).
    Decided slots whose recipe is missing from ``recipes_by_id`` are skipped, as
    are undecided slots. Events are returned in chronological order; the sort is
    stable, so within one instant a slot's THAW precedes its COOK_START.
    """
    events: list[ScheduleEvent] = []
    for slot in plan.slots:
        if slot.recipe_id is None:
            continue
        recipe = recipes_by_id.get(slot.recipe_id)
        if recipe is None:
            continue
        target = datetime.combine(slot.date, slot.target_time)

        if recipe.uses_frozen_meat and recipe.thaw_lead_hours is not None:
            events.append(
                ScheduleEvent(
                    kind=ScheduleEventKind.THAW,
                    when=target - timedelta(hours=recipe.thaw_lead_hours),
                    slot_date=slot.date,
                    recipe_id=recipe.id,
                    recipe_name=recipe.name,
                )
            )

        if recipe.prep_minutes is not None:
            events.append(
                ScheduleEvent(
                    kind=ScheduleEventKind.COOK_START,
                    when=target - timedelta(minutes=recipe.prep_minutes),
                    slot_date=slot.date,
                    recipe_id=recipe.id,
                    recipe_name=recipe.name,
                )
            )

    events.sort(key=lambda e: e.when)
    return events
