from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from hyperstate.dependencies import OptionsResponse
from hyperstate.fields import FieldOption
from app.infrastructure.database import get_db
from app.infrastructure.repositories.student_repo import StudentRepository

router = APIRouter(prefix="/api/students", tags=["options"])


@router.get("", response_model=OptionsResponse)
async def student_options(db: AsyncSession = Depends(get_db)):
    repo = StudentRepository(db)
    students = await repo.list_all()
    return OptionsResponse(
        options=[FieldOption(value=s.id, label=s.name) for s in students]
    )
