from datetime import date

import pytest

from app.domain.recipes.aggregate import Recipe
from app.domain.shared.themes import Theme
from app.domain.shopping.aggregate import ShoppingList
from app.domain.shopping.entities import ShoppingItem
from app.domain.shopping.errors import ShoppingError
from app.domain.shopping.events import (
    ShoppingListBuilt,
    ItemMarkedHave,
    ItemMarkedNeeded,
    ItemMarkedBought,
)
from app.domain.shopping.states import ItemStatus
from app.domain.shopping.value_objects import Quantity
from app.domain.weekplan.aggregate import WeekPlan

TUESDAY = date(2026, 6, 23)  # WeekPlan requires a Tuesday week_start


def make_recipe(rid: str, name: str, ingredients: list[tuple[str, str | None]]) -> Recipe:
    recipe = Recipe.create(id=rid, name=name, theme=Theme.AMERICAN)
    for ing_name, qty in ingredients:
        recipe.add_ingredient(ing_name, qty)
    return recipe


def plan_with(recipe_ids: list[str]) -> WeekPlan:
    """A plan whose leading slots are decided with the given recipe ids in order."""
    plan = WeekPlan.create(TUESDAY)
    for slot, rid in zip(plan.slots, recipe_ids):
        plan.decide_dinner(slot.date, rid)
    return plan


def item_named(shopping_list: ShoppingList, name: str) -> ShoppingItem:
    matches = [i for i in shopping_list.items if i.name == name]
    assert matches, f"no item named {name!r} in {[i.name for i in shopping_list.items]}"
    return matches[0]


class TestQuantityParse:
    @pytest.mark.parametrize(
        "raw, amount, unit",
        [
            ("1 lb", 1.0, "lb"),
            ("24 oz", 24.0, "oz"),
            ("2 cups", 2.0, "cups"),
            ("1", 1.0, ""),
            ("8", 8.0, ""),
            ("1.5 lb", 1.5, "lb"),
            ("1/2 cup", 0.5, "cup"),
            ("1 head", 1.0, "head"),
            ("  3   tbsp  ", 3.0, "tbsp"),
        ],
    )
    def test_parses_numeric_quantities(self, raw, amount, unit):
        assert Quantity.parse(raw) == Quantity(amount=amount, unit=unit)

    @pytest.mark.parametrize("raw", ["a pinch", "to taste", "some"])
    def test_keeps_unitless_text_when_no_leading_number(self, raw):
        assert Quantity.parse(raw) == Quantity(amount=None, unit=raw)

    @pytest.mark.parametrize("raw", [None, "", "   "])
    def test_blank_is_empty_quantity(self, raw):
        assert Quantity.parse(raw) == Quantity(amount=None, unit="")


class TestQuantityLabel:
    @pytest.mark.parametrize(
        "quantity, label",
        [
            (Quantity(2.0, "lb"), "2 lb"),
            (Quantity(24.0, "oz"), "24 oz"),
            (Quantity(2.0, ""), "2"),
            (Quantity(0.5, "cup"), "0.5 cup"),
            (Quantity(1.5, "lb"), "1.5 lb"),
            (Quantity(None, "a pinch"), "a pinch"),
            (Quantity(None, ""), None),
        ],
    )
    def test_label(self, quantity, label):
        assert quantity.label == label


class TestQuantityAddedTo:
    def test_sums_two_numeric_amounts(self):
        assert Quantity(1.0, "lb").added_to(Quantity(1.0, "lb")) == Quantity(2.0, "lb")

    def test_numeric_plus_unspecified_keeps_the_number(self):
        assert Quantity(1.0, "lb").added_to(Quantity(None, "lb")) == Quantity(1.0, "lb")
        assert Quantity(None, "lb").added_to(Quantity(2.0, "lb")) == Quantity(2.0, "lb")

    def test_two_unspecified_stay_unspecified(self):
        assert Quantity(None, "").added_to(Quantity(None, "")) == Quantity(None, "")


class TestShoppingItemKey:
    def test_slug_includes_unit(self):
        assert ShoppingItem(name="Ground beef", quantity=Quantity(2.0, "lb")).key == "ground-beef-lb"

    def test_slug_without_unit(self):
        assert ShoppingItem(name="Onion", quantity=Quantity(2.0, "")).key == "onion"

    def test_distinct_units_yield_distinct_keys(self):
        a = ShoppingItem(name="Milk", quantity=Quantity(1.0, "cup"))
        b = ShoppingItem(name="Milk", quantity=Quantity(None, ""))
        assert a.key != b.key


class TestBuildFrom:
    def test_merges_duplicate_ingredient_across_recipes(self):
        # Two different dinners both call for onions — they combine into one line.
        r1 = make_recipe("R1", "Soup", [("Onion", "1")])
        r2 = make_recipe("R2", "Stew", [("Onion", "1")])
        plan = plan_with(["R1", "R2"])

        shopping = ShoppingList.build_from(plan, {"R1": r1, "R2": r2})

        onion = item_named(shopping, "Onion")
        assert onion.quantity == Quantity(2.0, "")
        assert onion.label == "2"
        assert len([i for i in shopping.items if i.name == "Onion"]) == 1

    def test_sums_quantities_with_a_shared_unit(self):
        r1 = make_recipe("R1", "Spaghetti", [("Ground beef", "1 lb")])
        r2 = make_recipe("R2", "Tacos", [("Ground beef", "1 lb")])
        plan = plan_with(["R1", "R2"])

        shopping = ShoppingList.build_from(plan, {"R1": r1, "R2": r2})

        assert item_named(shopping, "Ground beef").quantity == Quantity(2.0, "lb")

    def test_keeps_ingredients_with_different_units_separate(self):
        r1 = make_recipe("R1", "A", [("Onion", "1")])
        r2 = make_recipe("R2", "B", [("Onion", "2 cups")])
        plan = plan_with(["R1", "R2"])

        shopping = ShoppingList.build_from(plan, {"R1": r1, "R2": r2})

        units = sorted(i.quantity.unit for i in shopping.items if i.name == "Onion")
        assert units == ["", "cups"]

    def test_items_start_needed(self):
        r1 = make_recipe("R1", "A", [("Salt", "1 tsp"), ("Pepper", None)])
        plan = plan_with(["R1"])

        shopping = ShoppingList.build_from(plan, {"R1": r1})

        assert {i.status for i in shopping.items} == {ItemStatus.NEEDED}

    def test_ignores_undecided_slots(self):
        # Only the first slot is decided; the rest of the week is left blank.
        r1 = make_recipe("R1", "A", [("Flour", "2 cups")])
        plan = plan_with(["R1"])

        shopping = ShoppingList.build_from(plan, {"R1": r1})

        assert [i.name for i in shopping.items] == ["Flour"]

    def test_skips_decided_slot_whose_recipe_is_missing(self):
        r1 = make_recipe("R1", "A", [("Egg", "2")])
        plan = plan_with(["R1", "GONE"])  # second slot references an unknown recipe

        shopping = ShoppingList.build_from(plan, {"R1": r1})

        assert [i.name for i in shopping.items] == ["Egg"]

    def test_same_recipe_in_two_slots_doubles_quantities(self):
        r1 = make_recipe("R1", "A", [("Rice", "1 cup")])
        plan = plan_with(["R1", "R1"])

        shopping = ShoppingList.build_from(plan, {"R1": r1})

        assert item_named(shopping, "Rice").quantity == Quantity(2.0, "cup")

    def test_merges_unspecified_quantities_into_one_line(self):
        r1 = make_recipe("R1", "A", [("Salt", "a pinch")])
        r2 = make_recipe("R2", "B", [("Salt", "a pinch")])
        plan = plan_with(["R1", "R2"])

        shopping = ShoppingList.build_from(plan, {"R1": r1, "R2": r2})

        salt = item_named(shopping, "Salt")
        assert salt.quantity == Quantity(None, "a pinch")

    def test_keys_off_the_plan_id(self):
        r1 = make_recipe("R1", "A", [("Egg", "1")])
        plan = plan_with(["R1"])

        shopping = ShoppingList.build_from(plan, {"R1": r1})

        assert shopping.week_plan_id == "WP-2026-06-23"
        assert shopping.id == "WP-2026-06-23"

    def test_empty_when_no_slots_decided(self):
        plan = WeekPlan.create(TUESDAY)  # nothing decided

        shopping = ShoppingList.build_from(plan, {})

        assert shopping.items == []
        assert shopping.is_empty()

    def test_preserves_first_seen_order(self):
        r1 = make_recipe("R1", "A", [("Bun", "8"), ("Beef", "1 lb")])
        r2 = make_recipe("R2", "B", [("Beef", "1 lb"), ("Cheese", "2 cups")])
        plan = plan_with(["R1", "R2"])

        shopping = ShoppingList.build_from(plan, {"R1": r1, "R2": r2})

        assert [i.name for i in shopping.items] == ["Bun", "Beef", "Cheese"]

    def test_emits_shopping_list_built_event(self):
        r1 = make_recipe("R1", "A", [("Egg", "1"), ("Milk", "1 cup")])
        plan = plan_with(["R1"])

        shopping = ShoppingList.build_from(plan, {"R1": r1})

        assert shopping.collect_events() == [
            ShoppingListBuilt(week_plan_id="WP-2026-06-23", item_count=2)
        ]


class TestItemStatuses:
    """Items move freely between the three statuses; only NEEDED stays to-buy."""

    def _list(self) -> ShoppingList:
        r1 = make_recipe("R1", "A", [("Onion", "2"), ("Beef", "1 lb")])
        plan = plan_with(["R1"])
        shopping = ShoppingList.build_from(plan, {"R1": r1})
        shopping.collect_events()  # drain ShoppingListBuilt
        return shopping

    def test_everything_starts_on_the_buy_list(self):
        shopping = self._list()
        assert {i.name for i in shopping.to_buy()} == {"Onion", "Beef"}

    def test_mark_have_removes_from_buy_list(self):
        shopping = self._list()
        onion = item_named(shopping, "Onion")

        shopping.mark_have(onion.key)

        assert onion.status == ItemStatus.HAVE
        assert "Onion" not in {i.name for i in shopping.to_buy()}

    def test_mark_bought_checks_it_off(self):
        shopping = self._list()
        beef = item_named(shopping, "Beef")

        shopping.mark_bought(beef.key)

        assert beef.status == ItemStatus.BOUGHT
        assert "Beef" not in {i.name for i in shopping.to_buy()}

    def test_mark_needed_puts_it_back(self):
        shopping = self._list()
        onion = item_named(shopping, "Onion")
        shopping.mark_have(onion.key)

        shopping.mark_needed(onion.key)

        assert onion.status == ItemStatus.NEEDED
        assert "Onion" in {i.name for i in shopping.to_buy()}

    def test_with_status_filters(self):
        shopping = self._list()
        onion = item_named(shopping, "Onion")
        shopping.mark_have(onion.key)
        assert shopping.with_status(ItemStatus.HAVE) == [onion]
        assert {i.name for i in shopping.with_status(ItemStatus.NEEDED)} == {"Beef"}

    def test_mark_methods_emit_events(self):
        shopping = self._list()
        key = item_named(shopping, "Onion").key

        shopping.mark_have(key)
        shopping.mark_bought(key)
        shopping.mark_needed(key)

        assert shopping.collect_events() == [
            ItemMarkedHave(week_plan_id="WP-2026-06-23", item_key=key),
            ItemMarkedBought(week_plan_id="WP-2026-06-23", item_key=key),
            ItemMarkedNeeded(week_plan_id="WP-2026-06-23", item_key=key),
        ]

    def test_marking_an_unknown_item_raises(self):
        shopping = self._list()
        with pytest.raises(ShoppingError, match="No shopping item"):
            shopping.mark_have("does-not-exist")

    def test_item_for_returns_the_matching_line(self):
        shopping = self._list()
        beef = item_named(shopping, "Beef")
        assert shopping.item_for(beef.key) is beef
