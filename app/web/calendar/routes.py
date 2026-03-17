from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from hyperstate.response import HyperStateResponse, ActorContext
from app.infrastructure.database import get_db
from app.infrastructure.repositories.lesson_repo import LessonRepository
from app.infrastructure.repositories.subject_repo import SubjectRepository
from app.projection.calendar.week import CalendarWeekProjection
from app.application.calendar.move_lesson import MoveLesson
from app.application.calendar.shift_week import ShiftWeek
from app.web.deps import get_current_actor

router = APIRouter(prefix="/calendar", tags=["calendar"])


def _week_start_for(ref: date) -> date:
    """Return the Monday of the week containing ref."""
    return ref - timedelta(days=ref.weekday())


@router.get("", response_model=HyperStateResponse)
async def get_calendar(
    view: str = Query("week"),
    week: str | None = Query(None),
    student_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    if week:
        week_start = date.fromisoformat(week)
        # Normalize to Monday
        week_start = _week_start_for(week_start)
    else:
        week_start = _week_start_for(date.today())

    week_end = week_start + timedelta(days=6)

    repo = LessonRepository(db)
    lessons = await repo.list_by_date_range(week_start, week_end, student_id=student_id)

    subject_repo = SubjectRepository(db)
    subjects = await subject_repo.list_all()
    subject_map = {s.id: s for s in subjects}

    return CalendarWeekProjection(lessons, subject_map, week_start, actor).build()


class MoveLessonBody(BaseModel):
    lesson_id: str
    target_date: date
    time_slot: str = "morning"
    week_start: date | None = None


@router.post("/move", response_model=HyperStateResponse)
async def move_lesson(
    body: MoveLessonBody,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    week_start = body.week_start or _week_start_for(body.target_date)
    use_case = MoveLesson(db)
    return await use_case.execute(
        lesson_id=body.lesson_id,
        target_date=body.target_date,
        time_slot=body.time_slot,
        actor=actor,
        week_start=week_start,
    )


class ShiftWeekBody(BaseModel):
    direction: str = "forward"
    days: int = 1
    week_start: date | None = None
    student_id: str | None = None


@router.post("/shift-week", response_model=HyperStateResponse)
async def shift_week(
    body: ShiftWeekBody,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    week_start = body.week_start or _week_start_for(date.today())
    use_case = ShiftWeek(db)
    return await use_case.execute(
        week_start=week_start,
        direction=body.direction,
        days=body.days,
        student_id=body.student_id,
        actor=actor,
    )
