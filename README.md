# Hockey Events Auto-Importer

Scrapes schedules from real-world league sites and adds events to Google Calendar, avoiding duplicates and emailing a summary when new events are added. Also builds per-team ICS feeds for easy user subscriptions.

## Features
- Deterministic event IDs to prevent duplicates per recipient
- Supports multiple recipients per event:
  - Direct insert into specified `calendar_id`
  - Or invite recipients via `email` to the default calendar
- Daily automation via GitHub Actions
- Summary email notification for newly added events
- Pluggable scrapers (Erie Metro, Harborcenter SPA via Playwright)
- Per-team ICS feeds hosted via GitHub Pages (users can subscribe via link)
- Only future-dated events are included in calendar inserts and ICS feeds

## Setup
1. Create and populate `.env` based on `.env.example`.
2. Edit `config.yaml` with your `urls`, `recipients`, and `teams` (each team has `id`, `name`, and `urls`).
3. Install dependencies:

```
python -m venv .venv && .venv/Scripts/activate  # Windows PowerShell
pip install -r requirements.txt
playwright install --with-deps
```

4. Run locally:

```
python -m src.main
```

## Google OAuth (recommended simple path)
- Create an OAuth client (Desktop) in Google Cloud Console.
- Use a helper to obtain a refresh token with scope `https://www.googleapis.com/auth/calendar`.
- Place values in `.env`: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`.
- Optionally set `GOOGLE_DEFAULT_CALENDAR_ID` or it will use `primary`.

## Recipients
- If a recipient has `calendar_id`, the event will be inserted into that calendar (requires token to have access).
- If a recipient has `email`, the event will be created on the default calendar and the person invited as an attendee.

## Subscriptions via ICS
- Define teams in `config.yaml` under `teams:`. Example:

```
teams:
  - id: audubon-north
    name: Audubon North
    urls:
      - https://www.eriemetrosports.com/schedule/team_instance/10191173?subseason=945400
```

- The workflow builds per-team ICS files under `docs/ics/{team_id}.ics` and an index at `docs/index.html`.
- Enable GitHub Pages for the repository (serve from the `main` branch, `/docs` folder).
- Share the subscription link with users, e.g.:
  - `https://<your-gh-username>.github.io/<repo>/ics/audubon-north.ics`
  - Users click the link to subscribe in Google Calendar, Apple Calendar, Outlook, etc.

## State & De-duplication
- State is stored in `data/state.json` per recipient.
- Dedup strategy:
  - Deterministic event ID from source URL, start/end, summary, location.
  - Search existing events around the time window and match via extended properties/description.
  - Events are created with `extendedProperties.private.source_hash` set.

## Automation (GitHub Actions)
- Scheduled workflow runs daily.
- Stores secrets (`.env` values) as repository or organization secrets.
- Steps:
  - Import to Google Calendar (future events only)
  - Build ICS feeds (future events only)
  - Commit updated `data/state.json` and `docs/` for GitHub Pages

## Verifications
- `verifications/check_parse.py` prints parsed events without modifying calendars.