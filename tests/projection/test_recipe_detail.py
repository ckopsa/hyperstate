import pytest

from app.domain.recipes.aggregate import Recipe
from app.domain.recipes.entities import Ingredient
from app.domain.recipes.states import RecipeState
from app.domain.shared.themes import Theme
from hyperstate.response import ActorContext
from app.projection.recipes.detail import RecipeDetailProjection


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
    return [s for s in flatten_sections(view.sections) if s.kind == "action"]


@pytest.fixture
def actor():
    return ActorContext(id="cook-1", roles=["parent"])


@pytest.fixture
def active_recipe():
    return Recipe(
        id="REC-001",
        name="Spaghetti Bolognese",
        theme=Theme.ITALIAN,
        uses_frozen_meat=True,
        thaw_lead_hours=12,
        prep_minutes=45,
        state=RecipeState.ACTIVE,
        ingredients=[
            Ingredient(name="Spaghetti", quantity="1 lb"),
            Ingredient(name="Ground beef", quantity="1 lb"),
        ],
    )


@pytest.fixture
def archived_recipe():
    return Recipe(
        id="REC-002",
        name="Old Casserole",
        theme=Theme.AMERICAN,
        state=RecipeState.ARCHIVED,
    )


class TestArchiveRestoreByState:
    def test_active_recipe_can_archive(self, actor, active_recipe):
        view = RecipeDetailProjection(active_recipe, actor).build()
        archive = next(a for a in _actions(view) if a.key == "archive")
        assert archive.condition is None
        assert archive.href == "/recipes/REC-001/archive"

    def test_active_recipe_restore_unavailable(self, actor, active_recipe):
        view = RecipeDetailProjection(active_recipe, actor).build()
        restore = next(a for a in _actions(view) if a.key == "restore")
        assert restore.condition is not None
        assert restore.condition.met is False

    def test_archived_recipe_can_restore(self, actor, archived_recipe):
        view = RecipeDetailProjection(archived_recipe, actor).build()
        restore = next(a for a in _actions(view) if a.key == "restore")
        assert restore.condition is None
        assert restore.href == "/recipes/REC-002/restore"

    def test_archived_recipe_archive_unavailable(self, actor, archived_recipe):
        view = RecipeDetailProjection(archived_recipe, actor).build()
        archive = next(a for a in _actions(view) if a.key == "archive")
        assert archive.condition is not None
        assert archive.condition.met is False


class TestIngredients:
    def test_ingredients_listed_with_remove_action(self, actor, active_recipe):
        view = RecipeDetailProjection(active_recipe, actor).build()
        sections = flatten_sections(view.sections)
        ing_list = next(s for s in sections if s.kind == "list" and s.title == "Ingredients")
        names = [item.data["name"] for item in ing_list.items]
        assert names == ["Spaghetti", "Ground beef"]

        first_remove = ing_list.items[0].actions[0]
        assert first_remove.key == "remove-ingredient"
        assert first_remove.href == "/recipes/REC-001/ingredients/remove"
        assert any(f.name == "name" and f.value == "Spaghetti" for f in first_remove.fields)

    def test_empty_ingredients_shows_empty_section(self, actor, archived_recipe):
        view = RecipeDetailProjection(archived_recipe, actor).build()
        kinds = [s.kind for s in flatten_sections(view.sections)]
        assert "empty" in kinds

    def test_add_ingredients_form_is_repeatable(self, actor, active_recipe):
        view = RecipeDetailProjection(active_recipe, actor).build()
        add = next(a for a in _actions(view) if a.key == "add-ingredients")
        assert add.href == "/recipes/REC-001/ingredients"
        repeatable = add.fields[0]
        assert repeatable.type == "repeatable"
        sub_fields = {f.name for f in repeatable.fields}
        assert {"name", "quantity"} <= sub_fields


class TestRecipeDetailContext:
    def test_context_reflects_state(self, actor, active_recipe):
        view = RecipeDetailProjection(active_recipe, actor).build()
        assert view.context is not None
        assert view.context.state == "active"
        assert view.context.domain == "recipes"

    def test_status_property_badge(self, actor, active_recipe):
        view = RecipeDetailProjection(active_recipe, actor).build()
        props = next(s for s in flatten_sections(view.sections) if s.kind == "properties")
        status = next(p for p in props.data if p.key == "status")
        assert status.display == "badge"
        assert status.value == "active"
        assert status.variant == "success"
