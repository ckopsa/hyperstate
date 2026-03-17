from datetime import date, datetime, UTC

import pytest

from app.domain.lessons.aggregate import Lesson
from app.domain.lessons.states import LessonState
from app.hyperstate.response import ActorContext
from app.projection.lessons.detail import LessonDetailProjection


def flatten_sections(sections):
    """Recursively flatten GroupSection trees into a flat list of leaf sections."""
    result = []
    for s in sections:
        if s.kind == "group":
            result.extend(flatten_sections(s.sections))
        else:
            result.append(s)
    return result


@pytest.fixture
def student_actor():
    return ActorContext(id="student-1", roles=["student"])


@pytest.fixture
def parent_actor():
    return ActorContext(id="parent-1", roles=["parent"])


@pytest.fixture
def today():
    return date(2026, 3, 15)


@pytest.fixture
def pending_lesson(today):
    return Lesson(
        id="LES-001",
        subject_id="SUB-MATH",
        student_id="STU-DEMO",
        title="Addition",
        time_slot="morning",
        scheduled_date=today,
        state=LessonState.PENDING,
    )


@pytest.fixture
def in_progress_lesson(today):
    return Lesson(
        id="LES-002",
        subject_id="SUB-MATH",
        student_id="STU-DEMO",
        title="Subtraction",
        time_slot="morning",
        scheduled_date=today,
        state=LessonState.IN_PROGRESS,
    )


@pytest.fixture
def completed_lesson(today):
    return Lesson(
        id="LES-003",
        subject_id="SUB-MATH",
        student_id="STU-DEMO",
        title="Multiplication",
        time_slot="morning",
        scheduled_date=today,
        state=LessonState.COMPLETED,
        completed_at=datetime(2026, 3, 15, 10, 0, tzinfo=UTC),
        completed_by="student-1",
    )


class TestStudentCompleteAction:
    def test_student_sees_i_finished_this_when_in_progress(self, student_actor, in_progress_lesson):
        view = LessonDetailProjection(in_progress_lesson, student_actor).build()
        sections = flatten_sections(view.sections)
        actions = [s for s in sections if s.kind == "action"]
        complete = next((a for a in actions if a.key == "complete"), None)
        assert complete is not None
        assert complete.label == "I finished this!"
        assert complete.condition is None
        assert complete.style == "primary"

    def test_student_can_complete_from_pending(self, student_actor, pending_lesson):
        view = LessonDetailProjection(pending_lesson, student_actor).build()
        sections = flatten_sections(view.sections)
        actions = [s for s in sections if s.kind == "action"]
        complete = next((a for a in actions if a.key == "complete"), None)
        assert complete is not None
        assert complete.label == "I finished this!"
        assert complete.condition is None

    def test_parent_sees_mark_complete_when_in_progress(self, parent_actor, in_progress_lesson):
        view = LessonDetailProjection(in_progress_lesson, parent_actor).build()
        sections = flatten_sections(view.sections)
        actions = [s for s in sections if s.kind == "action"]
        complete = next((a for a in actions if a.key == "complete"), None)
        assert complete is not None
        assert complete.label == "Mark Complete"

    def test_parent_cannot_complete_from_pending(self, parent_actor, pending_lesson):
        view = LessonDetailProjection(pending_lesson, parent_actor).build()
        sections = flatten_sections(view.sections)
        actions = [s for s in sections if s.kind == "action"]
        complete = next((a for a in actions if a.key == "complete"), None)
        assert complete is not None
        assert complete.condition is not None
        assert complete.condition.met is False

    def test_context_has_student_actor(self, student_actor, pending_lesson):
        view = LessonDetailProjection(pending_lesson, student_actor).build()
        assert view.context is not None
        assert view.context.actor is not None
        assert "student" in view.context.actor.roles


class TestCompletedLessonDetail:
    def test_completed_at_shown(self, parent_actor, completed_lesson):
        view = LessonDetailProjection(completed_lesson, parent_actor).build()
        sections = flatten_sections(view.sections)
        props = next(s for s in sections if s.kind == "properties")
        keys = [p.key for p in props.data]
        assert "completed_at" in keys

    def test_completed_by_shown(self, parent_actor, completed_lesson):
        view = LessonDetailProjection(completed_lesson, parent_actor).build()
        sections = flatten_sections(view.sections)
        props = next(s for s in sections if s.kind == "properties")
        by_item = next((p for p in props.data if p.key == "completed_by"), None)
        assert by_item is not None
        assert by_item.value == "student-1"
        assert by_item.display == "badge"
        assert by_item.variant == "success"

    def test_no_complete_action_when_completed(self, student_actor, completed_lesson):
        view = LessonDetailProjection(completed_lesson, student_actor).build()
        sections = flatten_sections(view.sections)
        actions = [s for s in sections if s.kind == "action"]
        complete = next((a for a in actions if a.key == "complete"), None)
        assert complete is None
