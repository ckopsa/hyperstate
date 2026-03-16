from dataclasses import dataclass, field
from typing import Any


@dataclass(kw_only=True)
class AggregateRoot:
    _events: list[Any] = field(default_factory=list, repr=False)

    def collect_events(self) -> list[Any]:
        events = self._events.copy()
        self._events.clear()
        return events
