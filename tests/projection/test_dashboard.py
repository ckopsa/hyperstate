from datetime import date, datetime, UTC

import pytest

from app.domain.lessons.aggregate import Lesson
from app.domain.lessons.states import LessonState
from app.domain.subjects.aggregate import Subject
from app.hyperstate.response import ActorContext
from app.projection.dashboard.view import DashboardProjection


@pytest.fixture
def actor():
    return ActorContext(id="user-1", roles=["parent"])


@pytest.fixture
def subject():
    return Subject(id="SUB-MATH", name="Math", color="#000", icon="📐", is_custom=False)


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
def completed_lesson(today):
    return Lesson(
        id="LES-002",
        subject_id="SUB-MATH",
        student_id="STU-DEMO",
        title="Subtraction",
        time_slot="afternoon",
        scheduled_date=today,
        state=LessonState.COMPLETED,
        completed_at=datetime(2026, 3, 15, 14, 0, tzinfo=UTC),
    )


class TestDashboardWithLessons:
    def test_summary_counts(self, actor, subject, pending_lesson, completed_lesson):
        proj = DashboardProjection(
            today_lessons=[pending_lesson, completed_lesson],
            recently_completed=[completed_lesson],
            instruction_days=5,
            subjects={"SUB-MATH": subject},
            actor=actor,
        )
        view = proj.build()
        summary = next(s for s in view.sections if s.kind == "summary")
        items = {i.label: i.value for i in summary.items}

        assert items["Today's Lessons"] == 2
        assert items["Completed"] == 1
        assert items["Instruction Days"] == 5
        assert items["Year Progress"] == pytest.approx(5 / 180, abs=1e-3)

    def test_schedule_list_present(self, actor, subject, pending_lesson):
        proj = DashboardProjection(
            today_lessons=[pending_lesson],
            recently_completed=[],
            instruction_days=0,
            subjects={"SUB-MATH": subject},
            actor=actor,
        )
        view = proj.build()
        lists = [s for s in view.sections if s.kind == "list"]
        assert any(s.title == "Today's Schedule" for s in lists)

    def test_schedule_item_subject_name(self, actor, subject, pending_lesson):
        proj = DashboardProjection(
            today_lessons=[pending_lesson],
            recently_completed=[],
            instruction_days=0,
            subjects={"SUB-MATH": subject},
            actor=actor,
        )
        view = proj.build()
        schedule = next(s for s in view.sections if s.kind == "list")
        assert schedule.items[0].data["subject"] == "Math"

    def test_timeline_shows_recent_completed(self, actor, subject, completed_lesson):
        proj = DashboardProjection(
            today_lessons=[completed_lesson],
            recently_completed=[completed_lesson],
            instruction_days=1,
            subjects={"SUB-MATH": subject},
            actor=actor,
        )
        view = proj.build()
        timelines = [s for s in view.sections if s.kind == "timeline"]
        assert len(timelines) == 1
        assert timelines[0].events[0].label == "Subtraction"

    def test_instruction_days_has_href(self, actor, subject, pending_lesson):
        proj = DashboardProjection(
            today_lessons=[pending_lesson],
            recently_completed=[],
            instruction_days=10,
            subjects={"SUB-MATH": subject},
            actor=actor,
        )
        view = proj.build()
        summary = next(s for s in view.sections if s.kind == "summary")
        instr = next(i for i in summary.items if i.label == "Instruction Days")
        assert instr.href == "/reports/instruction-days"


class TestDashboardInlineActions:
    def test_pending_lesson_has_done_action(self, actor, subject, pending_lesson):
        proj = DashboardProjection(
            today_lessons=[pending_lesson],
            recently_completed=[],
            instruction_days=0,
            subjects={"SUB-MATH": subject},
            actor=actor,
        )
        view = proj.build()
        schedule = next(s for s in view.sections if s.kind == "list")
        item = schedule.items[0]
        assert len(item.actions) == 2
        action_keys = {a.key for a in item.actions}
        assert "complete-task" in action_keys
        assert "push-tomorrow" in action_keys
        complete_action = next(a for a in item.actions if a.key == "complete-task")
        assert complete_action.label == "Done!"
        assert complete_action.method == "POST"
        assert complete_action.href == f"/lessons/{pending_lesson.id}/complete"
        assert complete_action.style == "primary"

    def test_completed_lesson_has_no_inline_action(self, actor, subject, completed_lesson):
        proj = DashboardProjection(
            today_lessons=[completed_lesson],
            recently_completed=[completed_lesson],
            instruction_days=1,
            subjects={"SUB-MATH": subject},
            actor=actor,
        )
        view = proj.build()
        schedule = next(s for s in view.sections if s.kind == "list")
        item = schedule.items[0]
        assert item.actions == []

    def test_flash_is_passed_through(self, actor, subject):
        from app.hyperstate.flash import Flash
        proj = DashboardProjection(
            today_lessons=[],
            recently_completed=[],
            instruction_days=0,
            subjects={},
            actor=actor,
        )
        flash = Flash(type="success", title="Great job!", body="Done.")
        view = proj.build(flash=flash)
        assert view.flash is not None
        assert view.flash.title == "Great job!"


class TestDashboardEmpty:
    def test_empty_section_when_no_lessons(self, actor, subject):
        proj = DashboardProjection(
            today_lessons=[],
            recently_completed=[],
            instruction_days=0,
            subjects={"SUB-MATH": subject},
            actor=actor,
        )
        view = proj.build()
        empties = [s for s in view.sections if s.kind == "empty"]
        assert len(empties) == 1
        assert "No lessons" in empties[0].title

    def test_nav_links(self, actor, subject):
        proj = DashboardProjection(
            today_lessons=[],
            recently_completed=[],
            instruction_days=0,
            subjects={},
            actor=actor,
        )
        view = proj.build()
        hrefs = {n.href for n in view.nav}
        assert "/calendar" in hrefs
        assert "/subjects" in hrefs
        assert "/reports" in hrefs
