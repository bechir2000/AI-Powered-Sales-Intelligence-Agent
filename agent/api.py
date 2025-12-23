"""
Agent API Server

FastAPI backend that exposes the agent via HTTP endpoints.
Supports both streaming and non-streaming responses.
"""

from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
import traceback

from main import run_agent, run_agent_streaming

app = FastAPI(title="Account Intelligence API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    """Request model for agent queries."""

    account_id: int
    user_query: str


class QueryResponse(BaseModel):
    """Response model for agent queries."""

    response: str


def load_accounts_from_data():
    """Load accounts from the MCP server data directory."""
    import json
    from pathlib import Path
    import os

    data_dir = Path(
        os.getenv("DATA_DIR", Path(__file__).parent.parent / "mcp_server" / "data")
    )
    accounts = []

    if not data_dir.exists():
        return accounts

    for file_path in sorted(data_dir.glob("account_*.json")):
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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/api/accounts")
async def get_accounts():
    """Get list of available accounts for the dropdown."""
    accounts = load_accounts_from_data()
    return {"accounts": accounts}


@app.post("/api/query", response_model=QueryResponse)
async def query_agent(request: QueryRequest):
    """
    Query the agent with a user question about an account.

    Returns the agent's response (non-streaming).
    """
    try:
        response = run_agent(
            user_query=request.user_query, account_id=request.account_id
        )

        return QueryResponse(response=response)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query/stream")
async def query_agent_stream(request: QueryRequest):
    """
    Query the agent with streaming response.

    Returns a Server-Sent Events stream.
    """

    async def generate() -> AsyncGenerator[str, None]:
        try:
            async for token in run_agent_streaming(
                user_query=request.user_query,
                account_id=request.account_id,
            ):
                yield f"data: {token}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
