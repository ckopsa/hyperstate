# app/main.py

from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import os

from hyperstate.middleware import HyperStateMiddleware
from hyperstate.response import HyperStateResponse
from hyperstate.sections import ContentSection
from hyperstate.nav import NavLink
from app.web.students.routes import router as students_router
from app.web.students.options import router as students_options_router
from app.web.subjects.routes import router as subjects_router
from app.web.subjects.options import router as subjects_options_router
from app.web.lessons.routes import router as lessons_router
from app.web.portfolio.routes import router as portfolio_router
from app.web.dashboard.routes import router as dashboard_router
from app.web.calendar.routes import router as calendar_router
from app.web.reports.routes import router as reports_router
from app.web.curricula.routes import router as curricula_router
from app.domain.students.errors import StudentNotFound
from app.domain.subjects.errors import SubjectNotFound, SubjectError
from app.domain.lessons.errors import LessonNotFound
from app.domain.curricula.errors import CurriculumNotFound, CurriculumItemNotFound

from app.infrastructure.database import engine, Base, async_session
from app.infrastructure.models.student_model import StudentRow
from app.infrastructure.models.subject_model import SubjectRow
from app.infrastructure.models.lesson_model import LessonRow, LessonResourceRow  # noqa: F401
from app.infrastructure.models.portfolio_photo_model import PortfolioPhotoRow  # noqa: F401
from app.infrastructure.models.instruction_day_model import InstructionDayRow  # noqa: F401
from app.infrastructure.models.curriculum_model import CurriculumRow, CurriculumItemRow, CurriculumItemResourceRow  # noqa: F401

_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads", "portfolio")

app = FastAPI(title="HyperState Homeschool Planner", version="0.1.0")
app.add_middleware(HyperStateMiddleware)
app.include_router(students_router)
app.include_router(students_options_router)
app.include_router(subjects_router)
app.include_router(subjects_options_router)
app.include_router(lessons_router)
app.include_router(portfolio_router)
app.include_router(dashboard_router)
app.include_router(calendar_router)
app.include_router(reports_router)
app.include_router(curricula_router)


@app.on_event("startup")
async def startup():
    os.makedirs(_UPLOAD_DIR, exist_ok=True)
    app.mount("/uploads/portfolio", StaticFiles(directory=_UPLOAD_DIR), name="portfolio-uploads")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed default subjects if none exist
    async with async_session() as session:
        from sqlalchemy import select
        stmt = select(SubjectRow).limit(1)
        result = await session.execute(stmt)
        if not result.scalar_one_or_none():
            default_subjects = [
                SubjectRow(id="SUB-MATH", name="Math", color="#4F46E5", icon="📐", is_custom=False),
                SubjectRow(id="SUB-READ", name="Reading", color="#7C3AED", icon="📚", is_custom=False),
                SubjectRow(id="SUB-SCI", name="Science", color="#16A34A", icon="🔬", is_custom=False),
                SubjectRow(id="SUB-HIST", name="History", color="#D97706", icon="🌍", is_custom=False),
                SubjectRow(id="SUB-LANG", name="Language Arts", color="#DB2777", icon="✏️", is_custom=False),
                SubjectRow(id="SUB-PE", name="PE", color="#0891B2", icon="🏃", is_custom=False),
                SubjectRow(id="SUB-ART", name="Art", color="#DC2626", icon="🎨", is_custom=False),
                SubjectRow(id="SUB-MUS", name="Music", color="#9CA3AF", icon="🎵", is_custom=False),
            ]
            session.add_all(default_subjects)
            await session.commit()

    # Seed demo student and lessons if no students exist
    async with async_session() as session:
        from sqlalchemy import select
        from datetime import date
        stmt = select(StudentRow).limit(1)
        result = await session.execute(stmt)
        if not result.scalar_one_or_none():
            demo_student = StudentRow(
                id="STU-DEMO",
                name="Demo Student",
                grade_level="3rd",
                enrollment_date=date.today(),
            )
            session.add(demo_student)
            await session.flush()

            demo_lessons = [
                LessonRow(
                    id="LES-001",
                    subject_id="SUB-MATH",
                    student_id="STU-DEMO",
                    title="Addition and Subtraction",
                    description="Practice basic addition and subtraction facts.",
                    scheduled_date=date.today(),
                    time_slot="morning",
                    state="pending",
                ),
                LessonRow(
                    id="LES-002",
                    subject_id="SUB-READ",
                    student_id="STU-DEMO",
                    title="Chapter Book Reading",
                    description="Read chapters 1-3 of the assigned book.",
                    scheduled_date=date.today(),
                    time_slot="afternoon",
                    state="pending",
                ),
            ]
            session.add_all(demo_lessons)
            await session.commit()



@app.get("/", response_class=HTMLResponse)
@app.get("/{path:path}", response_class=HTMLResponse)
async def get_client(path: str = ""):
    file_path = os.path.join(os.path.dirname(__file__), "web", "client.html")
    with open(file_path, "r") as f:
        return f.read()


@app.exception_handler(StudentNotFound)
async def student_not_found_handler(request, exc: StudentNotFound):
    response = HyperStateResponse(
        view="error",
        title="Not Found",
        self_=str(request.url.path),
        sections=[ContentSection(body=f"Student {exc.student_id} was not found.", format="plain")],
        nav=[NavLink(label="All Students", href="/students", rel="collection")],
    )
    return JSONResponse(status_code=404, content=response.model_dump(by_alias=True, exclude_none=True))


@app.exception_handler(SubjectNotFound)
async def subject_not_found_handler(request, exc: SubjectNotFound):
    response = HyperStateResponse(
        view="error",
        title="Not Found",
        self_=str(request.url.path),
        sections=[ContentSection(body=f"Subject {exc.subject_id} was not found.", format="plain")],
        nav=[NavLink(label="All Subjects", href="/subjects", rel="collection")],
    )
    return JSONResponse(status_code=404, content=response.model_dump(by_alias=True, exclude_none=True))


@app.exception_handler(SubjectError)
async def subject_error_handler(request, exc: SubjectError):
    response = HyperStateResponse(
        view="error",
        title="Cannot Complete Action",
        self_=str(request.url.path),
        sections=[ContentSection(body=str(exc), format="plain")],
        nav=[NavLink(label="All Subjects", href="/subjects", rel="collection")],
    )
    return JSONResponse(status_code=422, content=response.model_dump(by_alias=True, exclude_none=True))


@app.exception_handler(LessonNotFound)
async def lesson_not_found_handler(request, exc: LessonNotFound):
    response = HyperStateResponse(
        view="error",
        title="Not Found",
        self_=str(request.url.path),
        sections=[ContentSection(body=f"Lesson {exc.lesson_id} was not found.", format="plain")],
        nav=[NavLink(label="All Lessons", href="/lessons", rel="collection")],
    )
    return JSONResponse(status_code=404, content=response.model_dump(by_alias=True, exclude_none=True))

@app.exception_handler(CurriculumNotFound)
async def curriculum_not_found_handler(request, exc: CurriculumNotFound):
    response = HyperStateResponse(
        view="error",
        title="Not Found",
        self_=str(request.url.path),
        sections=[ContentSection(body=f"Curriculum {exc.curriculum_id} was not found.", format="plain")],
        nav=[NavLink(label="All Curricula", href="/curricula", rel="collection")],
    )
    return JSONResponse(status_code=404, content=response.model_dump(by_alias=True, exclude_none=True))

@app.exception_handler(CurriculumItemNotFound)
async def curriculum_item_not_found_handler(request, exc: CurriculumItemNotFound):
    response = HyperStateResponse(
        view="error",
        title="Not Found",
        self_=str(request.url.path),
        sections=[ContentSection(body=f"Curriculum item {exc.item_id} was not found.", format="plain")],
        nav=[NavLink(label="All Curricula", href="/curricula", rel="collection")],
    )
    return JSONResponse(status_code=404, content=response.model_dump(by_alias=True, exclude_none=True))
