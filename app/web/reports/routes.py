"""Reports: transcript generation, instruction days, and download."""
from __future__ import annotations

import csv
import os
import uuid
from datetime import date, datetime, UTC

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from hyperstate.display import PropertyItem
from hyperstate.fields import BooleanField, DateField, FieldOption, SelectField
from hyperstate.flash import Flash
from hyperstate.nav import NavLink
from hyperstate.response import ActorContext, HyperStateResponse, ViewContext
from hyperstate.sections import (
    ActionSection,
    ColumnDef,
    ContentSection,
    ListItem,
    ListSection,
    PropertiesSection,
)
from app.infrastructure.database import get_db
from app.infrastructure.repositories.instruction_day_repo import InstructionDayRepository
from app.infrastructure.repositories.lesson_repo import LessonRepository
from app.infrastructure.repositories.student_repo import StudentRepository
from app.infrastructure.repositories.subject_repo import SubjectRepository
from app.projection.reports.instruction_days import InstructionDaysProjection
from app.web.deps import get_current_actor

router = APIRouter(prefix="/reports", tags=["reports"])

# ── In-memory report store (keyed by report_id) ───────────────────────────────
# Stores metadata and the file path of the generated report.
_REPORTS: dict[str, dict] = {}

_REPORTS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "uploads", "reports"
)


def _ensure_reports_dir() -> str:
    os.makedirs(_REPORTS_DIR, exist_ok=True)
    return _REPORTS_DIR


# ── Helpers ───────────────────────────────────────────────────────────────────

def _reports_nav() -> list[NavLink]:
    return [NavLink(label="Dashboard", href="/dashboard", rel="parent")]


def _view_context(state: str, actor: ActorContext) -> ViewContext:
    return ViewContext(domain="reports", aggregate="report", state=state, actor=actor)


# ── Instruction Days Routes ───────────────────────────────────────────────────

class LogManualDayBody(BaseModel):
    date: date
    notes: str | None = None


@router.get("/instruction-days", response_model=HyperStateResponse)
async def get_instruction_days(
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    repo = InstructionDayRepository(db)
    days = await repo.list_all()
    return InstructionDaysProjection(days, actor).build()


@router.post("/instruction-days", response_model=HyperStateResponse)
async def log_manual_day(
    body: LogManualDayBody,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    repo = InstructionDayRepository(db)
    await repo.create_manual(body.date, body.notes)
    await db.commit()
    days = await repo.list_all()
    return InstructionDaysProjection(days, actor).build(
        flash=Flash(type="success", title="Day logged!", body=f"Instruction day for {body.date} recorded.")
    )


@router.get("/instruction-days/export")
async def export_instruction_days(
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    repo = InstructionDayRepository(db)
    days = await repo.list_all()
    days.sort(key=lambda d: d.date)  # chronological order for the report

    report_id = str(uuid.uuid4())
    filename = f"instruction_days_{report_id}.pdf"
    reports_dir = _ensure_reports_dir()
    filepath = os.path.join(reports_dir, filename)

    from fpdf import FPDF, XPos, YPos

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Instruction Days Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 7, f"Total Days Logged: {len(days)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    if not days:
        pdf.set_font("Helvetica", "I", 11)
        pdf.cell(0, 10, "No instruction days logged yet.", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    else:
        pdf.set_font("Helvetica", "B", 10)
        # Header
        pdf.cell(30, 8, "Date", border=1)
        pdf.cell(20, 8, "Lessons", border=1, align="C")
        pdf.cell(60, 8, "Subjects Covered", border=1)
        pdf.cell(0, 8, "Notes", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_font("Helvetica", "", 9)
        for day in days:
            date_str = day.date.isoformat()
            lessons = str(day.lessons_completed or 0)
            subjects = day.subjects_covered or ""
            notes = day.notes or ""

            # Ensure text fits or use multi_cell, but for simplicity we just truncate or let it run
            # A more robust approach would use multi_cell to handle wrapping
            # Let's truncate strings if they are too long just in case, or use a simple cell
            subjects = subjects[:40] + "..." if len(subjects) > 40 else subjects

            # Simple row
            # To handle long notes, we can calculate the height needed, but sticking to simple cell
            # if notes are short. Let's truncate notes to 50 chars for the simple row.
            notes_trunc = notes[:50] + "..." if len(notes) > 50 else notes

            pdf.cell(30, 7, date_str, border=1)
            pdf.cell(20, 7, lessons, border=1, align="C")
            pdf.cell(60, 7, subjects, border=1)
            pdf.cell(0, 7, notes_trunc, border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.output(filepath)

    return FileResponse(
        path=filepath,
        media_type="application/pdf",
        filename=filename,
    )


# ── Reports List ──────────────────────────────────────────────────────────────

@router.get("", response_model=HyperStateResponse)
async def list_reports(
    actor: ActorContext = Depends(get_current_actor),
):
    """List available report types."""
    return HyperStateResponse(
        view="list",
        title="Reports",
        self_="/reports",
        context=_view_context("overview", actor),
        nav=_reports_nav(),
        sections=[
            ListSection(
                title="Available Reports",
                columns=[
                    ColumnDef(key="name", label="Report"),
                    ColumnDef(key="description", label="Description"),
                ],
                items=[
                    ListItem(
                        href="/reports/transcript",
                        data={
                            "name": "Transcript",
                            "description": "Completed lessons with subject, date, and optional notes",
                        },
                    ),
                    ListItem(
                        href="/reports/instruction-days",
                        data={
                            "name": "Instruction Days",
                            "description": "Total instructional days completed toward annual goal",
                        },
                    ),
                ],
                empty_message="No reports available.",
            ),
        ],
    )


# ── Transcript Routes ─────────────────────────────────────────────────────────

@router.get("/transcript", response_model=HyperStateResponse)
async def transcript_form(
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """Render the transcript generation form."""
    student_repo = StudentRepository(db)
    students = await student_repo.list_all()
    student_options = [FieldOption(value=s.id, label=s.name) for s in students]

    return HyperStateResponse(
        view="form",
        title="Generate Transcript",
        self_="/reports/transcript",
        context=_view_context("form", actor),
        nav=[
            NavLink(label="Reports", href="/reports", rel="parent"),
        ],
        sections=[
            ActionSection(
                key="generate-transcript",
                label="Generate Transcript",
                description="Export completed lessons for a student over a date range.",
                method="POST",
                href="/reports/transcript/generate",
                style="primary",
                fields=[
                    SelectField(
                        name="student_id",
                        label="Student",
                        required=True,
                        options=student_options,
                        placeholder="Select a student",
                    ),
                    DateField(
                        name="date_range_start",
                        label="From",
                        required=True,
                    ),
                    DateField(
                        name="date_range_end",
                        label="To",
                        required=True,
                    ),
                    BooleanField(
                        name="include_grades",
                        label="Include Grades / Notes",
                        default=True,
                        value=True,
                    ),
                    BooleanField(
                        name="include_notes",
                        label="Include Lesson Descriptions",
                        default=False,
                        value=False,
                    ),
                    SelectField(
                        name="format",
                        label="Format",
                        required=True,
                        value="pdf",
                        options=[
                            FieldOption(value="pdf", label="PDF"),
                            FieldOption(value="csv", label="CSV"),
                        ],
                    ),
                ],
            ),
        ],
    )


class GenerateTranscriptBody(BaseModel):
    student_id: str
    date_range_start: date
    date_range_end: date
    include_grades: bool = True
    include_notes: bool = False
    format: str = "pdf"


@router.post("/transcript/generate", response_model=HyperStateResponse)
async def generate_transcript(
    body: GenerateTranscriptBody,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """Generate the transcript report and return a detail view with download link."""
    if body.date_range_start > body.date_range_end:
        return HyperStateResponse(
            view="error",
            title="Invalid Date Range",
            self_="/reports/transcript/generate",
            context=_view_context("error", actor),
            nav=[NavLink(label="Back to Form", href="/reports/transcript", rel="parent")],
            sections=[
                ContentSection(
                    body="Start date must be before or equal to end date.",
                    format="plain",
                ),
            ],
        )

    student_repo = StudentRepository(db)
    lesson_repo = LessonRepository(db)
    subject_repo = SubjectRepository(db)

    student = await student_repo.get(body.student_id)
    if student is None:
        return HyperStateResponse(
            view="error",
            title="Student Not Found",
            self_="/reports/transcript/generate",
            context=_view_context("error", actor),
            nav=[NavLink(label="Back to Form", href="/reports/transcript", rel="parent")],
            sections=[
                ContentSection(
                    body=f"Student {body.student_id} was not found.",
                    format="plain",
                ),
            ],
        )

    lessons = await lesson_repo.list_by_date_range(
        body.date_range_start, body.date_range_end, student_id=body.student_id
    )
    completed = [lesson for lesson in lessons if lesson.state.value == "completed"]

    subjects_map = {s.id: s for s in await subject_repo.list_all()}

    report_id = str(uuid.uuid4())
    generated_at = datetime.now(UTC)
    ext = "pdf" if body.format == "pdf" else "csv"
    filename = f"transcript_{report_id}.{ext}"
    reports_dir = _ensure_reports_dir()
    filepath = os.path.join(reports_dir, filename)

    if body.format == "csv":
        _write_csv(filepath, student, completed, subjects_map, body)
        page_count = 1
    else:
        page_count = _write_pdf(filepath, student, completed, subjects_map, body)

    file_size = os.path.getsize(filepath)

    _REPORTS[report_id] = {
        "filepath": filepath,
        "filename": filename,
        "format": body.format,
        "student_name": student.name,
        "generated_at": generated_at,
    }

    lesson_count = len(completed)
    empty_sections = []
    if lesson_count == 0:
        empty_sections.append(
            ContentSection(
                title="No Completed Lessons",
                body=(
                    f"No completed lessons were found for {student.name} "
                    f"between {body.date_range_start} and {body.date_range_end}. "
                    "The report was generated but contains no lesson records."
                ),
                format="plain",
            )
        )

    download_href = f"/reports/transcript/{report_id}/download"
    mime = "application/pdf" if body.format == "pdf" else "text/csv"

    return HyperStateResponse(
        view="detail",
        title="Transcript Generated",
        self_=f"/reports/transcript/{report_id}",
        context=_view_context("generated", actor),
        flash=Flash(type="success", title="Report ready", body="Your transcript has been generated."),
        nav=[
            NavLink(label="Download", href=download_href, rel="download", type=mime),
            NavLink(label="Reports", href="/reports", rel="collection"),
        ],
        sections=[
            PropertiesSection(
                title="Report Summary",
                data=[
                    PropertyItem(
                        key="student",
                        label="Student",
                        value=student.name,
                        display="plain",
                    ),
                    PropertyItem(
                        key="date_range",
                        label="Date Range",
                        value=f"{body.date_range_start} – {body.date_range_end}",
                        display="plain",
                    ),
                    PropertyItem(
                        key="lessons_included",
                        label="Lessons Included",
                        value=lesson_count,
                        display="number",
                    ),
                    PropertyItem(
                        key="generated_at",
                        label="Generated",
                        value=generated_at.isoformat(),
                        display="datetime",
                    ),
                    PropertyItem(
                        key="page_count",
                        label="Pages",
                        value=page_count,
                        display="number",
                    ),
                    PropertyItem(
                        key="file_size",
                        label="File Size",
                        value=f"{file_size:,} bytes",
                        display="plain",
                    ),
                ],
            ),
            *empty_sections,
        ],
    )


@router.get("/transcript/{report_id}/download")
async def download_transcript(report_id: str):
    """Serve the generated transcript file."""
    report = _REPORTS.get(report_id)
    if report is None or not os.path.exists(report["filepath"]):
        return Response(
            content=f"Report {report_id} not found or has expired.",
            status_code=404,
            media_type="text/plain",
        )
    media_type = "application/pdf" if report["format"] == "pdf" else "text/csv"
    return FileResponse(
        path=report["filepath"],
        media_type=media_type,
        filename=report["filename"],
    )


# ── PDF / CSV generation ──────────────────────────────────────────────────────

def _write_pdf(filepath: str, student, lessons: list, subjects_map: dict, body: GenerateTranscriptBody) -> int:
    """Write transcript PDF and return page count."""
    from fpdf import FPDF, XPos, YPos

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Homeschool Transcript", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Student: {student.name}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    if student.grade_level:
        pdf.cell(0, 7, f"Grade: {student.grade_level}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 7, f"Period: {body.date_range_start} to {body.date_range_end}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 7, f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    if not lessons:
        pdf.set_font("Helvetica", "I", 11)
        pdf.cell(0, 10, "No completed lessons in this date range.", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    else:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Completed Lessons", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 10)

        for lesson in lessons:
            subject = subjects_map.get(lesson.subject_id)
            subject_name = subject.name if subject else lesson.subject_id
            completed_date = ""
            if lesson.completed_at:
                completed_date = lesson.completed_at.strftime("%Y-%m-%d")
            elif lesson.scheduled_date:
                completed_date = str(lesson.scheduled_date)

            line = f"{completed_date}  |  {subject_name}  |  {lesson.title}"
            pdf.cell(0, 7, line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            if body.include_notes and lesson.description:
                pdf.set_font("Helvetica", "I", 9)
                pdf.multi_cell(0, 6, f"    {lesson.description}")
                pdf.set_font("Helvetica", "", 10)

    pdf.output(filepath)
    return pdf.page


def _write_csv(filepath: str, student, lessons: list, subjects_map: dict, body: GenerateTranscriptBody) -> None:
    """Write transcript CSV."""
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Student", student.name])
        writer.writerow(["Period", f"{body.date_range_start} to {body.date_range_end}"])
        writer.writerow([])
        header = ["Date", "Subject", "Lesson Title"]
        if body.include_notes:
            header.append("Description")
        writer.writerow(header)

        for lesson in lessons:
            subject = subjects_map.get(lesson.subject_id)
            subject_name = subject.name if subject else lesson.subject_id
            completed_date = ""
            if lesson.completed_at:
                completed_date = lesson.completed_at.strftime("%Y-%m-%d")
            elif lesson.scheduled_date:
                completed_date = str(lesson.scheduled_date)

            row = [completed_date, subject_name, lesson.title]
            if body.include_notes:
                row.append(lesson.description or "")
            writer.writerow(row)
