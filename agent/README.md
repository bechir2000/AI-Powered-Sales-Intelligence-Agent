# Agent Service

FastAPI backend that exposes the LangGraph agent.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Agent API                          │
│                    (FastAPI :8001)                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   ┌─────────┐      ┌────────────┐      ┌─────────────┐ │
│   │  START  │ ──►  │ Supervisor │ ──►  │Final Answer │ │
│   └─────────┘      └────────────┘      └─────────────┘ │
│                          │                    │        │
│                          ▼                    ▼        │
│                    ┌──────────┐         ┌─────────┐   │
│                    │MCP Server│         │GPT-4o-  │   │
│                    │  Tools   │         │  mini   │   │
│                    └──────────┘         └─────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Graph Flow

```
__start__ → supervisor → final_answer → __end__
```

### Nodes

1. **Supervisor** (`nodes/supervisor.py`)
   - Deterministic Python (no LLM)
   - Uses a **fixed plan**: always fetch all transcripts + emails
   - Calls MCP tools via `streamable_http` client
   - Passes context to final_answer

2. **Final Answer** (`nodes/final_answer.py`)
   - Uses GPT-4o-mini
   - Receives user query + retrieved context
   - Generates the final response

### Fixed Plan

```json
{
  "steps": [
    {"tool": "transcripts", "description": "Retrieve all transcripts for the account"},
    {"tool": "emails", "description": "Retrieve all emails for the account"}
  ]
}
```

## Files

```
agent/
├── api.py              # FastAPI server (run this)
├── main.py             # Agent entry point
├── graph.py            # LangGraph workflow definition
├── config.py           # Configuration, state, types
├── requirements.txt
└── nodes/
    ├── __init__.py
    ├── supervisor.py   # Orchestrator node
    └── final_answer.py # LLM response node
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/accounts` | List available accounts |
| POST | `/api/query` | Query agent (non-streaming) |
| POST | `/api/query/stream` | Query agent (streaming SSE) |

### Request

```json
POST /api/query
{
    "account_id": 1,
    "user_query": "What are the main pain points discussed?"
}
```

### Response

```json
{
    "response": "Based on the transcripts and emails..."
}
```

## Setup

```bash
cd agent
pip install -r requirements.txt
```

## Environment Variables

```bash
export OPENAI_API_KEY="your-key"
export MCP_SERVER_URL="http://localhost:8002/mcp"  # optional, this is default
```

## Running

```bash
cd agent
python api.py
# or: uvicorn api:app --reload --port 8001
```

API available at http://localhost:8001
