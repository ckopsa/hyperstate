# app/main.py

from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
import os

from app.hyperstate.middleware import HyperStateMiddleware
from app.hyperstate.response import HyperStateResponse
from app.hyperstate.sections import ContentSection
from app.hyperstate.nav import NavLink
from app.web.orders.routes import router as orders_router
from app.web.orders.options import router as orders_options_router
from app.web.students.routes import router as students_router
from app.web.students.options import router as students_options_router
from app.web.subjects.routes import router as subjects_router
from app.web.subjects.options import router as subjects_options_router
from app.web.lessons.routes import router as lessons_router
from app.web.dashboard.routes import router as dashboard_router
from app.application.orders.cancel_order import OrderNotFound
from app.domain.students.errors import StudentNotFound
from app.domain.subjects.errors import SubjectNotFound
from app.domain.lessons.errors import LessonNotFound

from app.infrastructure.database import engine, Base, async_session
from app.infrastructure.models.order_model import OrderRow, LineItemRow
from app.infrastructure.models.student_model import StudentRow
from app.infrastructure.models.subject_model import SubjectRow
from app.infrastructure.models.lesson_model import LessonRow

app = FastAPI(title="HyperState Homeschool Planner", version="0.1.0")
app.add_middleware(HyperStateMiddleware)
app.include_router(orders_router)
app.include_router(orders_options_router)
app.include_router(students_router)
app.include_router(students_options_router)
app.include_router(subjects_router)
app.include_router(subjects_options_router)
app.include_router(lessons_router)
app.include_router(dashboard_router)


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed sample order if none exists
    async with async_session() as session:
        from sqlalchemy import select
        stmt = select(OrderRow).limit(1)
        result = await session.execute(stmt)
        if not result.scalar_one_or_none():
            from decimal import Decimal
            from datetime import datetime, UTC
            order = OrderRow(
                id="ORD-001",
                customer_id="CUST-7",
                state="pending",
                placed_at=datetime.now(UTC),
                items=[
                    LineItemRow(
                        product_id="PROD-1",
                        product_name="Standard Widget",
                        quantity=2,
                        unit_price=Decimal("25.00"),
                        currency="USD"
                    )
                ]
            )
            session.add(order)
            await session.commit()

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


@app.get("/reports/instruction-days", response_model=HyperStateResponse)
async def reports_instruction_days():
    from app.infrastructure.database import async_session
    from app.infrastructure.repositories.lesson_repo import LessonRepository
    from app.hyperstate.response import ViewContext, ActorContext
    from app.hyperstate.sections import SummarySection, SummaryItem

    async with async_session() as session:
        repo = LessonRepository(session)
        instruction_days = await repo.count_instruction_days()

    return HyperStateResponse(
        view="report",
        title="Instruction Days",
        self_="/reports/instruction-days",
        context=ViewContext(
            domain="reports",
            aggregate="instruction-days",
            state="overview",
            actor=ActorContext(id="system", name="System", roles=[]),
        ),
        nav=[NavLink(label="Dashboard", href="/dashboard", rel="parent")],
        sections=[
            SummarySection(
                items=[
                    SummaryItem(label="Instruction Days Completed", value=instruction_days, display="number"),
                    SummaryItem(label="Target", value=180, display="number"),
                ]
            )
        ],
    )


@app.get("/", response_class=HTMLResponse)
async def get_client():
    path = os.path.join(os.path.dirname(__file__), "web", "client.html")
    with open(path, "r") as f:
        return f.read()


@app.exception_handler(OrderNotFound)
async def order_not_found_handler(request, exc: OrderNotFound):
    response = HyperStateResponse(
        view="error",
        title="Not Found",
        self_=str(request.url.path),
        sections=[
            ContentSection(
                body=f"Order {exc.order_id} was not found.",
                format="plain",
            ),
        ],
        nav=[NavLink(label="All Orders", href="/orders", rel="collection")],
    )
    return JSONResponse(
        status_code=404,
        content=response.model_dump(by_alias=True, exclude_none=True),
    )


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
