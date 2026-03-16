from app.domain.students.aggregate import Student
from app.hyperstate.response import HyperStateResponse, ViewContext, ActorContext
from app.hyperstate.flash import Flash
from app.hyperstate.nav import NavLink
from app.hyperstate.sections import PropertiesSection
from app.hyperstate.display import PropertyItem


class StudentDetailProjection:
    def __init__(self, student: Student, actor: ActorContext):
        self.student = student
        self.actor = actor

    def build(self, flash: Flash | None = None) -> HyperStateResponse:
        s = self.student
        return HyperStateResponse(
            view="detail",
            title=s.name,
            self_=f"/students/{s.id}",
            context=ViewContext(
                domain="students",
                aggregate="student",
                state="active",
                actor=self.actor,
            ),
            flash=flash,
            nav=[
                NavLink(label="All Students", href="/students", rel="collection"),
                NavLink(label="Dashboard", href="/dashboard", rel="parent"),
            ],
            sections=[
                PropertiesSection(
                    title="Student Details",
                    data=[
                        PropertyItem(key="name", label="Name", value=s.name),
                        PropertyItem(key="grade_level", label="Grade Level", value=s.grade_level),
                        PropertyItem(
                            key="enrollment_date", label="Enrollment Date",
                            value=s.enrollment_date.isoformat(), display="date",
                        ),
                    ],
                ),
            ],
        )
