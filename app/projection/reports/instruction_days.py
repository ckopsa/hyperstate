from __future__ import annotations

from datetime import date

from app.hyperstate.fields import DateField, TextareaField
from app.hyperstate.flash import Flash
from app.hyperstate.nav import NavLink
from app.hyperstate.response import ActorContext, HyperStateResponse, ViewContext
from app.hyperstate.sections import (
    ActionSection,
    ColumnDef,
    EmptySection,
    ListItem,
    ListSection,
    Section,
    SummaryItem,
    SummarySection,
)
from app.infrastructure.models.instruction_day_model import InstructionDayRow

DAYS_REQUIRED = 180


class InstructionDaysProjection:
    def __init__(self, days: list[InstructionDayRow], actor: ActorContext):
        self.days = days
        self.actor = actor

    def build(self, flash: Flash | None = None) -> HyperStateResponse:
        sections: list[Section] = [
            self._summary_section(),
            self._list_section(),
            self._add_manual_day_section(),
        ]

        return HyperStateResponse(
            view="list",
            title="Instruction Days",
            self_="/reports/instruction-days",
            context=ViewContext(
                domain="reports",
                aggregate="instruction-days",
                state="overview",
                actor=self.actor,
            ),
            flash=flash,
            nav=[
                NavLink(label="Dashboard", href="/dashboard", rel="parent"),
                NavLink(label="Export PDF", href="/reports/instruction-days/export", rel="related"),
            ],
            sections=sections,
        )

    def _summary_section(self) -> SummarySection:
        days_logged = len(self.days)
        days_remaining = max(0, DAYS_REQUIRED - days_logged)
        on_track = self._is_on_track(days_logged)

        return SummarySection(
            items=[
                SummaryItem(label="Days Logged", value=days_logged, display="number"),
                SummaryItem(label="Days Required", value=DAYS_REQUIRED, display="number"),
                SummaryItem(label="Days Remaining", value=days_remaining, display="number"),
                SummaryItem(
                    label="On Track",
                    value=on_track,
                    display="badge",
                ),
            ]
        )

    def _list_section(self) -> Section:
        if not self.days:
            return EmptySection(
                title="No instruction days logged yet",
                description="Complete a lesson to automatically log your first instruction day.",
            )

        return ListSection(
            title="Instruction Days",
            columns=[
                ColumnDef(key="date", label="Date"),
                ColumnDef(key="lessons_completed", label="Lessons", align="right"),
                ColumnDef(key="subjects_covered", label="Subjects"),
                ColumnDef(key="notes", label="Notes"),
            ],
            items=[
                ListItem(
                    href=f"/reports/instruction-days/{row.date.isoformat()}",
                    data={
                        "date": row.date.isoformat(),
                        "lessons_completed": row.lessons_completed or 0,
                        "subjects_covered": row.subjects_covered or "",
                        "notes": row.notes or "",
                    },
                )
                for row in reversed(self.days)  # most recent first
            ],
        )

    def _add_manual_day_section(self) -> ActionSection:
        return ActionSection(
            key="add-manual-day",
            label="Log Manual Day",
            description="Record a field trip, museum visit, or other non-lesson instruction day.",
            method="POST",
            href="/reports/instruction-days",
            style="default",
            fields=[
                DateField(
                    name="date",
                    label="Date",
                    required=True,
                    value=date.today().isoformat(),
                ),
                TextareaField(
                    name="notes",
                    label="Notes",
                    placeholder="Field trip, museum visit, etc.",
                    required=False,
                ),
            ],
        )

    def _is_on_track(self, days_logged: int) -> bool:
        today = date.today()
        # School year starts Sept 1 of the academic year.
        # Determine which academic year we're in.
        if today.month >= 9:
            school_year_start = date(today.year, 9, 1)
        else:
            school_year_start = date(today.year - 1, 9, 1)

        # School year ends ~June 15
        if today.month >= 9:
            school_year_end = date(today.year + 1, 6, 15)
        else:
            school_year_end = date(today.year, 6, 15)

        total_days = (school_year_end - school_year_start).days
        days_elapsed = (today - school_year_start).days

        if total_days <= 0:
            return True

        expected_pace = DAYS_REQUIRED * (days_elapsed / total_days)
        return days_logged >= expected_pace
