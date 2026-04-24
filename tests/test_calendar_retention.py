from __future__ import annotations

from datetime import datetime
import unittest
from unittest.mock import patch

import pytz

from src.scrapers.erie_metro import ErieMetroScraper
from src.scrapers.rinks_harborcenter import HarborcenterScraper
from src.utils.events import Event


TEAM_PAGE_HTML = """
<html>
  <body>
    <h1>Regular Season 2025-26</h1>
    <table>
      <tr>
        <th>Date</th>
        <th>Result</th>
        <th>Opponent</th>
        <th>Location</th>
        <th>Status</th>
      </tr>
      <tr class="completed" id="game_list_row_44577992">
        <td>Wed Sep 17</td>
        <td>
          <div class="scheduleListResult">W</div>
          <div class="scheduleListScore">
            <a href="https://www.eriemetrosports.com/game/show/44577992?subseason=952202">5-3</a>
          </div>
        </td>
        <td>
          <div class="scheduleListTeam">
            <a class="teamName" href="#">Hammers</a>
          </div>
        </td>
        <td><div class="scheduleListTeam">Buffalo State</div></td>
        <td class="nowrap">
          <a href="https://www.eriemetrosports.com/game/show/44577992?subseason=952202">
            <img alt="FINAL" src="/app_images/game_center/final.gif"/>
          </a>
        </td>
      </tr>
      <tr class="scheduled" id="game_list_row_45387197">
        <td>Mon Apr 27</td>
        <td>-</td>
        <td>
          <div class="scheduleListTeam">
            @
            <a class="teamName" href="#">RCR Yachts</a>
            <span class="grayed">(18-8)</span>
          </div>
        </td>
        <td><div class="scheduleListTeam">Riverside Rink</div></td>
        <td class="nowrap">
          <a href="https://www.eriemetrosports.com/game/show/45387197?subseason=952202">
            <span>8:50 PM EDT</span>
          </a>
        </td>
      </tr>
    </table>
  </body>
</html>
"""

GAME_PAGE_HTML = """
<html>
  <head>
    <meta property="og:title" content="Hammers at Audubon North - 9:20pm EDT, September 17th, 2025"/>
  </head>
</html>
"""

HARBORCENTER_SCHEDULE_HTML = """
<html>
  <body>
    <table>
      <tr role="article">
        <td class="center"></td>
        <td class="teams">
          <span>
            <div class="sr-only" id="g-1247275-label">Buffalo Cigars vs Golden Retrievers on 2026-04-27 at 19:15</div>
            <a href="/stats#/1367/game/1247275"><span class="d t">Buffalo Cigars</span></a>
          </span>
        </td>
        <td class="teams"><span class="vs">vs</span></td>
        <td class="teams">
          <span>
            <a href="/stats#/1367/game/1247275"><span class="d t">Golden Retrievers</span></a>
          </span>
        </td>
        <td class="center">Silver</td>
        <td class="center"></td>
        <td class="center">Mon Apr 27</td>
        <td class="center">7:15PM</td>
        <td class="center actions"><a href="/stats#/1367/game/1247275">Preview</a></td>
        <td>Rink 2</td>
      </tr>
    </table>
  </body>
</html>
"""

HARBORCENTER_SCORES_HTML = """
<html>
  <body>
    <table>
      <tr role="article">
        <td class="center"></td>
        <td class="teams">
          <span>
            <div class="sr-only" id="g-1238827-label">Reverse Retro vs Golden Retrievers on 2026-04-22 at 20:15</div>
            <a class="flex flex-pcenter" href="#/1367/game/1238827">
              <span class="team-inline"><span class="d t">Reverse Retro</span></span>
              <span class="vs">vs</span>
              <span class="team-inline"><span class="d t">Golden Retrievers</span></span>
            </a>
          </span>
        </td>
        <td class="center">Silver</td>
        <td class="center"><span>3 - 4</span></td>
        <td class="center">Wed Apr 22</td>
        <td class="center">8:15PM</td>
        <td class="center actions"><a href="/stats#/1367/game/1238827">Final</a></td>
        <td>Rink 2</td>
      </tr>
    </table>
  </body>
</html>
"""


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


class CalendarRetentionTests(unittest.TestCase):
    def test_external_id_keeps_uid_stable_when_summary_changes(self) -> None:
        tz = pytz.timezone("America/New_York")
        start = tz.localize(datetime(2026, 4, 27, 19, 15))
        end = tz.localize(datetime(2026, 4, 27, 20, 30))

        upcoming = Event(
            summary="Buffalo Cigars vs. Golden Retrievers",
            start=start,
            end=end,
            timezone="America/New_York",
            external_id="harborcenter:game:1247275",
        )
        final = Event(
            summary="Buffalo Cigars vs. Golden Retrievers (4-5)",
            start=start,
            end=end,
            timezone="America/New_York",
            external_id="harborcenter:game:1247275",
        )

        self.assertEqual(upcoming.google_event_id(), final.google_event_id())

    def test_erie_metro_keeps_completed_games_and_adds_scores(self) -> None:
        scraper = ErieMetroScraper(team_name="Audubon North")

        def fake_get(url: str, *args, **kwargs):
            if "game/show/44577992" in url:
                return FakeResponse(GAME_PAGE_HTML)
            return FakeResponse(TEAM_PAGE_HTML)

        with patch("src.scrapers.erie_metro.requests.get", side_effect=fake_get):
            events = scraper.scrape(
                "https://www.eriemetrosports.com/schedule/team_instance/10300893?subseason=952202",
                "America/New_York",
            )

        self.assertEqual(len(events), 2)

        completed = next(ev for ev in events if "Hammers" in ev.summary)
        upcoming = next(ev for ev in events if "RCR Yachts" in ev.summary)

        self.assertEqual(completed.start.year, 2025)
        self.assertIn("(W 5-3)", completed.summary)
        self.assertTrue(completed.external_id.endswith("44577992?subseason=952202"))
        self.assertIn("Result: W 5-3", completed.description or "")

        self.assertEqual(upcoming.start.year, 2026)
        self.assertIn("RCR Yachts", upcoming.summary)
        self.assertTrue(upcoming.external_id.endswith("45387197?subseason=952202"))

    def test_harborcenter_parses_schedule_and_scores_rows(self) -> None:
        scraper = HarborcenterScraper(team_name="Golden Retrievers")

        schedule_events = scraper._parse_page(
            "https://www.rinksatharborcenter.com/stats#/1367/team/589011/schedule",
            HARBORCENTER_SCHEDULE_HTML,
            "America/New_York",
        )
        score_events = scraper._parse_page(
            "https://www.rinksatharborcenter.com/stats#/1367/team/589011/scores",
            HARBORCENTER_SCORES_HTML,
            "America/New_York",
        )

        self.assertEqual(len(schedule_events), 1)
        self.assertEqual(len(score_events), 1)

        upcoming = schedule_events[0]
        completed = score_events[0]

        self.assertEqual(upcoming.summary, "Buffalo Cigars vs. Golden Retrievers")
        self.assertEqual(upcoming.location, "Rink 2")
        self.assertTrue(upcoming.external_id.endswith("/stats#/1367/game/1247275"))

        self.assertEqual(completed.summary, "Reverse Retro vs. Golden Retrievers (3-4)")
        self.assertIn("Status: Final", completed.description or "")
        self.assertIn("Score: 3-4", completed.description or "")
        self.assertTrue(completed.external_id.endswith("/stats#/1367/game/1238827"))


if __name__ == "__main__":
    unittest.main()
