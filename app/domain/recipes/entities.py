from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Ingredient:
    """Value object: a single ingredient line on a recipe.

    Ingredients have no identity of their own — two ingredients with the same
    name and quantity are interchangeable. They are owned wholesale by the
    Recipe aggregate and replaced as a set when the recipe is persisted.
    """

    name: str
    quantity: str | None = None
