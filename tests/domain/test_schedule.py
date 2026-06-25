from datetime import date, datetime

from app.domain.recipes.aggregate import Recipe
from app.domain.shared.themes import Theme
from app.domain.weekplan.aggregate import WeekPlan
from app.domain.weekplan.schedule import (
    compute_schedule,
    ScheduleEvent,
    ScheduleEventKind,
)


TUESDAY = date(2026, 6, 23)
WEDNESDAY = date(2026, 6, 24)


def make_plan() -> WeekPlan:
    return WeekPlan.create(TUESDAY)


def frozen_recipe(id="REC-FROZEN", thaw=12, prep=45) -> Recipe:
    return Recipe.create(
        id=id,
        name="Frozen Stew",
        theme=Theme.MEXICAN,
        uses_frozen_meat=True,
        thaw_lead_hours=thaw,
        prep_minutes=prep,
    )


def fresh_recipe(id="REC-FRESH", prep=20) -> Recipe:
    return Recipe.create(
        id=id,
        name="Quick Tacos",
        theme=Theme.AMERICAN,
        uses_frozen_meat=False,
        prep_minutes=prep,
    )


class TestCookStart:
    def test_cook_start_is_prep_minutes_before_target(self):
        plan = make_plan()
        plan.decide_dinner(TUESDAY, "REC-FRESH")
        events = compute_schedule(plan, {"REC-FRESH": fresh_recipe(prep=20)})
        assert events == [
            ScheduleEvent(
                kind=ScheduleEventKind.COOK_START,
                when=datetime(2026, 6, 23, 16, 25),
                slot_date=TUESDAY,
                recipe_id="REC-FRESH",
                recipe_name="Quick Tacos",
            )
        ]

    def test_no_cook_start_when_prep_minutes_missing(self):
        plan = make_plan()
        plan.decide_dinner(TUESDAY, "REC-NOPREP")
        recipe = Recipe.create(id="REC-NOPREP", name="Leftovers", theme=Theme.MEXICAN)
        assert compute_schedule(plan, {"REC-NOPREP": recipe}) == []


class TestThaw:
    def test_frozen_recipe_yields_thaw_then_cook(self):
        plan = make_plan()
        plan.decide_dinner(TUESDAY, "REC-FROZEN")
        events = compute_schedule(plan, {"REC-FROZEN": frozen_recipe(thaw=12, prep=45)})
        assert events == [
            ScheduleEvent(
                kind=ScheduleEventKind.THAW,
                when=datetime(2026, 6, 23, 4, 45),  # 16:45 − 12h
                slot_date=TUESDAY,
                recipe_id="REC-FROZEN",
                recipe_name="Frozen Stew",
            ),
            ScheduleEvent(
                kind=ScheduleEventKind.COOK_START,
                when=datetime(2026, 6, 23, 16, 0),  # 16:45 − 45m
                slot_date=TUESDAY,
                recipe_id="REC-FROZEN",
                recipe_name="Frozen Stew",
            ),
        ]

    def test_thaw_can_cross_into_a_previous_day(self):
        plan = make_plan()
        plan.decide_dinner(TUESDAY, "REC-FROZEN")
        events = compute_schedule(plan, {"REC-FROZEN": frozen_recipe(thaw=24, prep=30)})
        thaw = next(e for e in events if e.kind == ScheduleEventKind.THAW)
        assert thaw.when == datetime(2026, 6, 22, 16, 45)  # 16:45 − 24h

    def test_non_frozen_has_no_thaw(self):
        plan = make_plan()
        plan.decide_dinner(TUESDAY, "REC-FRESH")
        events = compute_schedule(plan, {"REC-FRESH": fresh_recipe()})
        assert all(e.kind != ScheduleEventKind.THAW for e in events)

    def test_frozen_without_thaw_hours_has_no_thaw(self):
        # Defensive guard: an (invariant-violating) frozen recipe with no thaw
        # lead time produces no thaw event rather than crashing.
        plan = make_plan()
        plan.decide_dinner(TUESDAY, "REC-X")
        recipe = Recipe(
            id="REC-X",
            name="Odd",
            theme=Theme.MEXICAN,
            uses_frozen_meat=True,
            thaw_lead_hours=None,
            prep_minutes=10,
        )
        events = compute_schedule(plan, {"REC-X": recipe})
        assert all(e.kind != ScheduleEventKind.THAW for e in events)


class TestSelection:
    def test_only_decided_slots_contribute(self):
        plan = make_plan()
        plan.decide_dinner(TUESDAY, "REC-FRESH")  # one of seven decided
        events = compute_schedule(plan, {"REC-FRESH": fresh_recipe()})
        assert {e.slot_date for e in events} == {TUESDAY}

    def test_unknown_recipe_is_skipped(self):
        plan = make_plan()
        plan.decide_dinner(TUESDAY, "REC-MISSING")
        assert compute_schedule(plan, {}) == []

    def test_empty_plan_yields_no_events(self):
        assert compute_schedule(make_plan(), {}) == []

    def test_events_sorted_chronologically(self):
        plan = make_plan()
        plan.decide_dinner(TUESDAY, "REC-FROZEN")
        plan.decide_dinner(WEDNESDAY, "REC-FRESH")
        recipes = {"REC-FROZEN": frozen_recipe(), "REC-FRESH": fresh_recipe()}
        whens = [e.when for e in compute_schedule(plan, recipes)]
        assert whens == sorted(whens)
        assert len(whens) == 3  # Tue: thaw + cook, Wed: cook
