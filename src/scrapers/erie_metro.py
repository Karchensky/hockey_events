from __future__ import annotations

from datetime import datetime
from typing import List, Optional
import time
import random
import asyncio
import warnings
import logging

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
import pytz
from playwright.async_api import async_playwright, Browser, Page

from src.scrapers.base import Scraper
from src.utils.events import Event, guess_end, localize, adjust_year_if_past

# Suppress asyncio warnings
logging.getLogger('asyncio').setLevel(logging.CRITICAL)
warnings.filterwarnings('ignore', category=RuntimeWarning, module='asyncio')


class ErieMetroScraper(Scraper):
    def __init__(self, team_name: Optional[str] = None) -> None:
        self.team_name = team_name

    def can_handle(self, url: str) -> bool:
        return "eriemetrosports.com" in url

    def scrape(self, url: str, timezone: str) -> List[Event]:
        """Main scrape method that uses Mac user agent (working) with browser automation fallback"""
        # Strategy 1: Mac user agent (most reliable)
        try:
            resp = requests.get(url, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            })
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

            status_text = cells[status_idx] if status_idx >= 0 and status_idx < len(cells) else ""
            
            # Skip games explicitly marked as completed
            # Note: Don't skip empty status - upcoming games may not have times populated yet
            if "final" in status_text.lower():
                continue

            time_candidate = status_text or (cells[1] if len(cells) > 1 else "")
            dt_text = f"{date_text} {time_candidate}".strip()

            try:
                dt_naive = dateparser.parse(dt_text, fuzzy=True, ignoretz=True)
                if dt_naive is None:
                    continue
                # Handle year rollover (e.g., "Jan 5" should be 2026, not 2025)
                dt_naive = adjust_year_if_past(dt_naive, now_local.replace(tzinfo=None))
                start = localize(dt_naive, timezone)
            except Exception:
                try:
                    date_only = dateparser.parse(date_text, fuzzy=True, ignoretz=True)
                    date_only = date_only.replace(hour=21, minute=0, second=0, microsecond=0)
                    # Handle year rollover
                    date_only = adjust_year_if_past(date_only, now_local.replace(tzinfo=None))
                    start = localize(date_only, timezone)
                except Exception:
                    continue

            if start < now_local:
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

            location = cells[location_idx] if location_idx >= 0 else None

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