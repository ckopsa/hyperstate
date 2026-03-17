from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.curricula.aggregate import Curriculum
from app.domain.curricula.entities import CurriculumItem, CurriculumItemResource
from app.infrastructure.models.curriculum_model import CurriculumRow, CurriculumItemRow, CurriculumItemResourceRow


class CurriculumRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, curriculum: Curriculum) -> None:
        stmt = select(CurriculumRow).options(selectinload(CurriculumRow.items).selectinload(CurriculumItemRow.resources)).where(CurriculumRow.id == curriculum.id)
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        if not row:
            row = CurriculumRow(
                id=curriculum.id,
                name=curriculum.name,
                description=curriculum.description,
                grade_level=curriculum.grade_level,
            )
            self.session.add(row)
        else:
            row.name = curriculum.name
            row.description = curriculum.description
            row.grade_level = curriculum.grade_level

        # Delete existing items not in the aggregate
        current_item_ids = {item.id for item in curriculum.items}
        for existing_item in list(row.items):
            if existing_item.id not in current_item_ids:
                row.items.remove(existing_item)

        # Upsert items
        existing_items_map = {item.id: item for item in row.items}
        for item in curriculum.items:
            if item.id in existing_items_map:
                item_row = existing_items_map[item.id]
                item_row.sequence = item.sequence
                item_row.subject_id = item.subject_id
                item_row.title = item.title
                item_row.description = item.description
                item_row.day_offset = item.day_offset
            else:
                item_row = CurriculumItemRow(
                    id=item.id,
                    curriculum_id=item.curriculum_id,
                    sequence=item.sequence,
                    subject_id=item.subject_id,
                    title=item.title,
                    description=item.description,
                    day_offset=item.day_offset,
                )
                row.items.append(item_row)

            # Upsert resources for this item
            current_res_ids = {res.id for res in item.resources}
            for existing_res in list(item_row.resources):
                if existing_res.id not in current_res_ids:
                    item_row.resources.remove(existing_res)

            existing_res_map = {res.id: res for res in item_row.resources}
            for res in item.resources:
                if res.id in existing_res_map:
                    res_row = existing_res_map[res.id]
                    res_row.resource_type = res.resource_type
                    res_row.title = res.title
                    res_row.url = res.url
                else:
                    res_row = CurriculumItemResourceRow(
                        id=res.id,
                        item_id=res.item_id,
                        resource_type=res.resource_type,
                        title=res.title,
                        url=res.url,
                    )
                    item_row.resources.append(res_row)


    async def get_by_id(self, curriculum_id: str) -> Curriculum | None:
        stmt = select(CurriculumRow).options(selectinload(CurriculumRow.items).selectinload(CurriculumItemRow.resources)).where(CurriculumRow.id == curriculum_id)
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()

        if not row:
            return None

        return self._to_aggregate(row)

    async def list_all(self) -> list[Curriculum]:
        stmt = select(CurriculumRow).order_by(CurriculumRow.created_at.desc())
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_aggregate_shallow(row) for row in rows]

    def _to_aggregate(self, row: CurriculumRow) -> Curriculum:
        curriculum = Curriculum(
            id=row.id,
            name=row.name,
            description=row.description,
            grade_level=row.grade_level,
        )
        for item_row in sorted(row.items, key=lambda x: x.sequence):
            item = CurriculumItem(
                id=item_row.id,
                curriculum_id=item_row.curriculum_id,
                sequence=item_row.sequence,
                subject_id=item_row.subject_id,
                title=item_row.title,
                description=item_row.description,
                day_offset=item_row.day_offset,
            )
            for res_row in item_row.resources:
                item.resources.append(CurriculumItemResource(
                    id=res_row.id,
                    item_id=res_row.item_id,
                    resource_type=res_row.resource_type,
                    title=res_row.title,
                    url=res_row.url,
                ))
            curriculum.items.append(item)
        return curriculum

    def _to_aggregate_shallow(self, row: CurriculumRow) -> Curriculum:
        return Curriculum(
            id=row.id,
            name=row.name,
            description=row.description,
            grade_level=row.grade_level,
        )
