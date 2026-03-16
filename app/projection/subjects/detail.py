from app.domain.subjects.aggregate import Subject
from app.hyperstate.response import HyperStateResponse, ViewContext, ActorContext
from app.hyperstate.flash import Flash
from app.hyperstate.nav import NavLink
from app.hyperstate.sections import PropertiesSection
from app.hyperstate.display import PropertyItem


class SubjectDetailProjection:
    def __init__(self, subject: Subject, actor: ActorContext):
        self.subject = subject
        self.actor = actor

    def build(self, flash: Flash | None = None) -> HyperStateResponse:
        s = self.subject
        data = [
            PropertyItem(key="name", label="Name", value=s.name),
            PropertyItem(key="icon", label="Icon", value=s.icon),
            PropertyItem(key="color", label="Color", value=s.color),
            PropertyItem(key="type", label="Type", value="Custom" if s.is_custom else "Default"),
        ]
        if s.description:
            data.append(PropertyItem(key="description", label="Description", value=s.description))

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
            sections=[PropertiesSection(title="Subject Details", data=data)],
        )
