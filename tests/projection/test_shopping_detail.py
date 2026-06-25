from datetime import date

import pytest

from app.domain.shopping.aggregate import ShoppingList
from app.domain.shopping.entities import ShoppingItem
from app.domain.shopping.states import ItemStatus
from app.domain.shopping.value_objects import Quantity
from app.projection.shopping.detail import ShoppingListDetailProjection
from hyperstate.response import ActorContext

WEEK_PLAN_ID = "WP-2026-06-23"


def flatten_sections(sections):
    """Recursively flatten GroupSection trees into a flat list of leaf sections."""
    result = []
    for s in sections:
        if s.kind == "group":
            result.extend(flatten_sections(s.sections))
        else:
            result.append(s)
    return result


def _list(view, title):
    return next(
        s for s in flatten_sections(view.sections)
        if s.kind == "list" and s.title == title
    )


@pytest.fixture
def actor():
    return ActorContext(id="cook-1", roles=["parent"])


def mixed_list() -> ShoppingList:
    """A list spanning all three statuses, for grouping/toggle assertions."""
    return ShoppingList(
        week_plan_id=WEEK_PLAN_ID,
        items=[
            ShoppingItem(name="Ground beef", quantity=Quantity(2.0, "lb"), status=ItemStatus.NEEDED),
            ShoppingItem(name="Onion", quantity=Quantity(3.0, ""), status=ItemStatus.NEEDED),
            ShoppingItem(name="Salt", quantity=Quantity(None, "a pinch"), status=ItemStatus.HAVE),
            ShoppingItem(name="Tortillas", quantity=Quantity(8.0, ""), status=ItemStatus.BOUGHT),
        ],
    )


class TestGrouping:
    def test_items_grouped_by_status(self, actor):
        view = ShoppingListDetailProjection(mixed_list(), actor).build()
        titles = [s.title for s in flatten_sections(view.sections) if s.kind == "list"]
        assert titles == ["To Buy", "Already Have", "Bought"]

        assert [i.data["item"] for i in _list(view, "To Buy").items] == ["Ground beef", "Onion"]
        assert [i.data["item"] for i in _list(view, "Already Have").items] == ["Salt"]
        assert [i.data["item"] for i in _list(view, "Bought").items] == ["Tortillas"]

    def test_empty_status_group_is_omitted(self, actor):
        only_needed = ShoppingList(
            week_plan_id=WEEK_PLAN_ID,
            items=[ShoppingItem(name="Egg", quantity=Quantity(2.0, ""))],
        )
        view = ShoppingListDetailProjection(only_needed, actor).build()
        titles = [s.title for s in flatten_sections(view.sections) if s.kind == "list"]
        assert titles == ["To Buy"]

    def test_quantity_label_rendered(self, actor):
        view = ShoppingListDetailProjection(mixed_list(), actor).build()
        rows = {i.data["item"]: i.data["quantity"] for i in _list(view, "To Buy").items}
        assert rows == {"Ground beef": "2 lb", "Onion": "3"}


class TestItemToggles:
    """Each line offers exactly the two statuses it is not currently in."""

    def test_needed_item_offers_have_and_bought(self, actor):
        view = ShoppingListDetailProjection(mixed_list(), actor).build()
        beef = _list(view, "To Buy").items[0]
        actions = {a.key: a for a in beef.actions}
        assert set(actions) == {"mark-have", "mark-bought"}
        assert actions["mark-have"].method == "POST"
        assert actions["mark-have"].href == f"/shopping/{WEEK_PLAN_ID}/items/ground-beef-lb/have"
        assert actions["mark-bought"].href == f"/shopping/{WEEK_PLAN_ID}/items/ground-beef-lb/bought"

    def test_have_item_offers_needed_and_bought(self, actor):
        view = ShoppingListDetailProjection(mixed_list(), actor).build()
        salt = _list(view, "Already Have").items[0]
        actions = {a.key: a for a in salt.actions}
        assert set(actions) == {"mark-needed", "mark-bought"}
        # key derives from name + unit, slugified
        assert actions["mark-needed"].href == f"/shopping/{WEEK_PLAN_ID}/items/salt-a-pinch/needed"

    def test_bought_item_offers_needed_and_have(self, actor):
        view = ShoppingListDetailProjection(mixed_list(), actor).build()
        tortillas = _list(view, "Bought").items[0]
        actions = {a.key: a for a in tortillas.actions}
        assert set(actions) == {"mark-needed", "mark-have"}
        assert actions["mark-have"].href == f"/shopping/{WEEK_PLAN_ID}/items/tortillas/have"

    def test_no_item_offers_a_toggle_to_its_own_status(self, actor):
        view = ShoppingListDetailProjection(mixed_list(), actor).build()
        needed_item = _list(view, "To Buy").items[0]
        assert "mark-needed" not in {a.key for a in needed_item.actions}


class TestSummary:
    def test_summary_counts_each_status(self, actor):
        view = ShoppingListDetailProjection(mixed_list(), actor).build()
        summary = next(s for s in flatten_sections(view.sections) if s.kind == "summary")
        counts = {i.label: i.value for i in summary.items}
        assert counts == {"To Buy": 2, "Have": 1, "Bought": 1}


class TestEmptyState:
    def test_empty_list_shows_empty_section_and_no_lists(self, actor):
        empty = ShoppingList(week_plan_id=WEEK_PLAN_ID, items=[])
        view = ShoppingListDetailProjection(empty, actor).build()
        kinds = [s.kind for s in flatten_sections(view.sections)]
        assert "empty" in kinds
        assert "list" not in kinds
        assert "summary" not in kinds


class TestContextAndChrome:
    def test_context_identifies_the_shopping_aggregate(self, actor):
        view = ShoppingListDetailProjection(mixed_list(), actor).build()
        assert view.context is not None
        assert view.context.domain == "shopping"
        assert view.context.aggregate == "shopping_list"

    def test_state_is_shopping_while_items_remain_to_buy(self, actor):
        view = ShoppingListDetailProjection(mixed_list(), actor).build()
        assert view.context.state == "shopping"

    def test_state_is_complete_when_nothing_left_to_buy(self, actor):
        done = ShoppingList(
            week_plan_id=WEEK_PLAN_ID,
            items=[
                ShoppingItem(name="A", quantity=Quantity(1.0, ""), status=ItemStatus.HAVE),
                ShoppingItem(name="B", quantity=Quantity(1.0, ""), status=ItemStatus.BOUGHT),
            ],
        )
        view = ShoppingListDetailProjection(done, actor).build()
        assert view.context.state == "complete"

    def test_state_is_empty_for_an_empty_list(self, actor):
        view = ShoppingListDetailProjection(
            ShoppingList(week_plan_id=WEEK_PLAN_ID, items=[]), actor
        ).build()
        assert view.context.state == "empty"

    def test_title_includes_week_start_when_provided(self, actor):
        view = ShoppingListDetailProjection(
            mixed_list(), actor, week_start=date(2026, 6, 23)
        ).build()
        assert "2026-06-23" in view.title

    def test_self_and_back_nav_point_at_the_week_plan(self, actor):
        view = ShoppingListDetailProjection(mixed_list(), actor).build()
        assert view.self_ == f"/shopping/{WEEK_PLAN_ID}"
        assert any(n.href == f"/weekplans/{WEEK_PLAN_ID}" for n in view.nav)
