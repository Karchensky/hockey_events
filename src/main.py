from __future__ import annotations

from pathlib import Path
from typing import List
from loguru import logger

from datetime import datetime
import pytz

from src.config import load_config
from src.scrapers.erie_metro import ErieMetroScraper
from src.scrapers.rinks_harborcenter import HarborcenterScraper
from src.utils.events import Event
from src.utils.ics import build_ics


def collect_events(urls: List[str], timezone: str) -> List[Event]:
    scrapers = [ErieMetroScraper(), HarborcenterScraper()]
    events: List[Event] = []

    for url in urls:
        handled = False
        for s in scrapers:
            if s.can_handle(url):
                handled = True
                logger.info(f"Scraping {url} with {s.__class__.__name__}")
                try:
                    found = s.scrape(url, timezone)
                    events.extend(found)
                except Exception as exc:
                    logger.error(f"Failed to scrape {url}: {exc}")
                break
        if not handled:
            logger.warning(f"No scraper available for URL: {url}")
    return events


def build_team_feeds() -> None:
    config = load_config()

    timezone = config.timezone
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)

    docs = Path("docs/ics")
    docs.mkdir(parents=True, exist_ok=True)

    for team in config.teams:
        events: List[Event] = collect_events(team.urls, timezone)
        events = [e for e in events if e.start >= now]
        ics_bytes = build_ics(events, cal_name=team.name, tz_name=timezone)
        (docs / f"{team.id}.ics").write_bytes(ics_bytes)

    index = Path("docs/index.html")
    links = "\n".join(
        f'<li><a href="ics/{team.id}.ics">Subscribe to {team.name}</a></li>' for team in config.teams
    )
    index.write_text(
        f"""
<!DOCTYPE html>
<html>
<head><meta charset=\"utf-8\"><title>Hockey Feeds</title></head>
<body>
  <h1>Hockey Team Subscriptions</h1>
  <ul>
    {links}
  </ul>
  <p>Click a link above to subscribe in your calendar app.</p>
</body>
</html>
""".strip(),
        encoding="utf-8",
    )


if __name__ == "__main__":
    build_team_feeds()