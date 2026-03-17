# HyperState

A server-driven hypermedia protocol and framework for building interactive web applications with Python.

The server decides what the client renders. Every response describes its own UI — sections, actions, forms, navigation — so the client never evaluates business logic. State transitions, available actions, and validation all live on the server.

## What It Looks Like

Every endpoint returns a `HyperStateResponse`:

```python
from hyperstate import HyperStateResponse, ViewContext, ActorContext
from hyperstate.sections import PropertiesSection, ActionSection, ActionCondition
from hyperstate.display import PropertyItem

response = HyperStateResponse(
    view="detail",
    title="Fractions Lesson",
    self_="/lessons/LES-A1B2C3",
    context=ViewContext(domain="lessons", aggregate="lesson", state="pending"),
    sections=[
        PropertiesSection(title="Details", data=[
            PropertyItem(key="status", label="Status", value="pending", display="badge"),
            PropertyItem(key="subject", label="Subject", value="Math"),
        ]),
        ActionSection(
            key="start", label="Start Lesson",
            method="POST", href="/lessons/LES-A1B2C3/start",
            style="primary",
        ),
        ActionSection(
            key="complete", label="Mark Complete",
            method="POST", href="/lessons/LES-A1B2C3/complete",
            condition=ActionCondition(met=False, explain="Start the lesson first."),
        ),
    ],
)
```

The client renders sections in order. Unavailable actions show as disabled buttons with explanations — they're never silently omitted.

## Quick Start

```bash
uv run python main.py              # Start server on :8000
uv run pytest                      # Run tests
uv run python scripts/hsclient.py  # Interactive CLI client
```

Open `http://localhost:8000` in a browser to see the SPA client, or use the CLI client to explore the hypermedia responses directly.

## Architecture

The project has two parts:

### `hyperstate/` — The Protocol Library

A standalone Python package defining the response format. No application dependencies — just Pydantic and Starlette.

- **Response envelope** — `HyperStateResponse` with view type, title, nav, and sections
- **8 section types** — properties, action, list, content, summary, timeline, group, empty
- **16 form field types** — text, select, date, file, repeatable groups, and more
- **Field dependencies** — dependent dropdowns, dynamic form reloading
- **Action conditions** — disabled actions with explanations and alternatives

See [docs/PROTOCOL.md](docs/PROTOCOL.md) for the full specification.

### `app/` — The Demo Application

A homeschool planner built with FastAPI, async SQLAlchemy, and DDD layers:

```
app/
├── domain/         # Pure business logic (aggregates, state machines, events)
├── application/    # Use case handlers
├── infrastructure/ # ORM models, repositories, database
├── projection/     # State-aware UI response builders
└── web/            # FastAPI routes
```

Four domains: **lessons**, **students**, **subjects**, **curricula** — plus dashboards, calendars, and reports.

## Key Ideas

**Server-driven UI.** The server sends structured responses describing what to render. The client is a generic renderer — it doesn't know what a "lesson" is.

**State machines drive actions.** Aggregate state determines which actions appear and which are disabled. A pending lesson shows "Start"; a completed lesson shows "Reset to Pending".

**Disabled, not hidden.** Unavailable actions include an `ActionCondition` explaining why they can't be used, rather than disappearing. Users always see what's possible.

**Projections, not templates.** Response builders (`projection/`) translate domain state into UI sections. Routes never construct responses directly.

**Discoverable.** Navigation, actions, and pagination are all server-provided URLs. Clients follow links — they never construct URLs.

## Testing

```bash
# Run unit tests
uv run pytest

# Crawl the app for broken links and protocol violations
uv run python scripts/hsclient.py --crawl --start /dashboard

# Record a user story as a regression test
uv run python scripts/hsclient.py --record my-story --start /dashboard

# Replay a recorded story
uv run python scripts/hsclient.py --replay stories/my-story.json
```

## Adding a New Domain

See [docs/SCAFFOLD.md](docs/SCAFFOLD.md) for the complete guide with file templates and a wiring checklist.

## Content Type

`application/vnd.hyperstate+json`
