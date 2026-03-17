# HyperState Protocol Specification v0.1.0

Content-Type: `application/vnd.hyperstate+json`

HyperState is a server-driven hypermedia protocol. The server decides what the
client renders. The client never evaluates business logic — it renders sections
in order and follows discovered links and actions.

## Response Envelope

Every response is a `HyperStateResponse`:

```json
{
  "$type": "application/vnd.hyperstate+json",
  "$version": "0.1.0",
  "view": "detail",
  "title": "Lesson: Fractions",
  "self": "/lessons/LES-A1B2C3",
  "context": { ... },
  "flash": { ... },
  "nav": [ ... ],
  "sections": [ ... ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `$type` | string | yes | Always `"application/vnd.hyperstate+json"` |
| `$version` | string | yes | Protocol version, currently `"0.1.0"` |
| `view` | enum | yes | One of: `detail`, `list`, `form`, `dashboard`, `error` |
| `title` | string | yes | Human-readable page title |
| `self` | string | yes | Canonical URL for this resource |
| `context` | ViewContext | no | DDD metadata about what's being viewed |
| `flash` | Flash | no | One-time notification from a prior action |
| `nav` | NavLink[] | no | Navigation links (breadcrumbs, related resources) |
| `sections` | Section[] | yes | Ordered list of UI sections to render |

### ViewContext

Tells the client (and developer tools) which aggregate and state produced this
response. Useful for debugging and for clients that want to optimize rendering.

```json
{
  "domain": "lessons",
  "aggregate": "lesson",
  "state": "in_progress",
  "actor": {
    "id": "user-1",
    "roles": ["teacher"]
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `domain` | string | DDD domain name |
| `aggregate` | string | Aggregate type |
| `state` | string | Current aggregate state |
| `actor` | ActorContext | Who is viewing (id + roles) |

### Flash

One-time notification shown after an action completes. The client displays it
once and discards it.

```json
{
  "type": "success",
  "title": "Lesson Created",
  "body": "'Fractions' has been scheduled."
}
```

| Field | Type | Values |
|-------|------|--------|
| `type` | enum | `success`, `warning`, `error`, `info` |
| `title` | string | Short message |
| `body` | string? | Optional detail |

### NavLink

```json
{ "label": "All Lessons", "href": "/lessons", "rel": "collection" }
```

| Field | Type | Description |
|-------|------|-------------|
| `label` | string | Display text |
| `href` | string | Navigation URL |
| `rel` | string? | Link relation (e.g. `collection`, `related`) |
| `type` | string? | Content type hint (e.g. `application/pdf` for downloads) |

---

## Section Types

Sections are the building blocks of every response. Each section has a `kind`
discriminator. The client renders them in order.

### `properties` — Key-Value Display

Displays a list of labeled values. Used for entity details.

```json
{
  "kind": "properties",
  "title": "Lesson Details",
  "data": [
    {
      "key": "status",
      "label": "Status",
      "value": "in_progress",
      "display": "badge",
      "variant": "warning"
    },
    {
      "key": "scheduled_date",
      "label": "Scheduled Date",
      "value": "2026-03-16",
      "display": "date"
    }
  ]
}
```

Each `PropertyItem` in `data`:

| Field | Type | Description |
|-------|------|-------------|
| `key` | string | Stable identifier |
| `label` | string | Human-readable label |
| `value` | any | The value to display |
| `display` | enum | How to format the value (see Display Hints) |
| `variant` | string? | For `badge`: `success`, `warning`, `danger`, `secondary` |
| `currency` | string? | For `currency`: ISO code like `USD` |
| `format` | string? | For `datetime`: `relative`, `short`, `long` |
| `href` | string? | Makes the value a navigable link |

**Display Hints:** `plain`, `badge`, `currency`, `datetime`, `date`,
`percentage`, `number`, `link`, `code`, `markdown`

### `action` — Button or Form

An action the user can perform. If `fields` is empty, render as a button. If
`fields` is non-empty, render as a form.

```json
{
  "kind": "action",
  "key": "start",
  "label": "Start Lesson",
  "method": "POST",
  "href": "/lessons/LES-A1B2C3/start",
  "style": "primary",
  "confirm": null,
  "condition": null,
  "fields": []
}
```

| Field | Type | Description |
|-------|------|-------------|
| `key` | string | Stable identifier for this action |
| `label` | string | Button/form label |
| `description` | string? | Explanatory text |
| `method` | string | HTTP method (default `POST`) |
| `href` | string | Action endpoint URL |
| `style` | enum | `default`, `primary`, `danger`, `subtle` |
| `confirm` | string? | If set, show confirmation dialog with this text |
| `condition` | ActionCondition? | If set and `met=false`, action is disabled |
| `fields` | FormField[] | Empty = button, non-empty = form |
| `reload_href` | string? | URL to fetch updated form (for `reload_form` behavior) |

#### ActionCondition

**Critical design principle:** Don't omit unavailable actions — include them with
a condition explaining WHY they're unavailable. This lets the UI show disabled
buttons with explanations instead of confusing the user with missing controls.

```json
{
  "met": false,
  "explain": "Start the lesson before marking complete.",
  "alternative": {
    "label": "Start Lesson",
    "href": "/lessons/LES-A1B2C3/start",
    "method": "POST"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `met` | bool | `true` = action available, `false` = disabled |
| `explain` | string? | Why the action is unavailable |
| `alternative` | ActionAlternative? | A different action the user can take instead |

### `list` — Collection of Items

Displays a table/list of items with optional inline actions per row.

```json
{
  "kind": "list",
  "title": "Resources",
  "columns": [
    { "key": "type", "label": "Type" },
    { "key": "title", "label": "Title" },
    { "key": "url", "label": "URL" }
  ],
  "items": [
    {
      "href": null,
      "data": { "type": "pdf", "title": "Workbook", "url": "https://..." },
      "actions": [
        {
          "kind": "action",
          "key": "remove-resource",
          "label": "Remove",
          "method": "POST",
          "href": "/lessons/LES-A1B2C3/resources/RES-1/remove",
          "style": "danger",
          "confirm": "Remove this resource?"
        }
      ]
    }
  ],
  "empty_message": "No resources.",
  "pagination": null
}
```

**ColumnDef:**

| Field | Type | Description |
|-------|------|-------------|
| `key` | string | Maps to `data` key in ListItem |
| `label` | string | Column header |
| `display` | string | Display hint (default `plain`) |
| `currency` | string? | For currency display |
| `align` | enum | `left`, `right`, `center` |

**ListItem:**

| Field | Type | Description |
|-------|------|-------------|
| `href` | string? | If set, row is navigable (click to follow) |
| `data` | object | Key-value data matching column keys |
| `actions` | ActionSection[] | Inline row actions |

**Pagination:**

| Field | Type | Description |
|-------|------|-------------|
| `next` | NavLink? | Link to next page |
| `prev` | NavLink? | Link to previous page |
| `total` | int? | Total item count |
| `page` | int | Current page number |
| `per_page` | int | Items per page |

### `content` — Rich Text Block

Renders a block of text content.

```json
{
  "kind": "content",
  "title": "Instructions",
  "body": "Complete the worksheet on page 42.",
  "format": "plain"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `title` | string? | Optional heading |
| `body` | string | The content |
| `format` | enum | `plain`, `markdown`, `html` |

### `summary` — Metric Cards / KPI Row

Displays a row of summary metrics or KPI cards.

```json
{
  "kind": "summary",
  "items": [
    { "label": "Completed Today", "value": 3, "display": "number" },
    { "label": "Total Hours", "value": 4.5, "display": "number" },
    { "label": "Instruction Days", "value": 42, "display": "number", "href": "/reports/instruction-days" }
  ]
}
```

**SummaryItem:**

| Field | Type | Description |
|-------|------|-------------|
| `label` | string | Metric label |
| `value` | any | Metric value |
| `display` | string | Display hint (default `number`) |
| `currency` | string? | For currency display |
| `href` | string? | Makes the metric navigable |

### `timeline` — Event History

Displays a chronological list of events.

```json
{
  "kind": "timeline",
  "title": "History",
  "events": [
    { "timestamp": "2026-03-16T10:00:00Z", "label": "Lesson started", "actor": "teacher-1" },
    { "timestamp": "2026-03-16T11:30:00Z", "label": "Lesson completed", "actor": "student-1" }
  ]
}
```

**TimelineEvent:**

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string | ISO 8601 datetime |
| `label` | string | Event description |
| `actor` | string? | Who performed the action |

### `group` — Visual Grouping

Groups sub-sections with a layout. Can be nested recursively.

```json
{
  "kind": "group",
  "title": null,
  "layout": "sidebar",
  "sections": [
    { "kind": "group", "layout": "stack", "sections": [ ... ] },
    { "kind": "group", "layout": "stack", "sections": [ ... ] }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `title` | string? | Optional heading |
| `layout` | enum | `stack` (vertical), `sidebar` (main + aside), `columns` (equal width) |
| `sections` | Section[] | Nested sections |

### `empty` — Empty State with CTA

Shown when a collection has no items. Provides a call-to-action.

```json
{
  "kind": "empty",
  "title": "No Student Work Yet",
  "description": "Upload a photo to start building this lesson's portfolio.",
  "action": {
    "label": "Upload Photo",
    "href": "/lessons/LES-A1B2C3/portfolio",
    "method": "POST"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Empty state heading |
| `description` | string? | Explanatory text |
| `action` | ActionAlternative? | Suggested next action |

---

## Form Field Types

Fields appear inside `ActionSection.fields`. Each field has a `type`
discriminator and shares a common base of attributes.

### Common Field Attributes

All fields inherit these:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | string | — | Field name (used as form key) |
| `label` | string | — | Human-readable label |
| `type` | string | — | Discriminator (see types below) |
| `required` | bool | false | Whether the field must have a value |
| `value` | any | null | Current value (for edit forms) |
| `default` | any | null | Default value for new forms |
| `disabled` | bool | false | Field is visible but not editable |
| `readonly` | bool | false | Field is visible, value shown but not editable |
| `hidden` | bool | false | Field is not rendered but value is submitted |
| `placeholder` | string? | null | Placeholder text |
| `help` | string? | null | Help text shown below the field |
| `error` | string? | null | Validation error message |
| `depends_on` | DependsOn? | null | Field dependency (see below) |
| `span` | int? | null | Column span in grid layout |

### Field Types

| Type | Extra Fields | Use For |
|------|-------------|---------|
| `text` | `validation` | Short text input |
| `textarea` | `rows`, `validation` | Multi-line text |
| `number` | `validation` | Numeric input |
| `currency` | `currency`, `validation` | Money amounts |
| `boolean` | — | Checkbox / toggle |
| `select` | `options`, `options_href` | Dropdown selection |
| `multi_select` | `options`, `options_href` | Multiple selection |
| `radio` | `options` | Radio button group |
| `date` | `validation` | Date picker |
| `datetime` | `validation` | Date + time picker |
| `email` | `validation` | Email input |
| `url` | `validation` | URL input |
| `phone` | `validation` | Phone number input |
| `file` | `accept`, `max_size_mb` | File upload |
| `hidden` | — | Hidden form value |
| `group` | `layout`, `fields` | Fieldset (nested fields) |
| `repeatable` | `fields`, `items`, `min_items`, `max_items` | Dynamic list of field groups |

### ValidationRules

Fields that support `validation` accept:

| Field | Type | Description |
|-------|------|-------------|
| `min_length` | int? | Minimum string length |
| `max_length` | int? | Maximum string length |
| `min` | float? | Minimum numeric value |
| `max` | float? | Maximum numeric value |
| `step` | float? | Numeric step increment |
| `pattern` | string? | Regex pattern |
| `pattern_description` | string? | Human-readable regex explanation |

### FieldOption (for select, multi_select, radio)

```json
{ "value": "morning", "label": "Morning", "disabled": false, "description": null }
```

### Field Dependencies (DependsOn)

Fields can declare dependencies on other fields. When a dependency field changes,
the client fetches updated data from the server.

```json
{
  "fields": ["subject_id"],
  "behavior": "reload_options",
  "options_href": "/subjects/{subject_id}/time-slots",
  "clear_on_change": true
}
```

| Field | Type | Description |
|-------|------|-------------|
| `fields` | string[] | Field names this depends on |
| `behavior` | enum | `reload_options`, `reload_field`, `reload_form` |
| `options_href` | string? | URL to fetch new options (for `reload_options`) |
| `field_href` | string? | URL to fetch replacement field (for `reload_field`) |
| `clear_on_change` | bool | Clear current value when dependency changes |

**Behaviors:**
- `reload_options` — Fetch new options list from `options_href`
- `reload_field` — Fetch entire replacement field definition from `field_href`
- `reload_form` — Re-fetch the entire form from `ActionSection.reload_href`

### Dependency Response Types

**OptionsResponse** (for `reload_options`):
```json
{ "options": [{ "value": "a", "label": "A" }] }
```

**FieldResponse** (for `reload_field`):
```json
{ "field": { "type": "select", "name": "time_slot", "label": "Time Slot", "options": [...] } }
```

---

## Client Behavior Contract

1. **Render sections in order.** The server decides layout, not the client.
2. **Never evaluate business logic.** If an action has `condition.met = false`,
   disable it. Don't decide yourself whether it should be available.
3. **Follow discovered links.** Navigation, actions, and pagination are all
   server-provided URLs. Don't construct URLs.
4. **Show disabled actions with explanations.** When `condition.met = false`,
   render the button as disabled and show `condition.explain`.
5. **Handle flash once.** Display flash notifications from the response, then
   discard. Don't persist across navigations.
6. **Respect field dependencies.** When a `depends_on` field changes, fetch
   updated data and replace the dependent field/options/form.
7. **Submit forms to `action.href` using `action.method`.** Send field values
   as JSON body (or multipart for file uploads).
8. **Navigate `href` links with GET.** ListItem hrefs, NavLink hrefs, and
   PropertyItem hrefs are all navigated with GET.

## Content Negotiation

- Requests with `Accept: application/vnd.hyperstate+json` receive JSON responses.
- Requests with `Accept: text/html` receive the SPA client HTML, which then
  fetches the JSON for the current URL.
- The middleware sets `Content-Type: application/vnd.hyperstate+json; charset=utf-8`
  on all API responses.
