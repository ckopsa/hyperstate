import os
from typing import List

from app.domain.lessons.entities import PortfolioPhoto
from hyperstate.display import PropertyItem
from hyperstate.flash import Flash
from hyperstate.nav import NavLink
from hyperstate.response import ActorContext, HyperStateResponse, ViewContext
from hyperstate.sections import ActionSection, ContentSection, PropertiesSection, Section

_UPLOAD_URL_PREFIX = "/uploads/portfolio"


class PortfolioPhotoDetailProjection:
    def __init__(self, photo: PortfolioPhoto, actor: ActorContext):
        self.photo = photo
        self.actor = actor

    def build(self, flash: Flash | None = None) -> HyperStateResponse:
        p = self.photo
        stored_filename = os.path.basename(p.file_path)
        img_url = f"{_UPLOAD_URL_PREFIX}/{stored_filename}"

        props = [
            PropertyItem(key="uploaded_at", label="Uploaded", value=p.uploaded_at.isoformat() if p.uploaded_at else "", display="datetime"),
            PropertyItem(key="file_size", label="File Size", value=self._format_size(p.file_size)),
        ]
        if p.caption:
            props.insert(0, PropertyItem(key="caption", label="Caption", value=p.caption))
        if p.tags:
            props.append(PropertyItem(key="tags", label="Tags", value=", ".join(p.tags)))

        sections: List[Section] = [
            PropertiesSection(title="Photo Details", data=props),
            ContentSection(
                title="Photo",
                format="html",
                body=f'<img src="{img_url}" alt="{p.caption or "Student work"}" style="max-width:100%;border-radius:8px;" />',
            ),
            ActionSection(
                key="delete-photo",
                label="Delete Photo",
                method="POST",
                href=f"/lessons/{p.lesson_id}/portfolio/{p.id}/delete",
                style="danger",
                confirm="Delete this photo?",
            ),
        ]

        return HyperStateResponse(
            view="detail",
            title=p.caption or "Student Work Photo",
            self_=f"/lessons/{p.lesson_id}/portfolio/{p.id}",
            context=ViewContext(
                domain="lessons",
                aggregate="portfolio_photo",
                state="uploaded",
                actor=self.actor,
            ),
            flash=flash,
            nav=[
                NavLink(label="← Lesson", href=f"/lessons/{p.lesson_id}", rel="parent"),
                NavLink(label="← Portfolio Gallery", href="/portfolio", rel="collection"),
            ],
            sections=sections,
        )

    def _format_size(self, size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
