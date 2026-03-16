from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.hyperstate.response import HyperStateResponse, ActorContext
from app.infrastructure.database import get_db
from app.infrastructure.repositories.subject_repo import SubjectRepository
from app.projection.subjects.list import SubjectListProjection
from app.projection.subjects.detail import SubjectDetailProjection
from app.application.subjects.create_subject import CreateSubject
from app.web.deps import get_current_actor

router = APIRouter(prefix="/subjects", tags=["subjects"])


class CreateSubjectBody(BaseModel):
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
    return SubjectDetailProjection(subject, actor).build()
