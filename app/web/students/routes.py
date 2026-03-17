from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from hyperstate.response import HyperStateResponse, ActorContext
from app.domain.students.errors import StudentNotFound
from app.infrastructure.database import get_db
from app.infrastructure.repositories.student_repo import StudentRepository
from app.projection.students.list import StudentListProjection
from app.projection.students.detail import StudentDetailProjection
from app.application.students.create_student import CreateStudent
from app.web.deps import get_current_actor

router = APIRouter(prefix="/students", tags=["students"])


class CreateStudentBody(BaseModel):
    name: str
    grade_level: str
    enrollment_date: date | None = None


@router.get("", response_model=HyperStateResponse)
async def list_students(
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    repo = StudentRepository(db)
    students = await repo.list_all()
    return StudentListProjection(students, actor).build()


@router.post("", response_model=HyperStateResponse)
async def create_student(
    body: CreateStudentBody,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    use_case = CreateStudent(db)
    return await use_case.execute(
        name=body.name,
        grade_level=body.grade_level,
        enrollment_date=body.enrollment_date,
        actor=actor,
    )


@router.get("/{student_id}", response_model=HyperStateResponse)
async def get_student(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    repo = StudentRepository(db)
    student = await repo.get(student_id)
    if student is None:
        raise StudentNotFound(student_id)
    return StudentDetailProjection(student, actor).build()
