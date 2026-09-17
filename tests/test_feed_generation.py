from __future__ import annotations

from contextlib import chdir
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup
from icalendar import Calendar
import pytz

from src.config import AppConfig, load_config
from src.main import build_team_feeds, slugify
from src.utils.events import Event


class FeedGenerationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = AppConfig.model_validate({
            "seasons": [
                {
                    "id": "old", "name": "Summer 2026", "start": "2026-06-01",
                    "active": False,
                    "teams": [{"id": "old-team", "name": "Golden Retrievers", "urls": []}],
                },
                {
                    "id": "new", "name": "Fall/Winter 2026/27", "start": "2026-09-01",
                    "teams": [{
                        "id": "new-team", "name": "Golden Retrievers",
                        "urls": ["https://www.rinksatharborcenter.com/stats#/1367/team/717325/schedule"],
                    }],
                },
            ],
        })
        tz = pytz.timezone("America/New_York")
        self.event = Event(
            summary="Mediak Construction Kings vs. The Golden Retrievers",
            start=tz.localize(datetime(2026, 10, 7, 22, 20)),
            end=tz.localize(datetime(2026, 10, 7, 23, 35)),
            timezone="America/New_York",
            external_id="harborcenter:1335891",
        )

    def test_new_season_is_configured_with_requested_feed_name(self) -> None:
        config = load_config()
        season = next(s for s in config.seasons if s.id == "fall-winter-2026-27")
        team = season.teams[0]
        self.assertTrue(season.active and team.active)
        self.assertEqual(team.id, "golden-retrievers-fallwinter-202627")
        self.assertEqual(f"{slugify(team.name)}-{slugify(season.name)}", team.id)
        self.assertEqual(team.urls, [
            "https://www.rinksatharborcenter.com/stats#/1367/team/717325/schedule",
        ])

    def test_build_keeps_archives_deduplicates_games_and_renders_subscription(self) -> None:
        with TemporaryDirectory() as directory, chdir(directory):
            archive = Path("docs/ics/golden-retrievers-summer-2026.ics")
            archive.parent.mkdir(parents=True)
            archive.write_bytes(b"archived calendar")
            with patch("src.main.load_config", return_value=self.config), patch(
                "src.main.collect_events", return_value=[self.event, self.event]
            ) as collect:
                build_team_feeds()

            collect.assert_called_once()
            self.assertEqual(archive.read_bytes(), b"archived calendar")
            feed = Path("docs/ics/golden-retrievers-fallwinter-202627.ics")
            calendar = Calendar.from_ical(feed.read_bytes())
            games = calendar.walk("VEVENT")
            self.assertEqual(len(games), 1)
            self.assertEqual(str(calendar["X-WR-CALNAME"]), "Golden Retrievers - Fall/Winter 2026/27")
            self.assertEqual(games[0].decoded("DTSTART"), self.event.start)

            html = Path("docs/index.html").read_text(encoding="utf-8")
            soup = BeautifulSoup(html, "html.parser")
            self.assertLess(html.index("Fall/Winter 2026/27"), html.index("Summer 2026"))
            self.assertIsNotNone(soup.find("a", href=(
                "webcal://karchensky.github.io/hockey_events/ics/"
                "golden-retrievers-fallwinter-202627.ics"
            )))
            self.assertIn("golden-retrievers-summer-2026.ics", html)

    def test_empty_scrape_preserves_all_existing_feeds_and_index(self) -> None:
        self.config.seasons[0].active = True
        with TemporaryDirectory() as directory, chdir(directory):
            feeds = Path("docs/ics")
            feeds.mkdir(parents=True)
            current = feeds / "golden-retrievers-fallwinter-202627.ics"
            archive = feeds / "golden-retrievers-summer-2026.ics"
            index = Path("docs/index.html")
            for path in (current, archive, index):
                path.write_bytes(b"previous published content")

            with patch("src.main.load_config", return_value=self.config), patch(
                "src.main.collect_events", side_effect=[[self.event], []]
            ), self.assertRaisesRegex(RuntimeError, "No games returned"):
                build_team_feeds()

            for path in (current, archive, index):
                self.assertEqual(path.read_bytes(), b"previous published content")


if __name__ == "__main__":
    unittest.main()
