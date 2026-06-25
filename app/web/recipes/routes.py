from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.recipes.add_ingredient import AddIngredient
from app.application.recipes.create_recipe import CreateRecipe
from app.application.recipes.remove_ingredient import RemoveIngredient
from app.application.recipes.transition_recipe import TransitionRecipe
from app.domain.recipes.errors import RecipeError, RecipeNotFound
from app.domain.shared.themes import Theme
from app.infrastructure.database import get_db
from app.infrastructure.repositories.recipe_repo import RecipeRepository
from app.projection.recipes.detail import RecipeDetailProjection
from app.projection.recipes.list import RecipeListProjection
from app.web.deps import get_current_actor
from hyperstate.flash import Flash
from hyperstate.response import ActorContext, HyperStateResponse

router = APIRouter(prefix="/recipes", tags=["recipes"])

_TRANSITION_ACTIONS = {"archive", "restore"}


class CreateRecipeReq(BaseModel):
    name: str
    theme: Theme
    uses_frozen_meat: bool = False
    thaw_lead_hours: int | None = None
    prep_minutes: int | None = None


class IngredientReq(BaseModel):
    name: str
    quantity: str | None = None


class AddIngredientsReq(BaseModel):
    ingredients: list[IngredientReq] = []


class RemoveIngredientReq(BaseModel):
    name: str


@router.get("", response_model=HyperStateResponse)
async def list_recipes(
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    recipes = await RecipeRepository(db).list_all()
    return RecipeListProjection(recipes, actor).build()


@router.post("", response_model=HyperStateResponse)
async def create_recipe(
    req: CreateRecipeReq,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    use_case = CreateRecipe(db)
    recipe = await use_case.execute(
        name=req.name,
        theme=req.theme,
        uses_frozen_meat=req.uses_frozen_meat,
        thaw_lead_hours=req.thaw_lead_hours,
        prep_minutes=req.prep_minutes,
    )
    return RecipeDetailProjection(recipe, actor).build(
        flash=Flash(type="success", title="Recipe created.")
    )


@router.get("/{recipe_id}", response_model=HyperStateResponse)
async def get_recipe(
    recipe_id: str,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    recipe = await RecipeRepository(db).get(recipe_id)
    if recipe is None:
        raise RecipeNotFound(recipe_id)
    return RecipeDetailProjection(recipe, actor).build()


@router.post("/{recipe_id}/ingredients", response_model=HyperStateResponse)
async def add_ingredients(
    recipe_id: str,
    req: AddIngredientsReq,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    rows = [i for i in req.ingredients if i.name.strip()]
    if not rows:
        raise RecipeError("Add at least one ingredient.")

    use_case = AddIngredient(db)
    recipe = None
    for row in rows:
        recipe = await use_case.execute(
            recipe_id=recipe_id,
            name=row.name,
            quantity=row.quantity,
        )

    assert recipe is not None  # rows is non-empty, so the loop ran
    plural = "Ingredient" if len(rows) == 1 else "Ingredients"
    return RecipeDetailProjection(recipe, actor).build(
        flash=Flash(type="success", title=f"{plural} added.")
    )


@router.post("/{recipe_id}/ingredients/remove", response_model=HyperStateResponse)
async def remove_ingredient(
    recipe_id: str,
    req: RemoveIngredientReq,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    recipe = await RemoveIngredient(db).execute(recipe_id=recipe_id, name=req.name)
    return RecipeDetailProjection(recipe, actor).build(
        flash=Flash(type="info", title="Ingredient removed.")
    )


@router.post("/{recipe_id}/{action}", response_model=HyperStateResponse)
async def transition_recipe(
    recipe_id: str,
    action: str,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    if action not in _TRANSITION_ACTIONS:
        raise RecipeError(f"Unknown recipe action: {action}")
    recipe = await TransitionRecipe(db).execute(recipe_id, action)
    return RecipeDetailProjection(recipe, actor).build(
        flash=Flash(type="success", title=f"Recipe {action}d.")
    )
