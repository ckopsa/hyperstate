from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.hyperstate.response import HyperStateResponse, ActorContext
from app.infrastructure.database import get_db
from app.infrastructure.repositories.lesson_repo import LessonRepository
from app.projection.lessons.list import LessonListProjection
from app.projection.lessons.detail import LessonDetailProjection
from app.application.lessons.create_lesson import CreateLesson
from app.application.lessons.transition_lesson import TransitionLesson
from app.domain.lessons.errors import LessonNotFound
from app.web.deps import get_current_actor

router = APIRouter(prefix="/lessons", tags=["lessons"])


class CreateLessonBody(BaseModel):
    title: str
    subject_id: str
    student_id: str
    description: str | None = None
    scheduled_date: date | None = None
    time_slot: str = "morning"


@router.get("", response_model=HyperStateResponse)
async def list_lessons(
    student_id: str | None = Query(None),
    subject_id: str | None = Query(None),
    state: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    repo = LessonRepository(db)
    lessons = await repo.list_all(student_id=student_id, subject_id=subject_id, state=state)
    return LessonListProjection(lessons, actor).build()


@router.post("", response_model=HyperStateResponse)
async def create_lesson(
    body: CreateLessonBody,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    use_case = CreateLesson(db)
    return await use_case.execute(
        subject_id=body.subject_id,
        student_id=body.student_id,
        title=body.title,
        description=body.description,
        scheduled_date=body.scheduled_date,
        time_slot=body.time_slot,
        actor=actor,
    )


@router.get("/{lesson_id}", response_model=HyperStateResponse)
async def get_lesson(
    lesson_id: str,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    repo = LessonRepository(db)
    lesson = await repo.get(lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail=f"Lesson {lesson_id} not found")
    return LessonDetailProjection(lesson, actor).build()


@router.post("/{lesson_id}/start", response_model=HyperStateResponse)
async def start_lesson(
    lesson_id: str,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    use_case = TransitionLesson(db)
    return await use_case.execute(lesson_id, "start", actor)


@router.post("/{lesson_id}/complete", response_model=HyperStateResponse)
async def complete_lesson(
    lesson_id: str,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    use_case = TransitionLesson(db)
    return await use_case.execute(lesson_id, "complete", actor)


@router.post("/{lesson_id}/reset", response_model=HyperStateResponse)
async def reset_lesson(
    lesson_id: str,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    use_case = TransitionLesson(db)
    return await use_case.execute(lesson_id, "reset", actor)
