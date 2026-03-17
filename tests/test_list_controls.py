"""Tests for ListSection search/filter/sort controls contract."""
import pytest
from pydantic import ValidationError

from hyperstate.sections import (
    ListSection,
    ListControls,
    SearchControl,
    FilterControl,
    FilterOption,
    SortOption,
    ColumnDef,
    ListItem,
)


class TestSearchControl:
    def test_minimal(self):
        s = SearchControl(href="/lessons")
        assert s.href == "/lessons"
        assert s.param == "q"
        assert s.value is None
        assert s.placeholder is None

    def test_with_all_fields(self):
        s = SearchControl(
            href="/lessons",
            param="search",
            value="fractions",
            placeholder="Search lessons...",
        )
        assert s.param == "search"
        assert s.value == "fractions"
        assert s.placeholder == "Search lessons..."


class TestFilterOption:
    def test_minimal(self):
        o = FilterOption(value="pending", label="Pending", href="/lessons?status=pending")
        assert o.value == "pending"
        assert o.active is False
        assert o.count is None

    def test_active_with_count(self):
        o = FilterOption(value="done", label="Done", href="/lessons?status=done", active=True, count=7)
        assert o.active is True
        assert o.count == 7


class TestFilterControl:
    def test_minimal(self):
        fc = FilterControl(
            key="status",
            label="Status",
            options=[
                FilterOption(value="pending", label="Pending", href="/lessons?status=pending"),
            ],
        )
        assert fc.key == "status"
        assert fc.clear_href is None
        assert len(fc.options) == 1

    def test_with_clear_href(self):
        fc = FilterControl(
            key="status",
            label="Status",
            options=[],
            clear_href="/lessons",
        )
        assert fc.clear_href == "/lessons"


class TestSortOption:
    def test_inactive(self):
        s = SortOption(key="title", label="Title", href="/lessons?sort=title&dir=asc")
        assert s.active is False
        assert s.direction is None

    def test_active_desc(self):
        s = SortOption(
            key="scheduled_date",
            label="Date",
            href="/lessons?sort=date&dir=desc",
            active=True,
            direction="desc",
        )
        assert s.active is True
        assert s.direction == "desc"

    def test_direction_values(self):
        SortOption(key="x", label="X", href="/x", direction="asc")
        SortOption(key="x", label="X", href="/x", direction="desc")
        with pytest.raises(ValidationError):
            SortOption(key="x", label="X", href="/x", direction="sideways")


class TestListControls:
    def test_empty_defaults(self):
        c = ListControls()
        assert c.search is None
        assert c.filters == []
        assert c.sort_options == []
        assert c.clear_href is None

    def test_full(self):
        c = ListControls(
            search=SearchControl(href="/lessons", value="math"),
            filters=[
                FilterControl(
                    key="status",
                    label="Status",
                    options=[
                        FilterOption(value="pending", label="Pending", href="/lessons?status=pending"),
                        FilterOption(value="done", label="Done", href="/lessons?status=done", active=True),
                    ],
                    clear_href="/lessons?q=math",
                )
            ],
            sort_options=[
                SortOption(key="title", label="Title", href="/lessons?sort=title&dir=asc"),
                SortOption(key="date", label="Date", href="/lessons?sort=date&dir=desc", active=True, direction="desc"),
            ],
            clear_href="/lessons",
        )
        assert c.search.value == "math"
        assert len(c.filters) == 1
        assert c.filters[0].options[1].active is True
        assert len(c.sort_options) == 2
        assert c.sort_options[1].active is True
        assert c.clear_href == "/lessons"


class TestListSectionControls:
    """ListSection.controls is optional — existing callers are unaffected."""

    def _make_list_section(self, controls=None):
        return ListSection(
            columns=[ColumnDef(key="title", label="Title")],
            items=[ListItem(data={"title": "Fractions"})],
            controls=controls,
        )

    def test_controls_default_none(self):
        section = self._make_list_section()
        assert section.controls is None

    def test_controls_roundtrip(self):
        controls = ListControls(
            search=SearchControl(href="/lessons", value="fractions"),
            sort_options=[
                SortOption(key="title", label="Title", href="/lessons?sort=title&dir=asc"),
            ],
        )
        section = self._make_list_section(controls=controls)
        assert section.controls.search.value == "fractions"
        assert section.controls.sort_options[0].key == "title"

    def test_json_serialization(self):
        controls = ListControls(
            search=SearchControl(href="/lessons"),
            filters=[
                FilterControl(
                    key="status",
                    label="Status",
                    options=[FilterOption(value="pending", label="Pending", href="/lessons?status=pending")],
                )
            ],
        )
        section = self._make_list_section(controls=controls)
        data = section.model_dump()
        assert data["controls"]["search"]["href"] == "/lessons"
        assert data["controls"]["filters"][0]["key"] == "status"
        assert data["controls"]["sort_options"] == []
        assert data["controls"]["clear_href"] is None
