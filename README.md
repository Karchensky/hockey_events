# Hockey Events

Automatically updated hockey calendars for Apple Calendar, Google Calendar, and Outlook.

**Start here: [Hockey Events calendars](https://karchensky.github.io/hockey_events/).** Choose your team and season, then follow the instructions for your device below.

## Golden Retrievers: Fall/Winter 2026-27

Copy this entire address when a calendar app asks for a URL:

```text
https://karchensky.github.io/hockey_events/ics/golden-retrievers-fallwinter-202627.ics
```

[View the Harborcenter schedule](https://www.rinksatharborcenter.com/stats#/1367/team/717325/schedule).

**Each season needs its own subscription.** A previous Golden Retrievers subscription will not switch to the new season. Add Fall/Winter 2026-27 once; you can keep or remove previous seasons separately.

## iPhone or iPad: Apple Calendar

On the [calendars page](https://karchensky.github.io/hockey_events/), select your team and season, then use the Apple Calendar subscription button. Complete the subscription in Calendar. If the button does not open a subscription prompt, use these manual steps:

1. Copy the calendar URL above, or copy the URL for your selected team on the calendars page.
2. Open Apple's **Calendar** app.
3. Tap **Calendars**, then **Add Calendar**.
4. Choose **Add Subscription Calendar**.
5. Paste the full URL. On iOS/iPadOS 26 or later, tap **Find**. On iOS/iPadOS 18 or earlier, tap **Subscribe**.
6. Give it a recognizable name, such as **Golden Retrievers 2026-27**, and choose a color. Select **iCloud** for **Account** to use it on devices signed into the same Apple Account.
7. Tap **Done** on newer versions, or **Add** on older versions.
8. Return to **Calendars** and check that the new calendar is selected. Open the date of a scheduled game to confirm it appears.

See [Apple's subscription instructions](https://support.apple.com/en-us/102301).

### Mac: Apple Calendar

1. Copy your team's calendar URL.
2. Open **Calendar**, then choose **File > New Calendar Subscription**.
3. Paste the URL and click **Subscribe**.
4. Choose a name and color. Set **Location** to **iCloud** to see it on your other Apple devices, then click **OK**.

See [Apple's Mac calendar guide](https://support.apple.com/guide/calendar/subscribe-to-calendars-icl1022/mac).

## Android: Google Calendar

**Set up the subscription in a computer browser first.** The Google Calendar phone app cannot add calendar subscriptions. Use the same Google account on your computer and phone.

### On your computer

1. Open the [Hockey Events calendars page](https://karchensky.github.io/hockey_events/), choose your team and season, and copy its calendar URL. The Golden Retrievers URL is also listed above.
2. Open [Google Calendar](https://calendar.google.com/) and check the account shown by your profile picture.
3. On the left, find **Other calendars** and click the **+** beside it. If the sidebar is hidden, open the menu at the top left first.
4. Choose **From URL**.
5. Paste the complete `https://` calendar URL into **URL of calendar**.
6. Click **Add calendar**. Return to the calendar view; the team should appear under **Other calendars**.

See [Google's instructions for adding a public calendar by URL](https://support.google.com/calendar/answer/37100?hl=en).

### On your Android phone

1. Open **Google Calendar**. Tap your profile picture and confirm you are using the same Google account as on the computer.
2. Open the menu at the top left. Find the team calendar under that account and check its box so events are visible.
3. If games are missing, open **Menu > Settings** and select the team calendar. Tap **Show more** if needed. Turn **Sync** on if that setting is available.
4. Return to the calendar and use **Menu > Refresh**. Check the date of a scheduled game.

If it is still missing, check your phone's account sync settings for Google Calendar. [Google's Android sync guide](https://support.google.com/calendar/answer/6261951?hl=en&co=GENIE.Platform%3DAndroid) includes device settings and further checks. Refreshing the app does not force Google to fetch a newer copy of the feed immediately.

## Outlook

In Outlook on the web, open **Calendar > Add calendar > Subscribe from web**. Paste your team's calendar URL, give it a name, and choose **Import** (or **Import and Save**). In this URL-based flow, that button creates a subscription. Use that same Outlook account in the mobile app. See [Microsoft's subscription guide](https://support.microsoft.com/en-us/outlook/import-or-subscribe-to-a-calendar-in-outlook-com-or-outlook-on-the-web).

## Updates and troubleshooting

- **Subscribe instead of import.** Downloading an `.ics` file and importing it creates a one-time copy. A URL subscription receives later schedule changes. If you imported games already, remove those imported copies before subscribing to avoid duplicates.
- **Feed updates:** GitHub Actions is scheduled to rebuild active feeds twice daily, at **03:00 and 15:00 UTC**. Scheduled runs can be delayed. Apple, Google, and Outlook check feeds on their own schedules; there is no guaranteed refresh time.
- **Changed or missing games:** Check the team's original schedule and the correct date, confirm the team calendar is visible, and allow time for your provider to refresh. A subscription cannot show games the league has not published yet.
- **Wrong season:** Add the new season's URL. Existing subscriptions continue to point to their original season.
- **Times:** Source schedules use **America/New_York**. Your calendar may display games in your device's local time zone.
- **Still stuck:** Contact Bryan Karchensky with your device, calendar app, team/season, and the step where you got stuck.

## Unsubscribe

- **iPhone/iPad:** Open **Calendar > Calendars**, tap the information button beside the team calendar, choose **Unsubscribe**, and confirm.
- **Mac:** Control-click the subscribed calendar in Calendar's sidebar, then choose **Unsubscribe**.
- **Google Calendar:** On a computer, open **Settings**, select the team calendar, then choose **Remove calendar > Unsubscribe**.
- **Outlook:** Open the calendar list and remove the subscribed team calendar.

Unsubscribing removes that team's subscribed events, not your personal calendar. Simply hiding a calendar keeps its subscription active.

## Maintenance

Team and season sources are configured in `config.yaml`. Keep existing season URLs available so earlier subscriptions continue to work.

```sh
python -m pip install -r requirements.txt
python -m playwright install chromium
python -m src.main
python -m unittest discover -s tests
```

The build generates `docs/index.html` and the feeds in `docs/ics/`. Change the page generator in `src/site.py` and the styles/scripts in `docs/assets/`; direct edits to generated HTML will be overwritten. GitHub Pages serves the published `docs/` directory.
