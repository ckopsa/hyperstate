from datetime import date
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.curricula.errors import CurriculumNotFound
from app.infrastructure.database import get_db
from app.infrastructure.repositories.curriculum_repo import CurriculumRepository
from app.application.curricula.create_curriculum import CreateCurriculum
from app.application.curricula.add_curriculum_item import AddCurriculumItem
from app.application.curricula.edit_curriculum_item import EditCurriculumItem
from app.application.curricula.remove_curriculum_item import RemoveCurriculumItem
from app.application.curricula.reorder_curriculum_items import ReorderCurriculumItems
from app.application.curricula.instantiate_curriculum import InstantiateCurriculum
from app.application.curricula.add_curriculum_item_resource import AddCurriculumItemResource
from app.projection.curricula.list import CurriculumListProjection
from app.projection.curricula.detail import CurriculumDetailProjection
from app.hyperstate.response import HyperStateResponse, ActorContext
from app.web.deps import get_current_actor

router = APIRouter(tags=["curricula"])

class CreateCurriculumReq(BaseModel):
    name: str
    description: str | None = None
    grade_level: str | None = None

class AddItemReq(BaseModel):
    subject_id: str
    title: str
    description: str | None = None
    day_offset: int | None = None

class ReorderReq(BaseModel):
    item_ids: str

class InstantiateReq(BaseModel):
    student_id: str
    start_date: date

class EditItemReq(BaseModel):
    title: str
    subject_id: str
    description: str | None = None
    day_offset: int | None = None

class AddItemResourceReq(BaseModel):
    resource_type: str
    title: str
    url: str


@router.get("/curricula", response_model=HyperStateResponse)
async def list_curricula(
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    repo = CurriculumRepository(db)
    curricula = await repo.list_all()
    return CurriculumListProjection(curricula, actor).build()

@router.post("/curricula", response_model=HyperStateResponse)
async def create_curriculum(
    req: CreateCurriculumReq,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    use_case = CreateCurriculum(db)
    return await use_case.execute(
        name=req.name,
        description=req.description,
        grade_level=req.grade_level,
        actor=actor,
    )

@router.get("/curricula/{curriculum_id}", response_model=HyperStateResponse)
async def get_curriculum(
    curriculum_id: str,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    repo = CurriculumRepository(db)
    curriculum = await repo.get_by_id(curriculum_id)
    if not curriculum:
        raise CurriculumNotFound(curriculum_id)
    return CurriculumDetailProjection(curriculum, actor).build()

@router.post("/curricula/{curriculum_id}/items", response_model=HyperStateResponse)
async def add_curriculum_item(
    curriculum_id: str,
    req: AddItemReq,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    use_case = AddCurriculumItem(db)
    return await use_case.execute(
        curriculum_id=curriculum_id,
        subject_id=req.subject_id,
        title=req.title,
        description=req.description,
        day_offset=req.day_offset,
        actor=actor,
    )

@router.post("/curricula/{curriculum_id}/items/{item_id}/edit", response_model=HyperStateResponse)
async def edit_curriculum_item(
    curriculum_id: str,
    item_id: str,
    req: EditItemReq,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    use_case = EditCurriculumItem(db)
    return await use_case.execute(
        curriculum_id=curriculum_id,
        item_id=item_id,
        title=req.title,
        subject_id=req.subject_id,
        description=req.description,
        day_offset=req.day_offset,
        actor=actor,
    )

@router.post("/curricula/{curriculum_id}/items/{item_id}/remove", response_model=HyperStateResponse)
async def remove_curriculum_item(
    curriculum_id: str,
    item_id: str,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    use_case = RemoveCurriculumItem(db)
    return await use_case.execute(
        curriculum_id=curriculum_id,
        item_id=item_id,
        actor=actor,
    )

@router.post("/curricula/{curriculum_id}/items/reorder", response_model=HyperStateResponse)
async def reorder_curriculum_items(
    curriculum_id: str,
    req: ReorderReq,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    use_case = ReorderCurriculumItems(db)
    ids_list = [i.strip() for i in req.item_ids.split(",") if i.strip()]
    return await use_case.execute(
        curriculum_id=curriculum_id,
        item_ids=ids_list,
        actor=actor,
    )

@router.post("/curricula/{curriculum_id}/items/{item_id}/resources", response_model=HyperStateResponse)
async def add_curriculum_item_resource(
    curriculum_id: str,
    item_id: str,
    req: AddItemResourceReq,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    use_case = AddCurriculumItemResource(db)
    return await use_case.execute(
        curriculum_id=curriculum_id,
        item_id=item_id,
        resource_type=req.resource_type,
        title=req.title,
        url=req.url,
        actor=actor,
    )

@router.post("/curricula/{curriculum_id}/instantiate", response_model=HyperStateResponse)
async def instantiate_curriculum(
    curriculum_id: str,
    req: InstantiateReq,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    use_case = InstantiateCurriculum(db)
    return await use_case.execute(
        curriculum_id=curriculum_id,
        student_id=req.student_id,
        start_date=req.start_date,
        actor=actor,
    )
