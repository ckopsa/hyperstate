from typing import Iterable

from app.domain.students.aggregate import Student
from app.hyperstate.response import HyperStateResponse, ViewContext, ActorContext
from app.hyperstate.sections import ListSection, ActionSection, ColumnDef, ListItem
from app.hyperstate.fields import TextField, SelectField, DateField, FieldOption
from app.hyperstate.nav import NavLink


GRADE_OPTIONS = [
    FieldOption(value="K", label="Kindergarten"),
    FieldOption(value="1st", label="1st Grade"),
    FieldOption(value="2nd", label="2nd Grade"),
    FieldOption(value="3rd", label="3rd Grade"),
    FieldOption(value="4th", label="4th Grade"),
    FieldOption(value="5th", label="5th Grade"),
    FieldOption(value="6th", label="6th Grade"),
    FieldOption(value="7th", label="7th Grade"),
    FieldOption(value="8th", label="8th Grade"),
    FieldOption(value="9th", label="9th Grade"),
    FieldOption(value="10th", label="10th Grade"),
    FieldOption(value="11th", label="11th Grade"),
    FieldOption(value="12th", label="12th Grade"),
]


class StudentListProjection:
    def __init__(self, students: Iterable[Student], actor: ActorContext):
        self.students = list(students)
        self.actor = actor

    def build(self) -> HyperStateResponse:
        return HyperStateResponse(
            view="list",
            title="Students",
            self_="/students",
            context=ViewContext(
                domain="students",
                aggregate="students",
                state="collection",
                actor=self.actor,
            ),
            nav=[NavLink(label="Dashboard", href="/dashboard", rel="parent")],
            sections=[
                ActionSection(
                    key="add-student",
                    label="Add Student",
                    method="POST",
                    href="/students",
                    fields=[
                        TextField(name="name", label="Name", required=True),
                        SelectField(name="grade_level", label="Grade Level", required=True, options=GRADE_OPTIONS),
                        DateField(name="enrollment_date", label="Enrollment Date"),
                    ],
                ),
                ListSection(
                    title="Enrolled Students",
                    columns=[
                        ColumnDef(key="name", label="Name"),
                        ColumnDef(key="grade", label="Grade"),
                        ColumnDef(key="enrolled", label="Enrollment Date", display="date"),
                    ],
                    items=[
                        ListItem(
                            href=f"/students/{s.id}",
                            data={
                                "name": s.name,
                                "grade": s.grade_level,
                                "enrolled": s.enrollment_date.isoformat(),
                            },
                        )
                        for s in self.students
                    ],
                ),
            ],
        )
