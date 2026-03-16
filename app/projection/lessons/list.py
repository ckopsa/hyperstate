from typing import Iterable

from app.domain.lessons.aggregate import Lesson
from app.hyperstate.response import HyperStateResponse, ViewContext, ActorContext
from app.hyperstate.sections import ListSection, ActionSection, ColumnDef, ListItem
from app.hyperstate.fields import (
    TextField, TextareaField, SelectField, DateField, FieldOption, DependsOn,
)
from app.hyperstate.nav import NavLink


TIME_SLOT_OPTIONS = [
    FieldOption(value="morning", label="Morning"),
    FieldOption(value="afternoon", label="Afternoon"),
]


class LessonListProjection:
    def __init__(self, lessons: Iterable[Lesson], actor: ActorContext):
        self.lessons = list(lessons)
        self.actor = actor

    def build(self) -> HyperStateResponse:
        return HyperStateResponse(
            view="list",
            title="Lessons",
            self_="/lessons",
            context=ViewContext(
                domain="lessons",
                aggregate="lessons",
                state="collection",
                actor=self.actor,
            ),
            nav=[NavLink(label="Dashboard", href="/dashboard", rel="parent")],
            sections=[
                ActionSection(
                    key="create-lesson",
                    label="Create Lesson",
                    method="POST",
                    href="/lessons",
                    fields=[
                        TextField(name="title", label="Title", required=True),
                        SelectField(
                            name="subject_id",
                            label="Subject",
                            required=True,
                            options=[],
                            depends_on=DependsOn(
                                fields=[],
                                behavior="reload_options",
                                options_href="/api/subjects",
                            ),
                        ),
                        SelectField(
                            name="student_id",
                            label="Student",
                            required=True,
                            options=[],
                            depends_on=DependsOn(
                                fields=[],
                                behavior="reload_options",
                                options_href="/api/students",
                            ),
                        ),
                        TextareaField(name="description", label="Description"),
                        DateField(name="scheduled_date", label="Scheduled Date"),
                        SelectField(name="time_slot", label="Time Slot", options=TIME_SLOT_OPTIONS, value="morning"),
                    ],
                ),
                ListSection(
                    title="All Lessons",
                    columns=[
                        ColumnDef(key="title", label="Title"),
                        ColumnDef(key="subject", label="Subject"),
                        ColumnDef(key="scheduled_date", label="Date", display="date"),
                        ColumnDef(key="status", label="Status", display="badge"),
                    ],
                    items=[
                        ListItem(
                            href=f"/lessons/{l.id}",
                            data={
                                "title": l.title,
                                "subject": l.subject_id,
                                "scheduled_date": l.scheduled_date.isoformat() if l.scheduled_date else None,
                                "status": l.state.value,
                            },
                        )
                        for l in self.lessons
                    ],
                ),
            ],
        )
