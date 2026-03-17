from __future__ import annotations
from typing import Annotated, Any, Literal
from pydantic import BaseModel, Field

from .display import PropertyItem
from .fields import FormField
from .nav import NavLink


# ──────────────────────────────────────────────
# Properties: key-value display
# ──────────────────────────────────────────────

class PropertiesSection(BaseModel):
    kind: Literal["properties"] = "properties"
    title: str | None = None
    data: list[PropertyItem]


# ──────────────────────────────────────────────
# Action: button or form
# ──────────────────────────────────────────────

class ActionCondition(BaseModel):
    """Why an action is unavailable, and what to do instead."""
    met: bool
    explain: str | None = None
    alternative: ActionAlternative | None = None


class ActionAlternative(BaseModel):
    label: str
    href: str
    method: str = "GET"


class ActionSection(BaseModel):
    kind: Literal["action"] = "action"
    key: str                                    # stable identifier for this action
    label: str
    description: str | None = None
    method: str = "POST"
    href: str
    style: Literal["default", "primary", "danger", "subtle"] = "default"
    confirm: str | None = None                  # confirmation dialog text
    condition: ActionCondition | None = None     # None = action is available
    fields: list[FormField] = []                # empty = button, non-empty = form
    reload_href: str | None = None              # for reload_form behavior


# ──────────────────────────────────────────────
# List: collection of items
# ──────────────────────────────────────────────

class ColumnDef(BaseModel):
    key: str
    label: str
    display: str = "plain"
    currency: str | None = None
    align: Literal["left", "right", "center"] = "left"


class ListItem(BaseModel):
    href: str | None = None
    data: dict[str, Any]
    actions: list[ActionSection] = []           # inline row actions


class Pagination(BaseModel):
    next: NavLink | None = None
    prev: NavLink | None = None
    total: int | None = None
    page: int
    per_page: int


class SortOption(BaseModel):
    """A column the server can sort by. href is ready-to-use (preserves current filters/search)."""
    key: str
    label: str
    href: str                                       # GET URL to apply this sort
    active: bool = False                            # is this the current sort?
    direction: Literal["asc", "desc"] | None = None  # current direction if active


class FilterOption(BaseModel):
    """A single selectable value for a filter. href is ready-to-use (preserves current state)."""
    value: str
    label: str
    href: str                                       # GET URL to apply this filter value
    active: bool = False                            # is this value currently selected?
    count: int | None = None                        # optional result-count hint


class FilterControl(BaseModel):
    """A group of related filter options (e.g. 'Status', 'Subject')."""
    key: str
    label: str
    options: list[FilterOption]
    clear_href: str | None = None                   # URL to clear just this filter


class SearchControl(BaseModel):
    """Search box. Client submits GET to href with ?{param}=value."""
    href: str
    param: str = "q"
    value: str | None = None                        # current search query
    placeholder: str | None = None


class ListControls(BaseModel):
    """Optional search/filter/sort controls advertised by the server."""
    search: SearchControl | None = None
    filters: list[FilterControl] = []
    sort_options: list[SortOption] = []
    clear_href: str | None = None                   # URL to clear all active controls


class ListSection(BaseModel):
    kind: Literal["list"] = "list"
    title: str | None = None
    columns: list[ColumnDef]
    items: list[ListItem]
    empty_message: str = "No items."
    pagination: Pagination | None = None
    controls: ListControls | None = None            # search/filter/sort contract


# ──────────────────────────────────────────────
# Content: rich text / markdown block
# ──────────────────────────────────────────────

class ContentSection(BaseModel):
    kind: Literal["content"] = "content"
    title: str | None = None
    body: str
    format: Literal["plain", "markdown", "html"] = "plain"


# ──────────────────────────────────────────────
# Summary: metric cards / KPI row
# ──────────────────────────────────────────────

class SummaryItem(BaseModel):
    label: str
    value: Any
    display: str = "number"
    currency: str | None = None
    href: str | None = None


class SummarySection(BaseModel):
    kind: Literal["summary"] = "summary"
    items: list[SummaryItem]


# ──────────────────────────────────────────────
# Timeline: event history
# ──────────────────────────────────────────────

class TimelineEvent(BaseModel):
    timestamp: str
    label: str
    actor: str | None = None


class TimelineSection(BaseModel):
    kind: Literal["timeline"] = "timeline"
    title: str | None = None
    events: list[TimelineEvent]


# ──────────────────────────────────────────────
# Group: visual grouping of sub-sections
# ──────────────────────────────────────────────

class GroupSection(BaseModel):
    kind: Literal["group"] = "group"
    title: str | None = None
    layout: Literal["stack", "sidebar", "columns"] = "stack"
    sections: list[Section]  # recursive


# ──────────────────────────────────────────────
# Empty: empty state with CTA
# ──────────────────────────────────────────────

class EmptySection(BaseModel):
    kind: Literal["empty"] = "empty"
    title: str
    description: str | None = None
    action: ActionAlternative | None = None


# ──────────────────────────────────────────────
# The discriminated union
# ──────────────────────────────────────────────

Section = Annotated[
    PropertiesSection
    | ActionSection
    | ListSection
    | ContentSection
    | SummarySection
    | TimelineSection
    | GroupSection
    | EmptySection,
    Field(discriminator="kind"),
]

# Required for recursive GroupSection
GroupSection.model_rebuild()
