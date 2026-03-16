from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.lessons.add_resource import AddResource
from app.application.lessons.create_lesson import CreateLesson
from app.application.lessons.delete_photo import DeletePhoto, PhotoNotFound
from app.application.lessons.remove_resource import RemoveResource
from app.application.lessons.transition_lesson import TransitionLesson
from app.application.lessons.upload_photo import UploadPhoto
from app.domain.lessons.errors import LessonNotFound
from app.domain.lessons.states import LessonState
from app.hyperstate.flash import Flash
from app.hyperstate.response import ActorContext, HyperStateResponse
from app.infrastructure.database import get_db
from app.infrastructure.repositories.lesson_repo import LessonRepository
from app.infrastructure.repositories.portfolio_photo_repo import PortfolioPhotoRepository
from app.infrastructure.repositories.subject_repo import SubjectRepository
from app.projection.dashboard.view import DashboardProjection
from app.projection.lessons.detail import LessonDetailProjection
from app.projection.lessons.list import LessonListProjection
from app.projection.lessons.portfolio_photo_detail import PortfolioPhotoDetailProjection
from app.application.lessons.defer_lesson import DeferLesson
from app.web.deps import get_current_actor

router = APIRouter(prefix="/lessons", tags=["lessons"])


class CreateLessonBody(BaseModel):
    title: str
    subject_id: str
    student_id: str
    description: str | None = None
    scheduled_date: date | None = None
    time_slot: str = "morning"


class AddResourceBody(BaseModel):
    resource_type: str
    title: str
    url: str


@router.get("", response_model=HyperStateResponse)
async def list_lessons(
    student_id: str | None = Query(None),
    subject_id: str | None = Query(None),
    state: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    repo = LessonRepository(db)
    lessons = await repo.list_all(student_id=student_id, subject_id=subject_id, state=state)
    return LessonListProjection(lessons, actor).build()


@router.post("", response_model=HyperStateResponse)
async def create_lesson(
    body: CreateLessonBody,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    use_case = CreateLesson(db)
    return await use_case.execute(
        subject_id=body.subject_id,
        student_id=body.student_id,
        title=body.title,
        description=body.description,
        scheduled_date=body.scheduled_date,
        time_slot=body.time_slot,
        actor=actor,
    )


@router.get("/{lesson_id}", response_model=HyperStateResponse)
async def get_lesson(
    lesson_id: str,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    repo = LessonRepository(db)
    lesson = await repo.get(lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail=f"Lesson {lesson_id} not found")
    photo_repo = PortfolioPhotoRepository(db)
    photos = await photo_repo.list_by_lesson(lesson_id)
    return LessonDetailProjection(lesson, actor, photos).build()


@router.post("/{lesson_id}/start", response_model=HyperStateResponse)
async def start_lesson(
    lesson_id: str,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    use_case = TransitionLesson(db)
    return await use_case.execute(lesson_id, "start", actor)


@router.post("/{lesson_id}/complete", response_model=HyperStateResponse)
async def complete_lesson(
    lesson_id: str,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    repo = LessonRepository(db)
    lesson = await repo.get(lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail=f"Lesson {lesson_id} not found")

    if lesson.state != LessonState.COMPLETED:
        if lesson.state == LessonState.PENDING:
            lesson.start()
        lesson.complete(completed_by=actor.id)
        await repo.save(lesson)
        await db.commit()

    subject_repo = SubjectRepository(db)
    today = date.today()
    today_lessons = await repo.list_by_date(today)
    recently_completed = await repo.list_recently_completed(5)
    instruction_days = await repo.count_instruction_days()
    all_subjects = await subject_repo.list_all()
    subjects_map = {s.id: s for s in all_subjects}

    return DashboardProjection(
        today_lessons=today_lessons,
        recently_completed=recently_completed,
        instruction_days=instruction_days,
        subjects=subjects_map,
        actor=actor,
    ).build(flash=Flash(type="success", title="Great job!", body="Lesson marked as complete."))


@router.post("/{lesson_id}/reset", response_model=HyperStateResponse)
async def reset_lesson(
    lesson_id: str,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    use_case = TransitionLesson(db)
    return await use_case.execute(lesson_id, "reset", actor)


@router.post("/{lesson_id}/resources", response_model=HyperStateResponse)
async def add_resource(
    lesson_id: str,
    body: AddResourceBody,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    use_case = AddResource(db)
    return await use_case.execute(
        lesson_id=lesson_id,
        resource_type=body.resource_type,  # type: ignore[arg-type]
        title=body.title,
        url=body.url,
        actor=actor,
    )


@router.post("/{lesson_id}/resources/{resource_id}/remove", response_model=HyperStateResponse)
async def remove_resource(
    lesson_id: str,
    resource_id: str,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    use_case = RemoveResource(db)
    return await use_case.execute(
        lesson_id=lesson_id,
        resource_id=resource_id,
        actor=actor,
    )


@router.post("/{lesson_id}/defer", response_model=HyperStateResponse)
async def defer_lesson(
    lesson_id: str,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    use_case = DeferLesson(db)
    return await use_case.execute(lesson_id, actor)


@router.post("/{lesson_id}/portfolio", response_model=HyperStateResponse)
async def upload_portfolio_photo(
    lesson_id: str,
    photo: UploadFile = File(...),
    caption: str | None = Form(None),
    tags: list[str] = Form(default=[]),
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    if not photo.content_type or not photo.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are accepted.")

    file_content = await photo.read()
    use_case = UploadPhoto(db)
    _, returned_lesson_id = await use_case.execute(
        lesson_id=lesson_id,
        filename=photo.filename or "photo.jpg",
        file_content=file_content,
        mime_type=photo.content_type,
        caption=caption,
        tags=tags,
        actor=actor,
    )

    lesson_repo = LessonRepository(db)
    lesson = await lesson_repo.get(returned_lesson_id)
    if lesson is None:
        raise LessonNotFound(lesson_id)
    photo_repo = PortfolioPhotoRepository(db)
    photos = await photo_repo.list_by_lesson(returned_lesson_id)
    return LessonDetailProjection(lesson, actor, photos).build(
        flash=Flash(type="success", title="Photo uploaded successfully.")
    )


@router.get("/{lesson_id}/portfolio/{photo_id}", response_model=HyperStateResponse)
async def get_portfolio_photo(
    lesson_id: str,
    photo_id: str,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    photo_repo = PortfolioPhotoRepository(db)
    photo = await photo_repo.get(photo_id)
    if photo is None or photo.lesson_id != lesson_id:
        raise HTTPException(status_code=404, detail=f"Photo {photo_id} not found")
    return PortfolioPhotoDetailProjection(photo, actor).build()


@router.post("/{lesson_id}/portfolio/{photo_id}/delete", response_model=HyperStateResponse)
async def delete_portfolio_photo(
    lesson_id: str,
    photo_id: str,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    use_case = DeletePhoto(db)
    try:
        returned_lesson_id = await use_case.execute(photo_id)
    except PhotoNotFound:
        raise HTTPException(status_code=404, detail=f"Photo {photo_id} not found")

    lesson_repo = LessonRepository(db)
    lesson = await lesson_repo.get(returned_lesson_id)
    if lesson is None:
        raise LessonNotFound(returned_lesson_id)
    photo_repo = PortfolioPhotoRepository(db)
    photos = await photo_repo.list_by_lesson(returned_lesson_id)
    return LessonDetailProjection(lesson, actor, photos).build(
        flash=Flash(type="info", title="Photo deleted.")
    )
