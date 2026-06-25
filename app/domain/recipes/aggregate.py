from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from app.domain.shared.aggregate import AggregateRoot
from app.domain.shared.themes import Theme
from .states import RecipeState, next_state, TRANSITIONS
from .errors import RecipeError
from .events import RecipeCreated, RecipeEdited, RecipeArchived, RecipeRestored
from .entities import Ingredient


@dataclass(kw_only=True)
class Recipe(AggregateRoot):
    """Aggregate root for a dinner recipe."""

    id: str
    name: str
    theme: Theme
    uses_frozen_meat: bool = False
    thaw_lead_hours: int | None = None
    prep_minutes: int | None = None
    state: RecipeState = RecipeState.ACTIVE
    ingredients: list[Ingredient] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        id: str,
        name: str,
        theme: Theme,
        uses_frozen_meat: bool = False,
        thaw_lead_hours: int | None = None,
        prep_minutes: int | None = None,
        ingredients: Iterable[Ingredient] | None = None,
    ) -> "Recipe":
        if not name.strip():
            raise RecipeError("Recipe name cannot be empty.")
        cls._validate_frozen_meat(uses_frozen_meat, thaw_lead_hours)
        recipe = cls(
            id=id,
            name=name.strip(),
            theme=theme,
            uses_frozen_meat=uses_frozen_meat,
            thaw_lead_hours=thaw_lead_hours,
            prep_minutes=prep_minutes,
            ingredients=list(ingredients or []),
        )
        recipe._events.append(RecipeCreated(recipe_id=id, name=recipe.name))
        return recipe

    def edit(
        self,
        name: str,
        theme: Theme,
        uses_frozen_meat: bool = False,
        thaw_lead_hours: int | None = None,
        prep_minutes: int | None = None,
    ) -> None:
        """Replace the recipe's descriptive fields (not its ingredients)."""
        if not name.strip():
            raise RecipeError("Recipe name cannot be empty.")
        self._validate_frozen_meat(uses_frozen_meat, thaw_lead_hours)
        self.name = name.strip()
        self.theme = theme
        self.uses_frozen_meat = uses_frozen_meat
        self.thaw_lead_hours = thaw_lead_hours
        self.prep_minutes = prep_minutes
        self._events.append(RecipeEdited(recipe_id=self.id))

    def add_ingredient(self, name: str, quantity: str | None = None) -> Ingredient:
        if not name.strip():
            raise RecipeError("Ingredient name cannot be empty.")
        clean_name = name.strip()
        if any(i.name.lower() == clean_name.lower() for i in self.ingredients):
            raise RecipeError(f"Ingredient '{clean_name}' is already on this recipe.")
        ingredient = Ingredient(name=clean_name, quantity=quantity)
        self.ingredients.append(ingredient)
        return ingredient

    def remove_ingredient(self, name: str) -> None:
        target = name.strip().lower()
        for i, ingredient in enumerate(self.ingredients):
            if ingredient.name.lower() == target:
                del self.ingredients[i]
                return
        raise RecipeError(f"Ingredient '{name}' not found on this recipe.")

    def archive(self) -> None:
        """Transition active → archived."""
        self._transition("archive")
        self._events.append(RecipeArchived(recipe_id=self.id))

    def restore(self) -> None:
        """Transition archived → active."""
        self._transition("restore")
        self._events.append(RecipeRestored(recipe_id=self.id))

    def available_actions(self) -> set[str]:
        return set(TRANSITIONS.get(self.state, {}).keys())

    @staticmethod
    def _validate_frozen_meat(uses_frozen_meat: bool, thaw_lead_hours: int | None) -> None:
        if uses_frozen_meat and thaw_lead_hours is None:
            raise RecipeError("thaw_lead_hours is required when the recipe uses frozen meat.")

    def _transition(self, action: str) -> None:
        self.state = next_state(self.state, action)
