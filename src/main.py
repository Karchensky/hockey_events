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


def collect_events(urls: List[str], timezone: str, team_name: str | None = None) -> List[Event]:
    scrapers = [ErieMetroScraper(team_name=team_name), HarborcenterScraper()]
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

    # Sort seasons by start date descending (most recent first), unknown dates last
    def season_sort_key(season):
        return (season.start is not None, season.start or datetime.min.date())

    sorted_seasons = sorted(config.seasons, key=season_sort_key, reverse=True)

    # Build ICS files
    for season in sorted_seasons:
        for team in season.teams:
            events: List[Event] = collect_events(team.urls, timezone, team_name=team.name)
            events = [e for e in events if e.start >= now]
            # dedupe
            unique_map = {e.google_event_id(): e for e in events}
            unique_events = sorted(unique_map.values(), key=lambda e: e.start)
            ics_bytes = build_ics(unique_events, cal_name=team.name, tz_name=timezone)
            (docs / f"{team.id}.ics").write_bytes(ics_bytes)

    # Render index grouped by season
    sections: List[str] = []
    for season in sorted_seasons:
        team_links = "\n".join(
            f'<li><a href="ics/{team.id}.ics">{team.name}</a></li>' for team in season.teams
        )
        sections.append(f"<h2>{season.name}</h2>\n<ul>\n{team_links}\n</ul>")

    index = Path("docs/index.html")
    index.write_text(
        f"""
<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Team Calendar Subscriptions</title>
  <style>
    body {{ font-family: 'Borda', 'Borda Regular', sans-serif; line-height: 1.5; margin: 24px; }}
    h1 {{ margin-bottom: 8px; }}
    h2 {{ margin-top: 24px; }}
    ul {{ padding-left: 20px; }}
    code {{ background: #f4f4f4; padding: 2px 4px; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>Team Calendar Subscriptions</h1>
  {''.join(sections)}

  <h2>Subscribe</h2>
  <p><strong>Apple (iPhone/iPad):</strong> Tap a team link above and choose Subscribe. Or go to Settings → Calendar → Accounts → Add Subscribed Calendar and paste the URL.</p>
  <p><strong>Android (Google Calendar):</strong> Use Google Calendar on the web: Other calendars → From URL → paste the team URL → Add. Then ensure it’s visible and set to Sync in the app. Tapping the link on Android typically downloads a file (one-time import) and won’t auto-update.</p>

  <h2>Unsubscribe</h2>
  <p><strong>Apple:</strong> Remove the subscribed calendar in Calendar settings.</p>
  <p><strong>Android (Google Calendar):</strong> On the web, open Settings, select the subscribed calendar, and Remove/Unsubscribe. It will disappear from the app.</p>

  <h2>Contact</h2>
  <p>Bryan Karchensky</p>
</body>
</html>
""".strip(),
        encoding="utf-8",
    )


if __name__ == "__main__":
    build_team_feeds()