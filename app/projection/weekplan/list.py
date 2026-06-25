from datetime import date
from typing import Iterable

from app.domain.weekplan.aggregate import WeekPlan
from app.domain.weekplan.states import WeekPlanState
from hyperstate.response import HyperStateResponse, ViewContext, ActorContext
from hyperstate.flash import Flash
from hyperstate.sections import (
    Section, ListSection, ActionSection, EmptySection, ColumnDef, ListItem,
)
from hyperstate.fields import DateField
from hyperstate.nav import NavLink


class WeekPlanListProjection:
    """Dashboard of week plans, newest week first, each with its state."""

    def __init__(
        self,
        plans: Iterable[WeekPlan],
        actor: ActorContext,
        default_week_start: date | None = None,
    ):
        self.plans = list(plans)
        self.actor = actor
        self.default_week_start = default_week_start

    def build(self, flash: Flash | None = None) -> HyperStateResponse:
        sections: list[Section] = [self._create_section()]

        if not self.plans:
            sections.append(EmptySection(
                title="No Week Plans Yet",
                description="Plan a week to start deciding the family's dinners.",
            ))
        else:
            sections.append(self._list_section())

        return HyperStateResponse(
            view="list",
            title="Week Plans",
            self_="/weekplans",
            flash=flash,
            context=ViewContext(
                domain="weekplan",
                aggregate="weekplans",
                state="collection",
                actor=self.actor,
            ),
            nav=[NavLink(label="Dashboard", href="/dashboard", rel="parent")],
            sections=sections,
        )

    def _create_section(self) -> ActionSection:
        return ActionSection(
            key="create-weekplan",
            label="Plan a Week",
            method="POST",
            href="/weekplans",
            style="primary",
            fields=[
                DateField(
                    name="week_start",
                    label="Week Start (Tuesday)",
                    required=True,
                    value=self.default_week_start.isoformat() if self.default_week_start else None,
                    help="A plan runs from its Tuesday start through the following Monday.",
                ),
            ],
        )

    def _list_section(self) -> ListSection:
        return ListSection(
            title="Weeks",
            columns=[
                ColumnDef(key="week_of", label="Week Of"),
                ColumnDef(key="decided", label="Dinners", align="right"),
                ColumnDef(key="status", label="Status", display="badge"),
            ],
            items=[
                ListItem(
                    href=f"/weekplans/{p.id}",
                    data={
                        "week_of": p.week_start.isoformat(),
                        "decided": f"{sum(1 for s in p.slots if s.is_decided)}/{len(p.slots)}",
                        "status": p.state.value,
                    },
                )
                for p in self.plans
            ],
        )
