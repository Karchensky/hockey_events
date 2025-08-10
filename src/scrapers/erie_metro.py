from __future__ import annotations

from datetime import datetime
from typing import List

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
import pytz

from src.scrapers.base import Scraper
from src.utils.events import Event, guess_end, localize


class ErieMetroScraper(Scraper):
    def can_handle(self, url: str) -> bool:
        return "eriemetrosports.com" in url

    def scrape(self, url: str, timezone: str) -> List[Event]:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        events: List[Event] = []

        # The schedule is in a table with rows containing Date | Result/Time | Opponent | Location | Status
        table = soup.find("table")
        if not table:
            return events

        rows = table.find_all("tr")
        tz = pytz.timezone(timezone)
        now_local = datetime.now(tz)

        headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(["th", "td"])] if rows else []
        # Attempt to find column indices
        def col_index(name: str) -> int:
            for i, h in enumerate(headers):
                if name in h:
                    return i
            return -1

        date_idx = col_index("date")
        opponent_idx = col_index("opponent")
        location_idx = col_index("location")
        status_idx = col_index("status")

        for tr in rows[1:]:
            cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            if not cells:
                continue

            try:
                date_text = cells[date_idx] if date_idx >= 0 else cells[0]
            except Exception:
                continue

            # Identify scheduled (future) entries. Status cell often contains time like '9:50 PM EDT'
            status_text = cells[status_idx] if status_idx >= 0 else ""
            if "final" in status_text.lower():
                # Skip completed games
                continue

            time_candidate = status_text or cells[1] if len(cells) > 1 else ""
            dt_text = f"{date_text} {time_candidate}".strip()

            try:
                dt_naive = dateparser.parse(dt_text, fuzzy=True, ignoretz=True)
                if dt_naive is None:
                    continue
                start = localize(dt_naive, timezone)
            except Exception:
                # Fallback: parse date only at 9:00 PM
                try:
                    date_only = dateparser.parse(date_text, fuzzy=True, ignoretz=True)
                    date_only = date_only.replace(hour=21, minute=0, second=0, microsecond=0)
                    start = localize(date_only, timezone)
                except Exception:
                    continue

            if start < now_local:
                # Skip past
                continue

            opponent = cells[opponent_idx] if opponent_idx >= 0 else "Opponent"
            location = cells[location_idx] if location_idx >= 0 else None
            summary = f"Hockey: {opponent}"

            end = guess_end(start)
            events.append(
                Event(
                    summary=summary,
                    start=start,
                    end=end,
                    timezone=timezone,
                    location=location,
                    description=f"Auto-imported from {url}",
                    source_url=url,
                )
            )

        return events