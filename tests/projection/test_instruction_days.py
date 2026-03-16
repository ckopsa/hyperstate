from datetime import date

import pytest

from app.hyperstate.response import ActorContext
from app.infrastructure.models.instruction_day_model import InstructionDayRow
from app.projection.reports.instruction_days import InstructionDaysProjection


@pytest.fixture
def actor():
    return ActorContext(id="parent-1", roles=["parent"])


@pytest.fixture
def no_days():
    return []


@pytest.fixture
def some_days():
    return [
        InstructionDayRow(
            date=date(2026, 1, 5),
            is_manual=False,
            lessons_completed=2,
            subjects_covered="Math,Reading",
            notes=None,
        ),
        InstructionDayRow(
            date=date(2026, 1, 6),
            is_manual=True,
            lessons_completed=0,
            subjects_covered="",
            notes="Museum field trip",
        ),
    ]


class TestInstructionDaysProjection:
    def test_summary_section_shows_counts(self, some_days, actor):
        view = InstructionDaysProjection(some_days, actor).build()
        summary = next(s for s in view.sections if s.kind == "summary")
        items = {i.label: i.value for i in summary.items}

        assert items["Days Logged"] == 2
        assert items["Days Required"] == 180
        assert items["Days Remaining"] == 178

    def test_summary_has_on_track_badge(self, some_days, actor):
        view = InstructionDaysProjection(some_days, actor).build()
        summary = next(s for s in view.sections if s.kind == "summary")
        labels = [i.label for i in summary.items]
        assert "On Track" in labels
        on_track_item = next(i for i in summary.items if i.label == "On Track")
        assert on_track_item.display == "badge"

    def test_empty_state_when_no_days(self, no_days, actor):
        view = InstructionDaysProjection(no_days, actor).build()
        empty = next((s for s in view.sections if s.kind == "empty"), None)
        assert empty is not None

    def test_list_section_with_days(self, some_days, actor):
        view = InstructionDaysProjection(some_days, actor).build()
        lst = next((s for s in view.sections if s.kind == "list"), None)
        assert lst is not None
        assert len(lst.items) == 2

    def test_list_items_have_hrefs(self, some_days, actor):
        view = InstructionDaysProjection(some_days, actor).build()
        lst = next(s for s in view.sections if s.kind == "list")
        for item in lst.items:
            assert item.href is not None
            assert "/reports/instruction-days/" in item.href

    def test_add_manual_day_action_present(self, no_days, actor):
        view = InstructionDaysProjection(no_days, actor).build()
        actions = [s for s in view.sections if s.kind == "action"]
        manual = next((a for a in actions if a.key == "add-manual-day"), None)
        assert manual is not None
        assert manual.method == "POST"
        assert manual.href == "/reports/instruction-days"
        field_names = {f.name for f in manual.fields}
        assert "date" in field_names
        assert "notes" in field_names

    def test_nav_includes_dashboard_and_export(self, no_days, actor):
        view = InstructionDaysProjection(no_days, actor).build()
        nav_hrefs = {n.href for n in view.nav}
        assert "/dashboard" in nav_hrefs
        assert "/reports/instruction-days/export" in nav_hrefs
