from typing import Iterable

from app.domain.recipes.aggregate import Recipe
from app.domain.recipes.states import RecipeState
from app.domain.shared.themes import Theme
from hyperstate.response import HyperStateResponse, ViewContext, ActorContext
from hyperstate.flash import Flash
from hyperstate.sections import (
    Section, ListSection, ActionSection, EmptySection, ColumnDef, ListItem,
)
from hyperstate.fields import TextField, SelectField, BooleanField, NumberField, FieldOption
from hyperstate.nav import NavLink


THEME_OPTIONS = [
    FieldOption(value=t.value, label=t.value.capitalize()) for t in Theme
]


class RecipeListProjection:
    def __init__(self, recipes: Iterable[Recipe], actor: ActorContext):
        self.recipes = list(recipes)
        self.actor = actor

    def build(self, flash: Flash | None = None) -> HyperStateResponse:
        sections: list[Section] = [self._create_section()]

        active = [r for r in self.recipes if r.state == RecipeState.ACTIVE]
        archived = [r for r in self.recipes if r.state == RecipeState.ARCHIVED]

        if not self.recipes:
            sections.append(EmptySection(
                title="No Recipes Yet",
                description="Add your first dinner recipe to start planning the week.",
            ))
        else:
            if active:
                sections.append(self._list_section("Active Recipes", active))
            if archived:
                sections.append(self._list_section("Archived Recipes", archived))

        return HyperStateResponse(
            view="list",
            title="Recipes",
            self_="/recipes",
            flash=flash,
            context=ViewContext(
                domain="recipes",
                aggregate="recipes",
                state="collection",
                actor=self.actor,
            ),
            nav=[NavLink(label="Dashboard", href="/dashboard", rel="parent")],
            sections=sections,
        )

    def _create_section(self) -> ActionSection:
        return ActionSection(
            key="create-recipe",
            label="Add Recipe",
            method="POST",
            href="/recipes",
            style="primary",
            fields=[
                TextField(name="name", label="Name", required=True),
                SelectField(name="theme", label="Theme", required=True, options=THEME_OPTIONS),
                BooleanField(name="uses_frozen_meat", label="Uses Frozen Meat"),
                NumberField(
                    name="thaw_lead_hours",
                    label="Thaw Lead Time (hours)",
                    help="Required when the recipe uses frozen meat.",
                ),
                NumberField(name="prep_minutes", label="Prep Time (minutes)"),
            ],
        )

    def _list_section(self, title: str, recipes: list[Recipe]) -> ListSection:
        return ListSection(
            title=title,
            columns=[
                ColumnDef(key="name", label="Recipe"),
                ColumnDef(key="theme", label="Theme", display="badge"),
                ColumnDef(key="ingredients", label="Ingredients", align="right"),
                ColumnDef(key="status", label="Status", display="badge"),
            ],
            items=[
                ListItem(
                    href=f"/recipes/{r.id}",
                    data={
                        "name": r.name,
                        "theme": r.theme.value,
                        "ingredients": len(r.ingredients),
                        "status": r.state.value,
                    },
                )
                for r in recipes
            ],
        )
