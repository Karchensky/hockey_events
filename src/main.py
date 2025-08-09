from __future__ import annotations

from pathlib import Path
from typing import List
from loguru import logger

from datetime import datetime
import pytz

from src.config import load_config, load_env
from src.scrapers.erie_metro import ErieMetroScraper
from src.scrapers.rinks_harborcenter import HarborcenterScraper
from src.state.store import StateStore
from src.calendar.google_calendar import GoogleCalendarClient
from src.email.notify import send_summary, send_personal
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


def import_to_google() -> None:
    config = load_config()
    env = load_env()

    if not env.google_refresh_token:
        logger.warning("GOOGLE_REFRESH_TOKEN not set; skipping Google Calendar insertion. Feeds will still be built.")
        return

    timezone = config.timezone or env.default_timezone

    events = collect_events(config.urls, timezone)
    # keep only future events
    now = datetime.now(pytz.timezone(timezone))
    events = [e for e in events if e.start >= now]
    logger.info(f"Collected {len(events)} future events")

    if not events:
        return

    state = StateStore()
    gcal = GoogleCalendarClient(
        client_id=env.google_client_id,
        client_secret=env.google_client_secret,
        refresh_token=env.google_refresh_token,
    )

    newly_added: List[str] = []

    for event in events:
        event_id = event.google_event_id()
        for recipient in config.recipients:
            recipient_key = recipient.calendar_id or recipient.email or recipient.name
            if state.has_seen(recipient_key, event_id):
                continue

            calendar_id = recipient.calendar_id or env.google_default_calendar_id or "primary"

            exists_link = gcal.event_exists(calendar_id, event)
            if exists_link:
                state.mark_seen(recipient_key, event_id)
                continue

            link = None
            if recipient.calendar_id:
                link = gcal.insert_event(calendar_id=calendar_id, event=event)
            else:
                attendees = [recipient.email] if recipient.email else []
                link = gcal.insert_event(calendar_id=calendar_id, event=event, attendees_emails=attendees)

            if link is not None:
                state.mark_seen(recipient_key, event_id)
                entry = f"- {event.summary} @ {event.start.strftime('%Y-%m-%d %I:%M %p')} ({link})"
                newly_added.append(entry)
                if recipient.email:
                    send_personal(
                        smtp_server=env.smtp_server,
                        smtp_port=env.smtp_port,
                        username=env.smtp_username,
                        password=env.smtp_password,
                        from_email=env.smtp_from,
                        to_email=recipient.email,
                        subject="New hockey event added",
                        body=f"A new event was added for you:\n\n{entry}\n\nSource: {event.source_url or ''}",
                        use_tls=env.smtp_use_tls,
                    )

    state.save()

    if newly_added and config.notify.summary_to:
        send_summary(
            smtp_server=env.smtp_server,
            smtp_port=env.smtp_port,
            username=env.smtp_username,
            password=env.smtp_password,
            from_email=env.smtp_from,
            to_emails=config.notify.summary_to,
            subject="New hockey events added",
            body="New events added:\n\n" + "\n".join(newly_added),
            use_tls=env.smtp_use_tls,
        )


def build_team_feeds() -> None:
    config = load_config()
    env = load_env()

    timezone = config.timezone or env.default_timezone
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)

    docs = Path("docs/ics")
    docs.mkdir(parents=True, exist_ok=True)

    for team in config.teams:
        events: List[Event] = collect_events(team.urls, timezone)
        # only future events
        events = [e for e in events if e.start >= now]
        ics_bytes = build_ics(events)
        (docs / f"{team.id}.ics").write_bytes(ics_bytes)

    # simple HTML index to pick a team
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
    # Always build feeds; insert to Google only if credentials are present
    import_to_google()
    build_team_feeds()