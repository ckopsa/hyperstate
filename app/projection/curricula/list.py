from typing import Iterable

from app.domain.curricula.aggregate import Curriculum
from app.hyperstate.response import HyperStateResponse, ViewContext, ActorContext
from app.hyperstate.sections import ListSection, ActionSection, ColumnDef, ListItem
from app.hyperstate.fields import TextField, TextareaField, SelectField, FieldOption
from app.hyperstate.nav import NavLink

GRADE_OPTIONS = [
    FieldOption(value="K", label="Kindergarten"),
    FieldOption(value="1st", label="1st Grade"),
    FieldOption(value="2nd", label="2nd Grade"),
    FieldOption(value="3rd", label="3rd Grade"),
    FieldOption(value="4th", label="4th Grade"),
    FieldOption(value="5th", label="5th Grade"),
    FieldOption(value="6th", label="6th Grade"),
    FieldOption(value="7th", label="7th Grade"),
    FieldOption(value="8th", label="8th Grade"),
    FieldOption(value="9th", label="9th Grade"),
    FieldOption(value="10th", label="10th Grade"),
    FieldOption(value="11th", label="11th Grade"),
    FieldOption(value="12th", label="12th Grade"),
]

class CurriculumListProjection:
    def __init__(self, curricula: Iterable[Curriculum], actor: ActorContext):
        self.curricula = list(curricula)
        self.actor = actor

    def build(self) -> HyperStateResponse:
        return HyperStateResponse(
            view="list",
            title="Curricula",
            self_="/curricula",
            context=ViewContext(
                domain="curricula",
                aggregate="curricula",
                state="collection",
                actor=self.actor,
            ),
            nav=[NavLink(label="Dashboard", href="/dashboard", rel="parent")],
            sections=[
                ActionSection(
                    key="create-curriculum",
                    label="Create Curriculum",
                    method="POST",
                    href="/curricula",
                    fields=[
                        TextField(name="name", label="Name", required=True),
                        TextareaField(name="description", label="Description"),
                        SelectField(name="grade_level", label="Grade Level", required=False, options=GRADE_OPTIONS),
                    ],
                ),
                ListSection(
                    title="All Curricula",
                    columns=[
                        ColumnDef(key="name", label="Name"),
                        ColumnDef(key="grade", label="Grade Level"),
                        ColumnDef(key="description", label="Description"),
                    ],
                    items=[
                        ListItem(
                            href=f"/curricula/{c.id}",
                            data={
                                "name": c.name,
                                "grade": c.grade_level or "-",
                                "description": c.description or "-",
                            },
                        )
                        for c in self.curricula
                    ],
                ),
            ],
        )
