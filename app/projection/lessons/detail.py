from app.domain.lessons.aggregate import Lesson
from app.domain.lessons.states import LessonState
from app.hyperstate.response import HyperStateResponse, ViewContext, ActorContext
from app.hyperstate.flash import Flash
from app.hyperstate.nav import NavLink
from app.hyperstate.sections import (
    PropertiesSection, ActionSection, ActionCondition,
)
from app.hyperstate.display import PropertyItem


class LessonDetailProjection:
    def __init__(self, lesson: Lesson, actor: ActorContext):
        self.lesson = lesson
        self.actor = actor

    def build(self, flash: Flash | None = None) -> HyperStateResponse:
        l = self.lesson
        sections = [self._properties_section()]

        if action := self._start_section():
            sections.append(action)
        if action := self._complete_section():
            sections.append(action)
        if action := self._reset_section():
            sections.append(action)

        return HyperStateResponse(
            view="detail",
            title=l.title,
            self_=f"/lessons/{l.id}",
            context=ViewContext(
                domain="lessons",
                aggregate="lesson",
                state=l.state.value,
                actor=self.actor,
            ),
            flash=flash,
            nav=[
                NavLink(label="All Lessons", href="/lessons", rel="collection"),
                NavLink(label="Subject", href=f"/subjects/{l.subject_id}", rel="related"),
                NavLink(label="Student", href=f"/students/{l.student_id}", rel="related"),
            ],
            sections=sections,
        )

    def _properties_section(self) -> PropertiesSection:
        l = self.lesson
        data = [
            PropertyItem(
                key="status", label="Status",
                value=l.state.value, display="badge",
                variant=self._state_variant(),
            ),
            PropertyItem(key="subject", label="Subject", value=l.subject_id),
            PropertyItem(key="student", label="Student", value=l.student_id),
            PropertyItem(key="time_slot", label="Time Slot", value=l.time_slot),
        ]
        if l.scheduled_date:
            data.append(PropertyItem(
                key="scheduled_date", label="Scheduled Date",
                value=l.scheduled_date.isoformat(), display="date",
            ))
        if l.description:
            data.append(PropertyItem(key="description", label="Description", value=l.description))
        if l.completed_at:
            data.append(PropertyItem(
                key="completed_at", label="Completed At",
                value=l.completed_at.isoformat(), display="datetime",
            ))
        return PropertiesSection(title="Lesson Details", data=data)

    def _start_section(self) -> ActionSection | None:
        l = self.lesson
        match l.state:
            case LessonState.PENDING:
                return ActionSection(
                    key="start",
                    label="Start Lesson",
                    method="POST",
                    href=f"/lessons/{l.id}/start",
                    style="primary",
                )
            case LessonState.IN_PROGRESS | LessonState.COMPLETED:
                return ActionSection(
                    key="start",
                    label="Start Lesson",
                    method="POST",
                    href=f"/lessons/{l.id}/start",
                    condition=ActionCondition(met=False, explain="Lesson is already started."),
                )
        return None

    def _complete_section(self) -> ActionSection | None:
        l = self.lesson
        match l.state:
            case LessonState.IN_PROGRESS:
                return ActionSection(
                    key="complete",
                    label="Mark Complete",
                    method="POST",
                    href=f"/lessons/{l.id}/complete",
                    style="primary",
                )
            case LessonState.PENDING:
                return ActionSection(
                    key="complete",
                    label="Mark Complete",
                    method="POST",
                    href=f"/lessons/{l.id}/complete",
                    condition=ActionCondition(met=False, explain="Start the lesson before marking complete."),
                )
            case LessonState.COMPLETED:
                return None
        return None

    def _reset_section(self) -> ActionSection | None:
        l = self.lesson
        match l.state:
            case LessonState.IN_PROGRESS | LessonState.COMPLETED:
                return ActionSection(
                    key="reset",
                    label="Reset to Pending",
                    method="POST",
                    href=f"/lessons/{l.id}/reset",
                    style="subtle",
                )
            case _:
                return None

    def _state_variant(self) -> str:
        return {
            LessonState.PENDING: "secondary",
            LessonState.IN_PROGRESS: "warning",
            LessonState.COMPLETED: "success",
        }.get(self.lesson.state, "secondary")
