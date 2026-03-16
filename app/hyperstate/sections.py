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


class ListSection(BaseModel):
    kind: Literal["list"] = "list"
    title: str | None = None
    columns: list[ColumnDef]
    items: list[ListItem]
    empty_message: str = "No items."
    pagination: Pagination | None = None


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
