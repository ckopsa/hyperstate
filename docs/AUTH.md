# Authentication Patterns for HyperState

Authentication in HyperState follows the same principle as everything else:
the server decides what the client renders. Login forms, permission errors,
and user-switching are all standard HyperState responses. The client doesn't
need special auth logic.

## How It Works

### Token Storage: httponly Cookies

HyperState uses httponly cookies for auth tokens. The client never touches
tokens directly — `fetch()` sends cookies automatically, and the server
sets/clears them via `Set-Cookie` headers.

This is intentional: the SPA client is a generic renderer. It doesn't know
about authentication. It just sends requests and renders whatever comes back.

### Login Flow

```
1. Client requests /dashboard
2. Server: no cookie → raises NotAuthenticated
3. Exception handler returns 401 + HyperStateResponse with login form
4. Client renders the login form (it's just a normal response)
5. User submits → POST /auth/login with credentials
6. Server validates → sets cookie → returns dashboard response
7. Client renders dashboard (cookie is now set for future requests)
```

### Logout Flow

```
1. User clicks "Sign Out" (an action section in the response)
2. POST /auth/logout
3. Server clears cookie → returns login form response
4. Client renders login form
```

## Architecture

### Library Layer (`hyperstate/auth.py`)

Framework-level primitives that any HyperState app can use:

```python
from hyperstate.auth import (
    # Exceptions (register as FastAPI exception handlers)
    NotAuthenticated,        # → 401 with login form
    NotAuthorized,           # → 403 with explanation

    # Role checking
    has_role,                # bool: does actor have this role?
    has_any_role,            # bool: does actor have any of these roles?
    require_role,            # raises NotAuthorized if missing
    require_any_role,        # raises NotAuthorized if missing all

    # Projection helpers
    role_condition,          # ActionCondition | None for role-gating actions

    # Action builders
    login_action,            # standard login form section
    logout_action,           # standard logout button section
    switch_user_action,      # user-switcher for dev/demo
)
```

### App Layer (`app/web/auth/`)

Application-specific auth implementation:

```
app/web/auth/
├── tokens.py    # JWT encode/decode (cookie-based)
├── users.py     # User store (demo: static dict; prod: database)
└── routes.py    # /auth/login, /auth/logout, /auth/me, /auth/switch
```

### Dependencies (`app/web/deps.py`)

Two FastAPI dependencies for resolving the current actor:

```python
from app.web.deps import get_current_actor, get_current_actor_optional

# Requires auth — raises NotAuthenticated if no cookie
@router.get("/lessons")
async def list_lessons(actor: ActorContext = Depends(get_current_actor)):
    ...

# Optional auth — returns None if not authenticated
@router.get("/auth/login")
async def login_page(actor: ActorContext | None = Depends(get_current_actor_optional)):
    ...
```

## Patterns

### Role-Gating an Entire Route

Use `require_role` in the route handler or use case:

```python
from hyperstate.auth import require_role

@router.post("/admin/reset")
async def reset_system(
    actor: ActorContext = Depends(get_current_actor),
    db: AsyncSession = Depends(get_db),
):
    require_role(actor, "admin")
    # ... only admins reach here
```

### Role-Gating an Action in a Projection

Use `role_condition` to disable the action for unauthorized users instead
of hiding it:

```python
from hyperstate.auth import role_condition

def _delete_section(self) -> ActionSection:
    return ActionSection(
        key="delete",
        label="Delete",
        method="POST",
        href=f"/items/{self.item.id}/delete",
        style="danger",
        confirm="Are you sure?",
        condition=role_condition(self.actor, "admin"),
    )
```

This renders a disabled "Delete" button with "Requires 'admin' role." for
non-admin users, rather than hiding it entirely.

### Customizing UI by Role

Check roles in projections to change labels, add/remove sections, or
adjust layouts:

```python
from hyperstate.auth import has_role

def _complete_section(self) -> ActionSection:
    is_student = has_role(self.actor, "student")
    label = "I finished this!" if is_student else "Mark Complete"
    return ActionSection(key="complete", label=label, ...)
```

### 401/403 Exception Handlers

Registered in `app/main.py`. They return valid HyperState responses:

- **401 (NotAuthenticated):** Returns a `form` view with the login action.
  The client renders it like any other response.
- **403 (NotAuthorized):** Returns an `error` view explaining what role
  is required. Includes navigation back to safe pages.

### Demo User Switching

For development and demos, the `/auth/me` page includes a user-switcher
dropdown. This lets you test role-based UI without logging in/out:

```python
from hyperstate.auth import switch_user_action

sections.append(switch_user_action([
    {"value": "parent-1", "label": "Sarah (parent)"},
    {"value": "student-1", "label": "Emma (student)"},
]))
```

## Adding Auth to an Existing App

1. **Create auth routes** (`app/web/auth/routes.py`):
   - `GET /auth/login` — login form
   - `POST /auth/login` — authenticate + set cookie
   - `POST /auth/logout` — clear cookie
   - `GET /auth/me` — current user profile

2. **Update `deps.py`** — replace mock actor with cookie-based resolution

3. **Register exception handlers** in `main.py`:
   ```python
   from hyperstate.auth import NotAuthenticated, NotAuthorized, login_action

   @app.exception_handler(NotAuthenticated)
   async def handle_401(request, exc):
       return JSONResponse(status_code=401, content=HyperStateResponse(
           view="form", title="Sign In Required", self_="/auth/login",
           sections=[ContentSection(body=exc.message), login_action()],
       ).model_dump(by_alias=True, exclude_none=True))

   @app.exception_handler(NotAuthorized)
   async def handle_403(request, exc):
       return JSONResponse(status_code=403, content=HyperStateResponse(
           view="error", title="Permission Denied", self_=str(request.url.path),
           sections=[ContentSection(body=exc.message)],
       ).model_dump(by_alias=True, exclude_none=True))
   ```

4. **Register auth router**:
   ```python
   app.include_router(auth_router)
   ```

5. **Update nav** — add "Sign In" / "Sign Out" links to your projections
   based on whether the actor is authenticated.

## Token Implementation

The reference implementation uses a minimal JWT (HS256) with no external
dependencies. For production, replace `app/web/auth/tokens.py` with:
- **PyJWT** (`pip install pyjwt`) for standard JWT
- **python-jose** for JWK/JWS support
- **Authlib** for OAuth2/OIDC integration

The cookie name, lifetime, and security settings are in `app/web/auth/routes.py`:

```python
_COOKIE_NAME = "hs_token"
_COOKIE_MAX_AGE = 86400  # 24 hours
# httponly=True, samesite="lax" — secure defaults
```

For production, also add `secure=True` (HTTPS only) and consider
`samesite="strict"`.
