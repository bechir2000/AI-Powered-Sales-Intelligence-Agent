# pylint: disable=line-too-long
"""
Supervisor Node

This node is the first entrypoint of the agent. It:
1. Uses the pre-determined plan to fetch all transcripts and emails
2. Calls the MCP tools directly to retrieve the context
3. Passes control to the final_answer node
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Tuple, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

import sys
import re

sys.path.append("..")
from config import MCP_SERVER_URL, AgentState, RetrievedContext, Plan, FIXED_PLAN, LLM_PROVIDER, FINAL_ANSWER_MODEL


# Thread pool for running async code from sync context
_executor = ThreadPoolExecutor(max_workers=4)

def _run_async(coro):
    """Run async coroutine from sync context, handling existing event loops."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop, safe to use asyncio.run()
        return asyncio.run(coro)

    # There's a running loop (e.g., FastAPI), run in a new thread
    import concurrent.futures

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(asyncio.run, coro)
        return future.result()


class MCPClient:
    """Simple MCP client wrapper for tool calls using streamable_http."""

    def __init__(self, server_url: str):
        self.server_url = server_url

    async def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Async method to call an MCP tool."""
        async with streamablehttp_client(self.server_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)

                # Extract text from result
                if result.content:
                    return "\n".join(
                        block.text for block in result.content if hasattr(block, "text")
                    )
                return ""

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Sync wrapper to call an MCP tool."""
        try:
            return _run_async(self._call_tool(tool_name, arguments))
        except Exception as e:
            return f"Error calling {tool_name}: {str(e)}"


# Initialize MCP client
mcp_client = MCPClient(MCP_SERVER_URL)

def supervisor_node(state: AgentState) -> Dict[str, Any]:
    """
    Supervisor node - orchestrates the agent execution.

    This node:
    1. Uses the fixed plan (fetch all transcripts and emails)
    2. Calls the MCP tools to retrieve data
    3. Stores the retrieved context in state
    """
    account_id = state["account_id"]
    spec = state.get("retrieval_spec") or {}

    use_transcripts = bool(spec.get("use_transcripts", True))
    use_emails = bool(spec.get("use_emails", True))
    metadata_only = bool(spec.get("metadata_only", True))

    base_args: Dict[str, Any] = {"account_id": account_id, "metadata_only": metadata_only}

    start_date = spec.get("start_date")
    end_date = spec.get("end_date")
    top_k = spec.get("top_k")

    if start_date:
        base_args["start_date"] = start_date
    if end_date:
        base_args["end_date"] = end_date
    if top_k is not None:
        base_args["top_k"] = top_k

    # Execute the plan: call MCP tools
    transcripts_data = None
    emails_data = None

    steps=[]
    
    if use_transcripts:
        transcripts_data = mcp_client.call_tool("transcripts", dict(base_args))
        steps.append({"tool": "transcripts", "description": f"Retrieve transcripts with {base_args}"})

    if use_emails:
        emails_data = mcp_client.call_tool("emails", dict(base_args))
        steps.append({"tool": "emails", "description": f"Retrieve emails with {base_args}"})

    #print("email data: ", emails_data)
    #print("transcript data: ", transcripts_data)
    plan = Plan(steps=steps)
    return {
        "plan": plan,
        "context": RetrievedContext(transcripts=transcripts_data, emails=emails_data),
    }
