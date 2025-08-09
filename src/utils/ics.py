from __future__ import annotations

from typing import Iterable
from icalendar import Calendar, Event as IcsEvent

from src.utils.events import Event


def build_ics(events: Iterable[Event], prodid: str = "-//Hockey Events//EN") -> bytes:
    cal = Calendar()
    cal.add("prodid", prodid)
    cal.add("version", "2.0")

    for ev in events:
        ics_ev = IcsEvent()
        ics_ev.add("summary", ev.summary)
        ics_ev.add("dtstart", ev.start)
        ics_ev.add("dtend", ev.end)
        if ev.location:
            ics_ev.add("location", ev.location)
        if ev.description:
            ics_ev.add("description", ev.description)
        if ev.source_url:
            ics_ev.add("url", ev.source_url)
        ics_ev.add("uid", ev.google_event_id())
        cal.add_component(ics_ev)

    return cal.to_ical()