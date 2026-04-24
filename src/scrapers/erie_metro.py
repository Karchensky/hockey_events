from __future__ import annotations

from datetime import datetime
from typing import List, Optional
import random
import asyncio
import warnings
import logging
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag
from dateutil import parser as dateparser
import pytz
from playwright.async_api import async_playwright, Page

from src.scrapers.base import Scraper
from src.utils.events import Event, guess_end, localize, adjust_year_if_past

# Suppress asyncio warnings
logging.getLogger('asyncio').setLevel(logging.CRITICAL)
warnings.filterwarnings('ignore', category=RuntimeWarning, module='asyncio')


SCORE_RE = re.compile(r"\b\d+\s*-\s*\d+\b")
SEASON_RANGE_RE = re.compile(r"\b(20\d{2})\s*[-/]\s*(\d{2,4})\b")
OG_TITLE_TIME_RE = re.compile(r"-\s*(.+)$")
MAC_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


class ErieMetroScraper(Scraper):
    def __init__(self, team_name: Optional[str] = None) -> None:
        self.team_name = team_name
        self._game_start_cache: dict[str, datetime] = {}

    def can_handle(self, url: str) -> bool:
        return "eriemetrosports.com" in url

    def _extract_season_years(self, soup: BeautifulSoup) -> tuple[Optional[int], Optional[int]]:
        page_text = " ".join(soup.stripped_strings)
        head_text = page_text[:1000]
        match = SEASON_RANGE_RE.search(head_text)
        if not match:
            return (None, None)

        start_year = int(match.group(1))
        end_year_text = match.group(2)
        end_year = int(end_year_text)
        if len(end_year_text) == 2:
            end_year = (start_year // 100) * 100 + end_year
        return (start_year, end_year)

    def _has_explicit_year(self, text: str) -> bool:
        return bool(re.search(r"\b20\d{2}\b", text))

    def _apply_season_year(
        self,
        dt: datetime,
        raw_text: str,
        season_start_year: Optional[int],
        season_end_year: Optional[int],
    ) -> tuple[datetime, bool]:
        if self._has_explicit_year(raw_text) or season_start_year is None:
            return (dt, False)

        target_year = season_start_year
        if season_end_year is not None and season_end_year != season_start_year:
            # Erie Metro fall/winter schedules span the hockey year: Jul-Dec belong to
            # the starting year, Jan-Jun belong to the ending year.
            target_year = season_start_year if dt.month >= 7 else season_end_year

        return (dt.replace(year=target_year), True)

    def _is_completed_result(self, result_text: str) -> bool:
        normalized = " ".join(result_text.split()).lower()
        if not normalized or normalized == "-":
            return False

        if SCORE_RE.search(normalized):
            return True

        tokens = re.findall(r"[a-z]+", normalized)
        return any(token in {"w", "l", "t", "otw", "otl", "sow", "sol"} for token in tokens)

    def _extract_score_text(self, result_cell: Optional[Tag]) -> str:
        if not result_cell:
            return ""

        score_div = result_cell.find("div", class_="scheduleListScore")
        if score_div:
            score_text = score_div.get_text(" ", strip=True)
            if SCORE_RE.search(score_text):
                return score_text.replace(" ", "")

        cell_text = result_cell.get_text(" ", strip=True)
        match = SCORE_RE.search(cell_text)
        if match:
            return match.group(0).replace(" ", "")
        return ""

    def _extract_result_flag(self, result_cell: Optional[Tag]) -> str:
        if not result_cell:
            return ""

        result_div = result_cell.find("div", class_="scheduleListResult")
        if result_div:
            return result_div.get_text(" ", strip=True).upper()

        text = result_cell.get_text(" ", strip=True)
        tokens = re.findall(r"[A-Za-z/]+", text)
        return tokens[0].upper() if tokens else ""

    def _extract_status_text(self, status_cell: Optional[Tag]) -> str:
        if not status_cell:
            return ""

        image = status_cell.find("img", alt=True)
        if image:
            return image["alt"].strip()

        return status_cell.get_text(" ", strip=True)

    def _extract_game_url(self, row: Tag, page_url: str) -> Optional[str]:
        for link in row.find_all("a", href=True):
            href = link["href"]
            if "/game/show/" in href:
                return urljoin(page_url, href)
        return None

    def _fetch_game_start(self, game_url: str, timezone: str) -> Optional[datetime]:
        if game_url in self._game_start_cache:
            return self._game_start_cache[game_url]

        try:
            resp = requests.get(game_url, timeout=20, headers=MAC_HEADERS)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            og_title = soup.find("meta", attrs={"property": "og:title"})
            if not og_title or not og_title.get("content"):
                return None

            match = OG_TITLE_TIME_RE.search(og_title["content"])
            if not match:
                return None

            dt_naive = dateparser.parse(match.group(1), fuzzy=True, ignoretz=True)
            if dt_naive is None:
                return None

            start = localize(dt_naive, timezone)
            self._game_start_cache[game_url] = start
            return start
        except Exception:
            return None

    def scrape(self, url: str, timezone: str) -> List[Event]:
        """Main scrape method that uses Mac user agent (working) with browser automation fallback"""
        # Strategy 1: Mac user agent (most reliable)
        try:
            resp = requests.get(url, timeout=30, headers=MAC_HEADERS)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        except Exception as e:
            print(f"Mac user agent failed, trying browser automation: {e}")
            
            # Strategy 2: Browser automation fallback
            try:
                content = asyncio.run(self._scrape_with_browser(url))
                soup = BeautifulSoup(content, "html.parser")
            except Exception as e2:
                print(f"Browser automation failed, trying mobile user agent: {e2}")
                
                # Strategy 3: Mobile user agent fallback
                try:
                    resp = requests.get(url, timeout=30, headers={
                        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Accept-Encoding': 'gzip, deflate',
                        'Connection': 'keep-alive',
                    })
                    resp.raise_for_status()
                    soup = BeautifulSoup(resp.text, "html.parser")
                except Exception as e3:
                    # If all strategies fail, return placeholder event
                    print(f"All scraping strategies failed for Erie Metro. Mac UA: {e}, Browser: {e2}, Mobile UA: {e3}")
                    return [Event(
                        summary=f"{self.team_name} - Schedule Unavailable",
                        start=datetime.now(pytz.timezone(timezone)),
                        end=datetime.now(pytz.timezone(timezone)),
                        timezone=timezone,
                        location="Erie Metro Sports",
                        description="Unable to retrieve schedule due to bot protection. Please check the website directly.",
                        source_url=url,
                    )]

        events: List[Event] = []

        table = soup.find("table")
        if not table:
            return events

        rows = table.find_all("tr")
        tz = pytz.timezone(timezone)
        now_local = datetime.now(tz)

        headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(["th", "td"])] if rows else []

        def col_index(name: str) -> int:
            for i, h in enumerate(headers):
                if name in h:
                    return i
            return -1

        date_idx = col_index("date")
        result_idx = col_index("result")
        opponent_idx = col_index("opponent")
        location_idx = col_index("location")
        status_idx = col_index("status")
        season_start_year, season_end_year = self._extract_season_years(soup)

        for tr in rows[1:]:
            cell_tags = tr.find_all("td")
            cells = [td.get_text(" ", strip=True) for td in cell_tags]
            if not cell_tags:
                continue

            try:
                date_text = cells[date_idx] if date_idx >= 0 else cells[0]
            except Exception:
                continue

            result_cell = cell_tags[result_idx] if result_idx >= 0 and result_idx < len(cell_tags) else None
            status_cell = cell_tags[status_idx] if status_idx >= 0 and status_idx < len(cell_tags) else None
            result_text = cells[result_idx] if result_idx >= 0 and result_idx < len(cells) else ""
            score_text = self._extract_score_text(result_cell)
            result_flag = self._extract_result_flag(result_cell)
            status_text = self._extract_status_text(status_cell)
            game_url = self._extract_game_url(tr, url)

            start = None
            time_candidate = status_text if re.search(r"\d", status_text or "") else ""

            if not time_candidate and game_url:
                start = self._fetch_game_start(game_url, timezone)

            if not start:
                dt_text = f"{date_text} {time_candidate}".strip()

                try:
                    dt_naive = dateparser.parse(dt_text, fuzzy=True, ignoretz=True)
                    if dt_naive is None:
                        continue
                    dt_naive, used_season_year = self._apply_season_year(
                        dt_naive,
                        date_text,
                        season_start_year,
                        season_end_year,
                    )
                    if not used_season_year:
                        dt_naive = adjust_year_if_past(dt_naive, now_local.replace(tzinfo=None))
                    start = localize(dt_naive, timezone)
                except Exception:
                    try:
                        date_only = dateparser.parse(date_text, fuzzy=True, ignoretz=True)
                        date_only = date_only.replace(hour=21, minute=0, second=0, microsecond=0)
                        date_only, used_season_year = self._apply_season_year(
                            date_only,
                            date_text,
                            season_start_year,
                            season_end_year,
                        )
                        if not used_season_year:
                            date_only = adjust_year_if_past(date_only, now_local.replace(tzinfo=None))
                        start = localize(date_only, timezone)
                    except Exception:
                        continue

            opponent_cell = cells[opponent_idx] if opponent_idx >= 0 else "Opponent"
            # Opponent cell often like '@ Ham Sub Club' or 'Realty Group'
            opponent = opponent_cell.replace("@", "").strip()
            # Compose summary with team name if available
            if self.team_name:
                summary = f"{self.team_name} vs. {opponent}"
            else:
                # Fallback: include generic label
                summary = f"Hockey: {opponent_cell}"

            if score_text:
                result_bits = " ".join(bit for bit in [result_flag, score_text] if bit).strip()
                summary = f"{summary} ({result_bits})" if result_bits else f"{summary} ({score_text})"

            location = cells[location_idx] if location_idx >= 0 else None
            description_lines = [f"Auto-imported from {url}"]
            if result_text and result_text != "-":
                description_lines.append(f"Result: {result_text}")
            if status_text:
                description_lines.append(f"Status: {status_text}")

            end = guess_end(start)
            external_id = game_url or f"{url}#{tr.get('id', date_text)}"
            events.append(
                Event(
                    summary=summary,
                    start=start,
                    end=end,
                    timezone=timezone,
                    location=location,
                    description="\n".join(description_lines),
                    source_url=game_url or url,
                    external_id=external_id,
                )
            )

        return events

    async def _scrape_with_browser(self, url: str) -> str:
        """Scrape using browser automation"""
        playwright = await async_playwright().start()
        browser = None
        page = None
        
        try:
            # Launch browser with enhanced stealth settings for cloud environments
            browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-gpu',
                    '--disable-software-rasterizer',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-field-trial-config',
                    '--disable-ipc-flooding-protection',
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-default-apps',
                    '--disable-popup-blocking',
                    '--disable-prompt-on-repost',
                    '--disable-sync',
                    '--disable-translate',
                    '--hide-scrollbars',
                    '--mute-audio',
                    '--no-zygote',
                    '--single-process',
                ]
            )
            
            # Create context with realistic settings
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='America/New_York',
            )
            
            page = await context.new_page()
            
            # Add stealth scripts to avoid detection
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
                
                Object.defineProperty(navigator, 'platform', {
                    get: () => 'Win32',
                });
                
                Object.defineProperty(navigator, 'hardwareConcurrency', {
                    get: () => 8,
                });
                
                Object.defineProperty(navigator, 'deviceMemory', {
                    get: () => 8,
                });
                
                window.chrome = {
                    runtime: {},
                };
                
                // Override permissions API
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // Override getParameter
                Object.defineProperty(WebGLRenderingContext.prototype, 'getParameter', {
                    value: function(parameter) {
                        if (parameter === 37445) {
                            return 'Intel Inc.';
                        }
                        if (parameter === 37446) {
                            return 'Intel Iris OpenGL Engine';
                        }
                        return WebGLRenderingContext.prototype.getParameter.call(this, parameter);
                    },
                });
            """)
            
            # First visit homepage to establish session
            try:
                await page.goto('https://www.eriemetrosports.com/', wait_until='domcontentloaded', timeout=10000)
                await asyncio.sleep(random.uniform(1, 3))
            except Exception:
                pass  # Continue even if homepage fails
            
            # Navigate to the target page
            response = await page.goto(url, wait_until='domcontentloaded', timeout=15000)
            
            if response and response.status == 403:
                raise Exception(f"403 Forbidden: {url}")
            
            # Wait a bit for content to load with random delay
            await asyncio.sleep(random.uniform(2, 4))
            
            # Get page content
            content = await page.content()
            
            # Clean up resources before returning
            await page.close()
            await browser.close()
            await playwright.stop()
            
            return content
            
        except Exception as e:
            # Clean up resources on error
            try:
                if page:
                    await page.close()
            except Exception:
                pass
            try:
                if browser:
                    await browser.close()
            except Exception:
                pass
            try:
                await playwright.stop()
            except Exception:
                pass
            raise Exception(f"Browser scraping failed: {e}")
