# Scaffold Guide: Adding a New Domain

Adding a new domain to a HyperState application requires files across 6 layers.
This guide provides the exact file list, templates, and wiring checklist.

## File Checklist

Replace `{name}` with your domain name (singular, lowercase). Replace `{Name}`
with PascalCase and `{NAME}` with UPPER_SNAKE_CASE.

```
app/
├── domain/{name}/
│   ├── __init__.py              # empty
│   ├── aggregate.py             # {Name} aggregate root
│   ├── states.py                # {Name}State enum + TRANSITIONS
│   ├── events.py                # Domain events (frozen dataclasses)
│   ├── commands.py              # Command DTOs (frozen dataclasses)
│   ├── errors.py                # Domain exceptions
│   └── entities.py              # Child entities (if needed)
├── application/{name}/
│   ├── __init__.py              # empty
│   └── create_{name}.py         # First use case
├── infrastructure/
│   ├── models/{name}_model.py   # SQLAlchemy ORM model
│   └── repositories/{name}_repo.py  # Repository
├── projection/{name}/
│   ├── __init__.py              # empty
│   ├── detail.py                # Detail view projection
│   └── list.py                  # List view projection
└── web/{name}/
    ├── __init__.py              # empty
    └── routes.py                # FastAPI router
```

**Minimum:** 13 files. Add more use cases, projections, and entity files as
the domain grows.

---

## Templates

### 1. `domain/{name}/states.py`

```python
from enum import StrEnum


class {Name}State(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


TRANSITIONS: dict[{Name}State, dict[str, {Name}State]] = {
    {Name}State.DRAFT: {
        "activate": {Name}State.ACTIVE,
    },
    {Name}State.ACTIVE: {
        "archive": {Name}State.ARCHIVED,
    },
    {Name}State.ARCHIVED: {
        "activate": {Name}State.ACTIVE,
    },
}


def can_transition(current: {Name}State, action: str) -> bool:
    return action in TRANSITIONS.get(current, {})


def next_state(current: {Name}State, action: str) -> {Name}State:
    transitions = TRANSITIONS.get(current, {})
    if action not in transitions:
        raise InvalidTransition(current, action)
    return transitions[action]


class InvalidTransition(Exception):
    def __init__(self, state: {Name}State, action: str):
        self.state = state
        self.action = action
        super().__init__(f"Cannot '{action}' from state '{state}'")
```

### 2. `domain/{name}/events.py`

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class {Name}Created:
    {name}_id: str


@dataclass(frozen=True)
class {Name}Activated:
    {name}_id: str


@dataclass(frozen=True)
class {Name}Archived:
    {name}_id: str
```

### 3. `domain/{name}/commands.py`

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Create{Name}:
    {name}_id: str
    title: str
    # Add domain-specific fields


@dataclass(frozen=True)
class Activate{Name}:
    {name}_id: str
```

### 4. `domain/{name}/errors.py`

```python
class {Name}Error(Exception):
    """Base for domain-level {name} errors."""
    pass


class {Name}NotFound(Exception):
    def __init__(self, {name}_id: str):
        self.{name}_id = {name}_id
        super().__init__(f"{Name} {{name}_id} not found")
```

### 5. `domain/{name}/aggregate.py`

```python
from __future__ import annotations

from dataclasses import dataclass

from app.domain.shared.aggregate import AggregateRoot
from .states import {Name}State, next_state
from .errors import {Name}Error
from .events import {Name}Created, {Name}Activated, {Name}Archived


@dataclass(kw_only=True)
class {Name}(AggregateRoot):
    """Aggregate root for {name}."""

    id: str
    title: str
    state: {Name}State = {Name}State.DRAFT

    @classmethod
    def create(cls, id: str, title: str) -> "{Name}":
        if not title.strip():
            raise {Name}Error("{Name} title cannot be empty.")
        {name} = cls(id=id, title=title)
        {name}._events.append({Name}Created({name}_id=id))
        return {name}

    def activate(self) -> None:
        self._transition("activate")
        self._events.append({Name}Activated({name}_id=self.id))

    def archive(self) -> None:
        self._transition("archive")
        self._events.append({Name}Archived({name}_id=self.id))

    def _transition(self, action: str) -> None:
        self.state = next_state(self.state, action)
```

### 6. `infrastructure/models/{name}_model.py`

```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class {Name}Row(Base):
    __tablename__ = "{name}s"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    state: Mapped[str] = mapped_column(String, index=True, default="draft")
```

### 7. `infrastructure/repositories/{name}_repo.py`

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.{name}.aggregate import {Name}
from app.domain.{name}.states import {Name}State
from app.infrastructure.models.{name}_model import {Name}Row


class {Name}Repository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, {name}_id: str) -> {Name} | None:
        stmt = select({Name}Row).where({Name}Row.id == {name}_id)
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return self._to_domain(row)

    async def list_all(self) -> list[{Name}]:
        stmt = select({Name}Row).order_by({Name}Row.title)
        rows = (await self.session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]

    async def save(self, {name}: {Name}) -> None:
        stmt = select({Name}Row).where({Name}Row.id == {name}.id)
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row is None:
            row = {Name}Row(id={name}.id)
            self.session.add(row)
        row.title = {name}.title
        row.state = {name}.state.value
        await self.session.flush()

    def _to_domain(self, row: {Name}Row) -> {Name}:
        return {Name}(
            id=row.id,
            title=row.title,
            state={Name}State(row.state),
        )
```

### 8. `application/{name}/create_{name}.py`

```python
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.{name}.aggregate import {Name}
from app.infrastructure.repositories.{name}_repo import {Name}Repository
from hyperstate.response import HyperStateResponse, ActorContext
from hyperstate.flash import Flash
from app.projection.{name}.detail import {Name}DetailProjection


class Create{Name}:
    def __init__(self, session: AsyncSession):
        self.repo = {Name}Repository(session)
        self.session = session

    async def execute(self, title: str, actor: ActorContext) -> HyperStateResponse:
        {name}_id = f"{NAME_PREFIX}-{{uuid.uuid4().hex[:6].upper()}}"
        {name} = {Name}.create(id={name}_id, title=title)
        await self.repo.save({name})
        await self.session.commit()

        return {Name}DetailProjection({name}, actor).build(
            flash=Flash(type="success", title="{Name} Created", body=f"'{{title}}' has been created.")
        )
```

### 9. `projection/{name}/detail.py`

```python
from app.domain.{name}.aggregate import {Name}
from app.domain.{name}.states import {Name}State
from hyperstate.display import PropertyItem
from hyperstate.fields import TextField
from hyperstate.flash import Flash
from hyperstate.nav import NavLink
from hyperstate.response import ActorContext, HyperStateResponse, ViewContext
from hyperstate.sections import (
    ActionCondition,
    ActionSection,
    PropertiesSection,
    Section,
)


class {Name}DetailProjection:
    def __init__(self, {name}: {Name}, actor: ActorContext):
        self.{name} = {name}
        self.actor = actor

    def build(self, flash: Flash | None = None) -> HyperStateResponse:
        sections: list[Section] = [self._properties_section()]

        # State-driven actions
        if action := self._activate_section():
            sections.append(action)
        if action := self._archive_section():
            sections.append(action)

        return HyperStateResponse(
            view="detail",
            title=self.{name}.title,
            self_=f"/{name}s/{{self.{name}.id}}",
            context=ViewContext(
                domain="{name}s",
                aggregate="{name}",
                state=self.{name}.state.value,
                actor=self.actor,
            ),
            flash=flash,
            nav=[
                NavLink(label="All {Name}s", href="/{name}s", rel="collection"),
            ],
            sections=sections,
        )

    def _properties_section(self) -> PropertiesSection:
        return PropertiesSection(
            title="{Name} Details",
            data=[
                PropertyItem(
                    key="status", label="Status",
                    value=self.{name}.state.value, display="badge",
                    variant=self._state_variant(),
                ),
                PropertyItem(key="title", label="Title", value=self.{name}.title),
            ],
        )

    def _activate_section(self) -> ActionSection | None:
        match self.{name}.state:
            case {Name}State.DRAFT | {Name}State.ARCHIVED:
                return ActionSection(
                    key="activate",
                    label="Activate",
                    method="POST",
                    href=f"/{name}s/{{self.{name}.id}}/activate",
                    style="primary",
                )
            case {Name}State.ACTIVE:
                return ActionSection(
                    key="activate",
                    label="Activate",
                    method="POST",
                    href=f"/{name}s/{{self.{name}.id}}/activate",
                    condition=ActionCondition(met=False, explain="Already active."),
                )
        return None

    def _archive_section(self) -> ActionSection | None:
        match self.{name}.state:
            case {Name}State.ACTIVE:
                return ActionSection(
                    key="archive",
                    label="Archive",
                    method="POST",
                    href=f"/{name}s/{{self.{name}.id}}/archive",
                    style="danger",
                    confirm="Are you sure you want to archive this?",
                )
            case _:
                return None

    def _state_variant(self) -> str:
        return {
            {Name}State.DRAFT: "secondary",
            {Name}State.ACTIVE: "success",
            {Name}State.ARCHIVED: "secondary",
        }.get(self.{name}.state, "secondary")
```

### 10. `projection/{name}/list.py`

```python
from app.domain.{name}.aggregate import {Name}
from hyperstate.fields import TextField
from hyperstate.flash import Flash
from hyperstate.nav import NavLink
from hyperstate.response import ActorContext, HyperStateResponse, ViewContext
from hyperstate.sections import (
    ActionSection,
    ColumnDef,
    EmptySection,
    ListItem,
    ListSection,
    Section,
)


class {Name}ListProjection:
    def __init__(self, {name}s: list[{Name}], actor: ActorContext):
        self.{name}s = {name}s
        self.actor = actor

    def build(self, flash: Flash | None = None) -> HyperStateResponse:
        sections: list[Section] = []

        if self.{name}s:
            sections.append(self._list_section())
        else:
            sections.append(EmptySection(
                title="No {Name}s Yet",
                description="Create your first {name} to get started.",
            ))

        sections.append(self._create_section())

        return HyperStateResponse(
            view="list",
            title="{Name}s",
            self_="/{name}s",
            context=ViewContext(
                domain="{name}s",
                aggregate="{name}",
                state="collection",
                actor=self.actor,
            ),
            flash=flash,
            nav=[
                NavLink(label="Dashboard", href="/dashboard", rel="up"),
            ],
            sections=sections,
        )

    def _list_section(self) -> ListSection:
        return ListSection(
            columns=[
                ColumnDef(key="title", label="Title"),
                ColumnDef(key="state", label="Status"),
            ],
            items=[
                ListItem(
                    href=f"/{name}s/{{item.id}}",
                    data={{"title": item.title, "state": item.state.value}},
                )
                for item in self.{name}s
            ],
        )

    def _create_section(self) -> ActionSection:
        return ActionSection(
            key="create-{name}",
            label="Create {Name}",
            method="POST",
            href="/{name}s",
            style="primary",
            fields=[
                TextField(name="title", label="Title", required=True),
            ],
        )
```

### 11. `web/{name}/routes.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.{name}.create_{name} import Create{Name}
from app.domain.{name}.errors import {Name}NotFound
from hyperstate.response import ActorContext, HyperStateResponse
from app.infrastructure.database import get_db
from app.infrastructure.repositories.{name}_repo import {Name}Repository
from app.projection.{name}.detail import {Name}DetailProjection
from app.projection.{name}.list import {Name}ListProjection
from app.web.deps import get_current_actor

router = APIRouter(prefix="/{name}s", tags=["{name}s"])


class Create{Name}Body(BaseModel):
    title: str


@router.get("", response_model=HyperStateResponse)
async def list_{name}s(
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    repo = {Name}Repository(db)
    items = await repo.list_all()
    return {Name}ListProjection(items, actor).build()


@router.post("", response_model=HyperStateResponse)
async def create_{name}(
    body: Create{Name}Body,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    use_case = Create{Name}(db)
    return await use_case.execute(title=body.title, actor=actor)


@router.get("/{{{name}_id}}", response_model=HyperStateResponse)
async def get_{name}(
    {name}_id: str,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    repo = {Name}Repository(db)
    {name} = await repo.get({name}_id)
    if {name} is None:
        raise HTTPException(status_code=404, detail=f"{Name} {{{name}_id}} not found")
    return {Name}DetailProjection({name}, actor).build()
```

---

## Wiring Checklist

After creating the files, wire them into the app:

### 1. Register the router in `app/main.py`

```python
from app.web.{name}.routes import router as {name}_router
app.include_router({name}_router)
```

### 2. Import the ORM model so SQLAlchemy creates the table

In `app/main.py` or `app/infrastructure/models/__init__.py`:

```python
from app.infrastructure.models.{name}_model import {Name}Row  # noqa: F401
```

### 3. Register domain exception handlers

In `app/main.py`:

```python
from app.domain.{name}.errors import {Name}Error

@app.exception_handler({Name}Error)
async def handle_{name}_error(request, exc):
    return JSONResponse(
        status_code=400,
        content=HyperStateResponse(
            view="error",
            title="Error",
            self_=str(request.url.path),
            sections=[ContentSection(body=str(exc))],
        ).model_dump(by_alias=True),
    )
```

### 4. Add seed data (optional)

In `app/main.py` startup event:

```python
# Guard with existence check
existing = await {Name}Repository(session).list_all()
if not existing:
    # Create seed data
```

### 5. Add nav links

Update dashboard or other projections to include navigation to the new domain:

```python
NavLink(label="{Name}s", href="/{name}s", rel="related")
```

---

## Validation

After scaffolding, verify with:

```bash
# Run the server
uv run python main.py

# Crawl for protocol violations
uv run python scripts/hsclient.py --crawl --start /{name}s

# Interactive exploration
uv run python scripts/hsclient.py --start /{name}s

# Record a regression story
uv run python scripts/hsclient.py --record create-{name} --start /{name}s
```

## Common Patterns

### Adding state transitions as actions

In your detail projection, use `match` on aggregate state:

```python
def _some_action(self) -> ActionSection | None:
    match self.{name}.state:
        case {Name}State.ACTIVE:
            return ActionSection(key="do-thing", label="Do Thing", ...)
        case _:
            return ActionSection(
                key="do-thing", label="Do Thing", ...,
                condition=ActionCondition(met=False, explain="Must be active."),
            )
```

### Adding child entities

1. Add entity dataclass to `domain/{name}/entities.py`
2. Add ORM model with ForeignKey to `infrastructure/models/{name}_model.py`
3. Add `relationship()` to the parent model
4. Update repository `save()` to sync child entities
5. Update repository `_to_domain()` to include children
6. Add `selectinload()` to repository queries
7. Add list/action sections to the detail projection

### Adding use cases for transitions

```python
# application/{name}/transition_{name}.py
class Transition{Name}:
    def __init__(self, session: AsyncSession):
        self.repo = {Name}Repository(session)
        self.session = session

    async def execute(self, {name}_id: str, action: str, actor: ActorContext) -> HyperStateResponse:
        {name} = await self.repo.get({name}_id)
        if {name} is None:
            raise {Name}NotFound({name}_id)
        getattr({name}, action)()  # calls aggregate method
        await self.repo.save({name})
        await self.session.commit()
        return {Name}DetailProjection({name}, actor).build(
            flash=Flash(type="success", title=f"{Name} {{action}}d.")
        )
```
