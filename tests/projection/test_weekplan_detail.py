from datetime import date

import pytest

from app.domain.recipes.aggregate import Recipe
from app.domain.recipes.states import RecipeState
from app.domain.shared.themes import Theme
from app.domain.shopping.aggregate import ShoppingList
from app.domain.shopping.entities import ShoppingItem
from app.domain.shopping.value_objects import Quantity
from app.domain.weekplan.aggregate import WeekPlan
from app.projection.weekplan.detail import WeekPlanDetailProjection
from hyperstate.response import ActorContext


TUESDAY = date(2026, 6, 23)
# Slot order seeded by WeekPlan.create: Tue, Wed, Thu, Fri, Sat, Sun, Mon.
SUNDAY_INDEX = 5


def flatten_sections(sections):
    """Recursively flatten GroupSection trees into a flat list of leaf sections."""
    result = []
    for s in sections:
        if s.kind == "group":
            result.extend(flatten_sections(s.sections))
        else:
            result.append(s)
    return result


def _actions(view):
    """Top-level action sections (lifecycle); row actions live inside list items."""
    return [s for s in flatten_sections(view.sections) if s.kind == "action"]


def _dinners_list(view):
    return next(
        s for s in flatten_sections(view.sections)
        if s.kind == "list" and s.title == "Dinners"
    )


@pytest.fixture
def actor():
    return ActorContext(id="cook-1", roles=["parent"])


@pytest.fixture
def recipes():
    return [
        Recipe.create(id="REC-TACO", name="Taco Night", theme=Theme.MEXICAN, prep_minutes=30),
        Recipe.create(
            id="REC-SPAG", name="Spaghetti", theme=Theme.ITALIAN,
            uses_frozen_meat=True, thaw_lead_hours=12, prep_minutes=45,
        ),
        # Archived: must never appear in the picker.
        Recipe(id="REC-OLD", name="Old Dish", theme=Theme.MEXICAN, state=RecipeState.ARCHIVED),
    ]


def planning_plan() -> WeekPlan:
    return WeekPlan.create(TUESDAY)


def decided_planning_plan() -> WeekPlan:
    plan = WeekPlan.create(TUESDAY)
    for slot in plan.slots:
        plan.decide_dinner(slot.date, "REC-TACO")
    return plan


def planned_plan() -> WeekPlan:
    plan = decided_planning_plan()
    plan.finalize()
    return plan


class TestFinalizeCondition:
    def test_finalize_disabled_until_all_decided(self, actor, recipes):
        view = WeekPlanDetailProjection(planning_plan(), recipes, actor).build()
        finalize = next(a for a in _actions(view) if a.key == "finalize")
        assert finalize.condition is not None
        assert finalize.condition.met is False
        assert "7 of 7" in finalize.condition.explain

    def test_finalize_explain_counts_remaining(self, actor, recipes):
        plan = WeekPlan.create(TUESDAY)
        for slot in plan.slots[:5]:  # 5 decided, 2 to go
            plan.decide_dinner(slot.date, "REC-TACO")
        view = WeekPlanDetailProjection(plan, recipes, actor).build()
        finalize = next(a for a in _actions(view) if a.key == "finalize")
        assert finalize.condition.met is False
        assert "2 of 7" in finalize.condition.explain

    def test_finalize_enabled_when_all_decided(self, actor, recipes):
        view = WeekPlanDetailProjection(decided_planning_plan(), recipes, actor).build()
        finalize = next(a for a in _actions(view) if a.key == "finalize")
        assert finalize.condition is None
        assert finalize.style == "primary"
        assert finalize.href == "/weekplans/WP-2026-06-23/finalize"

    def test_finalize_absent_once_planned(self, actor, recipes):
        view = WeekPlanDetailProjection(planned_plan(), recipes, actor).build()
        assert all(a.key != "finalize" for a in _actions(view))


class TestTimelineVisibility:
    def test_no_timeline_while_planning(self, actor, recipes):
        view = WeekPlanDetailProjection(decided_planning_plan(), recipes, actor).build()
        kinds = [s.kind for s in flatten_sections(view.sections)]
        assert "timeline" not in kinds

    def test_timeline_appears_once_planned(self, actor, recipes):
        view = WeekPlanDetailProjection(planned_plan(), recipes, actor).build()
        timelines = [s for s in flatten_sections(view.sections) if s.kind == "timeline"]
        assert len(timelines) == 1
        # All seven nights are Taco Night (30 min prep, no thaw) → 7 cook events.
        assert len(timelines[0].events) == 7


class TestRecipePicker:
    def test_undecided_slot_offers_theme_suggested_picker(self, actor, recipes):
        # Tuesday's theme is MEXICAN, so Taco Night should be suggested first.
        view = WeekPlanDetailProjection(planning_plan(), recipes, actor).build()
        tue_item = _dinners_list(view).items[0]
        decide = next(a for a in tue_item.actions if a.key == "decide-dinner")
        picker = decide.fields[0]
        assert picker.name == "recipe_id"

        values = [o.value for o in picker.options]
        # Every active recipe is selectable; the archived one is excluded.
        assert set(values) == {"REC-TACO", "REC-SPAG"}
        # Theme match is the soft suggestion: it sorts first and is flagged.
        assert values[0] == "REC-TACO"
        assert "Suggested" in picker.options[0].description
        assert "Suggested" not in (picker.options[1].description or "")

    def test_sunday_is_a_free_night(self, actor, recipes):
        view = WeekPlanDetailProjection(planning_plan(), recipes, actor).build()
        sun_item = _dinners_list(view).items[SUNDAY_INDEX]
        assert "Sun" in sun_item.data["day"]
        decide = next(a for a in sun_item.actions if a.key == "decide-dinner")
        picker = decide.fields[0]
        # All recipes offered, none privileged as "Suggested".
        assert {o.value for o in picker.options} == {"REC-TACO", "REC-SPAG"}
        assert all("Suggested" not in (o.description or "") for o in picker.options)

    def test_decided_slot_shows_clear_and_recipe_name(self, actor, recipes):
        plan = WeekPlan.create(TUESDAY)
        plan.decide_dinner(TUESDAY, "REC-TACO")
        view = WeekPlanDetailProjection(plan, recipes, actor).build()
        tue_item = _dinners_list(view).items[0]
        assert {a.key for a in tue_item.actions} == {"clear-dinner"}
        assert tue_item.data["dinner"] == "Taco Night"

    def test_planned_slots_are_locked(self, actor, recipes):
        view = WeekPlanDetailProjection(planned_plan(), recipes, actor).build()
        assert all(item.actions == [] for item in _dinners_list(view).items)


class TestLifecycleActions:
    def test_planning_only_offers_finalize(self, actor, recipes):
        view = WeekPlanDetailProjection(decided_planning_plan(), recipes, actor).build()
        lifecycle = {a.key for a in _actions(view)}
        assert lifecycle == {"finalize"}

    def test_planned_offers_start_shopping_and_reopen(self, actor, recipes):
        view = WeekPlanDetailProjection(planned_plan(), recipes, actor).build()
        keys = {a.key for a in _actions(view)}
        assert "start_shopping" in keys
        assert "reopen" in keys
        assert "finish_shopping" not in keys


class TestShoppingAction:
    def test_no_shopping_action_while_planning(self, actor, recipes):
        view = WeekPlanDetailProjection(decided_planning_plan(), recipes, actor).build()
        keys = {a.key for a in _actions(view)}
        assert "build-shopping-list" not in keys
        assert "view-shopping-list" not in keys

    def test_planned_without_list_offers_build(self, actor, recipes):
        view = WeekPlanDetailProjection(planned_plan(), recipes, actor).build()
        build = next(a for a in _actions(view) if a.key == "build-shopping-list")
        assert build.method == "POST"
        assert build.href == "/shopping/WP-2026-06-23"

    def test_planned_with_list_offers_view_and_rebuild(self, actor, recipes):
        shopping = ShoppingList(
            week_plan_id="WP-2026-06-23",
            items=[ShoppingItem(name="Beef", quantity=Quantity(1.0, "lb"))],
        )
        view = WeekPlanDetailProjection(
            planned_plan(), recipes, actor, shopping_list=shopping
        ).build()
        keys = {a.key for a in _actions(view)}
        assert "view-shopping-list" in keys
        assert "rebuild-shopping-list" in keys
        assert "build-shopping-list" not in keys

        view_action = next(a for a in _actions(view) if a.key == "view-shopping-list")
        assert view_action.method == "GET"
        assert view_action.href == "/shopping/WP-2026-06-23"


class TestContext:
    def test_context_reflects_state(self, actor, recipes):
        view = WeekPlanDetailProjection(planned_plan(), recipes, actor).build()
        assert view.context is not None
        assert view.context.domain == "weekplan"
        assert view.context.state == "planned"

    def test_status_property_badge(self, actor, recipes):
        view = WeekPlanDetailProjection(planning_plan(), recipes, actor).build()
        props = next(s for s in flatten_sections(view.sections) if s.kind == "properties")
        status = next(p for p in props.data if p.key == "status")
        assert status.display == "badge"
        assert status.value == "planning"
