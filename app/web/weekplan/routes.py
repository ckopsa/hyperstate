from datetime import date, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.weekplan.clear_dinner import ClearDinner
from app.application.weekplan.create_weekplan import CreateWeekPlan
from app.application.weekplan.decide_dinner import DecideDinner
from app.application.weekplan.transition_weekplan import TransitionWeekPlan
from app.domain.weekplan.aggregate import WeekPlan
from app.domain.weekplan.errors import WeekPlanNotFound
from app.infrastructure.database import get_db
from app.infrastructure.repositories.recipe_repo import RecipeRepository
from app.infrastructure.repositories.weekplan_repo import WeekPlanRepository
from app.projection.weekplan.detail import WeekPlanDetailProjection
from app.projection.weekplan.list import WeekPlanListProjection
from app.web.deps import get_current_actor
from hyperstate.flash import Flash
from hyperstate.response import ActorContext, HyperStateResponse

router = APIRouter(prefix="/weekplans", tags=["weekplan"])

_TUESDAY = 1  # date.weekday(): Monday == 0 ... Sunday == 6


class CreateWeekPlanReq(BaseModel):
    week_start: date


class SetDinnerReq(BaseModel):
    # Optional so the one slot endpoint can both decide (recipe_id present) and
    # clear (recipe_id absent) a dinner.
    recipe_id: str | None = None


def _next_tuesday(today: date) -> date:
    """The upcoming Tuesday, or today if today is already a Tuesday."""
    return today + timedelta(days=(_TUESDAY - today.weekday()) % 7)


async def _detail(
    db: AsyncSession,
    plan: WeekPlan,
    actor: ActorContext,
    flash: Flash | None = None,
) -> HyperStateResponse:
    # All recipes (any state) so already-decided dinners resolve to names and the
    # prep timeline can look them up; the picker filters to active ones itself.
    recipes = await RecipeRepository(db).list_all()
    return WeekPlanDetailProjection(plan, recipes, actor).build(flash=flash)


@router.get("", response_model=HyperStateResponse)
async def list_weekplans(
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    plans = await WeekPlanRepository(db).list_all()
    return WeekPlanListProjection(
        plans, actor, default_week_start=_next_tuesday(date.today())
    ).build()


@router.post("", response_model=HyperStateResponse)
async def create_weekplan(
    req: CreateWeekPlanReq,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    plan = await CreateWeekPlan(db).execute(week_start=req.week_start)
    return await _detail(db, plan, actor, flash=Flash(type="success", title="Week plan created."))


@router.get("/{plan_id}", response_model=HyperStateResponse)
async def get_weekplan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    plan = await WeekPlanRepository(db).get(plan_id)
    if plan is None:
        raise WeekPlanNotFound(plan_id)
    return await _detail(db, plan, actor)


@router.post("/{plan_id}/slots/{slot_date}", response_model=HyperStateResponse)
async def set_dinner(
    plan_id: str,
    slot_date: date,
    req: SetDinnerReq,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    if req.recipe_id and req.recipe_id.strip():
        plan = await DecideDinner(db).execute(plan_id, slot_date, req.recipe_id)
        flash = Flash(type="success", title="Dinner decided.")
    else:
        plan = await ClearDinner(db).execute(plan_id, slot_date)
        flash = Flash(type="info", title="Dinner cleared.")
    return await _detail(db, plan, actor, flash=flash)


@router.post("/{plan_id}/{action}", response_model=HyperStateResponse)
async def transition_weekplan(
    plan_id: str,
    action: str,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    plan = await TransitionWeekPlan(db).execute(plan_id, action)
    return await _detail(
        db, plan, actor,
        flash=Flash(type="success", title=f"Week plan: {action.replace('_', ' ')}."),
    )
