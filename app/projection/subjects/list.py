from typing import Iterable

from app.domain.subjects.aggregate import Subject
from hyperstate.response import HyperStateResponse, ViewContext, ActorContext
from hyperstate.flash import Flash
from hyperstate.sections import Section, ListSection, ActionSection, EmptySection, ColumnDef, ListItem
from hyperstate.fields import TextField, SelectField, TextareaField, FieldOption
from hyperstate.nav import NavLink


COLOR_OPTIONS = [
    FieldOption(value="#4F46E5", label="Indigo"),
    FieldOption(value="#7C3AED", label="Purple"),
    FieldOption(value="#DC2626", label="Red"),
    FieldOption(value="#D97706", label="Amber"),
    FieldOption(value="#16A34A", label="Green"),
    FieldOption(value="#0891B2", label="Cyan"),
    FieldOption(value="#DB2777", label="Pink"),
    FieldOption(value="#9CA3AF", label="Gray"),
]

ICON_OPTIONS = [
    FieldOption(value="📐", label="📐 Math"),
    FieldOption(value="📚", label="📚 Reading"),
    FieldOption(value="🔬", label="🔬 Science"),
    FieldOption(value="🌍", label="🌍 History"),
    FieldOption(value="✏️", label="✏️ Writing"),
    FieldOption(value="🏃", label="🏃 PE"),
    FieldOption(value="🎨", label="🎨 Art"),
    FieldOption(value="🎵", label="🎵 Music"),
    FieldOption(value="📖", label="📖 General"),
]


class SubjectListProjection:
    def __init__(self, subjects: Iterable[Subject], actor: ActorContext):
        self.subjects = list(subjects)
        self.actor = actor

    def build(self, flash: Flash | None = None) -> HyperStateResponse:
        sections: list[Section] = [self._create_section()]

        standard = [s for s in self.subjects if not s.is_custom]
        custom = [s for s in self.subjects if s.is_custom]

        if not self.subjects:
            sections.append(EmptySection(
                title="No Subjects Yet",
                description="Create your first subject to start organizing lessons.",
            ))
        else:
            if standard:
                sections.append(self._list_section("Standard Subjects", standard))
            if custom:
                sections.append(self._list_section("Custom Subjects", custom))

        return HyperStateResponse(
            view="list",
            title="Subjects",
            self_="/subjects",
            flash=flash,
            context=ViewContext(
                domain="subjects",
                aggregate="subjects",
                state="collection",
                actor=self.actor,
            ),
            nav=[NavLink(label="Dashboard", href="/dashboard", rel="parent")],
            sections=sections,
        )

    def _create_section(self) -> ActionSection:
        return ActionSection(
            key="create-subject",
            label="Create Subject",
            method="POST",
            href="/subjects",
            fields=[
                TextField(name="name", label="Name", required=True),
                SelectField(name="color", label="Color", options=COLOR_OPTIONS),
                SelectField(name="icon", label="Icon", options=ICON_OPTIONS),
                TextareaField(name="description", label="Description"),
            ],
        )

    def _list_section(self, title: str, subjects: list[Subject]) -> ListSection:
        return ListSection(
            title=title,
            columns=[
                ColumnDef(key="icon", label=""),
                ColumnDef(key="name", label="Subject"),
                ColumnDef(key="type", label="Type"),
            ],
            items=[
                ListItem(
                    href=f"/subjects/{s.id}",
                    data={
                        "icon": s.icon,
                        "name": s.name,
                        "type": "Custom" if s.is_custom else "Standard",
                    },
                )
                for s in subjects
            ],
        )
