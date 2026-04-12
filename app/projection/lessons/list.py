from typing import Iterable

from app.domain.lessons.aggregate import Lesson
from app.domain.students.aggregate import Student
from app.domain.subjects.aggregate import Subject
from hyperstate.response import HyperStateResponse, ViewContext, ActorContext
from hyperstate.sections import ListSection, ActionSection, ColumnDef, ListItem
from hyperstate.fields import (
    TextField, TextareaField, SelectField, DateField, FieldOption,
)
from hyperstate.nav import NavLink


TIME_SLOT_OPTIONS = [
    FieldOption(value="morning", label="Morning"),
    FieldOption(value="afternoon", label="Afternoon"),
]


class LessonListProjection:
    def __init__(
        self,
        lessons: Iterable[Lesson],
        actor: ActorContext,
        subjects: list[Subject] | None = None,
        students: list[Student] | None = None,
        student_id: str | None = None,
        subject_id: str | None = None,
        state: str | None = None,
        sort: str | None = None,
    ):
        self.lessons = list(lessons)
        self.actor = actor
        self.subjects = subjects or []
        self.students = students or []
        self.current_student_id = student_id
        self.current_subject_id = subject_id
        self.current_state = state
        self.current_sort = sort or "date_asc"

    def _sort_href(self, key: str) -> str:
        """Construct a URL that maintains filters but changes the sort."""
        params = []
        if self.current_student_id:
            params.append(f"student_id={self.current_student_id}")
        if self.current_subject_id:
            params.append(f"subject_id={self.current_subject_id}")
        if self.current_state:
            params.append(f"state={self.current_state}")

        # Toggle sort direction if already sorting by this key
        direction = "asc"
        if self.current_sort.startswith(key):
            direction = "desc" if self.current_sort.endswith("asc") else "asc"
        
        params.append(f"sort={key}_{direction}")
        return f"/lessons?{'&'.join(params)}"

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
                    key="create-new-lesson",
                    label="Create New Lesson",
                    method="GET",
                    href="/lessons/new",
                    style="primary",
                ),
                ActionSection(
                    key="filter-lessons",
                    label="Filter & Sort",
                    method="GET",
                    href="/lessons",
                    fields=[
                        SelectField(
                            name="student_id",
                            label="Student",
                            options_href="/api/students",
                            value=self.current_student_id,
                        ),
                        SelectField(
                            name="subject_id",
                            label="Subject",
                            options_href="/api/subjects",
                            value=self.current_subject_id,
                        ),
                        SelectField(
                            name="state",
                            label="Status",
                            options=[
                                FieldOption(value="", label="All Statuses"),
                                FieldOption(value="pending", label="Pending"),
                                FieldOption(value="in_progress", label="In Progress"),
                                FieldOption(value="completed", label="Completed"),
                            ],
                            value=self.current_state,
                        ),
                        SelectField(
                            name="sort",
                            label="Sort By",
                            options=[
                                FieldOption(value="date_asc", label="Date (Oldest First)"),
                                FieldOption(value="date_desc", label="Date (Newest First)"),
                                FieldOption(value="title_asc", label="Title (A-Z)"),
                                FieldOption(value="title_desc", label="Title (Z-A)"),
                            ],
                            value=self.current_sort,
                        ),
                    ],
                ),
                ListSection(
                    title="All Lessons",
                    columns=[
                        ColumnDef(key="title", label="Title", href=self._sort_href("title")),
                        ColumnDef(key="subject", label="Subject"),
                        ColumnDef(key="scheduled_date", label="Date", display="date", href=self._sort_href("date")),
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
