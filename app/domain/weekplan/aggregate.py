from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from app.domain.shared.aggregate import AggregateRoot
from app.domain.shared.themes import theme_for
from .states import WeekPlanState, next_state, TRANSITIONS
from .errors import WeekPlanError
from .events import (
    WeekPlanCreated,
    WeekPlanFinalized,
    ShoppingStarted,
    ShoppingFinished,
    WeekPlanCompleted,
    WeekPlanReopened,
)
from .entities import DinnerSlot

TUESDAY = 1  # date.weekday(): Monday == 0 ... Sunday == 6
DAYS_IN_PLAN = 7


@dataclass(kw_only=True)
class WeekPlan(AggregateRoot):
    """Aggregate root for one week of dinners, keyed by a Tuesday week_start.

    A plan owns exactly seven DinnerSlot children, one per day from the Tuesday
    ``week_start`` through the following Monday. Each slot carries the weekday's
    suggested Theme; dinners are decided per slot while PLANNING, then the plan
    is finalized once every slot has a recipe.
    """

    id: str
    week_start: date
    state: WeekPlanState = WeekPlanState.PLANNING
    slots: list[DinnerSlot] = field(default_factory=list)

    @classmethod
    def create(cls, week_start: date, id: str | None = None) -> "WeekPlan":
        """Create a plan with seven themed, undecided slots (Tue → Mon).

        ``id`` is derived from the week_start when not supplied, since a plan is
        keyed one-per-week by its Tuesday start.
        """
        if week_start.weekday() != TUESDAY:
            raise WeekPlanError("A week plan must start on a Tuesday.")
        plan_id = id or f"WP-{week_start.isoformat()}"
        slots: list[DinnerSlot] = []
        for offset in range(DAYS_IN_PLAN):
            day = week_start + timedelta(days=offset)
            slots.append(DinnerSlot(date=day, weekday=day.weekday(), theme=theme_for(day)))
        plan = cls(id=plan_id, week_start=week_start, slots=slots)
        plan._events.append(WeekPlanCreated(week_plan_id=plan_id, week_start=week_start))
        return plan

    # -- dinner decisions (only while PLANNING) -------------------------------

    def decide_dinner(self, slot_date: date, recipe_id: str) -> None:
        if not recipe_id or not recipe_id.strip():
            raise WeekPlanError("A recipe is required to decide a dinner.")
        self._require_planning("decide a dinner")
        self.slot_for(slot_date).recipe_id = recipe_id

    def clear_dinner(self, slot_date: date) -> None:
        self._require_planning("clear a dinner")
        self.slot_for(slot_date).recipe_id = None

    # -- workflow transitions -------------------------------------------------

    def finalize(self) -> None:
        """Transition PLANNING → PLANNED once every slot has a recipe."""
        undecided = [s for s in self.slots if not s.is_decided]
        if undecided:
            raise WeekPlanError(
                f"Cannot finalize: {len(undecided)} of {len(self.slots)} dinners are undecided."
            )
        self._transition("finalize")
        self._events.append(WeekPlanFinalized(week_plan_id=self.id))

    def start_shopping(self) -> None:
        """Transition PLANNED → SHOPPING."""
        self._transition("start_shopping")
        self._events.append(ShoppingStarted(week_plan_id=self.id))

    def finish_shopping(self) -> None:
        """Transition SHOPPING → ACTIVE."""
        self._transition("finish_shopping")
        self._events.append(ShoppingFinished(week_plan_id=self.id))

    def complete(self) -> None:
        """Transition ACTIVE → COMPLETED."""
        self._transition("complete")
        self._events.append(WeekPlanCompleted(week_plan_id=self.id))

    def reopen(self) -> None:
        """Return a finalized-or-later plan to PLANNING so dinners can change."""
        self._transition("reopen")
        self._events.append(WeekPlanReopened(week_plan_id=self.id))

    # -- queries --------------------------------------------------------------

    def slot_for(self, slot_date: date) -> DinnerSlot:
        for slot in self.slots:
            if slot.date == slot_date:
                return slot
        raise WeekPlanError(f"No dinner slot for {slot_date.isoformat()} in this week.")

    def is_fully_decided(self) -> bool:
        return all(s.is_decided for s in self.slots)

    def available_actions(self) -> set[str]:
        return set(TRANSITIONS.get(self.state, {}).keys())

    # -- internals ------------------------------------------------------------

    def _require_planning(self, action: str) -> None:
        if self.state != WeekPlanState.PLANNING:
            raise WeekPlanError(f"Cannot {action} once the plan is {self.state}.")

    def _transition(self, action: str) -> None:
        self.state = next_state(self.state, action)
