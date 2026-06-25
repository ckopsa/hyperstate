import pytest

from app.domain.recipes.aggregate import Recipe
from app.domain.recipes.entities import Ingredient
from app.domain.recipes.errors import RecipeError
from app.domain.recipes.events import (
    RecipeCreated,
    RecipeEdited,
    RecipeArchived,
    RecipeRestored,
)
from app.domain.recipes.states import RecipeState, InvalidTransition
from app.domain.shared.themes import Theme


def make_recipe(**overrides) -> Recipe:
    params = dict(id="REC-001", name="Spaghetti Bolognese", theme=Theme.ITALIAN)
    params.update(overrides)
    return Recipe.create(**params)


class TestCreate:
    def test_creates_with_sensible_defaults(self):
        recipe = make_recipe()
        assert recipe.id == "REC-001"
        assert recipe.name == "Spaghetti Bolognese"
        assert recipe.theme == Theme.ITALIAN
        assert recipe.state == RecipeState.ACTIVE
        assert recipe.uses_frozen_meat is False
        assert recipe.thaw_lead_hours is None
        assert recipe.prep_minutes is None
        assert recipe.ingredients == []

    def test_carries_all_fields(self):
        recipe = make_recipe(
            uses_frozen_meat=True,
            thaw_lead_hours=12,
            prep_minutes=45,
        )
        assert recipe.uses_frozen_meat is True
        assert recipe.thaw_lead_hours == 12
        assert recipe.prep_minutes == 45

    @pytest.mark.parametrize("bad_name", ["", "   ", "\t\n"])
    def test_rejects_empty_name(self, bad_name):
        with pytest.raises(RecipeError):
            make_recipe(name=bad_name)

    def test_strips_name(self):
        recipe = make_recipe(name="  Tacos  ")
        assert recipe.name == "Tacos"

    def test_emits_recipe_created_event(self):
        recipe = make_recipe(name="Carbonara")
        events = recipe.collect_events()
        assert events == [RecipeCreated(recipe_id="REC-001", name="Carbonara")]
        # collect_events drains the buffer
        assert recipe.collect_events() == []

    def test_accepts_initial_ingredients(self):
        ingredients = [Ingredient(name="Pasta", quantity="200g"), Ingredient(name="Egg")]
        recipe = make_recipe(ingredients=ingredients)
        assert recipe.ingredients == ingredients

    def test_frozen_meat_requires_thaw_lead_hours(self):
        with pytest.raises(RecipeError, match="thaw_lead_hours"):
            make_recipe(uses_frozen_meat=True)

    def test_frozen_meat_with_thaw_lead_hours_ok(self):
        recipe = make_recipe(uses_frozen_meat=True, thaw_lead_hours=8)
        assert recipe.uses_frozen_meat is True
        assert recipe.thaw_lead_hours == 8

    def test_no_frozen_meat_without_thaw_ok(self):
        recipe = make_recipe(uses_frozen_meat=False, thaw_lead_hours=None)
        assert recipe.thaw_lead_hours is None


class TestEdit:
    def test_updates_descriptive_fields(self):
        recipe = make_recipe()
        recipe.edit(
            name="Chicken Tikka",
            theme=Theme.ASIAN,
            uses_frozen_meat=True,
            thaw_lead_hours=6,
            prep_minutes=30,
        )
        assert recipe.name == "Chicken Tikka"
        assert recipe.theme == Theme.ASIAN
        assert recipe.uses_frozen_meat is True
        assert recipe.thaw_lead_hours == 6
        assert recipe.prep_minutes == 30

    def test_rejects_empty_name(self):
        recipe = make_recipe()
        with pytest.raises(RecipeError):
            recipe.edit(name="  ", theme=Theme.ITALIAN)

    def test_enforces_frozen_meat_invariant(self):
        recipe = make_recipe()
        with pytest.raises(RecipeError, match="thaw_lead_hours"):
            recipe.edit(name="Frozen Burgers", theme=Theme.AMERICAN, uses_frozen_meat=True)

    def test_emits_recipe_edited_event(self):
        recipe = make_recipe()
        recipe.collect_events()  # drain RecipeCreated
        recipe.edit(name="Updated", theme=Theme.MEXICAN)
        assert recipe.collect_events() == [RecipeEdited(recipe_id="REC-001")]

    def test_does_not_touch_ingredients(self):
        recipe = make_recipe()
        recipe.add_ingredient("Beef", "500g")
        recipe.edit(name="Renamed", theme=Theme.BBQ)
        assert [i.name for i in recipe.ingredients] == ["Beef"]


class TestIngredients:
    def test_add_appends_and_returns(self):
        recipe = make_recipe()
        result = recipe.add_ingredient("Tomato", "2 cans")
        assert result == Ingredient(name="Tomato", quantity="2 cans")
        assert recipe.ingredients == [Ingredient(name="Tomato", quantity="2 cans")]

    def test_add_without_quantity(self):
        recipe = make_recipe()
        recipe.add_ingredient("Salt")
        assert recipe.ingredients == [Ingredient(name="Salt", quantity=None)]

    def test_add_strips_name(self):
        recipe = make_recipe()
        recipe.add_ingredient("  Basil  ")
        assert recipe.ingredients[0].name == "Basil"

    @pytest.mark.parametrize("bad_name", ["", "   "])
    def test_add_rejects_empty_name(self, bad_name):
        recipe = make_recipe()
        with pytest.raises(RecipeError):
            recipe.add_ingredient(bad_name)

    def test_add_rejects_duplicate_case_insensitive(self):
        recipe = make_recipe()
        recipe.add_ingredient("Onion")
        with pytest.raises(RecipeError, match="already"):
            recipe.add_ingredient("onion")

    def test_remove_deletes_ingredient(self):
        recipe = make_recipe()
        recipe.add_ingredient("Garlic")
        recipe.add_ingredient("Pepper")
        recipe.remove_ingredient("Garlic")
        assert [i.name for i in recipe.ingredients] == ["Pepper"]

    def test_remove_is_case_insensitive(self):
        recipe = make_recipe()
        recipe.add_ingredient("Cumin")
        recipe.remove_ingredient("CUMIN")
        assert recipe.ingredients == []

    def test_remove_missing_raises(self):
        recipe = make_recipe()
        with pytest.raises(RecipeError, match="not found"):
            recipe.remove_ingredient("Saffron")


class TestArchiveRestore:
    def test_archive_active_to_archived(self):
        recipe = make_recipe()
        recipe.archive()
        assert recipe.state == RecipeState.ARCHIVED

    def test_restore_archived_to_active(self):
        recipe = make_recipe()
        recipe.archive()
        recipe.restore()
        assert recipe.state == RecipeState.ACTIVE

    def test_archive_emits_event(self):
        recipe = make_recipe()
        recipe.collect_events()
        recipe.archive()
        assert recipe.collect_events() == [RecipeArchived(recipe_id="REC-001")]

    def test_restore_emits_event(self):
        recipe = make_recipe()
        recipe.archive()
        recipe.collect_events()
        recipe.restore()
        assert recipe.collect_events() == [RecipeRestored(recipe_id="REC-001")]

    def test_cannot_archive_an_archived_recipe(self):
        recipe = make_recipe()
        recipe.archive()
        with pytest.raises(InvalidTransition):
            recipe.archive()

    def test_cannot_restore_an_active_recipe(self):
        recipe = make_recipe()
        with pytest.raises(InvalidTransition):
            recipe.restore()

    def test_available_actions(self):
        recipe = make_recipe()
        assert recipe.available_actions() == {"archive"}
        recipe.archive()
        assert recipe.available_actions() == {"restore"}


class TestFrozenMeatInvariant:
    """The core domain invariant: thaw lead time is required for frozen meat."""

    def test_create_blocks_frozen_without_thaw(self):
        with pytest.raises(RecipeError):
            Recipe.create(id="R", name="Stew", theme=Theme.AMERICAN, uses_frozen_meat=True)

    def test_edit_blocks_frozen_without_thaw(self):
        recipe = make_recipe()
        with pytest.raises(RecipeError):
            recipe.edit(name="Stew", theme=Theme.AMERICAN, uses_frozen_meat=True, thaw_lead_hours=None)

    def test_frozen_with_thaw_is_allowed(self):
        recipe = Recipe.create(
            id="R", name="Stew", theme=Theme.AMERICAN, uses_frozen_meat=True, thaw_lead_hours=24
        )
        assert recipe.thaw_lead_hours == 24
