from __future__ import annotations

from datetime import datetime
from typing import List
import re

import pytz
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from dateutil import parser as dateparser

from src.scrapers.base import Scraper
from src.utils.events import Event, guess_end, localize


TEAM_VS_REGEX = re.compile(
    r"([A-Za-z0-9 .\'&\-]+?)\s+vs\.?\s+([A-Za-z0-9 .\'&\-]+?)(?=\s+(?:on\b|@|\-|,|\d|$))",
    re.IGNORECASE,
)
RINK_REGEX = re.compile(r"Rink\s*([0-9]+)", re.IGNORECASE)


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
            page.wait_for_timeout(2500)
            html = page.content()
            context.close()
            browser.close()

        soup = BeautifulSoup(html, "html.parser")

        nodes = soup.find_all(["div", "li", "tr", "p", "span"])
        texts = [n.get_text(" ", strip=True) for n in nodes]
        texts = [t for t in texts if t and len(t) > 5]

        tz = pytz.timezone(timezone)
        now_local = datetime.now(tz)

        i = 0
        while i < len(texts):
            text = texts[i]
            if "vs" not in text.lower():
                i += 1
                continue

            m = TEAM_VS_REGEX.search(text)
            if not m:
                combined = " ".join(texts[i:i+2])
                m = TEAM_VS_REGEX.search(combined)
                if not m:
                    i += 1
                    continue

            team_a = m.group(1).strip()
            team_b = m.group(2).strip()
            
            # Filter out malformed matches (table headers, etc.)
            if team_a.lower() in ['away', 'home', 'division', 'score', 'date', 'time', 'actions', 'rink']:
                i += 1
                continue
            if team_b.lower() in ['away', 'home', 'division', 'score', 'date', 'time', 'actions', 'rink']:
                i += 1
                continue
                
            summary = f"{team_a} vs. {team_b}"

            # Try to extract date from the current text first
            dt = None
            try:
                dt = dateparser.parse(text, fuzzy=True, ignoretz=True)
            except Exception:
                # If that fails, try extracting just the date/time part
                try:
                    # Look for patterns like "on MM/DD/YY HH:MM AM/PM"
                    date_match = re.search(r'on\s+(\d+/\d+/\d+\s+\d+:\d+\s*[AP]M)', text, re.IGNORECASE)
                    if date_match:
                        date_text = date_match.group(1)
                        dt = dateparser.parse(date_text, fuzzy=True, ignoretz=True)
                except Exception:
                    # If that fails, try with a smaller context window
                    try:
                        context_text = " ".join(texts[i:i+2])
                        dt = dateparser.parse(context_text, fuzzy=True, ignoretz=True)
                    except Exception:
                        try:
                            prev_context = " ".join(texts[max(0, i-1):i+2])
                            dt = dateparser.parse(prev_context, fuzzy=True, ignoretz=True)
                        except Exception:
                            dt = None

            if not dt:
                i += 1
                continue

            start = localize(dt, timezone)
            if start < now_local:
                i += 1
                continue

            rink_label = None
            rink_match = RINK_REGEX.search(text)
            if not rink_match and i + 1 < len(texts):
                rink_match = RINK_REGEX.search(texts[i+1])
            if rink_match:
                rink_label = f"Rink {rink_match.group(1)}"

            location = "LECOM Harborcenter"
            if rink_label:
                location = f"{location} - {rink_label}"

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

            i += 1  # advance to next node to avoid infinite loops

        return events