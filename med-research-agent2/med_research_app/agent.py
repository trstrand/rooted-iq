# ruff: noqa
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

import os
import google.auth
from pydantic import BaseModel
from google.genai import types

from google.adk.agents import LlmAgent
from google.adk.models import Gemini
from google.adk.apps import App, ResumabilityConfig

from google.adk.tools.bigquery import BigQueryToolset
from google.adk.integrations.bigquery.config import BigQueryToolConfig
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from med_research_app.workspace_tools import (
    list_calendar_events,
    create_calendar_event,
    list_drive_files,
)

# Auth Setup
auth_credentials, auth_project_id = google.auth.default()
project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or auth_project_id
os.environ["GOOGLE_CLOUD_PROJECT"] = str(project_id)
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"


# 0. Helper to load skill instructions
def load_skill(name: str) -> str:
    path = os.path.join(os.path.dirname(__file__), "skills", f"{name}.md")
    with open(path, "r") as f:
        return f.read()


# 1. Configure Shared Model
shared_model = Gemini(
    model="gemini-2.5-flash",
    retry_options=types.HttpRetryOptions(attempts=5),
)


# 2. Define Communication Schemas
class ResearchInput(BaseModel):
    query: str


class ResearchOutput(BaseModel):
    findings: str
    sources: list[str]


class SummarizerInput(BaseModel):
    raw_findings: str


class SummarizerOutput(BaseModel):
    formatted_report: str


# 3. Configure Toolsets
bigquery_toolset = BigQueryToolset(
    bigquery_tool_config=BigQueryToolConfig(
        compute_project_id=project_id,
    )
)

maps_mcp = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="https://mapstools.googleapis.com/mcp",
        headers={
            "x-goog-api-key": os.environ.get("GOOGLE_MAPS_API_KEY", "MISSING_KEY"),
        },
    )
)

# 4. Define Specialized Agents (Task Mode)

researcher = LlmAgent(
    name="researcher",
    model=shared_model,
    mode="task",
    description="Researches PubMed PMC via BigQuery.",
    instruction=load_skill("researcher"),
    tools=[bigquery_toolset],
    input_schema=ResearchInput,
    output_schema=ResearchOutput,
)

maps_agent = LlmAgent(
    name="maps_agent",
    model=shared_model,
    mode="task",
    description="Geospatial expert for locations and routing.",
    instruction=load_skill("maps_agent"),
    tools=[maps_mcp],
)

workspace_agent = LlmAgent(
    name="workspace_agent",
    model=shared_model,
    mode="task",
    description="Productivity assistant for Google Workspace (Calendar, Drive, Docs).",
    instruction=load_skill("workspace_agent"),
    tools=[list_calendar_events, create_calendar_event, list_drive_files],
)

summarizer = LlmAgent(
    name="summarizer",
    model=shared_model,
    mode="task",
    description="Summarizes complex findings into clinical reports and formats them professionally.",
    instruction=load_skill("summarizer"),
    input_schema=SummarizerInput,
    output_schema=SummarizerOutput,
)

from google.adk.tools.google_search_tool import GoogleSearchTool

google_search = GoogleSearchTool(bypass_multi_tools_limit=True)

orchestrator = LlmAgent(
    name="orchestrator",
    model=shared_model,
    instruction=load_skill("orchestrator"),
    sub_agents=[researcher, maps_agent, workspace_agent, summarizer],
    tools=[google_search],
)

# 5. Wrap in an App
app = App(
    name="med_research_app",
    root_agent=orchestrator,
    resumability_config=ResumabilityConfig(is_resumable=True),
)

# For compatibility
root_agent = orchestrator
