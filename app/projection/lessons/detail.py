import os
from typing import List

from app.domain.lessons.aggregate import Lesson
from app.domain.lessons.entities import PortfolioPhoto
from app.domain.lessons.states import LessonState
from app.hyperstate.display import PropertyItem
from app.hyperstate.fields import FileField, FieldOption, MultiSelectField, SelectField, TextField, UrlField
from app.hyperstate.flash import Flash
from app.hyperstate.nav import NavLink
from app.hyperstate.response import ActorContext, HyperStateResponse, ViewContext
from app.hyperstate.sections import (
    ActionCondition,
    ActionSection,
    ColumnDef,
    EmptySection,
    GroupSection,
    ListItem,
    ListSection,
    PropertiesSection,
    Section,
)

_UPLOAD_URL_PREFIX = "/uploads/portfolio"

_TAG_OPTIONS = [
    FieldOption(value="art", label="Art"),
    FieldOption(value="writing", label="Writing"),
    FieldOption(value="math-work", label="Math Work"),
    FieldOption(value="science-experiment", label="Science Experiment"),
    FieldOption(value="project", label="Project"),
]


class LessonDetailProjection:
    def __init__(self, lesson: Lesson, actor: ActorContext, photos: list[PortfolioPhoto] | None = None):
        self.lesson = lesson
        self.actor = actor
        self.photos = photos or []

    def build(self, flash: Flash | None = None) -> HyperStateResponse:
        l = self.lesson

        left_sections: List[Section] = [self._properties_section()]
        if action := self._start_section():
            left_sections.append(action)
        if action := self._complete_section():
            left_sections.append(action)
        if action := self._reset_section():
            left_sections.append(action)
        left_sections.append(self._resources_section())
        left_sections.append(self._add_resource_section())

        right_sections: List[Section] = [
            self._portfolio_list_section(),
            self._upload_section(),
        ]

        sections: List[Section] = [
            GroupSection(
                layout="sidebar",
                sections=[
                    GroupSection(layout="stack", sections=left_sections),
                    GroupSection(layout="stack", sections=right_sections),
                ],
            )
        ]

        return HyperStateResponse(
            view="detail",
            title=l.title,
            self_=f"/lessons/{l.id}",
            context=ViewContext(
                domain="lessons",
                aggregate="lesson",
                state=l.state.value,
                actor=self.actor,
            ),
            flash=flash,
            nav=[
                NavLink(label="All Lessons", href="/lessons", rel="collection"),
                NavLink(label="Subject", href=f"/subjects/{l.subject_id}", rel="related"),
                NavLink(label="Student", href=f"/students/{l.student_id}", rel="related"),
                NavLink(label="Portfolio Gallery", href="/portfolio", rel="related"),
            ],
            sections=sections,
        )

    def _properties_section(self) -> PropertiesSection:
        l = self.lesson
        data = [
            PropertyItem(
                key="status", label="Status",
                value=l.state.value, display="badge",
                variant=self._state_variant(),
            ),
            PropertyItem(key="subject", label="Subject", value=l.subject_id),
            PropertyItem(key="student", label="Student", value=l.student_id),
            PropertyItem(key="time_slot", label="Time Slot", value=l.time_slot),
        ]
        if l.scheduled_date:
            data.append(PropertyItem(
                key="scheduled_date", label="Scheduled Date",
                value=l.scheduled_date.isoformat(), display="date",
            ))
        if l.description:
            data.append(PropertyItem(key="description", label="Description", value=l.description))
        if l.completed_at:
            data.append(PropertyItem(
                key="completed_at", label="Completed At",
                value=l.completed_at.isoformat(), display="datetime",
            ))
        if l.completed_by:
            data.append(PropertyItem(
                key="completed_by", label="Completed By",
                value=l.completed_by, display="badge",
                variant="success",
            ))
        return PropertiesSection(title="Lesson Details", data=data)

    def _resources_section(self) -> ListSection:
        lesson = self.lesson
        items = [
            ListItem(
                data={
                    "type": r.resource_type,
                    "title": r.title,
                    "url": r.url,
                },
                actions=[
                    ActionSection(
                        key="remove-resource",
                        label="Remove",
                        method="POST",
                        href=f"/lessons/{lesson.id}/resources/{r.id}/remove",
                        style="danger",
                        confirm="Remove this resource?",
                    )
                ],
            )
            for r in lesson.resources
        ]
        return ListSection(
            title="Resources",
            columns=[
                ColumnDef(key="type", label="Type"),
                ColumnDef(key="title", label="Title"),
                ColumnDef(key="url", label="URL"),
            ],
            items=items,
        )

    def _add_resource_section(self) -> ActionSection:
        lesson = self.lesson
        return ActionSection(
            key="add-resource",
            label="Add Resource",
            method="POST",
            href=f"/lessons/{lesson.id}/resources",
            style="default",
            fields=[
                SelectField(
                    name="resource_type",
                    label="Type",
                    required=True,
                    options=[
                        FieldOption(value="pdf", label="PDF"),
                        FieldOption(value="video", label="Video"),
                        FieldOption(value="link", label="Link"),
                    ],
                ),
                TextField(
                    name="title",
                    label="Title",
                    required=True,
                    placeholder="Resource title",
                ),
                UrlField(
                    name="url",
                    label="URL",
                    required=True,
                    placeholder="https://...",
                ),
            ],
        )

    def _portfolio_list_section(self) -> ListSection | EmptySection:
        if not self.photos:
            return EmptySection(
                title="No Student Work Yet",
                description="Upload a photo to start building this lesson's portfolio.",
            )
        columns = [
            ColumnDef(key="thumbnail", label="Photo", display="image"),
            ColumnDef(key="caption", label="Caption"),
            ColumnDef(key="uploaded_at", label="Date", display="datetime"),
        ]
        items = []
        for p in self.photos:
            stored_filename = os.path.basename(p.file_path)
            img_url = f"{_UPLOAD_URL_PREFIX}/{stored_filename}"
            items.append(ListItem(
                href=f"/lessons/{self.lesson.id}/portfolio/{p.id}",
                data={
                    "thumbnail": img_url,
                    "caption": p.caption or "—",
                    "uploaded_at": p.uploaded_at.isoformat() if p.uploaded_at else "",
                },
            ))
        return ListSection(title="Student Work", columns=columns, items=items)

    def _upload_section(self) -> ActionSection:
        return ActionSection(
            key="upload-work",
            label="Add Student Work",
            method="POST",
            href=f"/lessons/{self.lesson.id}/portfolio",
            fields=[
                FileField(
                    name="photo",
                    label="Upload Photo",
                    required=False,
                    accept=["image/*"],
                    help="Choose an image file from your device",
                ),
                UrlField(
                    name="photo_url",
                    label="Or Paste Image URL",
                    required=False,
                    placeholder="https://example.com/image.jpg",
                ),
                TextField(
                    name="caption",
                    label="Caption",
                    placeholder="What did they create?",
                ),
                MultiSelectField(
                    name="tags",
                    label="Tags",
                    options=_TAG_OPTIONS,
                ),
            ],
        )

    def _start_section(self) -> ActionSection | None:
        l = self.lesson
        match l.state:
            case LessonState.PENDING:
                return ActionSection(
                    key="start",
                    label="Start Lesson",
                    method="POST",
                    href=f"/lessons/{l.id}/start",
                    style="primary",
                )
            case LessonState.IN_PROGRESS | LessonState.COMPLETED:
                return ActionSection(
                    key="start",
                    label="Start Lesson",
                    method="POST",
                    href=f"/lessons/{l.id}/start",
                    condition=ActionCondition(met=False, explain="Lesson is already started."),
                )
        return None

    def _complete_section(self) -> ActionSection | None:
        l = self.lesson
        is_student = "student" in (self.actor.roles if self.actor else [])
        label = "I finished this!" if is_student else "Mark Complete"
        key = "mark-complete"
        match l.state:
            case LessonState.IN_PROGRESS:
                return ActionSection(
                    key=key,
                    label=label,
                    method="POST",
                    href=f"/lessons/{l.id}/complete",
                    style="primary",
                )
            case LessonState.PENDING:
                if is_student:
                    return ActionSection(
                        key=key,
                        label=label,
                        method="POST",
                        href=f"/lessons/{l.id}/complete",
                        style="primary",
                    )
                return ActionSection(
                    key=key,
                    label=label,
                    method="POST",
                    href=f"/lessons/{l.id}/complete",
                    condition=ActionCondition(met=False, explain="Start the lesson before marking complete."),
                )
            case LessonState.COMPLETED:
                return None
        return None

    def _reset_section(self) -> ActionSection | None:
        l = self.lesson
        match l.state:
            case LessonState.IN_PROGRESS | LessonState.COMPLETED:
                return ActionSection(
                    key="reset",
                    label="Reset to Pending",
                    method="POST",
                    href=f"/lessons/{l.id}/reset",
                    style="subtle",
                )
            case _:
                return None

    def _state_variant(self) -> str:
        return {
            LessonState.PENDING: "secondary",
            LessonState.IN_PROGRESS: "warning",
            LessonState.COMPLETED: "success",
        }.get(self.lesson.state, "secondary")
