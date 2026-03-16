from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.hyperstate.response import HyperStateResponse, ActorContext
from app.infrastructure.database import get_db
from app.infrastructure.repositories.lesson_repo import LessonRepository
from app.infrastructure.repositories.subject_repo import SubjectRepository
from app.projection.dashboard.view import DashboardProjection
from app.web.deps import get_current_actor

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=HyperStateResponse)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    lesson_repo = LessonRepository(db)
    subject_repo = SubjectRepository(db)

    today = date.today()
    today_lessons, recently_completed, instruction_days, all_subjects = await _gather(
        lesson_repo, subject_repo, today
    )
    subjects_map = {s.id: s for s in all_subjects}

    return DashboardProjection(
        today_lessons=today_lessons,
        recently_completed=recently_completed,
        instruction_days=instruction_days,
        subjects=subjects_map,
        actor=actor,
    ).build()


async def _gather(lesson_repo, subject_repo, today):
    today_lessons = await lesson_repo.list_by_date(today)
    recently_completed = await lesson_repo.list_recently_completed(5)
    instruction_days = await lesson_repo.count_instruction_days()
    all_subjects = await subject_repo.list_all()
    return today_lessons, recently_completed, instruction_days, all_subjects
