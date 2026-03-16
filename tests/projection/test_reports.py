"""Tests for the reports feature (QA checkpoints from hyp-3ag)."""
from __future__ import annotations

import os
import tempfile
from datetime import date, datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.hyperstate.response import ActorContext
from app.web.reports.routes import GenerateTranscriptBody, _write_csv, _write_pdf


@pytest.fixture
def actor():
    return ActorContext(id="parent-1", roles=["parent"])


@pytest.fixture
def student():
    s = MagicMock()
    s.id = "STU-DEMO"
    s.name = "Alice"
    s.grade_level = "4th"
    return s


@pytest.fixture
def subject_math():
    s = MagicMock()
    s.id = "SUB-MATH"
    s.name = "Math"
    return s


@pytest.fixture
def completed_lesson(subject_math):
    from app.domain.lessons.aggregate import Lesson
    from app.domain.lessons.states import LessonState
    return Lesson(
        id="LES-001",
        subject_id="SUB-MATH",
        student_id="STU-DEMO",
        title="Addition and Subtraction",
        description="Practice basic addition.",
        scheduled_date=date(2026, 1, 10),
        state=LessonState.COMPLETED,
        completed_at=datetime(2026, 1, 10, 12, 0, tzinfo=UTC),
    )


@pytest.fixture
def body_pdf():
    return GenerateTranscriptBody(
        student_id="STU-DEMO",
        date_range_start=date(2026, 1, 1),
        date_range_end=date(2026, 3, 31),
        include_grades=True,
        include_notes=False,
        format="pdf",
    )


@pytest.fixture
def body_csv():
    return GenerateTranscriptBody(
        student_id="STU-DEMO",
        date_range_start=date(2026, 1, 1),
        date_range_end=date(2026, 3, 31),
        include_grades=True,
        include_notes=True,
        format="csv",
    )


class TestGenerateTranscriptBody:
    def test_date_range_valid_when_start_equals_end(self):
        body = GenerateTranscriptBody(
            student_id="STU-1",
            date_range_start=date(2026, 1, 1),
            date_range_end=date(2026, 1, 1),
            format="pdf",
        )
        assert body.date_range_start == body.date_range_end

    def test_default_format_is_pdf(self):
        body = GenerateTranscriptBody(
            student_id="STU-1",
            date_range_start=date(2026, 1, 1),
            date_range_end=date(2026, 3, 31),
        )
        assert body.format == "pdf"

    def test_include_grades_defaults_true(self):
        body = GenerateTranscriptBody(
            student_id="STU-1",
            date_range_start=date(2026, 1, 1),
            date_range_end=date(2026, 3, 31),
        )
        assert body.include_grades is True

    def test_include_notes_defaults_false(self):
        body = GenerateTranscriptBody(
            student_id="STU-1",
            date_range_start=date(2026, 1, 1),
            date_range_end=date(2026, 3, 31),
        )
        assert body.include_notes is False


class TestPdfGeneration:
    def test_writes_pdf_file(self, student, completed_lesson, body_pdf, subject_math):
        subjects_map = {subject_math.id: subject_math}
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            filepath = f.name
        try:
            page_count = _write_pdf(filepath, student, [completed_lesson], subjects_map, body_pdf)
            assert os.path.exists(filepath)
            assert os.path.getsize(filepath) > 0
            assert page_count >= 1
            # Verify it's a PDF (starts with %PDF)
            with open(filepath, "rb") as f:
                header = f.read(4)
            assert header == b"%PDF"
        finally:
            os.unlink(filepath)

    def test_pdf_with_no_lessons(self, student, body_pdf):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            filepath = f.name
        try:
            page_count = _write_pdf(filepath, student, [], {}, body_pdf)
            assert os.path.exists(filepath)
            assert page_count >= 1
        finally:
            os.unlink(filepath)

    def test_pdf_with_notes_enabled(self, student, completed_lesson, body_pdf, subject_math):
        body_with_notes = GenerateTranscriptBody(
            student_id="STU-DEMO",
            date_range_start=date(2026, 1, 1),
            date_range_end=date(2026, 3, 31),
            include_notes=True,
            format="pdf",
        )
        subjects_map = {subject_math.id: subject_math}
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            filepath = f.name
        try:
            page_count = _write_pdf(filepath, student, [completed_lesson], subjects_map, body_with_notes)
            assert page_count >= 1
        finally:
            os.unlink(filepath)


class TestCsvGeneration:
    def test_writes_csv_file(self, student, completed_lesson, body_csv, subject_math):
        subjects_map = {subject_math.id: subject_math}
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            filepath = f.name
        try:
            _write_csv(filepath, student, [completed_lesson], subjects_map, body_csv)
            assert os.path.exists(filepath)
            with open(filepath, "r") as f:
                content = f.read()
            # Should contain student name in header
            assert "Alice" in content
            # Should contain lesson title
            assert "Addition and Subtraction" in content
            # Should contain subject name
            assert "Math" in content
        finally:
            os.unlink(filepath)

    def test_csv_includes_description_when_include_notes_true(self, student, completed_lesson, body_csv, subject_math):
        subjects_map = {subject_math.id: subject_math}
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            filepath = f.name
        try:
            _write_csv(filepath, student, [completed_lesson], subjects_map, body_csv)
            with open(filepath, "r") as f:
                content = f.read()
            assert "Practice basic addition." in content
        finally:
            os.unlink(filepath)

    def test_csv_excludes_description_when_include_notes_false(self, student, completed_lesson, subject_math):
        body = GenerateTranscriptBody(
            student_id="STU-DEMO",
            date_range_start=date(2026, 1, 1),
            date_range_end=date(2026, 3, 31),
            include_notes=False,
            format="csv",
        )
        subjects_map = {subject_math.id: subject_math}
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            filepath = f.name
        try:
            _write_csv(filepath, student, [completed_lesson], subjects_map, body)
            with open(filepath, "r") as f:
                content = f.read()
            assert "Practice basic addition." not in content
        finally:
            os.unlink(filepath)


class TestTranscriptRouteLogic:
    """Test the date range validation logic in the generate route."""

    @pytest.mark.asyncio
    async def test_invalid_date_range_returns_error(self, actor):
        from app.web.reports.routes import generate_transcript

        body = GenerateTranscriptBody(
            student_id="STU-DEMO",
            date_range_start=date(2026, 3, 31),
            date_range_end=date(2026, 1, 1),  # end before start
            format="pdf",
        )
        db_mock = AsyncMock()
        result = await generate_transcript(body, db=db_mock, actor=actor)
        assert result.view == "error"
        assert "date" in result.sections[0].body.lower()

    @pytest.mark.asyncio
    async def test_generate_returns_detail_view_with_pdf_download_link(self, actor, student, completed_lesson, subject_math):
        """QA checkpoint: PDF download nav link has type: application/pdf."""
        from app.web.reports.routes import generate_transcript

        body = GenerateTranscriptBody(
            student_id="STU-DEMO",
            date_range_start=date(2026, 1, 1),
            date_range_end=date(2026, 3, 31),
            format="pdf",
        )

        student_repo_mock = AsyncMock()
        student_repo_mock.get.return_value = student
        lesson_repo_mock = AsyncMock()
        lesson_repo_mock.list_by_date_range.return_value = [completed_lesson]
        subject_repo_mock = AsyncMock()
        subject_repo_mock.list_all.return_value = [subject_math]

        with patch("app.web.reports.routes.StudentRepository", return_value=student_repo_mock), \
             patch("app.web.reports.routes.LessonRepository", return_value=lesson_repo_mock), \
             patch("app.web.reports.routes.SubjectRepository", return_value=subject_repo_mock), \
             patch("app.web.reports.routes._ensure_reports_dir", return_value=tempfile.mkdtemp()):
            db_mock = AsyncMock()
            result = await generate_transcript(body, db=db_mock, actor=actor)

        assert result.view == "detail"
        download_links = [n for n in result.nav if n.type == "application/pdf"]
        assert len(download_links) == 1
        assert "/download" in download_links[0].href

    @pytest.mark.asyncio
    async def test_generate_csv_returns_csv_mime_type(self, actor, student, completed_lesson, subject_math):
        """CSV format option produces different output (type: text/csv)."""
        from app.web.reports.routes import generate_transcript

        body = GenerateTranscriptBody(
            student_id="STU-DEMO",
            date_range_start=date(2026, 1, 1),
            date_range_end=date(2026, 3, 31),
            format="csv",
        )

        student_repo_mock = AsyncMock()
        student_repo_mock.get.return_value = student
        lesson_repo_mock = AsyncMock()
        lesson_repo_mock.list_by_date_range.return_value = [completed_lesson]
        subject_repo_mock = AsyncMock()
        subject_repo_mock.list_all.return_value = [subject_math]

        with patch("app.web.reports.routes.StudentRepository", return_value=student_repo_mock), \
             patch("app.web.reports.routes.LessonRepository", return_value=lesson_repo_mock), \
             patch("app.web.reports.routes.SubjectRepository", return_value=subject_repo_mock), \
             patch("app.web.reports.routes._ensure_reports_dir", return_value=tempfile.mkdtemp()):
            db_mock = AsyncMock()
            result = await generate_transcript(body, db=db_mock, actor=actor)

        assert result.view == "detail"
        csv_links = [n for n in result.nav if n.type == "text/csv"]
        assert len(csv_links) == 1

    @pytest.mark.asyncio
    async def test_empty_lesson_range_shows_meaningful_message(self, actor, student, subject_math):
        """QA checkpoint: empty date range returns helpful state, not 500."""
        from app.web.reports.routes import generate_transcript

        body = GenerateTranscriptBody(
            student_id="STU-DEMO",
            date_range_start=date(2026, 1, 1),
            date_range_end=date(2026, 3, 31),
            format="pdf",
        )

        student_repo_mock = AsyncMock()
        student_repo_mock.get.return_value = student
        lesson_repo_mock = AsyncMock()
        lesson_repo_mock.list_by_date_range.return_value = []  # no lessons
        subject_repo_mock = AsyncMock()
        subject_repo_mock.list_all.return_value = []

        with patch("app.web.reports.routes.StudentRepository", return_value=student_repo_mock), \
             patch("app.web.reports.routes.LessonRepository", return_value=lesson_repo_mock), \
             patch("app.web.reports.routes.SubjectRepository", return_value=subject_repo_mock), \
             patch("app.web.reports.routes._ensure_reports_dir", return_value=tempfile.mkdtemp()):
            db_mock = AsyncMock()
            result = await generate_transcript(body, db=db_mock, actor=actor)

        # Should not error — still returns detail view
        assert result.view == "detail"
        # Should include a meaningful message about no lessons
        content_sections = [s for s in result.sections if s.kind == "content"]
        assert len(content_sections) == 1
        assert "no completed lessons" in content_sections[0].body.lower()
