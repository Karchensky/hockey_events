# Hockey Events ICS Feeds

Builds per-team ICS calendars from real-world league sites and hosts them (via GitHub Pages) so users can subscribe by URL. Only future events are included.

## Features
- Per-team ICS feeds (Google/Apple/Outlook compatible)
- Future-only events
- Daily automation via GitHub Actions
- Pluggable scrapers (Erie Metro, Harborcenter SPA via Playwright)

## Setup
1. Edit `config.yaml` with your teams:

```
timezone: America/New_York
teams:
  - id: audubon-north
    name: Audubon North
    urls:
      - https://www.eriemetrosports.com/schedule/team_instance/10191173?subseason=945400
  - id: harborcenter-549836
    name: Harborcenter Team 549836
    urls:
      - https://www.rinksatharborcenter.com/stats#/1367/team/549836/schedule
```

2. Install dependencies and build locally (optional preview):

```
python -m venv .venv && .venv/Scripts/activate  # Windows PowerShell
pip install -r requirements.txt
playwright install --with-deps
python -c "from src.main import build_team_feeds; build_team_feeds()"
```

3. Enable GitHub Pages
- Settings → Pages → Source: `main` branch, folder `/docs`

4. Share subscription links
- Index: `https://<your-username>.github.io/<repo>/`
- Team ICS links:
  - `https://<your-username>.github.io/<repo>/ics/audubon-north.ics`
  - `https://<your-username>.github.io/<repo>/ics/harborcenter-549836.ics`

## How users subscribe/unsubscribe
- Google Calendar (web): Other calendars → From URL → paste the `.ics` link → Add calendar. Remove to unsubscribe.
- Apple Calendar: File → New Calendar Subscription → paste link. Remove to unsubscribe.
- Outlook: Add calendar → Subscribe from web → paste link. Remove to unsubscribe.

## Automation
- GitHub Actions workflow builds feeds daily and commits `docs/`.
- When new season URLs appear, update `config.yaml` and the next run refreshes feeds automatically.