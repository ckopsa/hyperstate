from typing import Iterable

from app.domain.subjects.aggregate import Subject
from app.domain.lessons.aggregate import Lesson
from app.hyperstate.response import HyperStateResponse, ViewContext, ActorContext
from app.hyperstate.flash import Flash
from app.hyperstate.nav import NavLink
from app.hyperstate.sections import (
    Section, PropertiesSection, ActionSection, ListSection, EmptySection,
    ActionCondition, ActionAlternative, ColumnDef, ListItem,
)
from app.hyperstate.display import PropertyItem
from app.hyperstate.fields import TextField, SelectField, TextareaField
from app.projection.subjects.list import COLOR_OPTIONS, ICON_OPTIONS


class SubjectDetailProjection:
    def __init__(self, subject: Subject, lessons: Iterable[Lesson], actor: ActorContext):
        self.subject = subject
        self.lessons = list(lessons)
        self.actor = actor

    def build(self, flash: Flash | None = None) -> HyperStateResponse:
        s = self.subject
        sections: list[Section] = [self._properties_section()]
        sections.append(self._lessons_section())
        sections.append(self._edit_section())
        sections.append(self._delete_section())

        return HyperStateResponse(
            view="detail",
            title=f"{s.icon} {s.name}",
            self_=f"/subjects/{s.id}",
            context=ViewContext(
                domain="subjects",
                aggregate="subject",
                state="active",
                actor=self.actor,
            ),
            flash=flash,
            nav=[
                NavLink(label="All Subjects", href="/subjects", rel="collection"),
                NavLink(label="Dashboard", href="/dashboard", rel="parent"),
            ],
            sections=sections,
        )

    def _properties_section(self) -> PropertiesSection:
        s = self.subject
        data = [
            PropertyItem(key="name", label="Name", value=s.name),
            PropertyItem(key="icon", label="Icon", value=s.icon),
            PropertyItem(key="color", label="Color", value=s.color),
            PropertyItem(key="type", label="Type", value="Custom" if s.is_custom else "Standard"),
            PropertyItem(key="lesson_count", label="Lessons", value=str(len(self.lessons))),
        ]
        if s.description:
            data.append(PropertyItem(key="description", label="Description", value=s.description))
        return PropertiesSection(title="Subject Details", data=data)

    def _lessons_section(self) -> Section:
        s = self.subject
        if not self.lessons:
            return EmptySection(
                title="No Lessons Yet",
                description="This subject has no lessons scheduled.",
                action=ActionAlternative(
                    label="Add First Lesson",
                    href=f"/lessons?subject_id={s.id}",
                    method="GET",
                ),
            )
        return ListSection(
            title="Lessons",
            columns=[
                ColumnDef(key="title", label="Title"),
                ColumnDef(key="date", label="Date"),
                ColumnDef(key="state", label="Status"),
            ],
            items=[
                ListItem(
                    href=f"/lessons/{lesson.id}",
                    data={
                        "title": lesson.title,
                        "date": lesson.scheduled_date.isoformat() if lesson.scheduled_date else "—",
                        "state": lesson.state.value,
                    },
                )
                for lesson in self.lessons
            ],
        )

    def _edit_section(self) -> ActionSection:
        s = self.subject
        return ActionSection(
            key="edit-subject",
            label="Edit Subject",
            method="PATCH",
            href=f"/subjects/{s.id}",
            fields=[
                TextField(name="name", label="Name", required=True, value=s.name),
                SelectField(name="color", label="Color", options=COLOR_OPTIONS, value=s.color),
                SelectField(name="icon", label="Icon", options=ICON_OPTIONS, value=s.icon),
                TextareaField(name="description", label="Description", value=s.description),
            ],
        )

    def _delete_section(self) -> ActionSection:
        s = self.subject
        has_lessons = len(self.lessons) > 0
        condition = None if not has_lessons else ActionCondition(
            met=False,
            explain="Move or delete lessons first before deleting this subject.",
        )
        return ActionSection(
            key="delete-subject",
            label="Delete Subject",
            method="DELETE",
            href=f"/subjects/{s.id}",
            style="danger",
            confirm="Are you sure you want to delete this subject?" if not has_lessons else None,
            condition=condition,
        )
