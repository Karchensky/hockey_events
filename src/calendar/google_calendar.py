from __future__ import annotations

from typing import List, Optional
from loguru import logger

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from datetime import timedelta

from src.utils.events import Event


SCOPES = ["https://www.googleapis.com/auth/calendar"]


class GoogleCalendarClient:
    def __init__(self, client_id: str, client_secret: str, refresh_token: str) -> None:
        self.creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES,
        )
        self.service = build("calendar", "v3", credentials=self.creds, cache_discovery=False)

    def event_exists(self, calendar_id: str, event: Event, window_minutes: int = 15) -> Optional[str]:
        time_min = (event.start - timedelta(minutes=window_minutes)).isoformat()
        time_max = (event.end + timedelta(minutes=window_minutes)).isoformat()
        try:
            resp = (
                self.service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    maxResults=50,
                    orderBy="startTime",
                )
                .execute()
            )
            items = resp.get("items", [])
            target_hash = event.google_event_id()
            for it in items:
                ext = it.get("extendedProperties", {}).get("private", {})
                if ext.get("source_hash") == target_hash:
                    return it.get("htmlLink")
                desc = (it.get("description") or "").lower()
                if event.source_url and event.source_url.lower() in desc:
                    if (it.get("summary") or "").strip().lower() == event.summary.strip().lower():
                        return it.get("htmlLink")
            return None
        except HttpError as err:
            logger.error(f"Failed to check existing events: {err}")
            return None

    def insert_event(
        self,
        calendar_id: str,
        event: Event,
        attendees_emails: Optional[List[str]] = None,
    ) -> Optional[str]:
        body = event.to_google_body()
        if attendees_emails:
            body["attendees"] = [{"email": e} for e in attendees_emails]

        # Add extendedProperties for de-duplication tracking and deterministic id
        deterministic_id = event.google_event_id()
        body["extendedProperties"] = {"private": {"source_hash": deterministic_id}}
        body["id"] = deterministic_id

        try:
            created = (
                self.service.events()
                .insert(calendarId=calendar_id, body=body, sendUpdates="all", conferenceDataVersion=1)
                .execute()
            )
            return created.get("htmlLink")
        except HttpError as err:
            if getattr(err, "resp", None) and err.resp.status == 409:
                logger.info(f"Event already exists (conflict) on calendar {calendar_id}: {deterministic_id}")
                return None
            logger.error(f"Failed to insert event: {err}")
            return None