# Sportsengine/Harborcenter Calendar Feed

ICS feed that updates daily & refreshes your personal calendar with the team schedule. Works with Google Calendar, Apple Calendar, and Outlook... in theory.

## Subscribe

1) Open the subscription page:
   - `https://karchensky.github.io/hockey_events/`
2) Click your team’s link to subscribe (the link ends with `.ics`).
3) Follow the platform-specific steps below.

### iPhone / iPad (Apple Calendar)

- Tap the team’s `.ics` link.
- When prompted, choose Subscribe (or go to Settings → Calendar → Accounts → Add Subscribed Calendar → paste the URL).
- The calendar will appear in Apple Calendar and update automatically.

### Android (Google Calendar account)

- The Google Calendar app does NOT add ICS subscriptions directly.
- Use Google Calendar on the web (desktop browser, or mobile browser with “Desktop site” enabled):
  - Open Google Calendar → Other calendars → From URL → paste the team’s `.ics` URL → Add calendar.
  - Open the Google Calendar app on your phone and ensure the new calendar is visible and set to Sync.
- Note: Tapping the `.ics` link on Android typically downloads the file (one‑time import). Subscribing via “From URL” on the web is required for ongoing updates.

### Android alternative (3rd‑party app)

- Use an app that supports ICS subscriptions, e.g., “ICSx⁵”.
- Paste the same `.ics` URL in that app to maintain a live subscription on the device.

### Outlook (web and mobile)

- Outlook.com (web): Add calendar → Subscribe from web → paste the `.ics` URL → Save.
- The subscribed calendar will sync to your Outlook mobile app.

## Unsubscribe

- Remove the subscribed calendar from your app:
  - Google Calendar (web): Settings → select the subscribed calendar → Remove calendar → Unsubscribe
  - Apple Calendar (iOS/Mac): Select the subscribed calendar → Unsubscribe/Remove
  - Outlook: Right‑click the subscribed (Internet) calendar → Remove

## Update cadence and timing

- Each team’s feed is updated once daily.
- Your calendar provider refreshes subscribed calendars on its own schedule:
  - Google Calendar: usually every few hours (can be up to 24h)
  - Apple Calendar: you can choose refresh frequency when subscribing
  - Outlook: varies by service/version
- Updates won’t always appear instantly; this timing is controlled by your calendar provider.

## Timezone

- All events are localized to the timezone listed on the subscription page (default: America/New_York).

## Troubleshooting

- If no events appear immediately, wait for the provider’s next refresh cycle.
- Make sure you subscribed “From URL” (live feed) rather than importing a downloaded file (one‑time).
- If schedule URLs change between seasons, feeds will be updated; your subscription remains valid and will refresh automatically after the next daily update.
- Contact Bryan Karchensky
