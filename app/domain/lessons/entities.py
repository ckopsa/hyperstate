from __future__ import annotations
from dataclasses import dataclass
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
