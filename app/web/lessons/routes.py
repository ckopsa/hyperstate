import httpx
from datetime import date

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.lessons.add_resource import AddResource
from app.application.lessons.create_lesson import CreateLesson
from app.application.lessons.delete_photo import DeletePhoto, PhotoNotFound
from app.application.lessons.remove_resource import RemoveResource
from app.application.lessons.transition_lesson import TransitionLesson
from app.application.lessons.upload_photo import UploadPhoto
from app.domain.lessons.errors import LessonError, LessonNotFound
from app.domain.lessons.states import LessonState
from hyperstate.flash import Flash
from hyperstate.forms import FieldErrors
from hyperstate.response import ActorContext, HyperStateResponse
from app.infrastructure.database import get_db
from app.infrastructure.repositories.instruction_day_repo import InstructionDayRepository
from app.infrastructure.repositories.lesson_repo import LessonRepository
from app.infrastructure.repositories.portfolio_photo_repo import PortfolioPhotoRepository
from app.infrastructure.repositories.student_repo import StudentRepository
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
    sort: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    repo = LessonRepository(db)
    lessons = await repo.list_all(
        student_id=student_id,
        subject_id=subject_id,
        state=state,
        sort=sort,
    )
    subjects = await SubjectRepository(db).list_all()
    students = await StudentRepository(db).list_all()
    return LessonListProjection(
        lessons,
        actor,
        subjects=subjects,
        students=students,
        student_id=student_id,
        subject_id=subject_id,
        state=state,
        sort=sort,
    ).build()


@router.post("", response_model=HyperStateResponse)
async def create_lesson(
    body: CreateLessonBody,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    # Validate fields and return form with inline errors if invalid
    errors = FieldErrors()
    if not body.title.strip():
        errors.add("title", "Title cannot be empty.")
    if not body.subject_id:
        errors.add("subject_id", "Please select a subject.")
    if not body.student_id:
        errors.add("student_id", "Please select a student.")

    if errors:
        # Re-render the list page with the form errors applied
        repo = LessonRepository(db)
        lessons = await repo.list_all()
        subjects = await SubjectRepository(db).list_all()
        students = await StudentRepository(db).list_all()
        projection = LessonListProjection(lessons, actor, subjects=subjects, students=students)
        response = projection.build()

        # Find the create form action and apply errors + submitted values
        submitted = {
            "title": body.title,
            "subject_id": body.subject_id,
            "student_id": body.student_id,
            "description": body.description,
            "scheduled_date": body.scheduled_date.isoformat() if body.scheduled_date else "",
            "time_slot": body.time_slot,
        }
        for i, section in enumerate(response.sections):
            if hasattr(section, "key") and section.key == "create-lesson":
                response.sections[i], flash = errors.apply(section, submitted)
                response.flash = flash
                break

        return response

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
        raise LessonNotFound(lesson_id)
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
        raise LessonNotFound(lesson_id)

    just_completed = lesson.state != LessonState.COMPLETED
    if just_completed:
        if lesson.state == LessonState.PENDING:
            lesson.start()
        lesson.complete(completed_by=actor.id)
        await repo.save(lesson)

        # Auto-log instruction day for the completion date
        completion_date = lesson.completed_at.date() if lesson.completed_at else date.today()
        subject_repo_pre = SubjectRepository(db)
        subject = await subject_repo_pre.get(lesson.subject_id)
        subject_name = subject.name if subject else None
        instruction_day_repo = InstructionDayRepository(db)
        await instruction_day_repo.ensure_day(
            completion_date,
            lessons_delta=1,
            subject_name=subject_name,
        )

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
    photo: UploadFile | None = File(None),
    photo_url: str | None = Form(None),
    caption: str | None = Form(None),
    tags: list[str] = Form(default=[]),
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    if photo is None and not photo_url:
        raise LessonError("Must provide either a photo file or a photo URL.")
    if photo is not None and photo_url:
        raise LessonError("Cannot provide both a photo file and a photo URL.")

    if photo is not None:
        if not photo.content_type or not photo.content_type.startswith("image/"):
            raise LessonError("Only image files are accepted.")
        file_content = await photo.read()
        filename = photo.filename or "photo.jpg"
        mime_type = photo.content_type
    else:
        import urllib.parse
        parsed = urllib.parse.urlparse(photo_url)
        if parsed.scheme not in ("http", "https"):
            raise LessonError("Invalid URL scheme. Use http or https.")

        try:
            async with httpx.AsyncClient() as client:
                async with client.stream("GET", photo_url) as res:
                    res.raise_for_status()
                    mime_type = res.headers.get("content-type", "image/jpeg")
                    if not mime_type.startswith("image/"):
                        raise LessonError("URL must point to an image.")

                    content_length = res.headers.get("content-length")
                    if content_length and int(content_length) > 10 * 1024 * 1024:
                        raise LessonError("Image is too large (max 10MB).")

                    chunks = []
                    bytes_read = 0
                    async for chunk in res.aiter_bytes():
                        chunks.append(chunk)
                        bytes_read += len(chunk)
                        if bytes_read > 10 * 1024 * 1024:
                            raise LessonError("Image is too large (max 10MB).")

                    file_content = b"".join(chunks)

                    filename = photo_url.split("/")[-1]
                    if not filename or "." not in filename:
                        filename = "downloaded_photo.jpg"
        except httpx.RequestError as e:
            raise LessonError(f"Failed to download image from URL: {e}")
        except LessonError:
            raise
        except Exception as e:
            raise LessonError(f"Failed to download image from URL: {e}")

    use_case = UploadPhoto(db)
    _, returned_lesson_id = await use_case.execute(
        lesson_id=lesson_id,
        filename=filename,
        file_content=file_content,
        mime_type=mime_type,
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
        raise PhotoNotFound(photo_id)
    return PortfolioPhotoDetailProjection(photo, actor).build()


@router.post("/{lesson_id}/portfolio/{photo_id}/delete", response_model=HyperStateResponse)
async def delete_portfolio_photo(
    lesson_id: str,
    photo_id: str,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    use_case = DeletePhoto(db)
    returned_lesson_id = await use_case.execute(photo_id)

    lesson_repo = LessonRepository(db)
    lesson = await lesson_repo.get(returned_lesson_id)
    if lesson is None:
        raise LessonNotFound(returned_lesson_id)
    photo_repo = PortfolioPhotoRepository(db)
    photos = await photo_repo.list_by_lesson(returned_lesson_id)
    return LessonDetailProjection(lesson, actor, photos).build(
        flash=Flash(type="info", title="Photo deleted.")
    )
