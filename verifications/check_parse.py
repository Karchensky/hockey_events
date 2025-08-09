from __future__ import annotations

from src.config import load_config
from src.main import collect_events


def main() -> None:
    cfg = load_config()
    events = collect_events(cfg.urls, cfg.timezone)
    for ev in events:
        print(f"{ev.start} - {ev.summary} @ {ev.location or ''}")


if __name__ == "__main__":
    main()