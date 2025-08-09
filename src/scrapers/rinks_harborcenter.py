from __future__ import annotations

from datetime import datetime
from typing import List

import pytz
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from dateutil import parser as dateparser

from src.scrapers.base import Scraper
from src.utils.events import Event, guess_end, localize


class HarborcenterScraper(Scraper):
    def can_handle(self, url: str) -> bool:
        return "rinksatharborcenter.com" in url

    def scrape(self, url: str, timezone: str) -> List[Event]:
        events: List[Event] = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            page.goto(url, wait_until="networkidle")
            # Give SPA a moment to render
            page.wait_for_timeout(2000)
            html = page.content()
            context.close()
            browser.close()

        soup = BeautifulSoup(html, "html.parser")

        # Try to locate rows in schedule tables or cards. As the site is SPA, selectors may vary.
        # We'll search for elements containing a date and a time and an opponent.
        candidates = []
        for el in soup.find_all(["tr", "div", "li"]):
            text = el.get_text(" ", strip=True)
            if not text or len(text) < 10:
                continue
            if any(k in text.lower() for k in ["am", "pm"]):
                candidates.append((el, text))

        tz = pytz.timezone(timezone)
        now_local = datetime.now(tz)

        for el, text in candidates:
            # Attempt parse like: Tue Aug 12 9:50 PM vs Team @ Rink
            try:
                dt = dateparser.parse(text, fuzzy=True)
            except Exception:
                continue
            if not dt:
                continue
            start = localize(dt, timezone)
            if start < now_local:
                continue

            # Summary heuristics
            summary = "Hockey Game"
            location = None
            # Look for '@ Rink' or 'Rink' near the end
            words = text.split()
            if "Rink" in words:
                idx = words.index("Rink")
                location = " ".join(words[max(0, idx - 2): idx + 1])

            events.append(
                Event(
                    summary=summary,
                    start=start,
                    end=guess_end(start),
                    timezone=timezone,
                    location=location,
                    description=f"Auto-imported from {url}",
                    source_url=url,
                )
            )

        return events