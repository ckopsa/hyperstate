from datetime import date, time

import pytest

from app.domain.weekplan.aggregate import WeekPlan
from app.domain.weekplan.errors import WeekPlanError
from app.domain.weekplan.events import (
    WeekPlanCreated,
    WeekPlanFinalized,
    ShoppingStarted,
    ShoppingFinished,
    WeekPlanCompleted,
    WeekPlanReopened,
)
from app.domain.weekplan.states import WeekPlanState, InvalidTransition
from app.domain.shared.themes import Theme


TUESDAY = date(2026, 6, 23)      # a Tuesday
WEDNESDAY = date(2026, 6, 24)    # not a Tuesday

# (date, weekday, theme) for each slot a plan starting TUESDAY should seed.
EXPECTED_DAYS = [
    (date(2026, 6, 23), 1, Theme.MEXICAN),    # Tue
    (date(2026, 6, 24), 2, Theme.AMERICAN),   # Wed
    (date(2026, 6, 25), 3, Theme.ASIAN),      # Thu
    (date(2026, 6, 26), 4, Theme.PIZZA),      # Fri
    (date(2026, 6, 27), 5, Theme.BBQ),        # Sat
    (date(2026, 6, 28), 6, Theme.ROTATING),   # Sun
    (date(2026, 6, 29), 0, Theme.ITALIAN),    # Mon
]


def make_plan(**overrides) -> WeekPlan:
    params = dict(week_start=TUESDAY)
    params.update(overrides)
    return WeekPlan.create(**params)


def decide_all(plan: WeekPlan) -> None:
    for slot in plan.slots:
        plan.decide_dinner(slot.date, f"REC-{slot.date.isoformat()}")


class TestCreate:
    def test_rejects_non_tuesday(self):
        with pytest.raises(WeekPlanError, match="Tuesday"):
            WeekPlan.create(WEDNESDAY)

    def test_accepts_tuesday_with_planning_state(self):
        plan = make_plan()
        assert plan.week_start == TUESDAY
        assert plan.state == WeekPlanState.PLANNING

    def test_derives_id_from_week_start(self):
        assert make_plan().id == "WP-2026-06-23"

    def test_accepts_explicit_id(self):
        assert WeekPlan.create(TUESDAY, id="WP-CUSTOM").id == "WP-CUSTOM"

    def test_seeds_seven_slots(self):
        assert len(make_plan().slots) == 7

    def test_slots_are_tuesday_through_monday_with_themes(self):
        got = [(s.date, s.weekday, s.theme) for s in make_plan().slots]
        assert got == EXPECTED_DAYS

    def test_slots_start_undecided(self):
        plan = make_plan()
        assert all(s.recipe_id is None for s in plan.slots)
        assert plan.is_fully_decided() is False

    def test_slots_have_default_target_time(self):
        assert all(s.target_time == time(16, 45) for s in make_plan().slots)

    def test_emits_created_event_then_drains(self):
        plan = make_plan()
        assert plan.collect_events() == [
            WeekPlanCreated(week_plan_id="WP-2026-06-23", week_start=TUESDAY)
        ]
        assert plan.collect_events() == []


class TestDecideDinner:
    def test_sets_recipe_on_matching_slot_only(self):
        plan = make_plan()
        plan.decide_dinner(date(2026, 6, 25), "REC-ASIAN")
        assert plan.slot_for(date(2026, 6, 25)).recipe_id == "REC-ASIAN"
        assert plan.slot_for(TUESDAY).recipe_id is None

    def test_unknown_date_raises(self):
        with pytest.raises(WeekPlanError, match="No dinner slot"):
            make_plan().decide_dinner(date(2026, 7, 1), "REC-X")

    @pytest.mark.parametrize("bad", ["", "   "])
    def test_empty_recipe_raises(self, bad):
        with pytest.raises(WeekPlanError):
            make_plan().decide_dinner(TUESDAY, bad)

    def test_redecide_overwrites(self):
        plan = make_plan()
        plan.decide_dinner(TUESDAY, "REC-A")
        plan.decide_dinner(TUESDAY, "REC-B")
        assert plan.slot_for(TUESDAY).recipe_id == "REC-B"

    def test_cannot_decide_after_finalize(self):
        plan = make_plan()
        decide_all(plan)
        plan.finalize()
        with pytest.raises(WeekPlanError, match="planned"):
            plan.decide_dinner(TUESDAY, "REC-NEW")


class TestClearDinner:
    def test_clears_slot(self):
        plan = make_plan()
        plan.decide_dinner(TUESDAY, "REC-A")
        plan.clear_dinner(TUESDAY)
        assert plan.slot_for(TUESDAY).recipe_id is None

    def test_cannot_clear_after_finalize(self):
        plan = make_plan()
        decide_all(plan)
        plan.finalize()
        with pytest.raises(WeekPlanError):
            plan.clear_dinner(TUESDAY)


class TestFinalize:
    def test_raises_while_any_undecided(self):
        plan = make_plan()
        with pytest.raises(WeekPlanError, match="undecided"):
            plan.finalize()
        assert plan.state == WeekPlanState.PLANNING

    def test_raises_with_one_slot_left(self):
        plan = make_plan()
        for slot in plan.slots[:-1]:
            plan.decide_dinner(slot.date, "REC-X")
        with pytest.raises(WeekPlanError):
            plan.finalize()

    def test_transitions_to_planned_when_all_decided(self):
        plan = make_plan()
        decide_all(plan)
        plan.finalize()
        assert plan.state == WeekPlanState.PLANNED
        assert plan.is_fully_decided() is True

    def test_emits_finalized_event(self):
        plan = make_plan()
        decide_all(plan)
        plan.collect_events()
        plan.finalize()
        assert plan.collect_events() == [WeekPlanFinalized(week_plan_id=plan.id)]

    def test_cannot_finalize_twice(self):
        plan = make_plan()
        decide_all(plan)
        plan.finalize()
        with pytest.raises(InvalidTransition):
            plan.finalize()


class TestTransitions:
    def _planned(self) -> WeekPlan:
        plan = make_plan()
        decide_all(plan)
        plan.finalize()
        return plan

    def test_full_forward_path(self):
        plan = self._planned()
        plan.start_shopping()
        assert plan.state == WeekPlanState.SHOPPING
        plan.finish_shopping()
        assert plan.state == WeekPlanState.ACTIVE
        plan.complete()
        assert plan.state == WeekPlanState.COMPLETED

    def test_each_transition_emits_event(self):
        plan = self._planned()
        plan.collect_events()
        plan.start_shopping()
        plan.finish_shopping()
        plan.complete()
        assert plan.collect_events() == [
            ShoppingStarted(week_plan_id=plan.id),
            ShoppingFinished(week_plan_id=plan.id),
            WeekPlanCompleted(week_plan_id=plan.id),
        ]

    @pytest.mark.parametrize("action", ["start_shopping", "finish_shopping", "complete"])
    def test_cannot_skip_ahead_from_planning(self, action):
        plan = make_plan()
        with pytest.raises(InvalidTransition):
            getattr(plan, action)()

    def test_available_actions_per_state(self):
        plan = make_plan()
        assert plan.available_actions() == {"finalize"}
        decide_all(plan)
        plan.finalize()
        assert plan.available_actions() == {"start_shopping", "reopen"}
        plan.start_shopping()
        assert plan.available_actions() == {"finish_shopping", "reopen"}
        plan.finish_shopping()
        assert plan.available_actions() == {"complete", "reopen"}
        plan.complete()
        assert plan.available_actions() == {"reopen"}


class TestReopen:
    @pytest.mark.parametrize(
        "advance",
        [
            ["finalize"],
            ["finalize", "start_shopping"],
            ["finalize", "start_shopping", "finish_shopping"],
            ["finalize", "start_shopping", "finish_shopping", "complete"],
        ],
    )
    def test_reopen_returns_to_planning_from_any_later_state(self, advance):
        plan = make_plan()
        decide_all(plan)
        for step in advance:
            getattr(plan, step)()
        plan.reopen()
        assert plan.state == WeekPlanState.PLANNING

    def test_reopen_emits_event(self):
        plan = make_plan()
        decide_all(plan)
        plan.finalize()
        plan.collect_events()
        plan.reopen()
        assert plan.collect_events() == [WeekPlanReopened(week_plan_id=plan.id)]

    def test_cannot_reopen_while_planning(self):
        with pytest.raises(InvalidTransition):
            make_plan().reopen()

    def test_reopen_allows_editing_again(self):
        plan = make_plan()
        decide_all(plan)
        plan.finalize()
        plan.reopen()
        plan.clear_dinner(TUESDAY)
        assert plan.slot_for(TUESDAY).recipe_id is None
