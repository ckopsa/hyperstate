from datetime import date, timedelta

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.weekplan.clear_dinner import ClearDinner
from app.application.weekplan.create_weekplan import CreateWeekPlan
from app.application.weekplan.decide_dinner import DecideDinner
from app.application.weekplan.transition_weekplan import TransitionWeekPlan
from app.domain.weekplan.aggregate import WeekPlan
from app.domain.weekplan.errors import WeekPlanNotFound
from app.domain.weekplan.schedule import compute_schedule
from app.infrastructure.calendar.ics import render_schedule_ics
from app.infrastructure.database import get_db
from app.infrastructure.repositories.recipe_repo import RecipeRepository
from app.infrastructure.repositories.shopping_repo import ShoppingListRepository
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
    # The shopping list (if built) drives whether the detail offers to build it
    # or to view/rebuild the existing one.
    shopping_list = await ShoppingListRepository(db).get(plan.id)
    return WeekPlanDetailProjection(
        plan, recipes, actor, shopping_list=shopping_list
    ).build(flash=flash)


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


@router.get("/{plan_id}/schedule.ics")
async def export_schedule_ics(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
) -> Response:
    """Download the plan's prep timeline as an iCalendar (.ics) file.

    Renders the same ``compute_schedule`` events as the detail view's Prep
    Schedule — one VEVENT per thaw and per cook-start — so the cook can
    subscribe to the reminders from any calendar app.
    """
    plan = await WeekPlanRepository(db).get(plan_id)
    if plan is None:
        raise WeekPlanNotFound(plan_id)

    # All recipes (any state) so already-decided dinners resolve to names and
    # lead times, mirroring how the detail projection builds the timeline.
    recipes = await RecipeRepository(db).list_all()
    events = compute_schedule(plan, {r.id: r for r in recipes})
    body = render_schedule_ics(plan.id, events)

    return Response(
        content=body,
        media_type="text/calendar",
        headers={
            "Content-Disposition": f'attachment; filename="schedule-{plan.id}.ics"',
        },
    )


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
