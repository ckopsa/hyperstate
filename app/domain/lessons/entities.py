from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


ResourceType = Literal["pdf", "video", "link"]


@dataclass(kw_only=True)
class LessonResource:
    """A resource (PDF, video, or link) attached to a lesson."""

    id: str
    lesson_id: str
    resource_type: ResourceType
    title: str
    url: str


@dataclass
class PortfolioPhoto:
    """A photo of physical student work attached to a lesson."""

    id: str
    lesson_id: str
    filename: str
    file_path: str
    file_size: int
    caption: str | None = None
    tags: list[str] = field(default_factory=list)
    uploaded_at: datetime | None = None
    mime_type: str = "image/jpeg"
