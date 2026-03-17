# Error Handling Patterns for HyperState

Every error response is a valid `HyperStateResponse`. The client renders errors
the same way it renders everything else — no special error handling code needed.
This is the core principle: **errors are views, not exceptions.**

## Error Categories

There are exactly 5 error categories in a HyperState app. Each maps to an HTTP
status code and a specific response shape.

| Category | HTTP | View | When |
|----------|------|------|------|
| Not Found | 404 | `error` | Aggregate doesn't exist |
| Business Rule Violation | 422 | `error` | Domain rejects the action |
| Validation Error | 422 | `error` | Request body fails schema validation |
| Not Authenticated | 401 | `form` | No valid identity |
| Not Authorized | 403 | `error` | Identity lacks permission |

### 1. Not Found (404)

Raised when a `get()` returns `None`. Use a domain-specific `NotFound` exception.

**Domain exception:**
```python
# app/domain/{name}/errors.py
from app.domain.errors import DomainError

class {Name}NotFound(DomainError):
    def __init__(self, {name}_id: str):
        self.{name}_id = {name}_id
        super().__init__(f"{Name} {{{name}_id}} not found")
```

**Exception handler in `main.py`:**
```python
@app.exception_handler({Name}NotFound)
async def {name}_not_found_handler(request, exc: {Name}NotFound):
    response = HyperStateResponse(
        view="error",
        title="Not Found",
        self_=str(request.url.path),
        sections=[ContentSection(body=str(exc), format="plain")],
        nav=[NavLink(label="All {Name}s", href="/{name}s", rel="collection")],
    )
    return JSONResponse(status_code=404, content=response.model_dump(by_alias=True, exclude_none=True))
```

**Route usage — always raise the domain exception, never `HTTPException`:**
```python
# GOOD: domain exception → HyperState error response
{name} = await repo.get({name}_id)
if {name} is None:
    raise {Name}NotFound({name}_id)

# BAD: HTTPException → FastAPI default JSON, NOT a HyperState response
raise HTTPException(status_code=404, detail=f"{Name} not found")
```

### 2. Business Rule Violation (422)

Raised when the domain rejects an action — invalid state transition, empty
required field, constraint violation.

**Domain exception:**
```python
# app/domain/{name}/errors.py
from app.domain.errors import DomainError

class {Name}Error(DomainError):
    """Base for domain-level {name} errors."""
    pass
```

**Exception handler:**
```python
@app.exception_handler({Name}Error)
async def {name}_error_handler(request, exc: {Name}Error):
    response = HyperStateResponse(
        view="error",
        title="Cannot Complete Action",
        self_=str(request.url.path),
        sections=[ContentSection(body=str(exc), format="plain")],
        nav=[NavLink(label="Go Back", href=request.headers.get("referer", "/dashboard"))],
    )
    return JSONResponse(status_code=422, content=response.model_dump(by_alias=True, exclude_none=True))
```

**Domain usage:**
```python
# In the aggregate
def complete(self) -> None:
    if self.state == LessonState.COMPLETED:
        raise LessonError("Lesson is already completed.")
    self._transition("complete")
```

**The InvalidTransition exception** from `states.py` is also a business rule
violation. Register a handler for it too:

```python
from app.domain.{name}.states import InvalidTransition

@app.exception_handler(InvalidTransition)
async def invalid_transition_handler(request, exc: InvalidTransition):
    response = HyperStateResponse(
        view="error",
        title="Invalid Action",
        self_=str(request.url.path),
        sections=[ContentSection(body=str(exc), format="plain")],
    )
    return JSONResponse(status_code=422, content=response.model_dump(by_alias=True, exclude_none=True))
```

### 3. Validation Error (422)

Raised by Pydantic when the request body doesn't match the schema. FastAPI
handles this automatically but returns its own JSON format — not a HyperState
response. Override it:

```python
from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, exc: RequestValidationError):
    # Build a human-readable summary from Pydantic's error list
    messages = []
    for err in exc.errors():
        field = " → ".join(str(loc) for loc in err["loc"] if loc != "body")
        messages.append(f"{field}: {err['msg']}")
    body = "\n".join(messages) if messages else "Invalid request data."

    response = HyperStateResponse(
        view="error",
        title="Validation Error",
        self_=str(request.url.path),
        sections=[ContentSection(body=body, format="plain")],
    )
    return JSONResponse(status_code=422, content=response.model_dump(by_alias=True, exclude_none=True))
```

### 4. Not Authenticated (401)

See [AUTH.md](AUTH.md) for full details. The key: the 401 response includes
a login form, so the client just renders it.

```python
from hyperstate.auth import NotAuthenticated, login_action

@app.exception_handler(NotAuthenticated)
async def not_authenticated_handler(request, exc: NotAuthenticated):
    response = HyperStateResponse(
        view="form",
        title="Sign In Required",
        self_="/auth/login",
        sections=[
            ContentSection(body=exc.message, format="plain"),
            login_action(),
        ],
    )
    return JSONResponse(status_code=401, content=response.model_dump(by_alias=True, exclude_none=True))
```

### 5. Not Authorized (403)

```python
from hyperstate.auth import NotAuthorized

@app.exception_handler(NotAuthorized)
async def not_authorized_handler(request, exc: NotAuthorized):
    detail = exc.message
    if exc.required_roles:
        detail += f" Required: {', '.join(exc.required_roles)}."
    response = HyperStateResponse(
        view="error",
        title="Permission Denied",
        self_=str(request.url.path),
        sections=[ContentSection(body=detail, format="plain")],
        nav=[NavLink(label="Dashboard", href="/dashboard")],
    )
    return JSONResponse(status_code=403, content=response.model_dump(by_alias=True, exclude_none=True))
```

## Domain Exception Hierarchy

All domain exceptions should extend `DomainError` so you can register a
catch-all handler as a safety net:

```
DomainError (base)
├── {Name}Error           # business rule violations
├── {Name}NotFound        # entity not found
└── InvalidTransition     # state machine rejected the action
```

```python
# app/domain/errors.py
class DomainError(Exception):
    """Base class for all domain errors."""
    pass
```

```python
# app/domain/{name}/errors.py
from app.domain.errors import DomainError

class {Name}Error(DomainError):
    pass

class {Name}NotFound(DomainError):
    def __init__(self, {name}_id: str):
        self.{name}_id = {name}_id
        super().__init__(f"{Name} {{{name}_id}} not found")
```

**Catch-all handler** (register AFTER specific handlers — FastAPI matches
most-specific first):

```python
from app.domain.errors import DomainError

@app.exception_handler(DomainError)
async def domain_error_handler(request, exc: DomainError):
    response = HyperStateResponse(
        view="error",
        title="Error",
        self_=str(request.url.path),
        sections=[ContentSection(body=str(exc), format="plain")],
        nav=[NavLink(label="Dashboard", href="/dashboard")],
    )
    return JSONResponse(status_code=422, content=response.model_dump(by_alias=True, exclude_none=True))
```

## Rules

1. **Every error is a HyperState response.** Never let FastAPI return its
   default JSON for errors the client will see.

2. **Raise domain exceptions, not `HTTPException`.** Domain exceptions are
   caught by handlers that produce proper HyperState error views.
   `HTTPException` bypasses this and returns raw JSON.

3. **All domain exceptions extend `DomainError`.** This enables the catch-all
   handler and keeps the hierarchy consistent.

4. **Include navigation in error responses.** Always give the user a way
   to get back to a working page — usually the collection list or dashboard.

5. **Use `view="error"` for errors, `view="form"` for 401.** The 401 is
   special because it includes a login form. All other errors use the
   error view.

6. **Don't hide errors behind generic messages.** The domain exception's
   message IS the user-facing message. Write them clearly:
   - Good: `"Cannot defer a completed lesson."`
   - Bad: `"An error occurred."`

7. **Register the validation error handler.** Without it, Pydantic
   validation failures return FastAPI's default JSON, breaking the
   protocol contract.

## Checklist for New Domains

When adding a new domain, register these exception handlers in `main.py`:

```
[ ] {Name}NotFound    → 404 error view
[ ] {Name}Error       → 422 error view
[ ] InvalidTransition → 422 error view (if domain has state machine)
```

The catch-all `DomainError` handler covers anything you miss, but explicit
handlers give better error messages and navigation.
