"""
MCP Server

Provides tools for retrieving account data:
- transcripts: Get call transcripts for an account
- emails: Get emails for an account

Uses FastMCP with streamable_http transport.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import date

from mcp.server.fastmcp import FastMCP
from starlette.responses import JSONResponse
from starlette.requests import Request
import uvicorn


# Suppress noisy ClosedResourceError logs from MCP's stateless HTTP transport
# These are expected in stateless mode and don't affect functionality
class ClosedResourceFilter(logging.Filter):
    def filter(self, record):
        # Filter out "Error in message router" with ClosedResourceError
        msg = record.getMessage()
        if "Error in message router" in msg:
            return False
        if "Terminating session" in msg:
            return False
        # Also check exception info
        if record.exc_info and record.exc_info[0]:
            exc_name = record.exc_info[0].__name__
            if exc_name == "ClosedResourceError":
                return False
        return True


logging.getLogger("mcp.server.streamable_http").addFilter(ClosedResourceFilter())


SERVICE_NAME = "account-data-mcp"

# Data directory
DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).parent / "data"))

# Initialize MCP server
mcp = FastMCP(
    SERVICE_NAME,
    host="0.0.0.0",
    port=8002,
    streamable_http_path="/mcp",
    json_response=True,
    stateless_http=True,
)


def load_account_data(account_id: int) -> dict | None:
    """Load account data from JSON file.

    Account files are named account_<id>.json (e.g., account_1.json).
    """
    if not DATA_DIR.exists():
        return None

    # Try to load directly by account_id from filename
    file_path = DATA_DIR / f"account_{account_id}.json"
    if file_path.exists():
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                data["account_id"] = account_id  # Add account_id to the data
                return data
        except (json.JSONDecodeError, IOError):
            return None

    return None


def list_all_accounts() -> list[dict]:
    """List all available accounts from data files.

    Returns a list of {id, name} dicts for each account.
    """
    accounts = []
    if not DATA_DIR.exists():
        return accounts

    for file_path in sorted(DATA_DIR.glob("account_*.json")):
        try:
            # Extract account_id from filename (e.g., account_1.json -> 1)
            account_id = int(file_path.stem.replace("account_", ""))
            with open(file_path, "r") as f:
                data = json.load(f)
                accounts.append(
                    {
                        "id": account_id,
                        "name": data.get("account_name", f"Account {account_id}"),
                    }
                )
        except (json.JSONDecodeError, IOError, ValueError):
            continue

    return accounts

def parse_iso(d: Optional[str]) -> Optional[date]:
    if not d:
        return None
    try:
        return date.fromisoformat(d)
    except ValueError:
        return None


def in_range(d_str: Optional[str], start: Optional[date], end: Optional[date]) -> bool:
    if not d_str:
        return False
    try:
        d = date.fromisoformat(d_str)
    except ValueError:
        return False
    if start and d < start:
        return False
    if end and d > end:
        return False
    return True


def clamp_top_k(k: Optional[int], max_k: int = 20) -> Optional[int]:
    if k is None:
        return None
    try:
        k = int(k)
        if k <= 0:
            return None
        return min(k, max_k)
    except (TypeError, ValueError):
        return None



# ----- Tools -----

@mcp.tool(
    name="transcripts",
    description="Retrieve call transcripts for an account.",
)
async def get_transcripts(
    account_id: int,
    start_date: str | None = None,
    end_date: str | None = None,
    top_k: int | None = None,
    metadata_only: bool = False,
) -> Dict[str, Any]:
    account_data = load_account_data(account_id)

    if account_data is None:
        return {"found": False, "transcripts": None, "error": f"No data found for account_id: {account_id}"}

    calls = account_data.get("calls", [])
    if not calls:
        return {"found": False, "transcripts": None, "error": "No transcripts found for this account"}

    start = parse_iso(start_date)
    end = parse_iso(end_date)
    k = clamp_top_k(top_k)

    out: List[Dict[str, Any]] = []
    for call in calls:
        d = call.get("date")
        if (start or end) and not in_range(d, start, end):
            continue

        if metadata_only:
            out.append({
                "date": d,
                "call_name": call.get("call_name"),
                "summary": call.get("summary"),
                "crm_fields": call.get("crm_fields"),
            })
        else:
            out.append({
                "date": d,
                "call_name": call.get("call_name"),
                "transcript": call.get("transcript"),
                "summary": call.get("summary"),
                "crm_fields": call.get("crm_fields"),
            })

    # Most recent first (ISO string date sorts fine)
    out.sort(key=lambda x: x.get("date") or "", reverse=True)

    if k is not None:
        out = out[:k]

    return {
        "found": True, 
        "account_name": account_data.get("account_name"), 
        "transcripts": out
    }


@mcp.tool(
    name="emails",
    description="Retrieve emails for an account.",
)
async def get_emails(
    account_id: int,
    start_date: str | None = None,
    end_date: str | None = None,
    top_k: int | None = None,
    metadata_only: bool = False,
) -> Dict[str, Any]:
    account_data = load_account_data(account_id)

    if account_data is None:
        return {"found": False, "emails": None, "error": f"No data found for account_id: {account_id}"}

    emails = account_data.get("emails", [])
    if not emails:
        return {"found": False, "emails": None, "error": "No emails found for this account"}

    start = parse_iso(start_date)
    end = parse_iso(end_date)
    k = clamp_top_k(top_k)

    out: List[Dict[str, Any]] = []
    for email in emails:
        d = email.get("date")
        if (start or end) and not in_range(d, start, end):
            continue

        if metadata_only:
            out.append({
                "date": d,
                "subject": email.get("subject"),
            })
        else:
            out.append({
                "date": d,
                "subject": email.get("subject"),
                "content": email.get("content"),
            })

    out.sort(key=lambda x: x.get("date") or "", reverse=True)

    if k is not None:
        out = out[:k]

    return {
        "found": True, 
        "account_name": account_data.get("account_name"),
        "emails": out
    }

# ----- App -----


def create_app():
    """Create the Starlette app with MCP routes."""
    return mcp.streamable_http_app()


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("MCP_SERVER_PORT", 8002))
    print(f"Starting MCP Server on port {port}")
    print(f"Data directory: {DATA_DIR}")
    print(f"MCP endpoint: http://localhost:{port}/mcp")

    uvicorn.run(app, host="0.0.0.0", port=port)
