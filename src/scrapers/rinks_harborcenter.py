from __future__ import annotations

from datetime import datetime
from typing import List, Optional
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
from playwright.sync_api import Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from src.scrapers.base import Scraper
from src.utils.events import Event, guess_end, localize


GAME_LABEL_RE = re.compile(
    r"(.+?)\s+vs\s+(.+?)\s+on\s+(\d{4}-\d{2}-\d{2})\s+at\s+(\d{2}:\d{2})",
    re.IGNORECASE,
)
SCORE_RE = re.compile(r"\b(\d+)\s*-\s*(\d+)\b")


class HarborcenterScraper(Scraper):
    def __init__(self, team_name: Optional[str] = None) -> None:
        self.team_name = team_name

    def can_handle(self, url: str) -> bool:
        return "rinksatharborcenter.com" in url

    def scrape(self, url: str, timezone: str) -> List[Event]:
        pages: List[tuple[str, str]] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            for page_url in self._target_urls(url):
                # Render each tab in a fresh page. The schedule/scores URLs
                # differ only by the hash fragment, so reusing one page turns
                # the second navigation into a same-document (hash-only) change:
                # it doesn't reload, networkidle returns immediately, and the
                # SPA intermittently failed to re-render the new tab in time,
                # dropping every row. A fresh page forces a full load that boots
                # the SPA against the correct hash every time.
                page = browser.new_page()
                try:
                    html = self._render_page(page, page_url)
                    pages.append((page_url, html))
                finally:
                    page.close()

            browser.close()

        events: List[Event] = []
        for source_url, html in pages:
            events.extend(self._parse_page(source_url, html, timezone))
        return events

    def _target_urls(self, url: str) -> List[str]:
        companion = self._companion_url(url)
        urls: List[str] = []
        if companion and "/scores" in companion:
            urls.append(companion)
        if url not in urls:
            urls.append(url)
        if companion and companion not in urls:
            urls.append(companion)
        return urls

    def _companion_url(self, url: str) -> Optional[str]:
        if "/schedule" in url:
            return url.replace("/schedule", "/scores")
        if "/scores" in url:
            return url.replace("/scores", "/schedule")
        return None

    def _render_page(self, page: Page, url: str) -> str:
        page.goto(url, wait_until="networkidle", timeout=60000)
        # Wait for an actual game row (with its screen-reader label) to render
        # instead of sleeping a fixed interval. A page that genuinely has no
        # games will time out here and fall through with zero rows, which is
        # correct; a slow render no longer silently yields an empty table.
        try:
            page.wait_for_selector("tr[role='article'] div.sr-only", timeout=20000)
        except PlaywrightTimeoutError:
            pass
        page.wait_for_timeout(1000)
        self._load_all_rows(page)
        return page.content()

    def _load_all_rows(self, page: Page) -> None:
        while True:
            load_more = page.locator("text=LOAD MORE")
            if load_more.count() == 0:
                return

            button = load_more.first
            if not button.is_visible():
                return

            before = page.locator("tr[role='article']").count()
            button.click()
            page.wait_for_timeout(1500)
            after = page.locator("tr[role='article']").count()
            if after <= before:
                return

    def _parse_page(self, source_url: str, html: str, timezone: str) -> List[Event]:
        soup = BeautifulSoup(html, "html.parser")
        events: List[Event] = []

        for row in soup.select("tr[role='article']"):
            event = self._parse_row(row, source_url, timezone)
            if event:
                events.append(event)

        return events

    def _parse_row(self, row: Tag, source_url: str, timezone: str) -> Optional[Event]:
        label = row.find("div", class_="sr-only")
        if not label:
            return None

        label_text = " ".join(label.get_text(" ", strip=True).split())
        label_match = GAME_LABEL_RE.search(label_text)
        if not label_match:
            return None

        away_team = label_match.group(1).strip()
        home_team = label_match.group(2).strip()
        dt_naive = datetime.strptime(
            f"{label_match.group(3)} {label_match.group(4)}",
            "%Y-%m-%d %H:%M",
        )
        start = localize(dt_naive, timezone)

        cells = row.find_all("td")
        location = cells[-1].get_text(" ", strip=True) if cells else None
        status_text = ""
        actions_cell = row.find("td", class_=lambda cls: cls and "actions" in cls.split())
        if actions_cell:
            status_text = " ".join(actions_cell.get_text(" ", strip=True).split())

        score_text = self._extract_score_text(row)
        summary = f"{away_team} vs. {home_team}"
        if score_text:
            summary = f"{summary} ({score_text})"

        description_lines = [f"Auto-imported from {source_url}"]
        if status_text:
            description_lines.append(f"Status: {status_text}")
        if score_text:
            description_lines.append(f"Score: {score_text}")

        game_url = self._extract_game_url(row, source_url)
        return Event(
            summary=summary,
            start=start,
            end=guess_end(start),
            timezone=timezone,
            location=location or "LECOM Harborcenter",
            description="\n".join(description_lines),
            source_url=source_url,
            external_id=game_url,
        )

    def _extract_game_url(self, row: Tag, source_url: str) -> Optional[str]:
        for link in row.find_all("a", href=True):
            href = link["href"]
            if "/game/" in href:
                return urljoin(source_url.split("#", 1)[0], href)
        return None

    def _extract_score_text(self, row: Tag) -> Optional[str]:
        for cell in row.find_all("td"):
            text = " ".join(cell.get_text(" ", strip=True).split())
            if not text or re.search(r"[A-Za-z]", text):
                continue
            match = SCORE_RE.search(text)
            if match:
                return f"{match.group(1)}-{match.group(2)}"
        return None
