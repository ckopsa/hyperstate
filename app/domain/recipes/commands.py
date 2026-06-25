from dataclasses import dataclass

from app.domain.shared.themes import Theme


@dataclass(frozen=True)
class CreateRecipe:
    recipe_id: str
    name: str
    theme: Theme
    uses_frozen_meat: bool = False
    thaw_lead_hours: int | None = None
    prep_minutes: int | None = None


@dataclass(frozen=True)
class EditRecipe:
    recipe_id: str
    name: str
    theme: Theme
    uses_frozen_meat: bool = False
    thaw_lead_hours: int | None = None
    prep_minutes: int | None = None


@dataclass(frozen=True)
class AddIngredient:
    recipe_id: str
    name: str
    quantity: str | None = None


@dataclass(frozen=True)
class RemoveIngredient:
    recipe_id: str
    name: str


@dataclass(frozen=True)
class ArchiveRecipe:
    recipe_id: str


@dataclass(frozen=True)
class RestoreRecipe:
    recipe_id: str
