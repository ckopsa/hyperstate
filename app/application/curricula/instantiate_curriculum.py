from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.curricula.errors import CurriculumNotFound
from app.infrastructure.repositories.curriculum_repo import CurriculumRepository
from app.application.lessons.create_lesson import CreateLesson
from app.application.lessons.add_resource import AddResource
from app.hyperstate.response import HyperStateResponse, ActorContext
from app.hyperstate.flash import Flash
from app.projection.lessons.list import LessonListProjection
from app.infrastructure.repositories.student_repo import StudentRepository
from app.domain.students.errors import StudentNotFound


class InstantiateCurriculum:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.curriculum_repo = CurriculumRepository(session)
        self.student_repo = StudentRepository(session)
        self.create_lesson_use_case = CreateLesson(session)
        self.add_resource_use_case = AddResource(session)

    async def execute(
        self,
        curriculum_id: str,
        student_id: str,
        start_date: date,
        actor: ActorContext,
    ) -> HyperStateResponse:
        curriculum = await self.curriculum_repo.get_by_id(curriculum_id)
        if not curriculum:
            raise CurriculumNotFound(curriculum_id)

        student = await self.student_repo.get(student_id)
        if not student:
            raise StudentNotFound(student_id)

        lessons_created = 0
        created_lesson_ids = set()

        for item in curriculum.items:
            scheduled_date = start_date
            if item.day_offset:
                # Add days, skipping weekends (Saturday=5, Sunday=6)
                days_to_add = item.day_offset
                while days_to_add > 0:
                    scheduled_date += timedelta(days=1)
                    if scheduled_date.weekday() < 5:  # Monday to Friday
                        days_to_add -= 1

            # Use CreateLesson internal method to avoid parsing UI href
            lesson = await self.create_lesson_use_case.create_lesson_entity(
                subject_id=item.subject_id,
                student_id=student_id,
                title=item.title,
                description=item.description,
                scheduled_date=scheduled_date,
                time_slot="morning",  # Default
            )
            created_lesson_ids.add(lesson.id)

            # Add resources using AddResource internal method
            for res in item.resources:
                await self.add_resource_use_case.add_resource_to_entity(
                    lesson_id=lesson.id,
                    resource_type=res.resource_type,  # type: ignore
                    title=res.title,
                    url=res.url,
                )

            lessons_created += 1

        await self.session.commit()

        # Redirect to the student's lesson list filtered
        from app.infrastructure.repositories.lesson_repo import LessonRepository
        lesson_repo = LessonRepository(self.session)
        all_lessons = await lesson_repo.list_all(student_id=student_id)

        # Filter to only the lessons we just created
        filtered_lessons = [l for l in all_lessons if l.id in created_lesson_ids]

        flash = Flash(
            type="success",
            title="Curriculum Instantiated",
            body=f"Created {lessons_created} lessons for {student.name} starting {start_date.isoformat()}."
        )
        projection = LessonListProjection(lessons=filtered_lessons, actor=actor)
        response = projection.build()
        response.flash = flash
        return response
