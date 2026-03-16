from __future__ import annotations

from datetime import date

from app.domain.lessons.aggregate import Lesson
from app.domain.lessons.states import LessonState
from app.domain.subjects.aggregate import Subject
from app.hyperstate.response import HyperStateResponse, ViewContext, ActorContext
from app.hyperstate.flash import Flash
from app.hyperstate.nav import NavLink
from app.hyperstate.sections import (
    SummarySection, SummaryItem,
    GroupSection, ListSection, ColumnDef, ListItem,
    ActionSection,
    EmptySection,
    Section,
)
from app.hyperstate.fields import (
    DateField, SelectField, NumberField, FieldOption, HiddenField,
)


TIME_SLOT_OPTIONS = [
    FieldOption(value="morning", label="Morning"),
    FieldOption(value="afternoon", label="Afternoon"),
]

DIRECTION_OPTIONS = [
    FieldOption(value="forward", label="Forward"),
    FieldOption(value="backward", label="Backward"),
]

DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class CalendarWeekProjection:
    def __init__(
        self,
        lessons: list[Lesson],
        subject_map: dict[str, Subject],
        week_start: date,
        actor: ActorContext,
    ):
        self.lessons = lessons
        self.subject_map = subject_map
        self.week_start = week_start
        self.week_end = date.fromordinal(week_start.toordinal() + 6)
        self.actor = actor

    def build(self, flash: Flash | None = None) -> HyperStateResponse:
        week_start = self.week_start

        prev_week = date.fromordinal(week_start.toordinal() - 7)
        next_week = date.fromordinal(week_start.toordinal() + 7)

        week_label = f"Week of {week_start.strftime('%B %d, %Y')}"

        sections: list[Section] = [
            self._summary_section(),
            self._daily_group_section(),
            self._move_lesson_action(),
            self._shift_week_action(),
        ]

        return HyperStateResponse(
            view="dashboard",
            title=f"Calendar — {week_label}",
            self_=f"/calendar?view=week&week={week_start.isoformat()}",
            context=ViewContext(
                domain="calendar",
                aggregate="calendar",
                state="week",
                actor=self.actor,
            ),
            flash=flash,
            nav=[
                NavLink(
                    label="← Previous Week",
                    href=f"/calendar?view=week&week={prev_week.isoformat()}",
                    rel="prev",
                ),
                NavLink(
                    label="→ Next Week",
                    href=f"/calendar?view=week&week={next_week.isoformat()}",
                    rel="next",
                ),
                NavLink(
                    label="Month View",
                    href=f"/calendar?view=month&week={week_start.isoformat()}",
                    rel="alternate",
                ),
                NavLink(label="← Dashboard", href="/dashboard", rel="parent"),
            ],
            sections=sections,
        )

    def _summary_section(self) -> SummarySection:
        total = len(self.lessons)
        completed = sum(1 for l in self.lessons if l.state == LessonState.COMPLETED)
        remaining = total - completed

        return SummarySection(items=[
            SummaryItem(label="Lessons Planned", value=total),
            SummaryItem(label="Completed", value=completed),
            SummaryItem(label="Remaining", value=remaining),
        ])

    def _daily_group_section(self) -> GroupSection:
        # Group lessons by date
        by_date: dict[date, list[Lesson]] = {}
        for lesson in self.lessons:
            if lesson.scheduled_date is not None:
                by_date.setdefault(lesson.scheduled_date, []).append(lesson)

        daily_sections: list[Section] = []
        for i in range(7):
            day = date.fromordinal(self.week_start.toordinal() + i)
            day_lessons = by_date.get(day, [])
            day_label = f"{DAYS_OF_WEEK[i]} {day.strftime('%m/%d')}"

            if day_lessons:
                items = [
                    ListItem(
                        href=f"/lessons/{l.id}",
                        data={
                            "lesson_title": l.title,
                            "subject": self._subject_name(l.subject_id),
                            "time_slot": l.time_slot,
                            "status": l.state.value,
                        },
                    )
                    for l in day_lessons
                ]
                daily_sections.append(
                    ListSection(
                        title=day_label,
                        columns=[
                            ColumnDef(key="lesson_title", label="Lesson"),
                            ColumnDef(key="subject", label="Subject"),
                            ColumnDef(key="time_slot", label="Time"),
                            ColumnDef(key="status", label="Status", display="badge"),
                        ],
                        items=items,
                    )
                )
            else:
                daily_sections.append(
                    EmptySection(title=day_label, description="No lessons scheduled.")
                )

        return GroupSection(title="Weekly Schedule", layout="columns", sections=daily_sections)

    def _move_lesson_action(self) -> ActionSection:
        return ActionSection(
            key="move-lesson",
            label="Move Lesson",
            method="POST",
            href="/calendar/move",
            fields=[
                HiddenField(name="lesson_id", value=""),
                DateField(name="target_date", label="New Date", required=True),
                SelectField(
                    name="time_slot",
                    label="Time Slot",
                    options=TIME_SLOT_OPTIONS,
                    value="morning",
                ),
                HiddenField(
                    name="week_start",
                    value=self.week_start.isoformat(),
                ),
            ],
        )

    def _shift_week_action(self) -> ActionSection:
        return ActionSection(
            key="shift-week",
            label="Shift All Lessons in Week",
            method="POST",
            href="/calendar/shift-week",
            fields=[
                SelectField(
                    name="direction",
                    label="Direction",
                    options=DIRECTION_OPTIONS,
                    value="forward",
                ),
                NumberField(name="days", label="Days", value=1, required=True),
                HiddenField(
                    name="week_start",
                    value=self.week_start.isoformat(),
                ),
            ],
        )

    def _subject_name(self, subject_id: str) -> str:
        subject = self.subject_map.get(subject_id)
        if subject:
            return f"{subject.icon} {subject.name}" if subject.icon else subject.name
        return subject_id
