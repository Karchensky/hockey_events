from __future__ import annotations

from datetime import datetime
import pytz

from src.config import load_config
from src.main import collect_events


def main() -> None:
    cfg = load_config()
    tz = pytz.timezone(cfg.timezone)
    now = datetime.now(tz)

    for team in cfg.teams:
        print(f"\n== {team.name} ==")
        events = collect_events(team.urls, cfg.timezone)
        events = [e for e in events if e.start >= now]
        for ev in events:
            print(f"{ev.start} - {ev.summary} @ {ev.location or ''}")


if __name__ == "__main__":
    main()