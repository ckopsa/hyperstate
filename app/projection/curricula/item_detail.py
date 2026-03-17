from app.domain.curricula.aggregate import Curriculum
from app.domain.curricula.entities import CurriculumItem
from app.hyperstate.response import HyperStateResponse, ViewContext, ActorContext
from app.hyperstate.flash import Flash
from app.hyperstate.sections import PropertiesSection, ActionSection, ListSection, ColumnDef, ListItem, PropertyItem
from app.hyperstate.fields import TextField, TextareaField, SelectField, FieldOption, NumberField
from app.hyperstate.nav import NavLink

class CurriculumItemDetailProjection:
    def __init__(self, curriculum: Curriculum, item: CurriculumItem, actor: ActorContext):
        self.curriculum = curriculum
        self.item = item
        self.actor = actor

    def build(self, flash: Flash | None = None) -> HyperStateResponse:
        return HyperStateResponse(
            view="detail",
            title=f"Item {self.item.sequence}: {self.item.title}",
            self_=f"/curricula/{self.curriculum.id}/items/{self.item.id}",
            flash=flash,
            context=ViewContext(
                domain="curricula",
                aggregate="curriculum_item",
                state="detail",
                actor=self.actor,
            ),
            nav=[
                NavLink(label="All Curricula", href="/curricula", rel="collection"),
                NavLink(label=self.curriculum.name, href=f"/curricula/{self.curriculum.id}", rel="up"),
            ],
            sections=[
                PropertiesSection(
                    title="Item Details",
                    data=[
                        PropertyItem(key="id", label="ID", value=self.item.id),
                        PropertyItem(key="title", label="Title", value=self.item.title),
                        PropertyItem(key="subject", label="Subject ID", value=self.item.subject_id),
                        PropertyItem(key="description", label="Description", value=self.item.description or "-"),
                        PropertyItem(key="day_offset", label="Day Offset", value=f"+{self.item.day_offset}" if self.item.day_offset is not None else "-"),
                    ],
                ),
                ListSection(
                    title="Resources",
                    columns=[
                        ColumnDef(key="type", label="Type"),
                        ColumnDef(key="title", label="Title"),
                        ColumnDef(key="url", label="URL"),
                        ColumnDef(key="actions", label="Actions", align="right"),
                    ],
                    items=[
                        ListItem(
                            data={
                                "type": res.resource_type.upper(),
                                "title": res.title,
                                "url": res.url,
                            },
                            actions=[
                                ActionSection(
                                    key="remove-resource",
                                    label="Remove",
                                    method="POST",
                                    href=f"/curricula/{self.curriculum.id}/items/{self.item.id}/resources/{res.id}/remove",
                                    style="danger",
                                )
                            ]
                        )
                        for res in self.item.resources
                    ]
                ),
                ActionSection(
                    key="edit-item",
                    label="Edit Curriculum Item",
                    method="POST",
                    href=f"/curricula/{self.curriculum.id}/items/{self.item.id}/edit",
                    fields=[
                        SelectField(name="subject_id", label="Subject", required=True, options_href="/api/subjects", value=self.item.subject_id),
                        TextField(name="title", label="Title", required=True, value=self.item.title),
                        TextareaField(name="description", label="Description", value=self.item.description or ""),
                        NumberField(name="day_offset", label="Day Offset", required=False, value=self.item.day_offset),
                    ],
                ),
                ActionSection(
                    key="add-resource",
                    label="Add Resource",
                    method="POST",
                    href=f"/curricula/{self.curriculum.id}/items/{self.item.id}/resources",
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
                        TextField(name="title", label="Title", required=True),
                        TextField(name="url", label="URL", required=True),
                    ],
                ),
            ],
        )
