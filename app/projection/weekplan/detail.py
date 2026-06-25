from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, List

from app.domain.recipes.aggregate import Recipe
from app.domain.recipes.states import RecipeState
from app.domain.shared.themes import Theme
from app.domain.weekplan.aggregate import WeekPlan
from app.domain.weekplan.entities import DinnerSlot
from app.domain.weekplan.schedule import compute_schedule, ScheduleEventKind
from app.domain.weekplan.states import WeekPlanState, TRANSITIONS
from hyperstate.display import PropertyItem
from hyperstate.fields import FieldOption, SelectField
from hyperstate.flash import Flash
from hyperstate.nav import NavLink
from hyperstate.response import ActorContext, HyperStateResponse, ViewContext
from hyperstate.sections import (
    ActionCondition,
    ActionSection,
    ColumnDef,
    GroupSection,
    ListItem,
    ListSection,
    PropertiesSection,
    Section,
    TimelineEvent,
    TimelineSection,
)

if TYPE_CHECKING:  # type-only — keeps the weekplan view decoupled from shopping
    from app.domain.shopping.aggregate import ShoppingList


# date.weekday(): Monday == 0 ... Sunday == 6
WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

_STATE_VARIANTS = {
    WeekPlanState.PLANNING: "secondary",
    WeekPlanState.PLANNED: "info",
    WeekPlanState.SHOPPING: "warning",
    WeekPlanState.ACTIVE: "success",
    WeekPlanState.COMPLETED: "secondary",
}

# Lifecycle transitions rendered as buttons, in forward order with reopen last.
_LIFECYCLE: dict[str, tuple[str, str]] = {
    "finalize": ("Finalize Plan", "primary"),
    "start_shopping": ("Start Shopping", "primary"),
    "finish_shopping": ("Finish Shopping", "primary"),
    "complete": ("Mark Week Complete", "primary"),
    "reopen": ("Reopen for Editing", "subtle"),
}

_SCHEDULE_LABELS = {
    ScheduleEventKind.THAW: "Take out to thaw",
    ScheduleEventKind.COOK_START: "Start cooking",
}


class WeekPlanDetailProjection:
    """Detail view for a single week: themed dinner slots with a theme-filtered
    recipe picker, state-driven lifecycle actions, and the prep schedule
    timeline once the plan is finalized."""

    def __init__(
        self,
        plan: WeekPlan,
        recipes: Iterable[Recipe],
        actor: ActorContext,
        shopping_list: "ShoppingList | None" = None,
    ):
        self.plan = plan
        self.recipes = list(recipes)
        self.recipes_by_id = {r.id: r for r in self.recipes}
        self.actor = actor
        self.shopping_list = shopping_list

    def build(self, flash: Flash | None = None) -> HyperStateResponse:
        plan = self.plan

        side_sections: List[Section] = [self._properties_section()]
        side_sections.extend(self._lifecycle_sections())
        side_sections.extend(self._shopping_sections())

        main_sections: List[Section] = [self._slots_section()]
        timeline = self._timeline_section()
        if timeline is not None:
            main_sections.append(timeline)

        sections: List[Section] = [
            GroupSection(
                layout="sidebar",
                sections=[
                    GroupSection(layout="stack", sections=side_sections),
                    GroupSection(layout="stack", sections=main_sections),
                ],
            )
        ]

        return HyperStateResponse(
            view="detail",
            title=f"Week of {plan.week_start.isoformat()}",
            self_=f"/weekplans/{plan.id}",
            flash=flash,
            context=ViewContext(
                domain="weekplan",
                aggregate="weekplan",
                state=plan.state.value,
                actor=self.actor,
            ),
            nav=[NavLink(label="All Week Plans", href="/weekplans", rel="collection")],
            sections=sections,
        )

    # -- left column: status + lifecycle actions ------------------------------

    def _properties_section(self) -> PropertiesSection:
        plan = self.plan
        decided = sum(1 for s in plan.slots if s.is_decided)
        return PropertiesSection(
            title="Week Plan",
            data=[
                PropertyItem(
                    key="status", label="Status",
                    value=plan.state.value, display="badge",
                    variant=_STATE_VARIANTS.get(plan.state, "secondary"),
                ),
                PropertyItem(key="week_start", label="Week Start", value=plan.week_start.isoformat()),
                PropertyItem(key="decided", label="Dinners Decided", value=f"{decided} / {len(plan.slots)}"),
            ],
        )

    def _lifecycle_sections(self) -> List[ActionSection]:
        plan = self.plan
        available = set(TRANSITIONS.get(plan.state, {}).keys())
        sections: List[ActionSection] = []
        for action, (label, style) in _LIFECYCLE.items():
            if action == "finalize":
                finalize = self._finalize_section()
                if finalize is not None:
                    sections.append(finalize)
                continue
            if action in available:
                sections.append(ActionSection(
                    key=action,
                    label=label,
                    method="POST",
                    href=f"/weekplans/{plan.id}/{action}",
                    style=style,
                    confirm="Reopen this plan? Dinners can be changed again." if action == "reopen" else None,
                ))
        return sections

    def _finalize_section(self) -> ActionSection | None:
        plan = self.plan
        # Finalize is only contextually relevant while still planning; once the
        # plan is PLANNED or later it has already been finalized.
        if plan.state != WeekPlanState.PLANNING:
            return None
        href = f"/weekplans/{plan.id}/finalize"
        undecided = [s for s in plan.slots if not s.is_decided]
        if undecided:
            return ActionSection(
                key="finalize",
                label="Finalize Plan",
                method="POST",
                href=href,
                condition=ActionCondition(
                    met=False,
                    explain=f"{len(undecided)} of {len(plan.slots)} dinners still need a recipe.",
                ),
            )
        return ActionSection(
            key="finalize",
            label="Finalize Plan",
            method="POST",
            href=href,
            style="primary",
        )

    # -- left column: shopping list -------------------------------------------

    def _shopping_sections(self) -> List[ActionSection]:
        """Shopping only makes sense once dinners are locked in. While PLANNING
        there is nothing to shop for, so no action is shown; once finalized we
        offer to build the list, then to view (or rebuild) it once it exists."""
        plan = self.plan
        if plan.state == WeekPlanState.PLANNING:
            return []
        href = f"/shopping/{plan.id}"
        if self.shopping_list is None:
            return [
                ActionSection(
                    key="build-shopping-list",
                    label="Build Shopping List",
                    method="POST",
                    href=href,
                    style="primary",
                )
            ]
        return [
            ActionSection(
                key="view-shopping-list",
                label="View Shopping List",
                method="GET",
                href=href,
                style="primary",
            ),
            ActionSection(
                key="rebuild-shopping-list",
                label="Rebuild Shopping List",
                method="POST",
                href=href,
                style="subtle",
                confirm="Rebuild from the current plan? Item statuses will reset.",
            ),
        ]

    # -- main column: dinner slots --------------------------------------------

    def _slots_section(self) -> ListSection:
        plan = self.plan
        editable = plan.state == WeekPlanState.PLANNING
        return ListSection(
            title="Dinners",
            columns=[
                ColumnDef(key="day", label="Day"),
                ColumnDef(key="theme", label="Theme", display="badge"),
                ColumnDef(key="dinner", label="Dinner"),
            ],
            items=[self._slot_item(slot, editable) for slot in plan.slots],
        )

    def _slot_item(self, slot: DinnerSlot, editable: bool) -> ListItem:
        plan = self.plan
        recipe = self.recipes_by_id.get(slot.recipe_id) if slot.recipe_id else None
        if recipe is not None:
            dinner = recipe.name
        elif slot.recipe_id:
            dinner = slot.recipe_id  # decided but recipe unknown — show the id
        else:
            dinner = "—"

        actions: list[ActionSection] = []
        if editable:
            if slot.is_decided:
                actions.append(ActionSection(
                    key="clear-dinner",
                    label="Clear",
                    method="POST",
                    href=f"/weekplans/{plan.id}/slots/{slot.date.isoformat()}",
                    style="subtle",
                    confirm="Clear this dinner?",
                ))
            else:
                actions.append(self._decide_action(slot))

        return ListItem(
            data={
                "day": f"{WEEKDAY_NAMES[slot.weekday]} {slot.date.isoformat()}",
                "theme": slot.theme.value,
                "dinner": dinner,
            },
            actions=actions,
        )

    def _decide_action(self, slot: DinnerSlot) -> ActionSection:
        plan = self.plan
        return ActionSection(
            key="decide-dinner",
            label="Decide",
            method="POST",
            href=f"/weekplans/{plan.id}/slots/{slot.date.isoformat()}",
            style="primary",
            fields=[
                SelectField(
                    name="recipe_id",
                    label="Recipe",
                    required=True,
                    options=self._recipe_options(slot.theme),
                    help=self._picker_help(slot.theme),
                ),
            ],
        )

    def _recipe_options(self, theme: Theme) -> list[FieldOption]:
        """Theme is a soft suggestion: every active recipe is selectable, but the
        ones matching the day's theme are listed first and flagged. Sunday's
        ROTATING theme is a free night, so nothing is privileged."""
        active = sorted(
            (r for r in self.recipes if r.state == RecipeState.ACTIVE),
            key=lambda r: r.name,
        )

        def opt(r: Recipe, suggested: bool) -> FieldOption:
            theme_label = r.theme.value.capitalize()
            description = f"Suggested · {theme_label}" if suggested else theme_label
            return FieldOption(value=r.id, label=r.name, description=description)

        if theme == Theme.ROTATING:
            return [opt(r, False) for r in active]

        suggested = [opt(r, True) for r in active if r.theme == theme]
        others = [opt(r, False) for r in active if r.theme != theme]
        return suggested + others

    def _picker_help(self, theme: Theme) -> str:
        if theme == Theme.ROTATING:
            return "Sunday is a free night — pick any recipe."
        return f"{theme.value.capitalize()} recipes are suggested, but any recipe works."

    # -- main column: prep schedule -------------------------------------------

    def _timeline_section(self) -> TimelineSection | None:
        # The prep schedule is only meaningful once dinners are locked in, i.e.
        # the moment the plan leaves PLANNING (is finalized) and onward.
        if self.plan.state == WeekPlanState.PLANNING:
            return None
        events = compute_schedule(self.plan, self.recipes_by_id)
        return TimelineSection(
            title="Prep Schedule",
            events=[
                TimelineEvent(
                    timestamp=e.when.isoformat(),
                    label=f"{_SCHEDULE_LABELS[e.kind]}: {e.recipe_name}",
                )
                for e in events
            ],
        )
