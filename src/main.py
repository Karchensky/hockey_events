from __future__ import annotations

from pathlib import Path
from typing import List
from loguru import logger

from datetime import datetime
import re

from src.config import load_config
from src.scrapers.bond_sports import BondSportsScraper
from src.scrapers.erie_metro import ErieMetroScraper
from src.scrapers.rinks_harborcenter import HarborcenterScraper
from src.site import render_index
from src.utils.events import Event
from src.utils.ics import build_ics


def slugify(name: str) -> str:
    slug = name.strip().lower()
    slug = re.sub(r"[^a-z0-9\s\-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug or "calendar"


def collect_events(urls: List[str], timezone: str, team_name: str | None = None) -> List[Event]:
    scrapers = [BondSportsScraper(team_name=team_name), ErieMetroScraper(team_name=team_name), HarborcenterScraper(team_name=team_name)]
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

    docs = Path("docs/ics")
    docs.mkdir(parents=True, exist_ok=True)

    # Sort seasons by start date descending (most recent first), unknown dates last
    def season_sort_key(season):
        return (season.start is not None, season.start or datetime.min.date())

    sorted_seasons = sorted(config.seasons, key=season_sort_key, reverse=True)

    season_sections: List[dict] = []
    pending_feeds: dict[Path, bytes] = {}

    for season in sorted_seasons:
        season_slug = slugify(season.name)
        team_links = []
        
        for team in season.teams:
            # Always show team in index with link, but only update ICS for active teams
            name_slug = slugify(team.name)
            preferred_filename = f"{name_slug}-{season_slug}.ics"
            
            if team.active and season.active:
                # Generate fresh ICS for active teams
                events: List[Event] = collect_events(team.urls, timezone, team_name=team.name)
                if not events:
                    raise RuntimeError(
                        f"No games returned for {team.name} ({season.name}); "
                        "keeping existing feeds and stopping publication."
                    )
                # Dedupe with source IDs when available so the same game can move from
                # "schedule" to "scores" without creating a second calendar event.
                unique_map = {}
                for e in events:
                    if e.external_id:
                        key = e.external_id
                        if key not in unique_map:
                            unique_map[key] = e
                        continue

                    # Create a normalized version for deduplication
                    normalized_location = ""
                    if e.location:
                        # Normalize Harborcenter locations to be consistent
                        if "LECOM Harborcenter" in e.location:
                            normalized_location = "LECOM Harborcenter"
                        else:
                            normalized_location = e.location
                    
                    key = f"{e.summary}|{e.start.isoformat()}|{e.end.isoformat()}|{normalized_location}"
                    if key not in unique_map:
                        unique_map[key] = e
                unique_events = sorted(unique_map.values(), key=lambda e: e.start)
                ics_bytes = build_ics(
                    unique_events, cal_name=f"{team.name} - {season.name}", tz_name=timezone
                )
                pending_feeds[docs / preferred_filename] = ics_bytes

            team_links.append({
                "name": team.name,
                "filename": preferred_filename,
                "source_url": team.urls[0] if team.urls else "",
            })
        
        # Always add season section if there are teams
        if team_links:
            season_sections.append({
                "name": season.name,
                "active": season.active,
                "teams": team_links,
            })

    # Finish all scrapes before replacing any published feed.
    for path, content in pending_feeds.items():
        path.write_bytes(content)

    index = Path("docs/index.html")
    index.write_text(
        render_index(season_sections, timezone),
        encoding="utf-8",
    )


if __name__ == "__main__":
    build_team_feeds()
