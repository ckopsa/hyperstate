import os
from typing import List

from app.domain.lessons.entities import PortfolioPhoto
from hyperstate.flash import Flash
from hyperstate.nav import NavLink
from hyperstate.response import ActorContext, HyperStateResponse, ViewContext
from hyperstate.sections import ColumnDef, EmptySection, ListItem, ListSection, Section

_UPLOAD_URL_PREFIX = "/uploads/portfolio"


class PortfolioGalleryProjection:
    def __init__(self, photos: list[PortfolioPhoto], actor: ActorContext):
        self.photos = photos
        self.actor = actor

    def build(self, flash: Flash | None = None) -> HyperStateResponse:
        sections: List[Section]
        if not self.photos:
            sections = [
                EmptySection(
                    title="No Photos Yet",
                    description="Upload photos of student work from any lesson.",
                )
            ]
        else:
            columns = [
                ColumnDef(key="thumbnail", label="Photo", display="image"),
                ColumnDef(key="caption", label="Caption"),
                ColumnDef(key="lesson", label="Lesson"),
                ColumnDef(key="uploaded_at", label="Date", display="datetime"),
            ]
            items = []
            for p in self.photos:
                stored_filename = os.path.basename(p.file_path)
                img_url = f"{_UPLOAD_URL_PREFIX}/{stored_filename}"
                items.append(ListItem(
                    href=f"/lessons/{p.lesson_id}/portfolio/{p.id}",
                    data={
                        "thumbnail": img_url,
                        "caption": p.caption or "—",
                        "lesson": p.lesson_id,
                        "uploaded_at": p.uploaded_at.isoformat() if p.uploaded_at else "",
                    },
                ))
            sections = [ListSection(title="All Student Work", columns=columns, items=items)]

        return HyperStateResponse(
            view="list",
            title="Portfolio Gallery",
            self_="/portfolio",
            context=ViewContext(
                domain="lessons",
                aggregate="portfolio",
                state="gallery",
                actor=self.actor,
            ),
            flash=flash,
            nav=[NavLink(label="Dashboard", href="/dashboard", rel="parent")],
            sections=sections,
        )
