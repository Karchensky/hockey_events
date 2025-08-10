from __future__ import annotations

from typing import Iterable, Optional
from datetime import datetime
import pytz
from icalendar import Calendar, Event as IcsEvent

from src.utils.events import Event


def build_ics(
    events: Iterable[Event],
    prodid: str = "-//Hockey Events//EN",
    cal_name: Optional[str] = None,
    tz_name: Optional[str] = None,
) -> bytes:
    cal = Calendar()
    cal.add("prodid", prodid)
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    if cal_name:
        cal.add("X-WR-CALNAME", cal_name)
    if tz_name:
        cal.add("X-WR-TIMEZONE", tz_name)

    now_utc = datetime.utcnow().replace(tzinfo=pytz.UTC)

    for ev in events:
        ics_ev = IcsEvent()
        ics_ev.add("summary", ev.summary)
        # Convert to UTC for broad compatibility
        start_utc = ev.start.astimezone(pytz.UTC)
        end_utc = ev.end.astimezone(pytz.UTC)
        ics_ev.add("dtstart", start_utc)
        ics_ev.add("dtend", end_utc)
        ics_ev.add("dtstamp", now_utc)
        if ev.location:
            ics_ev.add("location", ev.location)
        if ev.description:
            ics_ev.add("description", ev.description)
        if ev.source_url:
            ics_ev.add("url", ev.source_url)
        ics_ev.add("uid", ev.google_event_id())
        cal.add_component(ics_ev)

    return cal.to_ical()