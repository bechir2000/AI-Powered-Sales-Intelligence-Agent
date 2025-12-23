# pylint: disable=too-few-public-methods
# pylint: disable=line-too-long

import os
from typing import Annotated, List, Optional, Any
from pydantic import BaseModel, Field
from typing_extensions import TypedDict
from langgraph.graph import MessagesState, add_messages
from langchain_core.messages import BaseMessage

# LLM settings
# Set LLM_PROVIDER to "google" or "openai"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")

# OpenAI settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-mini"

# Google Gemini settings
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_MODEL = "gemini-2.5-flash"

# Active model based on provider
FINAL_ANSWER_MODEL = GOOGLE_MODEL if LLM_PROVIDER == "google" else OPENAI_MODEL

# MCP Server settings
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8002/mcp")


class Message(BaseModel):
    """Message structure for chat."""

    role: str
    content: str


class Response(BaseModel):
    """Response to user."""

    response: str


class Step(TypedDict):
    """A single step in the plan."""

    tool: str  # Name of the tool to use: either transcripts or emails
    description: str  # Description of what this step does


class Plan(BaseModel):
    """Plan to follow - pre-determined for this agent."""

    steps: List[Step] = Field(description="Steps to execute in order")


class RetrievedContext(BaseModel):
    """Context retrieved from MCP tools."""

    transcripts: Optional[str] = None
    emails: Optional[str] = None


class AgentState(MessagesState):
    """State class to track the agent execution."""

    # Input
    user_query: str
    account_id: int

    # Plan (pre-determined)
    plan: Plan

    # Retrieved data
    context: RetrievedContext

    # Output
    final_response: str

    # Tracking
    messages: Annotated[List[BaseMessage], add_messages]

    retrieval_spec: Optional[Any] = None


# Pre-determined plan - always fetch all transcripts and emails for the account
FIXED_PLAN = Plan(
    steps=[
        Step(
            tool="transcripts", description="Retrieve all transcripts for the account"
        ),
        Step(tool="emails", description="Retrieve all emails for the account"),
    ]
)
