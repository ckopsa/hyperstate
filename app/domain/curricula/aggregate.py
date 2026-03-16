from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime

from .entities import CurriculumItem

@dataclass
class Curriculum:
    id: str
    name: str
    description: str | None = None
    grade_level: str | None = None
    items: list[CurriculumItem] = field(default_factory=list)

    @classmethod
    def create(cls, id: str, name: str, description: str | None = None, grade_level: str | None = None) -> Curriculum:
        return cls(id=id, name=name, description=description, grade_level=grade_level)

    def add_item(self, item: CurriculumItem) -> None:
        self.items.append(item)
        self._resequence()

    def remove_item(self, item_id: str) -> None:
        self.items = [item for item in self.items if item.id != item_id]
        self._resequence()

    def reorder_items(self, item_ids: list[str]) -> None:
        new_items = []
        added_ids = set()
        for id_ in item_ids:
            for item in self.items:
                if item.id == id_ and id_ not in added_ids:
                    new_items.append(item)
                    added_ids.add(id_)
                    break

        # Ensure any missing items are appended to the end, protecting against deletion
        for item in self.items:
            if item.id not in added_ids:
                new_items.append(item)
                added_ids.add(item.id)

        self.items = new_items
        self._resequence()

    def _resequence(self) -> None:
        for idx, item in enumerate(self.items):
            item.sequence = idx + 1
