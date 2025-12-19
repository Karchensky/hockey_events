from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha1
from typing import Optional
import re

import pytz


@dataclass
class Event:
    summary: str
    start: datetime
    end: datetime
    timezone: str
    location: Optional[str] = None
    description: Optional[str] = None
    source_url: Optional[str] = None

    def google_event_id(self) -> str:
        base = f"{self.source_url}|{self.start.isoformat()}|{self.end.isoformat()}|{self.summary}|{self.location or ''}"
        digest = sha1(base.encode("utf-8")).hexdigest()
        # Google Calendar event IDs must be between 5 and 1024 chars, and may contain only letters, digits, '-' and '_'
        return f"evt_{digest[:40]}"

    def to_google_body(self) -> dict:
        tz = self.timezone
        return {
            "summary": self.summary,
            "location": self.location or None,
            "description": self.description or None,
            "start": {"dateTime": self.start.isoformat(), "timeZone": tz},
            "end": {"dateTime": self.end.isoformat(), "timeZone": tz},
            "source": {"title": "Source", "url": self.source_url} if self.source_url else None,
        }


TIME_MATCH = re.compile(r"(?i)(\d{1,2}):(\d{2})\s*([ap])m|\b(\d{1,2})\s*([ap])\b")


def guess_end(start: datetime, default_minutes: int = 75) -> datetime:
    return start + timedelta(minutes=default_minutes)


def localize(dt: datetime, tz_name: str) -> datetime:
    tz = pytz.timezone(tz_name)
    if dt.tzinfo is None:
        return tz.localize(dt)
    return dt.astimezone(tz)


def adjust_year_if_past(dt: datetime, now: datetime) -> datetime:
    """
    If a parsed date is in the past but would be in the future with +1 year,
    assume it's meant to be next year (handles year rollover for dates without explicit years).
    """
    if dt < now:
        next_year = dt.replace(year=dt.year + 1)
        if next_year > now:
            return next_year
    return dt