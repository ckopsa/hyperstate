from hyperstate.response import HyperStateResponse, ViewContext, ActorContext
from hyperstate.sections import ActionSection, ContentSection
from hyperstate.fields import (
    TextField, TextareaField, SelectField, DateField, FieldOption,
)
from hyperstate.nav import NavLink

TIME_SLOT_OPTIONS = [
    FieldOption(value="morning", label="Morning"),
    FieldOption(value="afternoon", label="Afternoon"),
]

class LessonCreateProjection:
    def __init__(self, actor: ActorContext):
        self.actor = actor

    def build(self) -> HyperStateResponse:
        return HyperStateResponse(
            view="form",
            title="Create Lesson",
            self_="/lessons/new",
            context=ViewContext(
                domain="lessons",
                aggregate="lesson",
                state="new",
                actor=self.actor,
            ),
            nav=[NavLink(label="All Lessons", href="/lessons", rel="collection")],
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
                            options_href="/api/subjects",
                        ),
                        SelectField(
                            name="student_id",
                            label="Student",
                            required=True,
                            options_href="/api/students",
                        ),
                        TextareaField(name="description", label="Description"),
                        DateField(name="scheduled_date", label="Scheduled Date"),
                        SelectField(name="time_slot", label="Time Slot", options=TIME_SLOT_OPTIONS, value="morning"),
                    ],
                ),
            ],
        )
