from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.lessons.errors import LessonNotFound
from app.domain.lessons.states import InvalidTransition
from app.infrastructure.repositories.lesson_repo import LessonRepository
from app.hyperstate.response import HyperStateResponse, ActorContext
from app.hyperstate.flash import Flash
from app.projection.lessons.detail import LessonDetailProjection


class TransitionLesson:
    """Generic use case for lesson state transitions (start, complete, reset)."""

    def __init__(self, session: AsyncSession):
        self.repo = LessonRepository(session)
        self.session = session

    async def execute(self, lesson_id: str, action: str, actor: ActorContext) -> HyperStateResponse:
        lesson = await self.repo.get(lesson_id)
        if lesson is None:
            raise LessonNotFound(lesson_id)

        try:
            if action == "start":
                lesson.start()
            elif action == "complete":
                lesson.complete(completed_by=actor.id)
            elif action == "reset":
                lesson.reset()
            else:
                raise ValueError(f"Unknown action: {action}")
        except InvalidTransition:
            return LessonDetailProjection(lesson, actor).build(
                flash=Flash(
                    type="error",
                    title="Cannot Perform Action",
                    body=f"Cannot '{action}' a lesson in '{lesson.state.value}' state.",
                )
            )

        await self.repo.save(lesson)
        await self.session.commit()

        labels = {"start": "Started", "complete": "Completed", "reset": "Reset"}
        return LessonDetailProjection(lesson, actor).build(
            flash=Flash(type="success", title=f"Lesson {labels.get(action, action)}", body="Status updated.")
        )
