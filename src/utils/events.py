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


def adjust_year_if_past(dt: datetime, now: datetime, threshold_days: int = 180) -> datetime:
    """
    If a parsed date is significantly in the past (more than threshold_days),
    assume it's meant to be next year (handles year rollover for dates without explicit years).
    
    Default is 180 days (6 months) which works well for seasonal sports schedules:
    - Games from current season (last ~6 months) stay in current year
    - Games from >6 months ago are assumed to be next year's schedule
    
    Dates only a few days/weeks in the past are NOT adjusted - they're likely
    recent games, not dates from the previous year that need correction.
    """
    if dt < now:
        days_in_past = (now - dt).days
        # Only adjust if significantly in the past (e.g., "Jan 5" parsed as last January)
        # Don't adjust if only a few days/weeks old (e.g., "Dec 17" that was 2 days ago)
        if days_in_past > threshold_days:
            next_year = dt.replace(year=dt.year + 1)
            if next_year > now:
                return next_year
    return dt