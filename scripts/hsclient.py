#!/usr/bin/env python3
"""
hsclient — CLI test client for HyperState applications.

Interactive REPL that speaks the HyperState protocol. Navigate links,
submit forms, record stories, replay them, and crawl for broken links.

Usage:
    hsclient.py [--base-url URL]                    # Interactive REPL
    hsclient.py --record <name> [--base-url URL]    # Record a story
    hsclient.py --replay <file> [--until <step>]    # Replay a story
    hsclient.py --crawl [--base-url URL]            # Crawl & validate
"""

from __future__ import annotations

import argparse
import json
import re
import readline  # noqa: F401 — enables line editing in input()
import sys
import textwrap
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

HYPERSTATE_ACCEPT = "application/vnd.hyperstate+json"
HEADERS = {"Accept": HYPERSTATE_ACCEPT}
DEFAULT_BASE = "http://localhost:8000"


# ── Data structures ────────────────────────────────────────────────

@dataclass
class Step:
    """One recorded interaction."""
    method: str = "GET"
    url: str = ""
    body: dict[str, Any] | None = None
    status_code: int = 200
    response_title: str | None = None
    assertions: list[dict[str, Any]] | None = None
    action: str | None = None       # action key to look up in current response
    item: int | None = None         # list item index for item-level actions
    click: int | None = None        # click list item N to navigate to its href

    def to_dict(self) -> dict:
        d: dict[str, Any] = {}
        if self.click is not None:
            d["click"] = self.click
        elif self.action:
            d["action"] = self.action
            if self.item is not None:
                d["item"] = self.item
            if self.body:
                d["body"] = self.body
        else:
            d["method"] = self.method
            d["url"] = self.url
            d["body"] = self.body
            d["status_code"] = self.status_code
        d["response_title"] = self.response_title
        if self.assertions is not None:
            d["assertions"] = self.assertions
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Step:
        return cls(
            method=d.get("method", "GET"),
            url=d.get("url", ""),
            body=d.get("body"),
            status_code=d.get("status_code", 200),
            response_title=d.get("response_title"),
            assertions=d.get("assertions"),
            action=d.get("action"),
            item=d.get("item"),
            click=d.get("click"),
        )


@dataclass
class Story:
    name: str
    base_url: str
    steps: list[Step] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "base_url": self.base_url,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Story:
        return cls(
            name=d["name"],
            base_url=d["base_url"],
            steps=[Step.from_dict(s) for s in d["steps"]],
            created_at=d.get("created_at", ""),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n")

    @classmethod
    def load(cls, path: Path) -> Story:
        return cls.from_dict(json.loads(path.read_text()))


# ── Display helpers ─────────────────────────────────────────────────

def _dim(text: str) -> str:
    return f"\033[2m{text}\033[0m"

def _bold(text: str) -> str:
    return f"\033[1m{text}\033[0m"

def _green(text: str) -> str:
    return f"\033[32m{text}\033[0m"

def _red(text: str) -> str:
    return f"\033[31m{text}\033[0m"

def _yellow(text: str) -> str:
    return f"\033[33m{text}\033[0m"

def _cyan(text: str) -> str:
    return f"\033[36m{text}\033[0m"


def format_value(value: Any, item: dict) -> str:
    """Format a value using its display hint."""
    display = item.get("display", "plain")
    if value is None:
        return _dim("—")
    if display == "badge":
        variant = item.get("variant", "")
        color = {"success": _green, "warning": _yellow, "danger": _red}.get(variant, str)
        return color(f"[{value}]")
    if display == "currency":
        currency = item.get("currency", "USD")
        return f"{currency} {value}"
    if display in ("datetime", "date"):
        return str(value)
    if display == "percentage":
        return f"{float(value) * 100:.1f}%"
    return str(value)


def print_flash(flash: dict) -> None:
    ftype = flash.get("type", "info")
    color = {"success": _green, "error": _red, "warning": _yellow}.get(ftype, _cyan)
    title = flash.get("title", "")
    body = flash.get("body", "")
    print(color(f"  ▸ {title}"))
    if body:
        print(f"    {body}")
    print()


def print_nav(nav: list[dict], start_index: int = 0) -> list[dict]:
    """Print nav links and return them for selection. Returns the nav list."""
    if not nav:
        return []
    print(_bold("  Navigation:"))
    for i, link in enumerate(nav):
        rel = f" ({link['rel']})" if link.get("rel") else ""
        if link.get("rel") == "download":
            print(f"    [{start_index + i}] ⬇ {link['label']}{_dim(rel)}  →  {_dim(link['href'])}")
        else:
            print(f"    [{start_index + i}] ← {link['label']}{_dim(rel)}  →  {_dim(link['href'])}")
    return nav


def print_properties(section: dict) -> None:
    title = section.get("title")
    if title:
        print(_bold(f"  {title}"))
    for item in section.get("data", []):
        label = item.get("label", item.get("key", ""))
        value = format_value(item.get("value"), item)
        print(f"    {label}: {value}")
    print()


def print_list_section(section: dict, actions_list: list[dict]) -> list[dict]:
    """Print a list/table section. Returns clickable items."""
    title = section.get("title")
    if title:
        print(_bold(f"  {title}"))

    columns = section.get("columns", [])
    items = section.get("items", [])
    clickable = []

    if not items:
        print(f"    {_dim(section.get('empty_message', 'No items.'))}")
        print()
        return clickable

    # Print header
    clickable_headers = []
    base_idx = len(actions_list)
    
    col_parts = []
    for col in columns:
        label = col.get("label", col.get("key", ""))
        if col.get("href"):
            idx = base_idx + len(clickable_headers)
            clickable_headers.append({"label": f"Sort by {label}", "href": col["href"], "_type": "sort_header"})
            col_parts.append(f"[{idx}] {label}")
        else:
            col_parts.append(label)
            
    header = "    " + "  │  ".join(f"{lbl:<16}" for lbl in col_parts)
    print(_dim(header))
    print(_dim("    " + "─" * len(header.strip())))

    base = base_idx + len(clickable_headers)
    for idx, item in enumerate(items):
        data = item.get("data", {})
        cells = []
        for col in columns:
            key = col.get("key", "")
            raw = data.get(key, "")
            cells.append(format_value(raw, col))

        prefix = f"    [{base + idx}]" if item.get("href") else "       "
        row = "  │  ".join(f"{c:<16}" for c in cells)
        print(f"{prefix} {row}")

        if item.get("href"):
            clickable.append({"label": str(data), "href": item["href"], "_type": "list_item"})

        # Inline row actions
        for act in item.get("actions", []):
            actions_list.append(act)

    clickable = clickable_headers + clickable

    pag = section.get("pagination")
    if pag:
        parts = []
        if pag.get("prev"):
            parts.append(f"prev: {pag['prev']['href']}")
        if pag.get("next"):
            parts.append(f"next: {pag['next']['href']}")
        if pag.get("total") is not None:
            parts.append(f"total: {pag['total']}")
        if parts:
            print(f"    {_dim(' | '.join(parts))}")
    print()
    return clickable


def print_action(section: dict, index: int) -> None:
    """Print an action (button or form summary)."""
    label = section.get("label", "Action")
    style = section.get("style", "default")
    method = section.get("method", "POST")
    href = section.get("href", "")
    fields = section.get("fields", [])
    condition = section.get("condition")

    color = {"primary": _cyan, "danger": _red}.get(style, str)

    if condition and not condition.get("met", True):
        explain = condition.get("explain", "Unavailable")
        alt = condition.get("alternative")
        print(f"    [{index}] {_dim(label)} — {_dim(explain)}")
        if alt:
            print(f"         → {alt['label']} ({alt.get('href', '')})")
        return

    if fields:
        field_names = [f.get("name", "?") for f in fields if not f.get("hidden")]
        print(f"    [{index}] {color(label)} {_dim(f'{method} {href}')}")
        print(f"         fields: {', '.join(field_names)}")
    else:
        confirm = section.get("confirm")
        confirm_note = _yellow(f" (confirm: {confirm})") if confirm else ""
        print(f"    [{index}] {color(label)} {_dim(f'{method} {href}')}{confirm_note}")


def print_content(section: dict) -> None:
    title = section.get("title")
    if title:
        print(_bold(f"  {title}"))
    body = section.get("body", "")
    for line in body.split("\n"):
        print(f"    {line}")
    print()


def print_summary(section: dict) -> None:
    items = section.get("items", [])
    parts = []
    for item in items:
        label = item.get("label", "")
        value = format_value(item.get("value"), item)
        parts.append(f"{label}: {value}")
    print(f"    {_dim(' │ '.join(parts))}")
    print()


def print_timeline(section: dict) -> None:
    title = section.get("title")
    if title:
        print(_bold(f"  {title}"))
    for ev in section.get("events", []):
        ts = ev.get("timestamp", "")[:19]
        label = ev.get("label", "")
        actor = f" ({ev['actor']})" if ev.get("actor") else ""
        print(f"    {_dim(ts)}  {label}{actor}")
    print()


def print_empty(section: dict) -> None:
    title = section.get("title", "Empty")
    desc = section.get("description", "")
    print(f"    {title}")
    if desc:
        print(f"    {_dim(desc)}")
    action = section.get("action")
    if action:
        print(f"    → {action.get('label', 'Go')} ({action.get('href', '')})")
    print()


# ── Section renderer (dispatch) ────────────────────────────────────

def render_sections(
    sections: list[dict],
    actions: list[dict],
    clickable_items: list[dict],
) -> None:
    """Render sections, collecting actions and clickable items as side effects."""
    for section in sections:
        kind = section.get("kind", "")
        if kind == "properties":
            print_properties(section)
        elif kind == "action":
            idx = len(actions)
            actions.append(section)
            print_action(section, idx)
        elif kind == "list":
            new_clickable = print_list_section(section, actions)
            clickable_items.extend(new_clickable)
        elif kind == "content":
            print_content(section)
        elif kind == "summary":
            print_summary(section)
        elif kind == "timeline":
            print_timeline(section)
        elif kind == "empty":
            print_empty(section)
        elif kind == "group":
            gtitle = section.get("title")
            if gtitle:
                print(_bold(f"  ┌ {gtitle}"))
            render_sections(section.get("sections", []), actions, clickable_items)
            if gtitle:
                print(_dim(f"  └─"))
        else:
            print(f"    {_dim(f'[unknown section: {kind}]')}")


# ── Form filling ───────────────────────────────────────────────────

def fill_form(fields: list[dict], existing: dict[str, Any] | None = None, hs_client: 'HSClient' | None = None) -> dict[str, Any]:
    """Interactively fill form fields. Returns nested dict for submission."""
    values: dict[str, Any] = {}
    print()
    for f in fields:
        if f.get("hidden"):
            _set_nested(values, f["name"], f.get("value", f.get("default")))
            continue

        ftype = f.get("type", "text")
        name = f.get("name", "?")
        label = f.get("label", name)
        required = f.get("required", False)
        current = f.get("value") or f.get("default")
        req_mark = " *" if required else ""
        help_text = f.get("help", "")

        if ftype == "group":
            print(_bold(f"    ── {label} ──"))
            sub = fill_form(f.get("fields", []), existing, hs_client)
            values.update(sub)
            continue

        if ftype == "select" or ftype == "radio":
            options = f.get("options", [])
            
            # Auto-fetch options if they are empty, not dependent on other fields, and we have an hs_client
            if not options and f.get("options_href") and not f.get("depends_on") and hs_client:
                href_val = f.get("options_href")
                print(f"    {_dim(f'Fetching options from {href_val}...')}")
                # Use a silent GET that doesn't affect the current state or story
                try:
                    res = hs_client.client.get(hs_client.resolve_url(href_val), headers={"Accept": "application/json"})
                    if res.status_code < 400:
                        data = res.json()
                        if "options" in data:
                            options = data["options"]
                except Exception as e:
                    print(f"      {_dim(f'Failed to fetch options: {e}')}")

            print(f"    {label}{req_mark}:")
            for oi, opt in enumerate(options):
                marker = "●" if opt["value"] == str(current) else "○"
                desc = f" — {opt['description']}" if opt.get("description") else ""
                print(f"      {oi}. {marker} {opt['label']}{desc}")
            if help_text:
                print(f"      {_dim(help_text)}")
            raw = input(f"      choice [{current or ''}]: ").strip()
            if raw == "" and current is not None:
                _set_nested(values, name, current)
            elif raw.isdigit() and 0 <= int(raw) < len(options):
                _set_nested(values, name, options[int(raw)]["value"])
            elif raw:
                _set_nested(values, name, raw)
            continue

        if ftype == "boolean":
            raw = input(f"    {label}{req_mark} (y/n) [{_yn(current)}]: ").strip().lower()
            if raw in ("y", "yes", "true", "1"):
                _set_nested(values, name, True)
            elif raw in ("n", "no", "false", "0"):
                _set_nested(values, name, False)
            elif current is not None:
                _set_nested(values, name, current)
            continue

        if ftype == "textarea":
            print(f"    {label}{req_mark} (multi-line, empty line to end):")
            if current:
                print(f"      {_dim(f'current: {current}')}")
            lines = []
            while True:
                line = input("      ")
                if line == "":
                    break
                lines.append(line)
            if lines:
                _set_nested(values, name, "\n".join(lines))
            elif current is not None:
                _set_nested(values, name, current)
            continue

        if ftype == "file":
            print(f"    {label}{req_mark} (file path):")
            if current:
                print(f"      {_dim(f'current: {current}')}")
            raw = input(f"      path: ").strip()
            if raw:
                _set_nested(values, name, {"__file__": raw})
            elif current is not None:
                _set_nested(values, name, current)
            continue

        # Default: text-like input
        placeholder = f.get("placeholder", "")
        default_display = current if current is not None else placeholder
        if help_text:
            print(f"      {_dim(help_text)}")
        raw = input(f"    {label}{req_mark} [{default_display}]: ").strip()
        if raw:
            if ftype == "number" or ftype == "currency":
                try:
                    _set_nested(values, name, float(raw))
                except ValueError:
                    _set_nested(values, name, raw)
            else:
                _set_nested(values, name, raw)
        elif current is not None:
            _set_nested(values, name, current)

    return values


def _set_nested(target: dict, dotted_key: str, value: Any) -> None:
    """Set a value in a nested dict using dot-notation key."""
    parts = dotted_key.split(".")
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    target[parts[-1]] = value


def _yn(val: Any) -> str:
    if val is True:
        return "y"
    if val is False:
        return "n"
    return ""


# ── HTTP client ─────────────────────────────────────────────────────

class HSClient:
    """HyperState HTTP client with optional story recording."""

    def __init__(self, base_url: str, story: Story | None = None):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(base_url=self.base_url, timeout=30.0)
        self.story = story
        self.current: dict | None = None  # last response data
        self.last_status: int | None = None  # last HTTP status code

    def close(self) -> None:
        self.client.close()

    def resolve_url(self, href: str) -> str:
        """Turn a path into a full URL (or leave it if already absolute)."""
        if href.startswith("http"):
            return href
        return href  # httpx handles base_url + relative path

    def fetch(self, href: str, method: str = "GET", body: dict | None = None) -> dict | None:
        """Make a request, record if story mode, return parsed JSON."""
        url = self.resolve_url(href)

        # Check for files or form data
        files = None
        data = None
        is_form = False

        if body:
            if method.upper() == "GET":
                import urllib.parse
                parsed = urllib.parse.urlparse(url)
                query = urllib.parse.parse_qsl(parsed.query)
                for k, v in body.items():
                    if v is not None and v != "":
                        if isinstance(v, list):
                            for item in v:
                                query.append((k, str(item)))
                        else:
                            query.append((k, str(v)))
                new_query = urllib.parse.urlencode(query)
                url = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
                body = None  # Clear body so it doesn't get recorded/re-appended
            else:
                files = []
                data = []
                # Check if any field is a file
                for k, v in body.items():
                    if isinstance(v, dict) and "__file__" in v:
                        is_form = True

                # For specific endpoints like portfolio that require Form data even without a file
                if "portfolio" in url:
                    is_form = True

                if is_form:
                    for k, v in body.items():
                        if isinstance(v, dict) and "__file__" in v:
                            try:
                                import mimetypes
                                path = v["__file__"]
                                mime_type, _ = mimetypes.guess_type(path)
                                mime_type = mime_type or "application/octet-stream"
                                filename = path.split("/")[-1]
                                files.append((k, (filename, open(path, "rb"), mime_type)))
                            except Exception as e:
                                print(f"Error reading file {path}: {e}")
                        elif isinstance(v, list):
                            for item in v:
                                data.append((k, str(item)))
                        else:
                            data.append((k, str(v) if v is not None else ""))
                    if not files:
                        files = None
                    # data is always set if is_form is True
                else:
                    files = None
                    data = None

        def list_to_dict(pairs: list[tuple[str, str]]) -> dict[str, Any]:
            res = {}
            for k, v in pairs:
                if k in res:
                    if isinstance(res[k], list):
                        res[k].append(v)
                    else:
                        res[k] = [res[k], v]
                else:
                    res[k] = v
            return res

        try:
            if method.upper() == "GET":
                resp = self.client.get(url, headers=HEADERS)
            else:
                if files or data is not None:
                    # Remove Content-Type to let httpx determine it
                    req_headers = {k: v for k, v in HEADERS.items() if k.lower() != "content-type"}
                    if files:
                        dict_data = list_to_dict(data)
                        resp = self.client.request(
                            method.upper(), url, headers=req_headers, data=dict_data, files=files,
                        )
                    else:
                        dict_data = list_to_dict(data)
                        resp = self.client.request(
                            method.upper(), url, headers=req_headers, data=dict_data,
                        )
                else:
                    resp = self.client.request(
                        method.upper(), url, headers=HEADERS, json=body,
                    )
            self.last_status = resp.status_code
        except httpx.ConnectError:
            print(_red(f"  Connection refused: {self.base_url}{url}"), file=sys.stderr)
            self.last_status = None
            return None
        except httpx.RequestError as e:
            print(_red(f"  Request error: {e}"), file=sys.stderr)
            self.last_status = None
            return None

        try:
            data = resp.json()
        except Exception:
            if resp.status_code < 400 and resp.headers.get("Content-Type") in ("application/pdf", "text/csv"):
                # Handle file downloads gracefully during tests
                filename = url.split("/")[-1]
                content_disp = resp.headers.get("Content-Disposition", "")
                if "filename=" in content_disp:
                    filename = content_disp.split("filename=")[-1].strip('"').strip("'")

                data = {
                    "title": "File Download",
                    "_download": True,
                    "filename": filename,
                    "content_type": resp.headers.get("Content-Type"),
                    "size": len(resp.content)
                }
            else:
                print(_red(f"  Non-JSON response ({resp.status_code}): {resp.text[:200]}"), file=sys.stderr)
                return None

        # Record step
        if self.story is not None:
            self.story.steps.append(Step(
                method=method.upper(),
                url=url,
                body=body,
                status_code=resp.status_code,
                response_title=data.get("title"),
            ))

        if resp.status_code >= 400:
            print(_red(f"  HTTP {resp.status_code}"), file=sys.stderr)

        self.current = data
        return data

    def navigate(self, href: str) -> dict | None:
        return self.fetch(href, "GET")

    def submit(self, action: dict, body: dict | None = None) -> dict | None:
        method = action.get("method", "POST")
        href = action.get("href", "")
        confirm = action.get("confirm")
        if confirm:
            answer = input(f"  {_yellow(f'Confirm: {confirm}')} (y/n): ").strip().lower()
            if answer not in ("y", "yes"):
                print("  Cancelled.")
                return self.current
        return self.fetch(href, method, body)


# ── REPL ────────────────────────────────────────────────────────────

def render_response(data: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """Render a full HyperState response. Returns (nav, actions, clickable_items)."""
    print()

    # Context breadcrumb
    ctx = data.get("context")
    if ctx:
        parts = [ctx.get("domain", ""), ctx.get("aggregate", ""), ctx.get("state", "")]
        crumb = " › ".join(p for p in parts if p)
        print(_dim(f"  {crumb}"))

    # Title
    title = data.get("title", "(untitled)")
    view = data.get("view", "")
    print(_bold(f"  {title}") + _dim(f"  [{view}]"))
    print(_dim(f"  self: {data.get('self', '?')}"))
    print()

    # Flash
    flash = data.get("flash")
    if flash:
        print_flash(flash)

    # Collect interactive elements
    actions: list[dict] = []
    clickable_items: list[dict] = []

    # Nav links (printed first, but numbered from 0)
    nav = data.get("nav", [])

    # Sections
    render_sections(data.get("sections", []), actions, clickable_items)

    # Print nav at bottom so numbered actions are visible first
    if nav:
        print()
        print_nav(nav, start_index=len(actions) + len(clickable_items))

    return nav, actions, clickable_items


def interactive_loop(hs: HSClient, start_href: str = "/") -> None:
    """Main REPL loop."""
    data = hs.navigate(start_href)
    if not data:
        print(_red("Failed to fetch initial page."))
        return

    while True:
        nav, actions, clickable = render_response(data)

        # Build selection map: actions first, then clickable items, then nav
        selectable: list[dict] = []
        for a in actions:
            selectable.append({"_kind": "action", **a})
        for c in clickable:
            selectable.append({"_kind": "clickable", **c})
        for n in nav:
            selectable.append({"_kind": "nav", **n})

        print()
        try:
            raw = input(_dim("  > ")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not raw:
            continue

        # Commands
        if raw in ("q", "quit", "exit"):
            break
        if raw in ("?", "help"):
            print_help()
            continue
        if raw == "json":
            print(json.dumps(hs.current, indent=2))
            continue
        if raw == "reload" or raw == "r":
            href = data.get("self", start_href)
            data = hs.navigate(href)
            if not data:
                break
            continue
        if raw.startswith("go "):
            href = raw[3:].strip()
            result = hs.navigate(href)
            if result:
                data = result
            continue
        if raw == "back" or raw == "b":
            # Navigate to first nav link with rel="collection"
            for n in nav:
                if n.get("rel") == "collection":
                    result = hs.navigate(n["href"])
                    if result:
                        data = result
                    break
            else:
                print(_dim("  No 'collection' link to go back to."))
            continue
        if raw == "story":
            if hs.story:
                print(f"  Recording: {hs.story.name} ({len(hs.story.steps)} steps)")
            else:
                print(_dim("  Not recording."))
            continue
        if raw == "save":
            if hs.story:
                path = _story_path(hs.story.name)
                hs.story.save(path)
                print(_green(f"  Saved: {path}"))
            else:
                print(_dim("  Not recording — nothing to save."))
            continue

        # Inspect field
        if raw.startswith("inspect ") or raw.startswith("? "):
            prefix_len = 8 if raw.startswith("inspect ") else 2
            field_name = raw[prefix_len:].strip()
            
            found = False
            for action in actions:
                fields = action.get("fields", [])
                for f in fields:
                    if f.get("name") == field_name:
                        print(_bold(f"  Field: {field_name}"))
                        print(f"    type: {f.get('type')}")
                        print(f"    label: {f.get('label')}")
                        print(f"    required: {f.get('required', False)}")
                        
                        if 'default' in f:
                            print(f"    default: {f.get('default')}")
                        if 'value' in f:
                            print(f"    value: {f.get('value')}")
                        if 'help' in f:
                            print(f"    help: {f.get('help')}")
                        if 'placeholder' in f:
                            print(f"    placeholder: {f.get('placeholder')}")
                            
                        # Specific attributes
                        if 'options' in f:
                            options = f.get('options', [])
                            print(f"    options: {len(options)} items")
                            for opt in options:
                                print(f"      - {opt.get('value')}: {opt.get('label')}")
                        if 'options_href' in f:
                            print(f"    options_href: {f.get('options_href')}")
                        if 'depends_on' in f:
                            depends_on = f.get('depends_on')
                            print(f"    depends_on: {depends_on.get('field')} -> {depends_on.get('href')}")
                            
                        found = True
                        break
                if found:
                    break
                    
            if not found:
                print(_red(f"  Field '{field_name}' not found in any visible action."))
            continue

        # Number selection
        if raw.isdigit():
            idx = int(raw)
            if 0 <= idx < len(selectable):
                item = selectable[idx]
                kind = item.get("_kind")

                if kind == "nav" or kind == "clickable":
                    if kind == "nav" and item.get("rel") == "download":
                        href = item["href"]
                        print(f"  {_dim(f'Downloading {href}...')}")
                        url = hs.resolve_url(href)
                        try:
                            # Use httpx.get with stream to save memory, or just normal get
                            resp = hs.client.get(url)
                            if resp.status_code < 400:
                                filename = href.split("/")[-1]
                                content_disp = resp.headers.get("Content-Disposition", "")
                                if "filename=" in content_disp:
                                    filename = content_disp.split("filename=")[-1].strip('"').strip("'")

                                path = Path(filename)
                                path.write_bytes(resp.content)
                                print(_green(f"  Downloaded {len(resp.content)} bytes to {path}"))
                            else:
                                print(_red(f"  Download failed with HTTP {resp.status_code}"))
                        except Exception as e:
                            print(_red(f"  Download error: {e}"))
                    else:
                        result = hs.navigate(item["href"])
                        if result:
                            data = result
                elif kind == "action":
                    fields = item.get("fields", [])
                    condition = item.get("condition")
                    if condition and not condition.get("met", True):
                        alt = condition.get("alternative")
                        if alt:
                            result = hs.navigate(alt.get("href", ""))
                            if result:
                                data = result
                        else:
                            print(_dim(f"  Action unavailable: {condition.get('explain', '')}"))
                        continue

                    if fields:
                        body = fill_form(fields, hs_client=hs)
                        result = hs.submit(item, body)
                    else:
                        result = hs.submit(item)
                    if result:
                        data = result
            else:
                print(_dim(f"  Invalid index. Range: 0–{len(selectable) - 1}"))
            continue

        print(_dim(f"  Unknown command: {raw}. Type ? for help."))


def print_help() -> None:
    print(textwrap.dedent("""
    Commands:
      <number>    Select a nav link, action, or list item
      go <href>   Navigate to an arbitrary URL path
      r, reload   Reload current page
      b, back     Navigate to 'collection' nav link
      json        Dump raw JSON response
      story       Show recording status
      save        Save current story to disk
      inspect <f> Inspect form field metadata (also ? <f>)
      q, quit     Exit
      ?, help     Show this help
    """))


# ── Story replay ────────────────────────────────────────────────────

def _get_nested_val(data: dict, path: str) -> Any:
    parts = path.split('.')
    curr = data
    for p in parts:
        if isinstance(curr, dict) and p in curr:
            curr = curr[p]
        elif isinstance(curr, list) and p.isdigit() and int(p) < len(curr):
            curr = curr[int(p)]
        else:
            return None
    return curr

def _find_section(sections: list[dict], key: str) -> dict | None:
    for s in sections:
        if s.get("key") == key:
            return s
        if "sections" in s:
            found = _find_section(s["sections"], key)
            if found:
                return found
    return None

def _find_field(sections: list[dict], name: str) -> dict | None:
    for s in sections:
        if s.get("kind") == "action":
            for f in s.get("fields", []):
                if f.get("name") == name:
                    return f
        if "sections" in s:
            found = _find_field(s["sections"], name)
            if found:
                return found
    return None

def evaluate_assertion(assertion: dict, data: dict) -> tuple[bool, str]:
    type_ = assertion.get("type")
    
    if type_ == "value_equals":
        path = assertion.get("path", "")
        expected = assertion.get("value")
        actual = _get_nested_val(data, path)
        if actual != expected:
            return False, f"expected '{path}' to be {expected!r}, got {actual!r}"
        return True, ""
        
    elif type_ == "section_exists":
        key = assertion.get("key", "")
        section = _find_section(data.get("sections", []), key)
        if not section:
            return False, f"section with key '{key}' not found"
        return True, ""
        
    elif type_ == "field_options_count":
        name = assertion.get("field", "")
        op = assertion.get("op", "==")
        value = assertion.get("value", 0)
        
        field = _find_field(data.get("sections", []), name)
        if not field:
            return False, f"field '{name}' not found"
            
        options = field.get("options", [])
        count = len(options)
        
        import operator
        ops = {
            "==": operator.eq,
            "!=": operator.ne,
            ">": operator.gt,
            "<": operator.lt,
            ">=": operator.ge,
            "<=": operator.le,
        }
        
        op_fn = ops.get(op)
        if not op_fn:
            return False, f"unknown operator '{op}'"
            
        if not op_fn(count, value):
            return False, f"expected field '{name}' options count {op} {value}, got {count}"
            
        return True, ""
        
    return False, f"unknown assertion type '{type_}'"

def _resolve_path(data: Any, path: str) -> Any:
    """Resolve a dot-path like 'sections.1.items.0.data.id' from response data."""
    current = data
    for part in path.split("."):
        if isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None
        if current is None:
            return None
    return current


def _substitute_refs(value: Any, data: dict) -> Any:
    """Replace {response:dot.path} placeholders in strings (recursively in dicts/lists)."""
    if isinstance(value, str):
        return re.sub(
            r"\{response:([^}]+)\}",
            lambda m: str(resolved) if (resolved := _resolve_path(data, m.group(1))) is not None else m.group(0),
            value,
        )
    if isinstance(value, dict):
        return {k: _substitute_refs(v, data) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute_refs(v, data) for v in value]
    return value


def _find_action_recursive(sections: list[dict], key: str) -> dict | None:
    """Recursively search sections for a top-level action by key."""
    for section in sections:
        if section.get("kind") == "action" and section.get("key") == key:
            return section
        if section.get("kind") == "group":
            result = _find_action_recursive(section.get("sections", []), key)
            if result:
                return result
    return None


def _find_action_in_response(data: dict, key: str, item_index: int | None = None) -> dict | None:
    """Find an action by key in the response. For item actions, search list items."""
    sections = data.get("sections", [])

    if item_index is not None:
        # Search in list item actions (check all list sections, including inside groups)
        def search_lists(secs: list[dict]) -> dict | None:
            for sec in secs:
                if sec.get("kind") == "list":
                    items = sec.get("items", [])
                    if 0 <= item_index < len(items):
                        for action in items[item_index].get("actions", []):
                            if action.get("key") == key:
                                return action
                elif sec.get("kind") == "group":
                    result = search_lists(sec.get("sections", []))
                    if result:
                        return result
            return None
        return search_lists(sections)

    return _find_action_recursive(sections, key)


def replay_story(path: Path, until: int | None = None, base_url_override: str | None = None) -> bool:
    """Replay a saved story. Returns True if all steps pass."""
    story = Story.load(path)
    base = base_url_override or story.base_url
    hs = HSClient(base)
    total = len(story.steps)
    stop_at = until if until is not None else total

    print(_bold(f"  Replaying: {story.name} ({total} steps, stopping at {stop_at})"))
    print(_dim(f"  Base URL: {base}"))
    print()

    ok = True
    data: dict | None = None
    last_step = 0
    for i, step in enumerate(story.steps[:stop_at]):
        method = step.method
        url = step.url
        body = step.body

        # Click step: navigate to a list item's href
        if step.click is not None:
            if data is None:
                print(_red(f"FAIL: click requires a previous response."))
                ok = False
                last_step = i
                break

            click_idx = step.click
            # Find the item in list sections (including inside groups)
            def find_list_item(secs, idx):
                for sec in secs:
                    if sec.get("kind") == "list":
                        items = sec.get("items", [])
                        if 0 <= idx < len(items):
                            return items[idx]
                    elif sec.get("kind") == "group":
                        result = find_list_item(sec.get("sections", []), idx)
                        if result:
                            return result
                return None

            clicked = find_list_item(data.get("sections", []), click_idx)
            if not clicked or not clicked.get("href"):
                print(_red(f"FAIL: list item {click_idx} has no href to navigate to."))
                ok = False
                last_step = i
                break

            method = "GET"
            url = clicked["href"]
            body = None
            label = f"  [{i + 1}/{stop_at}] click item {click_idx} → GET {url}"

        # Action-based step: look up action in current response
        elif step.action:
            if data is None:
                print(_red(f"FAIL: action '{step.action}' requires a previous response."))
                ok = False
                last_step = i
                break

            item_label = f" (item {step.item})" if step.item is not None else ""
            found = _find_action_in_response(data, step.action, step.item)
            if not found:
                print(_red(f"FAIL: action '{step.action}'{item_label} not found on current page."))
                ok = False
                last_step = i
                break

            method = found.get("method", "POST")
            url = found["href"]
            label = f"  [{i + 1}/{stop_at}] {step.action}{item_label} → {method} {url}"

        else:
            # URL-based step (GET navigation only)
            if "{self}" in url and data is not None and "self" in data:
                url = url.replace("{self}", data["self"])
            if url.startswith("nav:") and data is not None:
                rel = url[4:]
                nav = data.get("nav", [])
                for link in nav:
                    if link.get("rel") == rel:
                        url = link["href"]
                        break
                else:
                    print(_red(f"FAIL: nav link '{rel}' not found on current page."))
                    ok = False
                    last_step = i
                    break

            if data is not None:
                url = _substitute_refs(url, data)
            label = f"  [{i + 1}/{stop_at}] {method} {url}"

        body = _substitute_refs(body, data) if data and body else body
        data = hs.fetch(url, method, body)

        if data is None:
            print(f"{_red('FAIL')} {label}")
            print(_red(f"       No response (connection error)"))
            ok = False
            last_step = i
            break

        actual_title = data.get("title", "")
        if step.response_title and actual_title != step.response_title:
            print(f"{_yellow('DRIFT')} {label}")
            print(f"       expected title: {_dim(step.response_title)}")
            print(f"       actual title:   {actual_title}")
        else:
            print(f"{_green('OK')}   {label} → {actual_title}")

        if step.assertions:
            assertions_failed = False
            for i_assert, assertion in enumerate(step.assertions):
                passed, err_msg = evaluate_assertion(assertion, data)
                if not passed:
                    if not assertions_failed:
                        print(f"{_red('FAIL')} {label} (Assertion failed)")
                        assertions_failed = True
                    print(_red(f"       Assertion {i_assert + 1} failed: {err_msg}"))
                    print(_dim(f"       {assertion}"))

            if assertions_failed:
                ok = False
                last_step = i
                break

    print()
    if ok:
        print(_green(f"  Replay complete. {stop_at} steps passed."))
        if until is not None and until < total:
            print(_dim(f"  Stopped at step {until}/{total}. Remaining steps not replayed."))
    else:
        print(_red(f"  Replay failed at step {last_step + 1}."))

    # If replay succeeded and we stopped early, offer interactive continuation
    if ok and hs.current:
        print()
        answer = input("  Continue interactively from here? (y/n): ").strip().lower()
        if answer in ("y", "yes"):
            # Start a new recording that extends the story
            new_story = Story(
                name=f"{story.name}_continued",
                base_url=base,
                steps=list(story.steps[:stop_at]),
                created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
            )
            hs.story = new_story
            # Re-render current page and enter REPL
            interactive_loop(hs, data.get("self", "/") if data else "/")

    hs.close()
    return ok


# ── Crawl mode ──────────────────────────────────────────────────────

@dataclass
class CrawlResult:
    visited: set[str] = field(default_factory=set)
    broken_links: list[dict] = field(default_factory=list)
    form_errors: list[dict] = field(default_factory=list)
    protocol_errors: list[dict] = field(default_factory=list)


def crawl(base_url: str, start: str = "/students") -> CrawlResult:
    """Crawl the app following all nav links. Report issues."""
    hs = HSClient(base_url)
    result = CrawlResult()
    queue = [start]

    print(_bold(f"  Crawling {base_url} starting at {start}"))
    print()

    while queue:
        href = queue.pop(0)
        if href in result.visited:
            continue
        result.visited.add(href)

        data = hs.fetch(href, "GET")
        if data is None:
            result.broken_links.append({"href": href, "source": "crawl", "error": "no response"})
            print(f"  {_red('BROKEN')} {href} — no response")
            continue

        # Validate protocol shape
        if data.get("$type") != "application/vnd.hyperstate+json":
            result.protocol_errors.append({"href": href, "error": "missing $type"})
            print(f"  {_yellow('PROTO')}  {href} — missing $type")

        view = data.get("view")
        if view not in ("detail", "list", "form", "dashboard", "error"):
            result.protocol_errors.append({"href": href, "error": f"invalid view: {view}"})

        title = data.get("title", "(no title)")
        print(f"  {_green('OK')}     {href} → {title} [{view}]")

        # Queue nav links
        for nav_link in data.get("nav", []):
            nav_href = nav_link.get("href", "")
            if nav_href and nav_href not in result.visited and not nav_href.startswith("http"):
                queue.append(nav_href)

        # Queue list item links
        for section in data.get("sections", []):
            _crawl_section(section, href, queue, result, hs)

    print()
    print(_bold("  Crawl Summary"))
    print(f"    Pages visited:    {len(result.visited)}")
    print(f"    Broken links:     {len(result.broken_links)}")
    print(f"    Form errors:      {len(result.form_errors)}")
    print(f"    Protocol errors:  {len(result.protocol_errors)}")

    if result.broken_links:
        print()
        print(_red("  Broken Links:"))
        for bl in result.broken_links:
            print(f"    {bl['href']} — {bl.get('error', '?')} (from {bl.get('source', '?')})")

    if result.form_errors:
        print()
        print(_red("  Form Errors:"))
        for fe in result.form_errors:
            print(f"    {fe['action']} {fe['href']} — {fe.get('error', '?')}")

    if result.protocol_errors:
        print()
        print(_yellow("  Protocol Issues:"))
        for pe in result.protocol_errors:
            print(f"    {pe['href']} — {pe['error']}")

    hs.close()
    return result


def _crawl_section(
    section: dict,
    source_href: str,
    queue: list[str],
    result: CrawlResult,
    hs: HSClient,
) -> None:
    """Process a section during crawl: queue links, probe forms."""
    kind = section.get("kind", "")

    if kind == "list":
        for item in section.get("items", []):
            item_href = item.get("href")
            if item_href and item_href not in result.visited:
                queue.append(item_href)

    elif kind == "action":
        fields = section.get("fields", [])
        href = section.get("href", "")
        method = section.get("method", "POST")
        condition = section.get("condition")

        # Skip unavailable actions
        if condition and not condition.get("met", True):
            return

        # Probe: submit with empty body to check for 500s
        if fields and href:
            empty_body = {}
            for f in fields:
                if f.get("hidden"):
                    val = f.get("value", f.get("default"))
                    if val is not None:
                        _set_nested(empty_body, f["name"], val)

            probe = hs.fetch(href, method, empty_body)
            if probe is None:
                result.form_errors.append({
                    "href": href,
                    "action": method,
                    "error": "no response on empty submit",
                    "source": source_href,
                })
                print(f"  {_red('FORM')}   {method} {href} — no response on empty submit")

        # Check action href is reachable (non-form buttons)
        if not fields and href:
            # Don't actually submit destructive actions during crawl
            if method.upper() != "GET":
                return
            if href not in result.visited:
                queue.append(href)

    elif kind == "group":
        for sub in section.get("sections", []):
            _crawl_section(sub, source_href, queue, result, hs)

    elif kind == "empty":
        action = section.get("action")
        if action and action.get("href"):
            action_href = action["href"]
            if action_href not in result.visited:
                queue.append(action_href)


# ── Helpers ─────────────────────────────────────────────────────────

def _story_path(name: str) -> Path:
    return Path("stories") / f"{name}.json"


# ── Main ────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="HyperState CLI test client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Modes:
              (default)       Interactive REPL — navigate, fill forms, explore
              --record NAME   Record interactions as a named story
              --replay FILE   Replay a saved story file
              --crawl         Crawl all reachable pages and report issues
              --get PATH      Make a one-shot GET request to PATH
              --post PATH     Make a one-shot POST request to PATH
              --request M P   Make a one-shot request using method M to path P
        """),
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE, help=f"Base URL (default: {DEFAULT_BASE})")
    parser.add_argument("--start", default="/students", help="Starting path (default: /students)")
    parser.add_argument("--record", metavar="NAME", help="Record interactions as a named story")
    parser.add_argument("--replay", metavar="FILE", help="Replay a saved story file")
    parser.add_argument("--until", type=int, metavar="N", help="Stop replay at step N")
    parser.add_argument("--crawl", action="store_true", help="Crawl and validate all reachable pages")
    
    # Non-interactive command modes
    parser.add_argument("--get", metavar="PATH", help="Make a non-interactive GET request")
    parser.add_argument("--post", metavar="PATH", help="Make a non-interactive POST request")
    parser.add_argument("--request", nargs=2, metavar=("METHOD", "PATH"), help="Make a non-interactive request")
    parser.add_argument("--data", help="JSON data body for non-interactive requests")

    args = parser.parse_args()

    if args.replay:
        path = Path(args.replay)
        if not path.exists():
            print(_red(f"Story file not found: {path}"))
            sys.exit(1)
        success = replay_story(path, args.until, args.base_url if args.base_url != DEFAULT_BASE else None)
        sys.exit(0 if success else 1)

    if args.crawl:
        result = crawl(args.base_url, args.start)
        sys.exit(0 if not result.broken_links and not result.form_errors else 1)

    # Non-interactive commands
    if args.get or args.post or args.request:
        method = "GET"
        path = ""
        if args.get:
            method = "GET"
            path = args.get
        elif args.post:
            method = "POST"
            path = args.post
        elif args.request:
            method = args.request[0].upper()
            path = args.request[1]

        body = None
        if args.data:
            try:
                body = json.loads(args.data)
            except json.JSONDecodeError as e:
                print(f"Invalid JSON data: {e}", file=sys.stderr)
                sys.exit(1)

        hs = HSClient(args.base_url)
        data = hs.fetch(path, method, body)
        hs.close()

        if data is None:
            sys.exit(1)

        print(json.dumps(data, indent=2))
        
        # Determine exit code based on HTTP status
        # Success is 2xx, 3xx
        if hs.last_status is not None and 200 <= hs.last_status < 400:
            sys.exit(0)
        
        sys.exit(1)

    # Interactive / record mode
    story = None
    if args.record:
        story = Story(
            name=args.record,
            base_url=args.base_url,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )
        print(_green(f"  Recording story: {args.record}"))

    hs = HSClient(args.base_url, story=story)
    print(_bold(f"  HyperState Client — {args.base_url}"))
    print(_dim("  Type ? for help, q to quit"))

    try:
        interactive_loop(hs, args.start)
    finally:
        if story and story.steps:
            path = _story_path(story.name)
            story.save(path)
            print(_green(f"  Story auto-saved: {path}"))
        hs.close()


if __name__ == "__main__":
    main()
