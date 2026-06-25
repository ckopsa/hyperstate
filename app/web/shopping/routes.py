from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.shopping.build_shopping_list import BuildShoppingList
from app.application.shopping.mark_item import MarkItem
from app.domain.shopping.aggregate import ShoppingList
from app.domain.shopping.errors import ShoppingListNotFound
from app.infrastructure.database import get_db
from app.infrastructure.repositories.shopping_repo import ShoppingListRepository
from app.infrastructure.repositories.weekplan_repo import WeekPlanRepository
from app.projection.shopping.detail import ShoppingListDetailProjection
from app.web.deps import get_current_actor
from hyperstate.flash import Flash
from hyperstate.response import ActorContext, HyperStateResponse

router = APIRouter(prefix="/shopping", tags=["shopping"])


async def _detail(
    db: AsyncSession,
    shopping_list: ShoppingList,
    actor: ActorContext,
    flash: Flash | None = None,
) -> HyperStateResponse:
    # The owning plan supplies the week_start for a friendly title; the list can
    # still render without it (the plan is keyed one-per-week by the list id).
    plan = await WeekPlanRepository(db).get(shopping_list.week_plan_id)
    week_start = plan.week_start if plan is not None else None
    return ShoppingListDetailProjection(
        shopping_list, actor, week_start=week_start
    ).build(flash=flash)


@router.get("/{week_plan_id}", response_model=HyperStateResponse)
async def get_shopping_list(
    week_plan_id: str,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    shopping_list = await ShoppingListRepository(db).get(week_plan_id)
    if shopping_list is None:
        raise ShoppingListNotFound(week_plan_id)
    return await _detail(db, shopping_list, actor)


@router.post("/{week_plan_id}", response_model=HyperStateResponse)
async def build_shopping_list(
    week_plan_id: str,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    shopping_list = await BuildShoppingList(db).execute(week_plan_id)
    return await _detail(
        db, shopping_list, actor,
        flash=Flash(type="success", title="Shopping list built."),
    )


@router.post("/{week_plan_id}/items/{item_key}/{action}", response_model=HyperStateResponse)
async def mark_item(
    week_plan_id: str,
    item_key: str,
    action: str,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    shopping_list = await MarkItem(db).execute(week_plan_id, item_key, action)
    return await _detail(
        db, shopping_list, actor,
        flash=Flash(type="info", title=f"Marked {action}."),
    )
