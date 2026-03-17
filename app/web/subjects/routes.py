from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from hyperstate.response import HyperStateResponse, ActorContext
from app.infrastructure.database import get_db
from app.infrastructure.repositories.subject_repo import SubjectRepository
from app.infrastructure.repositories.lesson_repo import LessonRepository
from app.projection.subjects.list import SubjectListProjection
from app.projection.subjects.detail import SubjectDetailProjection
from app.application.subjects.create_subject import CreateSubject
from app.application.subjects.update_subject import UpdateSubject
from app.application.subjects.delete_subject import DeleteSubject
from app.web.deps import get_current_actor

router = APIRouter(prefix="/subjects", tags=["subjects"])


class CreateSubjectBody(BaseModel):
    name: str
    color: str = "#9CA3AF"
    icon: str = "📖"
    description: str | None = None


class UpdateSubjectBody(BaseModel):
    name: str
    color: str = "#9CA3AF"
    icon: str = "📖"
    description: str | None = None


@router.get("", response_model=HyperStateResponse)
async def list_subjects(
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    repo = SubjectRepository(db)
    subjects = await repo.list_all()
    return SubjectListProjection(subjects, actor).build()


@router.post("", response_model=HyperStateResponse)
async def create_subject(
    body: CreateSubjectBody,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    use_case = CreateSubject(db)
    return await use_case.execute(
        name=body.name,
        color=body.color,
        icon=body.icon,
        description=body.description,
        actor=actor,
    )


@router.get("/{subject_id}", response_model=HyperStateResponse)
async def get_subject(
    subject_id: str,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    repo = SubjectRepository(db)
    subject = await repo.get(subject_id)
    if subject is None:
        raise HTTPException(status_code=404, detail=f"Subject {subject_id} not found")
    lesson_repo = LessonRepository(db)
    lessons = await lesson_repo.list_all(subject_id=subject_id)
    return SubjectDetailProjection(subject, lessons, actor).build()


@router.patch("/{subject_id}", response_model=HyperStateResponse)
async def update_subject(
    subject_id: str,
    body: UpdateSubjectBody,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    use_case = UpdateSubject(db)
    return await use_case.execute(
        subject_id=subject_id,
        name=body.name,
        color=body.color,
        icon=body.icon,
        description=body.description,
        actor=actor,
    )


@router.delete("/{subject_id}", response_model=HyperStateResponse)
async def delete_subject(
    subject_id: str,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    use_case = DeleteSubject(db)
    return await use_case.execute(subject_id=subject_id, actor=actor)
