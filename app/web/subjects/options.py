from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from hyperstate.dependencies import OptionsResponse
from hyperstate.fields import FieldOption
from app.infrastructure.database import get_db
from app.infrastructure.repositories.subject_repo import SubjectRepository

router = APIRouter(prefix="/api/subjects", tags=["options"])


@router.get("", response_model=OptionsResponse)
async def subject_options(db: AsyncSession = Depends(get_db)):
    repo = SubjectRepository(db)
    subjects = await repo.list_all()
    return OptionsResponse(
        options=[FieldOption(value=s.id, label=f"{s.icon} {s.name}") for s in subjects]
    )
