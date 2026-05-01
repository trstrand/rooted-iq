# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.adk.tools import ToolContext


async def list_calendar_events(tool_context: ToolContext) -> dict:
    """Lists the next 10 events on the user's primary calendar."""
    token = tool_context.state.get("google_access_token")
    if not token:
        return {"error": "Google Access Token missing in session state."}

    creds = Credentials(token)
    service = build("calendar", "v3", credentials=creds)

    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin="2026-01-01T00:00:00Z",  # In a real app, use current time
            maxResults=10,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    events = events_result.get("items", [])

    if not events:
        return {"message": "No upcoming events found."}

    return {"events": events}


async def create_calendar_event(
    summary: str, start_time: str, end_time: str, tool_context: ToolContext
) -> dict:
    """Creates a new event on the user's primary calendar.

    Args:
        summary: The event title.
        start_time: Start time in ISO format (e.g., '2026-05-28T09:00:00-07:00').
        end_time: End time in ISO format.
    """
    token = tool_context.state.get("google_access_token")
    if not token:
        return {"error": "Google Access Token missing."}

    creds = Credentials(token)
    service = build("calendar", "v3", credentials=creds)

    event = {
        "summary": summary,
        "start": {"dateTime": start_time},
        "end": {"dateTime": end_time},
    }

    event = service.events().insert(calendarId="primary", body=event).execute()
    return {"status": "success", "event_id": event.get("id")}


async def list_drive_files(tool_context: ToolContext) -> dict:
    """Lists the names and IDs of the first 10 files in Google Drive."""
    token = tool_context.state.get("google_access_token")
    if not token:
        return {"error": "Google Access Token missing."}

    creds = Credentials(token)
    service = build("drive", "v3", credentials=creds)

    results = (
        service.files()
        .list(pageSize=10, fields="nextPageToken, files(id, name)")
        .execute()
    )
    items = results.get("files", [])

    if not items:
        return {"message": "No files found."}

    return {"files": items}
