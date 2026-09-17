"""Render the static calendar subscription page."""

from __future__ import annotations

from html import escape
from urllib.parse import quote


SITE_URL = "https://karchensky.github.io/hockey_events/"


def _icon(name: str) -> str:
    return (
        '<svg class="icon" width="20" height="20" aria-hidden="true">'
        f'<use href="assets/icons.svg#{name}"></use></svg>'
    )


def _feed_url(filename: str) -> str:
    return f"{SITE_URL}ics/{quote(filename)}"


def _team_row(team: dict, season_name: str) -> str:
    name = escape(team["name"])
    label = escape(f'{team["name"]} - {season_name}', quote=True)
    feed_url = escape(_feed_url(team["filename"]), quote=True)
    apple_url = feed_url.replace("https://", "webcal://", 1)
    source_url = escape(team.get("source_url", ""), quote=True)
    source = (
        f'<a href="{source_url}" target="_blank" rel="noopener noreferrer">'
        f'League schedule {_icon("external-link")}</a>'
        if source_url else ""
    )
    return f"""
      <li class="team-row">
        <div class="team-info">
          <h3>{name}</h3>
          <div class="team-links">{source}
            <a href="{feed_url}" aria-label="{label}: calendar feed, one-time download">Calendar feed (.ics)</a>
          </div>
        </div>
        <div class="team-actions">
          <a class="button button-primary" href="{apple_url}" aria-label="Subscribe to {label} in Apple Calendar">
            {_icon("calendar-plus")} Apple Calendar
          </a>
          <a class="button button-secondary" href="#instructions" data-setup-feed="{feed_url}"
             aria-label="Set up {label} in Google Calendar">{_icon("calendar-days")} Google / Android</a>
        </div>
      </li>"""


def render_index(seasons: list[dict], timezone: str) -> str:
    """Render seasons in the caller's order, with the newest season expanded."""
    visible_seasons = [season for season in seasons if season["teams"]]
    sections = []
    options = []
    first_feed = ""
    first_label = ""

    for index, season in enumerate(visible_seasons):
        season_name = escape(season["name"])
        rows = "".join(_team_row(team, season["name"]) for team in season["teams"])
        count = len(season["teams"])
        for team in season["teams"]:
            feed_url = _feed_url(team["filename"])
            label = f'{team["name"]} - {season["name"]}'
            options.append(
                f'<option value="{escape(feed_url, quote=True)}">{escape(label)}</option>'
            )
            if not first_feed:
                first_feed, first_label = feed_url, label
        if index == 0:
            status = "Current season" if season.get("active") else "Latest season"
            sections.append(f"""
    <section class="current-season" aria-labelledby="current-season-title">
      <div class="section-heading">
        <h2 id="current-season-title">{season_name}</h2>
        <span class="season-status">{status}</span>
      </div>
      <ul class="team-list">{rows}</ul>
      <p class="season-note">{_icon("info")}<span><strong>New season, new subscription.</strong>
        Add this season even if you already follow last season's calendar.</span></p>
    </section>""")
        else:
            sections.append(f"""
    <details class="past-season">
      <summary><span>{season_name}</span><span class="season-count">{count} {"team" if count == 1 else "teams"}</span></summary>
      <ul class="team-list">{rows}</ul>
    </details>""")

    safe_feed = escape(first_feed, quote=True)
    safe_label = escape(first_label)
    safe_apple = safe_feed.replace("https://", "webcal://", 1)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Subscribe to your hockey team's schedule in Apple or Google Calendar. Current and past seasons, with step-by-step setup for iPhone and Android.">
  <meta name="theme-color" content="#ffffff">
  <link rel="canonical" href="{SITE_URL}">
  <link rel="icon" type="image/svg+xml" href="assets/calendar.svg">
  <link rel="stylesheet" href="assets/site.css">
  <script src="assets/site.js" defer></script>
  <title>Hockey Events | Team Calendars</title>
</head>
<body>
  <a class="skip-link" href="#calendars">Skip to calendars</a>
  <header class="site-header">
    <div class="header-inner">
      <a class="wordmark" href="./" aria-label="Hockey Events home"><img src="assets/calendar.svg" alt="" width="32" height="32"><span>Hockey Events</span></a>
      <nav aria-label="Main navigation"><a href="#calendars">Calendars</a><a href="#instructions">Setup help</a></nav>
    </div>
  </header>
  <main class="page-shell">
    <div class="page-heading">
      <p class="eyebrow">Team calendar subscriptions</p>
      <h1>Hockey Events</h1>
      <p>Your team's schedule, in your calendar.</p>
    </div>
    <div id="calendars" class="calendars" tabindex="-1">
{''.join(sections) if sections else '<p>No team calendars are available yet.</p>'}
    </div>

    <section id="instructions" class="instructions" aria-labelledby="instructions-title" tabindex="-1">
      <div class="section-heading"><div><p class="eyebrow">Get connected</p><h2 id="instructions-title">Add your calendar</h2></div></div>
      <p class="section-intro">Subscribe once for this season. Schedule changes will appear when your calendar refreshes.</p>

      <div class="feed-picker" data-js-only hidden>
        <label for="calendar-select">Team &amp; season</label>
        <select id="calendar-select">{''.join(options)}</select>
      </div>
      <noscript><p>These steps use <strong>{safe_label}</strong>. For another team, copy its Calendar feed link above and use that address instead.</p></noscript>
      <div class="feed-field">
        <label for="feed-url">Calendar subscription link</label>
        <div class="copy-control">
          <input id="feed-url" type="url" value="{safe_feed}" readonly spellcheck="false" aria-describedby="copy-status">
          <button class="button button-copy" id="copy-feed" type="button" title="Copy calendar subscription link" data-js-only hidden>{_icon("copy")}<span>Copy link</span></button>
        </div>
        <p class="field-hint" id="copy-status" role="status" aria-live="polite">Select the full link to copy it manually.</p>
      </div>

      <div class="platform-tabs" aria-label="Choose your device" data-js-only hidden>
        <button type="button" id="tab-iphone" data-platform="iphone">iPhone / iPad</button>
        <button type="button" id="tab-android" data-platform="android">Android / Google</button>
        <button type="button" id="tab-mac" data-platform="mac">Mac</button>
      </div>

      <section class="platform-panel" id="panel-iphone" aria-labelledby="iphone-title">
        <h3 id="iphone-title">iPhone &amp; iPad</h3>
        <p>Use Apple's Calendar app.</p>
        <ol class="steps">
          <li><div><strong>Open the subscription.</strong><p>Tap the button below. Allow your browser to open Calendar if asked.</p>
            <a class="button button-primary guide-apple-link" href="{safe_apple}">{_icon("calendar-plus")} Subscribe in Apple Calendar</a></div></li>
          <li><div><strong>Confirm the calendar.</strong><p>Choose <b>Subscribe</b> or follow the subscription prompt. Pick a name and color. Choose <b>iCloud</b> as the account to see it on your other Apple devices, then tap <b>Add</b> or <b>Done</b>.</p></div></li>
          <li><div><strong>Make it visible.</strong><p>In Calendar, tap <b>Calendars</b> at the bottom and check your team's calendar.</p></div></li>
        </ol>
        <details class="inline-help"><summary>Button didn't open Calendar?</summary><p>Copy the subscription link above. In the Calendar app, tap <b>Calendars</b>, then <b>Add Calendar</b> and <b>Add Subscription Calendar</b>. Paste the link and tap <b>Find</b> (or <b>Subscribe</b> on older versions). Finish with <b>Done</b> or <b>Add</b>.</p></details>
        <p class="support-link"><a href="https://support.apple.com/en-us/102301" target="_blank" rel="noopener noreferrer">Apple's subscription instructions {_icon("external-link")}</a></p>
      </section>

      <section class="platform-panel" id="panel-android" aria-labelledby="android-title">
        <h3 id="android-title">Android &amp; Google Calendar</h3>
        <p class="important-note">Start on a computer. The Google Calendar phone app cannot add a calendar from a URL.</p>
        <ol class="steps">
          <li><div><strong>Copy your calendar link.</strong><p>Choose the correct team and season above, then copy the full subscription link.</p></div></li>
          <li><div><strong>Open Google Calendar on a computer.</strong><p>Go to <a href="https://calendar.google.com/" target="_blank" rel="noopener noreferrer">calendar.google.com {_icon("external-link")}</a> and sign in with the same Google account you use on your phone.</p></div></li>
          <li><div><strong>Add it by URL.</strong><p>Next to <b>Other calendars</b> on the left, click <b>+</b>, then <b>From URL</b>. Paste the subscription link and click <b>Add calendar</b>.</p></div></li>
          <li><div><strong>Show it on your phone.</strong><p>Open the Google Calendar app. Tap the menu at the top left, scroll to your account, and check the team calendar.</p></div></li>
          <li><div><strong>Check sync if it's missing.</strong><p>In the app, open <b>Menu &gt; Settings</b>, select the team calendar (tap <b>Show more</b> if needed), and turn <b>Sync</b> on. Then return to your calendar and refresh.</p></div></li>
        </ol>
        <details class="inline-help"><summary>Only have your phone?</summary><p>You can try opening Google Calendar in your browser and requesting <b>Desktop site</b> from the browser menu. If the full calendar settings do not appear, finish setup on a computer. Downloading an .ics file is a one-time import, not a subscription.</p></details>
        <p class="support-link"><a href="https://support.google.com/calendar/answer/37100?hl=en" target="_blank" rel="noopener noreferrer">Google's subscription instructions {_icon("external-link")}</a> &middot; <a href="https://support.google.com/calendar/answer/6261951?hl=en&amp;co=GENIE.Platform%3DAndroid" target="_blank" rel="noopener noreferrer">Android sync help {_icon("external-link")}</a></p>
      </section>

      <section class="platform-panel" id="panel-mac" aria-labelledby="mac-title">
        <h3 id="mac-title">Mac</h3>
        <ol class="steps">
          <li><div><strong>Copy the subscription link above.</strong><p>Check the team and season before copying.</p></div></li>
          <li><div><strong>Open Apple's Calendar app.</strong><p>Choose <b>File &gt; New Calendar Subscription</b>. Paste the link and click <b>Subscribe</b>.</p></div></li>
          <li><div><strong>Save your subscription.</strong><p>Choose a name, color, and refresh interval. Set <b>Location</b> to <b>iCloud</b> to use the calendar across your Apple devices, then click <b>OK</b>.</p></div></li>
        </ol>
        <p class="support-link"><a href="https://support.apple.com/en-us/102301" target="_blank" rel="noopener noreferrer">Apple's subscription instructions {_icon("external-link")}</a></p>
      </section>
    </section>

    <section class="help-section" aria-labelledby="help-title">
      <h2 id="help-title">A few helpful details</h2>
      <details class="faq"><summary>When do schedule changes appear?</summary><p>Active feeds are checked twice daily. Apple, Google, and other calendar providers refresh subscriptions on their own schedules, so a change may take time to appear. For a last-minute change, check the league schedule linked beside your team.</p><p>Game times use <strong>{escape(timezone)}</strong>. Your calendar app may display them in your device's local time zone.</p></details>
      <details class="faq"><summary>I downloaded a file or see duplicate games.</summary><p>An .ics download is a snapshot. It will not receive schedule updates. Remove the imported games or the calendar you imported them into, then subscribe using the steps above. If you subscribed twice, remove the extra subscription.</p></details>
      <details class="faq"><summary>Do I need to subscribe again each season?</summary><p>Yes. Each team and season has a separate calendar link. Add the new season's subscription here; your old subscription keeps that season's games. You can keep or remove old calendars.</p></details>
      <details class="faq"><summary>How do I unsubscribe?</summary><p><strong>iPhone / iPad:</strong> In Calendar, tap <b>Calendars</b>, tap the information button beside the team calendar, and choose <b>Unsubscribe</b>.</p><p><strong>Mac:</strong> In Calendar's sidebar, Control-click the subscribed calendar and choose <b>Unsubscribe</b>.</p><p><strong>Google Calendar:</strong> On a computer, open <b>Settings</b>, select the team under <b>Settings for other calendars</b>, then choose <b>Remove calendar &gt; Unsubscribe</b>.</p></details>
      <details class="faq"><summary>Can I use Outlook?</summary><p>In Outlook on the web, open Calendar, choose <b>Add calendar &gt; Subscribe from web</b>, and paste the subscription link above. Name the calendar and save it.</p></details>
    </section>
  </main>
  <footer class="site-footer"><div><span>Hockey Events</span><span>Maintained by Bryan Karchensky</span><a href="https://github.com/karchensky/hockey_events" target="_blank" rel="noopener noreferrer">Project on GitHub {_icon("external-link")}</a></div></footer>
</body>
</html>
"""
