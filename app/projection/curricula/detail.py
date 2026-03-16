from app.domain.curricula.aggregate import Curriculum
from app.hyperstate.response import HyperStateResponse, ViewContext, ActorContext
from app.hyperstate.flash import Flash
from app.hyperstate.sections import PropertiesSection, ActionSection, ListSection, GroupSection, ColumnDef, ListItem, PropertyItem
from app.hyperstate.fields import TextField, SelectField, DateField, NumberField, FieldOption
from app.hyperstate.nav import NavLink

class CurriculumDetailProjection:
    def __init__(self, curriculum: Curriculum, actor: ActorContext):
        self.curriculum = curriculum
        self.actor = actor

    def build(self, flash: Flash | None = None) -> HyperStateResponse:
        return HyperStateResponse(
            view="detail",
            title=self.curriculum.name,
            self_=f"/curricula/{self.curriculum.id}",
            flash=flash,
            context=ViewContext(
                domain="curricula",
                aggregate="curriculum",
                state="detail",
                actor=self.actor,
            ),
            nav=[
                NavLink(label="All Curricula", href="/curricula", rel="collection"),
            ],
            sections=[
                GroupSection(
                    layout="columns",
                    sections=[
                        PropertiesSection(
                            title="Curriculum Details",
                            data=[
                                PropertyItem(label="ID", value=self.curriculum.id),
                                PropertyItem(label="Name", value=self.curriculum.name),
                                PropertyItem(label="Description", value=self.curriculum.description or "-"),
                                PropertyItem(label="Grade Level", value=self.curriculum.grade_level or "-"),
                            ],
                        ),
                        ActionSection(
                            key="instantiate-curriculum",
                            title="Instantiate for Student",
                            method="POST",
                            href=f"/curricula/{self.curriculum.id}/instantiate",
                            fields=[
                                SelectField(name="student_id", label="Student", required=True, options_href="/api/students"),
                                DateField(name="start_date", label="Start Date", required=True),
                            ],
                        ),
                    ],
                ),
                ListSection(
                    title="Curriculum Items",
                    columns=[
                        ColumnDef(key="sequence", label="#", align="right"),
                        ColumnDef(key="id", label="Item ID", align="right"),
                        ColumnDef(key="title", label="Title"),
                        ColumnDef(key="subject", label="Subject ID"),
                        ColumnDef(key="resources", label="Resources"),
                        ColumnDef(key="day_offset", label="Day Offset", align="right"),
                        ColumnDef(key="actions", label="Actions", align="right"),
                    ],
                    items=[
                        ListItem(
                            data={
                                "sequence": item.sequence,
                                "id": item.id,
                                "title": item.title,
                                "subject": item.subject_id,
                                "resources": ", ".join(r.title for r in item.resources) if item.resources else "None",
                                "day_offset": f"+{item.day_offset}" if item.day_offset is not None else "-",
                            },
                            actions=[
                                ActionSection(
                                    key="add-resource",
                                    label="Add Resource",
                                    method="POST",
                                    href=f"/curricula/{self.curriculum.id}/items/{item.id}/resources",
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
                                ActionSection(
                                    key="remove-item",
                                    label="Remove",
                                    method="POST",
                                    href=f"/curricula/{self.curriculum.id}/items/{item.id}/remove",
                                    style="danger",
                                )
                            ],
                        )
                        for item in self.curriculum.items
                    ],
                ),
                ActionSection(
                    key="add-item",
                    title="Add Curriculum Item",
                    method="POST",
                    href=f"/curricula/{self.curriculum.id}/items",
                    fields=[
                        SelectField(name="subject_id", label="Subject", required=True, options_href="/api/subjects"),
                        TextField(name="title", label="Title", required=True),
                        TextField(name="description", label="Description", type="textarea"),
                        NumberField(name="day_offset", label="Day Offset", required=False),
                    ],
                ),
                                ActionSection(
                                    key="reorder-items",
                                    title="Reorder Items",
                                    method="POST",
                                    href=f"/curricula/{self.curriculum.id}/items/reorder",
                                    fields=[
                                        TextField(
                                            name="item_ids",
                                            label="Comma Separated Item IDs",
                                            required=True,
                                            help="Enter the Item IDs in the new order, separated by commas. Any omitted IDs will be appended to the end.",
                                        ),
                                    ],
                                ),
            ],
        )
