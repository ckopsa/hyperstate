from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

ResourceType = Literal["pdf", "video", "link"]

@dataclass(kw_only=True)
class CurriculumItemResource:
    """A template resource attached to a curriculum item."""
    id: str
    item_id: str
    resource_type: ResourceType
    title: str
    url: str

@dataclass(kw_only=True)
class CurriculumItem:
    """A single item in a curriculum."""
    id: str
    curriculum_id: str
    sequence: int
    subject_id: str
    title: str
    description: str | None = None
    day_offset: int | None = None
    resources: list[CurriculumItemResource] = field(default_factory=list)
