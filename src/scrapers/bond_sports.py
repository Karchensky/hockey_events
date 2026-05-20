from __future__ import annotations

from datetime import datetime
from typing import List, Optional
import re

from bs4 import BeautifulSoup, Tag
from playwright.sync_api import sync_playwright
import pytz

from src.scrapers.base import Scraper
from src.utils.events import Event, guess_end


SCORE_RE = re.compile(r"\b(\d+)\s*-\s*(\d+)\b")


class BondSportsScraper(Scraper):
    def __init__(self, team_name: Optional[str] = None) -> None:
        self.team_name = team_name

    def can_handle(self, url: str) -> bool:
        return "bondsports.co" in url

    def scrape(self, url: str, timezone: str) -> List[Event]:
        html = self._render_page(url)
        return self._parse(html, url, timezone)

    def _render_page(self, url: str) -> str:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(5000)

            show_all = page.locator("text=/Show All/")
            if show_all.count() > 0 and show_all.first.is_visible():
                show_all.first.click()
                page.wait_for_timeout(3000)

            html = page.content()
            browser.close()
        return html

    def _parse(self, html: str, source_url: str, timezone: str) -> List[Event]:
        soup = BeautifulSoup(html, "html.parser")
        events: List[Event] = []

        venue_el = soup.find(attrs={"data-testid": "competition-subtitle"})
        venue = venue_el.get_text(strip=True) if venue_el else None

        cards = soup.find_all(
            "article",
            attrs={"data-testid": lambda v: v and v.startswith("game-card-") and v.count("-") == 2},
        )

        for card in cards:
            event = self._parse_card(card, source_url, timezone, venue)
            if event:
                events.append(event)

        return events

    def _parse_card(self, card: Tag, source_url: str, timezone: str, venue: Optional[str] = None) -> Optional[Event]:
        game_id = card["data-testid"].replace("game-card-", "")

        teams_div = card.find(attrs={"data-testid": f"game-card-{game_id}-teams"})
        if not teams_div:
            return None

        teams_text = teams_div.get_text(" ", strip=True)

        if self.team_name and not self._team_matches(teams_text):
            return None

        start = self._parse_start(card, game_id, timezone)
        if not start:
            return None

        space_div = card.find(attrs={"data-testid": f"game-card-{game_id}-space"})
        space = space_div.get_text(" ", strip=True) if space_div else None
        if space and venue:
            location = f"{space}, {venue}"
        else:
            location = space or venue

        status_div = card.find(attrs={"data-testid": f"game-card-{game_id}-status"})
        status = status_div.get_text(" ", strip=True) if status_div else ""

        score = self._extract_score(card, game_id)
        summary = teams_text
        if score:
            summary = f"{summary} ({score})"

        description_lines = [f"Auto-imported from {source_url}"]
        if status:
            description_lines.append(f"Status: {status}")

        return Event(
            summary=summary,
            start=start,
            end=guess_end(start),
            timezone=timezone,
            location=location,
            description="\n".join(description_lines),
            source_url=source_url,
            external_id=f"bondsports-{game_id}",
        )

    def _team_matches(self, teams_text: str) -> bool:
        if not self.team_name:
            return True
        needle = self.team_name.lower()
        haystack = teams_text.lower()
        return needle in haystack

    def _parse_start(self, card: Tag, game_id: str, timezone: str) -> Optional[datetime]:
        date_div = card.find(attrs={"data-testid": f"game-card-{game_id}-date"})
        if not date_div:
            return None

        # Prefer the <time datetime="..."> ISO attribute (UTC)
        time_el = date_div.find("time", attrs={"datetime": True})
        if time_el:
            iso = time_el["datetime"]
            try:
                dt_utc = datetime.fromisoformat(iso.replace("Z", "+00:00"))
                return dt_utc.astimezone(pytz.timezone(timezone))
            except (ValueError, TypeError):
                pass

        # Fallback: parse text
        date_text = date_div.get_text(" ", strip=True)
        time_div = card.find(attrs={"data-testid": f"game-card-{game_id}-time"})
        time_text = time_div.get_text(" ", strip=True) if time_div else ""
        combined = f"{date_text} {time_text}".strip()

        try:
            from dateutil import parser as dateparser
            dt_naive = dateparser.parse(combined, fuzzy=True, ignoretz=True)
            if dt_naive:
                return pytz.timezone(timezone).localize(dt_naive)
        except Exception:
            pass

        return None

    def _extract_score(self, card: Tag, game_id: str) -> Optional[str]:
        status_div = card.find(attrs={"data-testid": f"game-card-{game_id}-status"})
        if not status_div:
            return None
        text = status_div.get_text(" ", strip=True)
        match = SCORE_RE.search(text)
        if match:
            return f"{match.group(1)}-{match.group(2)}"
        return None
