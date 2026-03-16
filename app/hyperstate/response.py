# app/hyperstate/response.py

from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field

from .sections import Section
from .nav import NavLink
from .flash import Flash


class ActorContext(BaseModel):
    id: str
    roles: list[str] = []


class ViewContext(BaseModel):
    """DDD metadata — which aggregate, what state, who's looking."""
    domain: str
    aggregate: str
    state: str
    actor: ActorContext | None = None


class HyperStateResponse(BaseModel):
    """Top-level envelope for every HyperState response."""

    type_: Literal["application/vnd.hyperstate+json"] = Field(
        default="application/vnd.hyperstate+json",
        alias="$type",
    )
    version: Literal["0.1.0"] = Field(
        default="0.1.0",
        alias="$version",
    )
    view: Literal["detail", "list", "form", "dashboard", "error"]
    title: str
    self_: str = Field(alias="self")
    context: ViewContext | None = None
    flash: Flash | None = None
    nav: list[NavLink] = []
    sections: list[Section] = []

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "description": "A server-driven hypermedia response. "
            "The client renders sections in order and never evaluates business logic.",
        },
    }
