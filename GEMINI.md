# HyperState — Homeschool Planner

A server-driven hypermedia application for homeschool planning and tracking.
Built with FastAPI, async SQLAlchemy, and the HyperState protocol.

## Quick Start

```bash
uv run python main.py              # Start server on :8000
uv run pytest                      # Run tests
uv run python scripts/hsclient.py  # CLI test client (interactive)
uv run python scripts/hsclient.py --crawl  # QA crawl
```

## Key Documentation

| Doc | Purpose |
|-----|---------|
| `docs/PROTOCOL.md` | HyperState protocol specification — section types, field types, contracts |
| `docs/SCAFFOLD.md` | Step-by-step guide with templates for adding new domains |

## Architecture: DDD + Server-Driven Hypermedia

The app uses clean DDD layers. **The lessons domain is the reference implementation.**
Study it before building new features.

### Project Structure

```
hyperstate/                        # Standalone protocol library (import as `hyperstate`)
├── response.py                    # HyperStateResponse envelope
├── sections.py                    # Section types (properties, action, list, content, etc.)
├── fields.py                      # Form field types (text, select, boolean, file, etc.)
├── flash.py                       # Flash notifications
├── nav.py                         # NavLink
├── display.py                     # PropertyItem, DisplayHint
├── dependencies.py                # OptionsResponse, FieldResponse, DependsOn
└── middleware.py                  # Content-Type middleware

app/
├── domain/<name>/                 # Pure business logic — NO framework imports
│   ├── aggregate.py               # Aggregate root (extends AggregateRoot)
│   ├── commands.py                # Frozen dataclass command DTOs
│   ├── entities.py                # Child entities belonging to aggregate
│   ├── value_objects.py           # Frozen dataclass value objects (frozen=True)
│   ├── states.py                  # StrEnum + TRANSITIONS dict
│   ├── events.py                  # Frozen dataclass domain events
│   └── errors.py                  # Domain-specific exceptions
├── application/<name>/            # Use case handlers
│   └── <verb>_<noun>.py           # Async class: __init__(session), execute() → HyperStateResponse
├── infrastructure/
│   ├── database.py                # SHARED: engine, async_session, Base, get_db
│   ├── models/<name>_model.py     # SQLAlchemy ORM (Mapped[], mapped_column)
│   └── repositories/<name>_repo.py  # get() → domain, save(domain) → flush
├── projection/<name>/             # State-aware UI response builders
│   ├── list.py                    # Collection → list view
│   ├── detail.py                  # Aggregate → detail view (match state: for actions)
│   └── form.py                    # Form fragment for reload_form
└── web/<name>/
    ├── routes.py                  # FastAPI router with Depends(get_db, get_current_actor)
    └── options.py                 # OptionsResponse endpoints for dependent fields
```

### Key Conventions

1. **Absolute imports only**: `from app.domain.shared.aggregate import AggregateRoot`
2. **HyperState imports from top-level**: `from hyperstate.response import HyperStateResponse`
3. **Async everywhere**: All DB operations, repository methods, use case execute()
4. **Projections build all responses**: Routes never construct HyperStateResponse directly
5. **State-driven UI**: Use `match aggregate.state:` in projections to include/exclude sections
6. **ActionCondition for unavailable actions**: Don't omit the action — set `condition=ActionCondition(met=False, explain="...")`
7. **Repository is the bridge**: ORM stays in infrastructure, domain objects never import SQLAlchemy
8. **Value objects flatten into columns**: Address → shipping_street, shipping_city, etc.
9. **Startup seeding**: New seed data goes in `app/main.py` startup event (guard with existence check)
10. **Router registration**: New routers go in `app/main.py` via `app.include_router()`
11. **Exception handlers**: Domain exceptions → HyperState error views, registered in `app/main.py`

### Reference Implementation Files (Lessons Domain)

| What | File |
|------|------|
| Aggregate root | `app/domain/lessons/aggregate.py` |
| State machine | `app/domain/lessons/states.py` |
| Use case handler | `app/application/lessons/create_lesson.py` |
| ORM model | `app/infrastructure/models/lesson_model.py` |
| Repository | `app/infrastructure/repositories/lesson_repo.py` |
| Detail projection | `app/projection/lessons/detail.py` |
| List projection | `app/projection/lessons/list.py` |
| Routes | `app/web/lessons/routes.py` |
| Tests | `tests/projection/test_lesson_detail.py` |

### Common Imports

```python
# Response envelope
from hyperstate.response import HyperStateResponse, ViewContext, ActorContext
from hyperstate.flash import Flash
from hyperstate.nav import NavLink

# Sections
from hyperstate.sections import (
    PropertiesSection, ActionSection, ListSection, ContentSection,
    SummarySection, TimelineSection, GroupSection, EmptySection,
    ActionCondition, ActionAlternative, ColumnDef, ListItem, Pagination,
)

# Form fields
from hyperstate.fields import (
    TextField, TextareaField, NumberField, SelectField, BooleanField,
    DateField, DatetimeField, FileField, HiddenField, MultiSelectField,
    CurrencyField, RadioField, FieldOption, DependsOn,
)

# Display
from hyperstate.display import PropertyItem

# Infrastructure
from app.infrastructure.database import get_db, async_session, Base
from app.web.deps import get_current_actor
```

## Adding a New Domain

See `docs/SCAFFOLD.md` for the complete guide with file templates and wiring checklist.

## QA Testing

The CLI test client (`scripts/hsclient.py`) speaks the HyperState protocol:

```bash
# Interactive exploration
uv run python scripts/hsclient.py --start /dashboard

# Record a story (saves to stories/<name>.json)
uv run python scripts/hsclient.py --record create-lesson

# Replay a story (stops at step N, optionally continue interactively)
uv run python scripts/hsclient.py --replay stories/create-lesson.json --until 3

# Crawl all reachable pages, report broken links and protocol violations
uv run python scripts/hsclient.py --crawl --start /dashboard
```

Each bead's description includes a "HyperState QA Path" — the sequence of
requests and expected responses to validate that feature. Use `--record` to
capture the path as a regression story.
