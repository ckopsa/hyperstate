from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.hyperstate.flash import Flash
from app.hyperstate.response import ActorContext, HyperStateResponse
from app.infrastructure.database import get_db
from app.infrastructure.repositories.instruction_day_repo import InstructionDayRepository
from app.projection.reports.instruction_days import InstructionDaysProjection
from app.web.deps import get_current_actor

router = APIRouter(prefix="/reports", tags=["reports"])


class LogManualDayBody(BaseModel):
    date: date
    notes: str | None = None


@router.get("/instruction-days", response_model=HyperStateResponse)
async def get_instruction_days(
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    repo = InstructionDayRepository(db)
    days = await repo.list_all()
    return InstructionDaysProjection(days, actor).build()


@router.post("/instruction-days", response_model=HyperStateResponse)
async def log_manual_day(
    body: LogManualDayBody,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    repo = InstructionDayRepository(db)
    await repo.create_manual(body.date, body.notes)
    await db.commit()
    days = await repo.list_all()
    return InstructionDaysProjection(days, actor).build(
        flash=Flash(type="success", title="Day logged!", body=f"Instruction day for {body.date} recorded.")
    )
