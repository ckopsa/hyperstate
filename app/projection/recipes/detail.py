from typing import List

from app.domain.recipes.aggregate import Recipe
from app.domain.recipes.states import RecipeState
from hyperstate.display import PropertyItem
from hyperstate.fields import HiddenField, RepeatableField, TextField
from hyperstate.flash import Flash
from hyperstate.nav import NavLink
from hyperstate.response import ActorContext, HyperStateResponse, ViewContext
from hyperstate.sections import (
    ActionCondition,
    ActionSection,
    ColumnDef,
    EmptySection,
    GroupSection,
    ListItem,
    ListSection,
    PropertiesSection,
    Section,
)


class RecipeDetailProjection:
    def __init__(self, recipe: Recipe, actor: ActorContext):
        self.recipe = recipe
        self.actor = actor

    def build(self, flash: Flash | None = None) -> HyperStateResponse:
        r = self.recipe

        left_sections: List[Section] = [
            self._properties_section(),
            self._archive_section(),
            self._restore_section(),
        ]
        right_sections: List[Section] = [
            self._ingredients_section(),
            self._add_ingredients_section(),
        ]

        sections: List[Section] = [
            GroupSection(
                layout="sidebar",
                sections=[
                    GroupSection(layout="stack", sections=left_sections),
                    GroupSection(layout="stack", sections=right_sections),
                ],
            )
        ]

        return HyperStateResponse(
            view="detail",
            title=r.name,
            self_=f"/recipes/{r.id}",
            flash=flash,
            context=ViewContext(
                domain="recipes",
                aggregate="recipe",
                state=r.state.value,
                actor=self.actor,
            ),
            nav=[NavLink(label="All Recipes", href="/recipes", rel="collection")],
            sections=sections,
        )

    def _properties_section(self) -> PropertiesSection:
        r = self.recipe
        data = [
            PropertyItem(
                key="status", label="Status",
                value=r.state.value, display="badge",
                variant=self._state_variant(),
            ),
            PropertyItem(key="theme", label="Theme", value=r.theme.value, display="badge"),
            PropertyItem(
                key="uses_frozen_meat", label="Uses Frozen Meat",
                value=r.uses_frozen_meat, display="badge",
                variant="warning" if r.uses_frozen_meat else "secondary",
            ),
        ]
        if r.thaw_lead_hours is not None:
            data.append(PropertyItem(
                key="thaw_lead_hours", label="Thaw Lead Time",
                value=f"{r.thaw_lead_hours} h",
            ))
        if r.prep_minutes is not None:
            data.append(PropertyItem(
                key="prep_minutes", label="Prep Time",
                value=f"{r.prep_minutes} min",
            ))
        return PropertiesSection(title="Recipe Details", data=data)

    def _archive_section(self) -> ActionSection:
        r = self.recipe
        if r.state == RecipeState.ACTIVE:
            return ActionSection(
                key="archive",
                label="Archive",
                method="POST",
                href=f"/recipes/{r.id}/archive",
                style="subtle",
                confirm="Archive this recipe?",
            )
        return ActionSection(
            key="archive",
            label="Archive",
            method="POST",
            href=f"/recipes/{r.id}/archive",
            condition=ActionCondition(met=False, explain="Recipe is already archived."),
        )

    def _restore_section(self) -> ActionSection:
        r = self.recipe
        if r.state == RecipeState.ARCHIVED:
            return ActionSection(
                key="restore",
                label="Restore",
                method="POST",
                href=f"/recipes/{r.id}/restore",
                style="primary",
            )
        return ActionSection(
            key="restore",
            label="Restore",
            method="POST",
            href=f"/recipes/{r.id}/restore",
            condition=ActionCondition(met=False, explain="Recipe is already active."),
        )

    def _ingredients_section(self) -> ListSection | EmptySection:
        r = self.recipe
        if not r.ingredients:
            return EmptySection(
                title="No Ingredients Yet",
                description="Add ingredients below to complete this recipe.",
            )
        items = [
            ListItem(
                data={"name": ing.name, "quantity": ing.quantity or "—"},
                actions=[
                    ActionSection(
                        key="remove-ingredient",
                        label="Remove",
                        method="POST",
                        href=f"/recipes/{r.id}/ingredients/remove",
                        style="danger",
                        confirm=f"Remove {ing.name}?",
                        fields=[HiddenField(name="name", value=ing.name)],
                    )
                ],
            )
            for ing in r.ingredients
        ]
        return ListSection(
            title="Ingredients",
            columns=[
                ColumnDef(key="name", label="Ingredient"),
                ColumnDef(key="quantity", label="Quantity"),
            ],
            items=items,
        )

    def _add_ingredients_section(self) -> ActionSection:
        r = self.recipe
        return ActionSection(
            key="add-ingredients",
            label="Add Ingredients",
            method="POST",
            href=f"/recipes/{r.id}/ingredients",
            fields=[
                RepeatableField(
                    name="ingredients",
                    label="Ingredients",
                    min_items=1,
                    fields=[
                        TextField(name="name", label="Name", required=True),
                        TextField(name="quantity", label="Quantity", placeholder="e.g. 2 cups"),
                    ],
                ),
            ],
        )

    def _state_variant(self) -> str:
        return {
            RecipeState.ACTIVE: "success",
            RecipeState.ARCHIVED: "secondary",
        }.get(self.recipe.state, "secondary")
