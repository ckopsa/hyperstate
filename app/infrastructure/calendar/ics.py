"""Render a week plan's prep timeline as an iCalendar (VCALENDAR) document.

Pure infrastructure: it takes the domain's ``ScheduleEvent`` timeline (from
``compute_schedule``) and emits a ``text/calendar`` body with one VEVENT per
thaw and per cook-start reminder. No I/O and no plan/recipe lookups — callers
pass the already-computed events.

UIDs are derived deterministically from the plan, slot date, and event kind so
re-exporting the same plan yields stable identifiers. A calendar client (or the
follow-on Home Assistant feed) reconciles events by UID, so stability is what
keeps a refreshed subscription from duplicating every reminder.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

from icalendar import Calendar, Event

from app.domain.weekplan.schedule import ScheduleEvent, ScheduleEventKind

_PRODID = "-//HyperState//Dinner Planner//EN"

# Human-readable VEVENT summary prefix per event kind.
_KIND_SUMMARY = {
    ScheduleEventKind.THAW: "Thaw",
    ScheduleEventKind.COOK_START: "Start cooking",
}

# Each reminder is a short block on the calendar; the exact length is cosmetic,
# it just gives the event a visible duration rather than a zero-length point.
_EVENT_DURATION = timedelta(minutes=15)


def event_uid(plan_id: str, event: ScheduleEvent) -> str:
    """Return the stable UID for one schedule event.

    Keyed by ``(kind, slot_date, plan)`` — the natural identity of a reminder —
    so the same plan/slot always maps to the same UID across regenerations, even
    if the recipe or its target time changes. A slot's THAW and COOK_START get
    distinct UIDs because the kind is part of the key.
    """
    return f"{event.kind.value}-{event.slot_date.isoformat()}-{plan_id}@hyperstate.dinner"


def _new_calendar(calname: str) -> Calendar:
    """Start a VCALENDAR with the shared PUBLISH headers and a display name."""
    cal = Calendar()
    cal.add("prodid", _PRODID)
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", calname)
    return cal


def _vevent_for(plan_id: str, event: ScheduleEvent, stamp: datetime) -> Event:
    """Build one VEVENT for a schedule event.

    Times are emitted as floating local date-times (no timezone): a "thaw at
    4:45am" reminder should fire at that wall-clock time wherever the cook is,
    which is exactly how ``compute_schedule`` models them (naive datetimes).
    """
    vevent = Event()
    vevent.add("uid", event_uid(plan_id, event))
    vevent.add("summary", f"{_KIND_SUMMARY[event.kind]}: {event.recipe_name}")
    vevent.add("dtstart", event.when)
    vevent.add("dtend", event.when + _EVENT_DURATION)
    vevent.add("dtstamp", stamp)
    return vevent


def render_schedule_ics(
    plan_id: str,
    events: Iterable[ScheduleEvent],
    *,
    dtstamp: datetime | None = None,
) -> bytes:
    """Build the VCALENDAR bytes for ``events`` belonging to ``plan_id``.

    ``dtstamp`` stamps when the calendar object was generated; it defaults to the
    current UTC time. It does not affect UIDs, so the feed stays reconcilable
    even though DTSTAMP advances on each export.
    """
    stamp = dtstamp or datetime.now(timezone.utc)
    cal = _new_calendar(f"Dinner prep — {plan_id}")
    for event in events:
        cal.add_component(_vevent_for(plan_id, event, stamp))
    return cal.to_ical()


def render_feed_ics(
    plans: Iterable[tuple[str, Iterable[ScheduleEvent]]],
    *,
    calname: str = "Dinner prep",
    dtstamp: datetime | None = None,
) -> bytes:
    """Build one VCALENDAR aggregating several plans' prep timelines.

    ``plans`` is an iterable of ``(plan_id, events)`` pairs — typically every
    upcoming (non-completed) week. Each event becomes a VEVENT in a single
    calendar, which is what a Home Assistant Remote Calendar subscription polls.

    UIDs already embed the plan id (see :func:`event_uid`), so events from
    different weeks never collide and a calendar client reconciles by UID across
    refreshes rather than duplicating reminders.
    """
    stamp = dtstamp or datetime.now(timezone.utc)
    cal = _new_calendar(calname)
    for plan_id, events in plans:
        for event in events:
            cal.add_component(_vevent_for(plan_id, event, stamp))
    return cal.to_ical()
