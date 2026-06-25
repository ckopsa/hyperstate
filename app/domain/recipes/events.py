from dataclasses import dataclass


@dataclass(frozen=True)
class RecipeCreated:
    recipe_id: str
    name: str


@dataclass(frozen=True)
class RecipeEdited:
    recipe_id: str


@dataclass(frozen=True)
class RecipeArchived:
    recipe_id: str


@dataclass(frozen=True)
class RecipeRestored:
    recipe_id: str
