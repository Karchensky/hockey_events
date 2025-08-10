# Sportsengine/Harborcenter Calendar Feed

ICS feed that updates daily & refreshes your personal calendar with the team schedule. Works with Google Calendar, Apple Calendar, and Outlook... in theory.

## Subscribe

1) Open the subscription page:
   - `https://karchensky.github.io/hockey_events/`
2) Click your team’s link to subscribe (the link ends with `.ics`).
3) Follow your calendar app’s prompt:
   - Google Calendar (web): Other calendars → From URL → paste the `.ics` link → Add calendar
   - Apple Calendar (Mac): File → New Calendar Subscription → paste the `.ics` link → Subscribe
   - Outlook: Add calendar → Subscribe from web → paste the `.ics` link → Import

Tip: You can also copy the `.ics` link and add it directly in your calendar app’s “Subscribe by URL” option.

## Unsubscribe

- Remove the subscribed calendar from your app:
  - Google Calendar (web): Settings → select the subscribed calendar → Remove calendar → Unsubscribe
  - Apple Calendar: Right‑click the subscribed calendar → Unsubscribe
  - Outlook: Right‑click the subscribed calendar → Remove

## Update cadence and timing

- Each team’s feed is updated once daily.
- Your calendar app periodically fetches updates:
  - Google Calendar typically refreshes subscribed calendars every few hours (can be up to 24h).
  - Apple Calendar lets you choose the refresh interval when subscribing.
  - Outlook refresh frequency varies by version and service.
- Because refresh is controlled by your calendar provider, updates may not appear immediately.

## Timezone

- All events are localized to the timezone listed on the subscription page (default: America/New_York).

## Troubleshooting

- If you don’t see events right away, the provider may not have refreshed yet. Check again later.
- Confirm you added the `.ics` URL as a “subscribed” calendar, not imported once.
- If a team’s schedule URL changes between seasons, we’ll update the feed; your subscription remains valid and will refresh automatically after the next daily update.
- Contact Bryan Karchensky
