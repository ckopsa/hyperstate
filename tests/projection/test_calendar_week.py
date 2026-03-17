import pytest
from datetime import date

from app.domain.lessons.aggregate import Lesson
from app.domain.lessons.states import LessonState
from app.domain.subjects.aggregate import Subject
from hyperstate.response import ActorContext
from app.projection.calendar.week import CalendarWeekProjection


@pytest.fixture
def actor():
    return ActorContext(id="parent-1", roles=["parent"])


@pytest.fixture
def subjects():
    return {
        "SUB-MATH": Subject(id="SUB-MATH", name="Math", color="#4F46E5", icon="📐", is_custom=False),
        "SUB-READ": Subject(id="SUB-READ", name="Reading", color="#7C3AED", icon="📚", is_custom=False),
    }


@pytest.fixture
def week_start():
    # Monday 2026-03-16
    return date(2026, 3, 16)


@pytest.fixture
def lessons(week_start):
    return [
        Lesson(
            id="LES-001",
            subject_id="SUB-MATH",
            student_id="STU-1",
            title="Addition",
            scheduled_date=week_start,
            time_slot="morning",
            state=LessonState.COMPLETED,
        ),
        Lesson(
            id="LES-002",
            subject_id="SUB-READ",
            student_id="STU-1",
            title="Chapter 1",
            scheduled_date=date(2026, 3, 17),
            time_slot="afternoon",
            state=LessonState.PENDING,
        ),
    ]


class TestCalendarWeekProjection:
    def test_view_is_dashboard(self, lessons, subjects, week_start, actor):
        view = CalendarWeekProjection(lessons, subjects, week_start, actor).build()
        assert view.view == "dashboard"

    def test_title_contains_week_date(self, lessons, subjects, week_start, actor):
        view = CalendarWeekProjection(lessons, subjects, week_start, actor).build()
        assert "March 16, 2026" in view.title

    def test_summary_section_counts(self, lessons, subjects, week_start, actor):
        view = CalendarWeekProjection(lessons, subjects, week_start, actor).build()
        summary = next(s for s in view.sections if s.kind == "summary")
        items = {item.label: item.value for item in summary.items}
        assert items["Lessons Planned"] == 2
        assert items["Completed"] == 1
        assert items["Remaining"] == 1

    def test_group_section_present(self, lessons, subjects, week_start, actor):
        view = CalendarWeekProjection(lessons, subjects, week_start, actor).build()
        groups = [s for s in view.sections if s.kind == "group"]
        assert len(groups) == 1
        assert groups[0].layout == "columns"

    def test_daily_sections_cover_seven_days(self, lessons, subjects, week_start, actor):
        view = CalendarWeekProjection(lessons, subjects, week_start, actor).build()
        group = next(s for s in view.sections if s.kind == "group")
        assert len(group.sections) == 7

    def test_monday_has_lesson(self, lessons, subjects, week_start, actor):
        view = CalendarWeekProjection(lessons, subjects, week_start, actor).build()
        group = next(s for s in view.sections if s.kind == "group")
        monday = group.sections[0]
        assert monday.kind == "list"
        assert len(monday.items) == 1
        assert monday.items[0].data["lesson_title"] == "Addition"

    def test_subject_name_resolved(self, lessons, subjects, week_start, actor):
        view = CalendarWeekProjection(lessons, subjects, week_start, actor).build()
        group = next(s for s in view.sections if s.kind == "group")
        monday = group.sections[0]
        assert "Math" in monday.items[0].data["subject"]

    def test_move_lesson_action_present(self, lessons, subjects, week_start, actor):
        view = CalendarWeekProjection(lessons, subjects, week_start, actor).build()
        actions = [s for s in view.sections if s.kind == "action"]
        move = next((a for a in actions if a.key == "move-lesson"), None)
        assert move is not None
        assert move.href == "/calendar/move"
        field_names = {f.name for f in move.fields}
        assert {"lesson_id", "target_date", "time_slot", "week_start"} == field_names

    def test_shift_week_action_present(self, lessons, subjects, week_start, actor):
        view = CalendarWeekProjection(lessons, subjects, week_start, actor).build()
        actions = [s for s in view.sections if s.kind == "action"]
        shift = next((a for a in actions if a.key == "shift-week"), None)
        assert shift is not None
        assert shift.href == "/calendar/shift-week"
        field_names = {f.name for f in shift.fields}
        assert {"direction", "days", "week_start"} == field_names

    def test_nav_has_prev_next_and_dashboard(self, lessons, subjects, week_start, actor):
        view = CalendarWeekProjection(lessons, subjects, week_start, actor).build()
        nav_rels = {link.rel for link in view.nav}
        assert "prev" in nav_rels
        assert "next" in nav_rels
        assert "parent" in nav_rels
