from __future__ import annotations

from datetime import date
from typing import List

from app.domain.shopping.aggregate import ShoppingList
from app.domain.shopping.entities import ShoppingItem
from app.domain.shopping.states import ItemStatus
from hyperstate.flash import Flash
from hyperstate.nav import NavLink
from hyperstate.response import ActorContext, HyperStateResponse, ViewContext
from hyperstate.sections import (
    ActionAlternative,
    ActionSection,
    ColumnDef,
    EmptySection,
    ListItem,
    ListSection,
    Section,
    SummaryItem,
    SummarySection,
)


# Items are grouped under these headings, in shopping order: what is still
# outstanding first, then what we already have, then what is checked off.
_GROUPS: list[tuple[str, ItemStatus]] = [
    ("To Buy", ItemStatus.NEEDED),
    ("Already Have", ItemStatus.HAVE),
    ("Bought", ItemStatus.BOUGHT),
]

# For each status, the *other* two statuses it can be toggled to, rendered as
# row buttons: (action, label, style). A line never offers a toggle to its own
# current status.
_TOGGLES: dict[ItemStatus, list[tuple[str, str, str]]] = {
    ItemStatus.NEEDED: [("have", "Have It", "subtle"), ("bought", "Bought", "primary")],
    ItemStatus.HAVE: [("needed", "Need It", "primary"), ("bought", "Bought", "primary")],
    ItemStatus.BOUGHT: [("needed", "Need It", "subtle"), ("have", "Have It", "subtle")],
}


class ShoppingListDetailProjection:
    """Detail view for one week's shopping list: a count summary on top, then the
    lines grouped by status, each with the toggles to move it between needed /
    have / bought as the cook shops."""

    def __init__(
        self,
        shopping_list: ShoppingList,
        actor: ActorContext,
        week_start: date | None = None,
    ):
        self.shopping_list = shopping_list
        self.actor = actor
        self.week_start = week_start

    def build(self, flash: Flash | None = None) -> HyperStateResponse:
        sl = self.shopping_list

        sections: List[Section]
        if sl.is_empty():
            sections = [self._empty_section()]
        else:
            sections = [self._summary_section(), *self._group_sections()]

        return HyperStateResponse(
            view="detail",
            title=self._title(),
            self_=f"/shopping/{sl.week_plan_id}",
            flash=flash,
            context=ViewContext(
                domain="shopping",
                aggregate="shopping_list",
                state=self._state(),
                actor=self.actor,
            ),
            nav=[
                NavLink(
                    label="Back to Week Plan",
                    href=f"/weekplans/{sl.week_plan_id}",
                    rel="up",
                ),
            ],
            sections=sections,
        )

    # -- summary --------------------------------------------------------------

    def _summary_section(self) -> SummarySection:
        sl = self.shopping_list
        return SummarySection(
            items=[
                SummaryItem(label="To Buy", value=len(sl.with_status(ItemStatus.NEEDED))),
                SummaryItem(label="Have", value=len(sl.with_status(ItemStatus.HAVE))),
                SummaryItem(label="Bought", value=len(sl.with_status(ItemStatus.BOUGHT))),
            ]
        )

    # -- grouped item lists ---------------------------------------------------

    def _group_sections(self) -> List[ListSection]:
        sections: List[ListSection] = []
        for title, status in _GROUPS:
            items = self.shopping_list.with_status(status)
            if not items:
                continue
            sections.append(
                ListSection(
                    title=title,
                    columns=[
                        ColumnDef(key="item", label="Item"),
                        ColumnDef(key="quantity", label="Quantity"),
                    ],
                    items=[self._row(item) for item in items],
                )
            )
        return sections

    def _row(self, item: ShoppingItem) -> ListItem:
        return ListItem(
            data={"item": item.name, "quantity": item.label or "—"},
            actions=[
                self._toggle(item, action, label, style)
                for action, label, style in _TOGGLES[item.status]
            ],
        )

    def _toggle(
        self, item: ShoppingItem, action: str, label: str, style: str
    ) -> ActionSection:
        return ActionSection(
            key=f"mark-{action}",
            label=label,
            method="POST",
            href=f"/shopping/{self.shopping_list.week_plan_id}/items/{item.key}/{action}",
            style=style,
        )

    # -- empty state ----------------------------------------------------------

    def _empty_section(self) -> EmptySection:
        return EmptySection(
            title="Nothing to Shop For",
            description="This week's recipes list no ingredients.",
            action=ActionAlternative(
                label="Back to Week Plan",
                href=f"/weekplans/{self.shopping_list.week_plan_id}",
            ),
        )

    # -- helpers --------------------------------------------------------------

    def _title(self) -> str:
        if self.week_start is not None:
            return f"Shopping — week of {self.week_start.isoformat()}"
        return "Shopping List"

    def _state(self) -> str:
        """Derived progress, surfaced as the view's state for the client to badge:
        ``empty`` when there are no lines, ``complete`` once nothing is left on
        the buy list, otherwise ``shopping``."""
        sl = self.shopping_list
        if sl.is_empty():
            return "empty"
        if not sl.to_buy():
            return "complete"
        return "shopping"
