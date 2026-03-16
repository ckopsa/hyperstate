"""Tests for dashboard projection defer actions and next_weekday helper."""
from datetime import date

import pytest

from app.domain.lessons.aggregate import Lesson, next_weekday
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


class TestNextWeekday:
    def test_monday_returns_tuesday(self):
        mon = date(2026, 3, 16)  # Monday
        assert next_weekday(mon) == date(2026, 3, 17)

    def test_friday_skips_weekend_to_monday(self):
        fri = date(2026, 3, 20)  # Friday
        assert next_weekday(fri) == date(2026, 3, 23)

    def test_saturday_skips_to_monday(self):
        sat = date(2026, 3, 21)
        assert next_weekday(sat) == date(2026, 3, 23)

    def test_sunday_skips_to_monday(self):
        sun = date(2026, 3, 22)
        assert next_weekday(sun) == date(2026, 3, 23)


class TestLessonDefer:
    def test_defer_pending_moves_to_next_weekday(self):
        lesson = Lesson(
            id="LES-001",
            subject_id="SUB-MATH",
            student_id="STU-DEMO",
            title="Math",
            time_slot="morning",
            scheduled_date=date(2026, 3, 16),
            state=LessonState.PENDING,
        )
        lesson.defer()
        assert lesson.scheduled_date == date(2026, 3, 17)

    def test_defer_completed_raises(self):
        from app.domain.lessons.errors import LessonError
        lesson = Lesson(
            id="LES-001",
            subject_id="SUB-MATH",
            student_id="STU-DEMO",
            title="Math",
            time_slot="morning",
            scheduled_date=date(2026, 3, 16),
            state=LessonState.COMPLETED,
        )
        with pytest.raises(LessonError):
            lesson.defer()

    def test_defer_unscheduled_raises(self):
        from app.domain.lessons.errors import LessonError
        lesson = Lesson(
            id="LES-001",
            subject_id="SUB-MATH",
            student_id="STU-DEMO",
            title="Math",
            time_slot="morning",
            scheduled_date=None,
            state=LessonState.PENDING,
        )
        with pytest.raises(LessonError):
            lesson.defer()


class TestDashboardDeferActions:
    def _make_lesson(self, lesson_id: str, state: LessonState, today: date) -> Lesson:
        return Lesson(
            id=lesson_id,
            subject_id="SUB-MATH",
            student_id="STU-DEMO",
            title="Test",
            time_slot="morning",
            scheduled_date=today,
            state=state,
        )

    def test_incomplete_lesson_has_push_tomorrow_action(self, actor, subject):
        today = date(2026, 3, 16)
        lesson = self._make_lesson("LES-001", LessonState.PENDING, today)
        proj = DashboardProjection(
            today_lessons=[lesson],
            recently_completed=[],
            instruction_days=0,
            subjects={"SUB-MATH": subject},
            actor=actor,
        )
        view = proj.build()
        schedule = next(s for s in view.sections if s.kind == "list")
        actions = schedule.items[0].actions
        assert any(a.key == "push-tomorrow" for a in actions)

    def test_completed_lesson_has_no_push_tomorrow_action(self, actor, subject):
        from datetime import datetime, UTC
        today = date(2026, 3, 16)
        lesson = Lesson(
            id="LES-002",
            subject_id="SUB-MATH",
            student_id="STU-DEMO",
            title="Done",
            time_slot="afternoon",
            scheduled_date=today,
            state=LessonState.COMPLETED,
            completed_at=datetime(2026, 3, 16, 14, 0, tzinfo=UTC),
        )
        proj = DashboardProjection(
            today_lessons=[lesson],
            recently_completed=[lesson],
            instruction_days=1,
            subjects={"SUB-MATH": subject},
            actor=actor,
        )
        view = proj.build()
        schedule = next(s for s in view.sections if s.kind == "list")
        actions = schedule.items[0].actions
        assert not any(a.key == "push-tomorrow" for a in actions)

    def test_push_all_action_present_when_incomplete_lessons_exist(self, actor, subject):
        today = date(2026, 3, 16)
        lesson = self._make_lesson("LES-001", LessonState.PENDING, today)
        proj = DashboardProjection(
            today_lessons=[lesson],
            recently_completed=[],
            instruction_days=0,
            subjects={"SUB-MATH": subject},
            actor=actor,
        )
        view = proj.build()
        actions = [s for s in view.sections if s.kind == "action"]
        assert any(a.key == "push-all-remaining" for a in actions)

    def test_no_push_all_action_when_all_completed(self, actor, subject):
        from datetime import datetime, UTC
        today = date(2026, 3, 16)
        lesson = Lesson(
            id="LES-001",
            subject_id="SUB-MATH",
            student_id="STU-DEMO",
            title="Done",
            time_slot="morning",
            scheduled_date=today,
            state=LessonState.COMPLETED,
            completed_at=datetime(2026, 3, 16, 14, 0, tzinfo=UTC),
        )
        proj = DashboardProjection(
            today_lessons=[lesson],
            recently_completed=[lesson],
            instruction_days=1,
            subjects={"SUB-MATH": subject},
            actor=actor,
        )
        view = proj.build()
        actions = [s for s in view.sections if s.kind == "action"]
        assert not any(a.key == "push-all-remaining" for a in actions)

    def test_push_tomorrow_action_href(self, actor, subject):
        today = date(2026, 3, 16)
        lesson = self._make_lesson("LES-001", LessonState.PENDING, today)
        proj = DashboardProjection(
            today_lessons=[lesson],
            recently_completed=[],
            instruction_days=0,
            subjects={"SUB-MATH": subject},
            actor=actor,
        )
        view = proj.build()
        schedule = next(s for s in view.sections if s.kind == "list")
        push_action = next(a for a in schedule.items[0].actions if a.key == "push-tomorrow")
        assert push_action.href == "/lessons/LES-001/defer"
        assert push_action.method == "POST"
        assert push_action.style == "subtle"
