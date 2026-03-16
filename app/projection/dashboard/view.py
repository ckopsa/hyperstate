from app.domain.lessons.aggregate import Lesson
from app.domain.lessons.states import LessonState
from app.domain.subjects.aggregate import Subject
from app.hyperstate.response import HyperStateResponse, ViewContext, ActorContext
from app.hyperstate.flash import Flash
from app.hyperstate.sections import (
    SummarySection, SummaryItem, ListSection, ColumnDef, ListItem,
    TimelineSection, TimelineEvent, EmptySection, ActionSection,
)
from app.hyperstate.nav import NavLink

_SCHOOL_YEAR_DAYS = 180


class DashboardProjection:
    def __init__(
        self,
        today_lessons: list[Lesson],
        recently_completed: list[Lesson],
        instruction_days: int,
        subjects: dict[str, Subject],
        actor: ActorContext,
    ):
        self.today_lessons = today_lessons
        self.recently_completed = recently_completed
        self.instruction_days = instruction_days
        self.subjects = subjects
        self.actor = actor

    def build(self, flash: Flash | None = None) -> HyperStateResponse:
        total_today = len(self.today_lessons)
        completed_today = sum(1 for l in self.today_lessons if l.state == "completed")
        year_progress = round(self.instruction_days / _SCHOOL_YEAR_DAYS, 4)

        summary = SummarySection(
            items=[
                SummaryItem(label="Today's Lessons", value=total_today, display="number"),
                SummaryItem(label="Completed", value=completed_today, display="number"),
                SummaryItem(
                    label="Instruction Days",
                    value=self.instruction_days,
                    display="number",
                    href="/reports/instruction-days",
                ),
                SummaryItem(label="Year Progress", value=year_progress, display="percentage"),
            ]
        )

        if self.today_lessons:
            schedule = ListSection(
                title="Today's Schedule",
                columns=[
                    ColumnDef(key="time", label="Time"),
                    ColumnDef(key="subject", label="Subject"),
                    ColumnDef(key="lesson", label="Lesson"),
                    ColumnDef(key="status", label="Status", display="badge"),
                ],
                items=[
                    ListItem(
                        href=f"/lessons/{l.id}",
                        data={
                            "time": l.time_slot.capitalize(),
                            "subject": self.subjects[l.subject_id].name
                            if l.subject_id in self.subjects
                            else l.subject_id,
                            "lesson": l.title,
                            "status": l.state.value,
                        },
                        actions=[] if l.state == LessonState.COMPLETED else [
                            ActionSection(
                                key="complete-task",
                                label="Done!",
                                method="POST",
                                href=f"/lessons/{l.id}/complete",
                                style="primary",
                            )
                        ],
                    )
                    for l in self.today_lessons
                ],
            )
        else:
            schedule = EmptySection(
                title="No lessons planned today",
                description="Enjoy your day off, or add lessons via the Lessons section.",
                action=None,
            )

        timeline_events = [
            TimelineEvent(
                timestamp=l.completed_at.isoformat() if l.completed_at else "",
                label=l.title,
                actor=l.completed_by,
            )
            for l in self.recently_completed
            if l.completed_at
        ]
        timeline = TimelineSection(title="Recent Activity", events=timeline_events)

        sections = [summary, schedule]
        if timeline_events:
            sections.append(timeline)

        return HyperStateResponse(
            view="dashboard",
            title="Daily Dashboard",
            self_="/dashboard",
            context=ViewContext(
                domain="dashboard",
                aggregate="dashboard",
                state="overview",
                actor=self.actor,
            ),
            flash=flash,
            nav=[
                NavLink(label="Calendar", href="/calendar", rel="section"),
                NavLink(label="Subjects", href="/subjects", rel="section"),
                NavLink(label="Reports", href="/reports", rel="section"),
            ],
            sections=sections,
        )
