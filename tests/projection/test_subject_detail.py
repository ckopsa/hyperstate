import pytest
from datetime import date

from app.domain.subjects.aggregate import Subject
from app.domain.lessons.aggregate import Lesson
from app.domain.lessons.states import LessonState
from hyperstate.response import ActorContext
from app.projection.subjects.detail import SubjectDetailProjection
from app.projection.subjects.list import SubjectListProjection


@pytest.fixture
def actor():
    return ActorContext(id="parent-1", roles=["parent"])


@pytest.fixture
def custom_subject():
    return Subject(
        id="SUB-001",
        name="Kitchen Science",
        color="#16A34A",
        icon="🔬",
        is_custom=True,
        description="Hands-on science experiments in the kitchen.",
    )


@pytest.fixture
def standard_subject():
    return Subject(
        id="SUB-MATH",
        name="Math",
        color="#4F46E5",
        icon="📐",
        is_custom=False,
    )


def make_lesson(subject_id: str, lesson_id: str = "LES-001") -> Lesson:
    return Lesson(
        id=lesson_id,
        subject_id=subject_id,
        student_id="STU-1",
        title="Test Lesson",
        scheduled_date=date(2026, 3, 16),
        state=LessonState.PENDING,
    )


class TestSubjectDetailProjection:
    def test_properties_include_lesson_count(self, custom_subject, actor):
        lessons = [make_lesson(custom_subject.id)]
        view = SubjectDetailProjection(custom_subject, lessons, actor).build()
        props = next(s for s in view.sections if s.kind == "properties")
        keys = {p.key for p in props.data}
        assert "lesson_count" in keys
        count_item = next(p for p in props.data if p.key == "lesson_count")
        assert count_item.value == "1"

    def test_shows_lessons_list_when_lessons_exist(self, custom_subject, actor):
        lessons = [make_lesson(custom_subject.id)]
        view = SubjectDetailProjection(custom_subject, lessons, actor).build()
        lists = [s for s in view.sections if s.kind == "list"]
        assert len(lists) == 1
        assert lists[0].items[0].data["title"] == "Test Lesson"

    def test_shows_empty_section_when_no_lessons(self, custom_subject, actor):
        view = SubjectDetailProjection(custom_subject, [], actor).build()
        empty = [s for s in view.sections if s.kind == "empty"]
        assert len(empty) == 1
        assert empty[0].action is not None
        assert "lesson" in empty[0].action.label.lower()

    def test_includes_edit_action(self, custom_subject, actor):
        view = SubjectDetailProjection(custom_subject, [], actor).build()
        actions = [s for s in view.sections if s.kind == "action"]
        edit = next((a for a in actions if a.key == "edit-subject"), None)
        assert edit is not None
        assert edit.method == "PATCH"
        field_names = {f.name for f in edit.fields}
        assert field_names == {"name", "color", "icon", "description"}

    def test_delete_action_available_when_no_lessons(self, custom_subject, actor):
        view = SubjectDetailProjection(custom_subject, [], actor).build()
        actions = [s for s in view.sections if s.kind == "action"]
        delete = next((a for a in actions if a.key == "delete-subject"), None)
        assert delete is not None
        assert delete.style == "danger"
        assert delete.condition is None

    def test_delete_action_blocked_when_has_lessons(self, custom_subject, actor):
        lessons = [make_lesson(custom_subject.id)]
        view = SubjectDetailProjection(custom_subject, lessons, actor).build()
        actions = [s for s in view.sections if s.kind == "action"]
        delete = next((a for a in actions if a.key == "delete-subject"), None)
        assert delete is not None
        assert delete.condition is not None
        assert delete.condition.met is False
        assert "lesson" in delete.condition.explain.lower()

    def test_nav_includes_all_subjects_and_dashboard(self, custom_subject, actor):
        view = SubjectDetailProjection(custom_subject, [], actor).build()
        hrefs = {n.href for n in view.nav}
        assert "/subjects" in hrefs
        assert "/dashboard" in hrefs


class TestSubjectListProjection:
    def test_groups_standard_and_custom_subjects(self, standard_subject, custom_subject, actor):
        subjects = [standard_subject, custom_subject]
        view = SubjectListProjection(subjects, actor).build()
        lists = [s for s in view.sections if s.kind == "list"]
        titles = [lst.title for lst in lists]
        assert "Standard Subjects" in titles
        assert "Custom Subjects" in titles

    def test_shows_empty_section_when_no_subjects(self, actor):
        view = SubjectListProjection([], actor).build()
        empty = [s for s in view.sections if s.kind == "empty"]
        assert len(empty) == 1

    def test_includes_create_action(self, actor):
        view = SubjectListProjection([], actor).build()
        actions = [s for s in view.sections if s.kind == "action"]
        create = next((a for a in actions if a.key == "create-subject"), None)
        assert create is not None
        assert create.method == "POST"
