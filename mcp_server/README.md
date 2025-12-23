# MCP Server

Model Context Protocol server that provides data retrieval tools.

## Tools

| Tool | Description | Input | Output |
|------|-------------|-------|--------|
| `transcripts` | Get call transcripts | `account_id: int` | Raw transcript JSON |
| `emails` | Get emails | `account_id: int` | Raw email JSON |

## Architecture

Uses **FastMCP** with `streamable_http` transport:

```python
mcp = FastMCP(
    "account-data-mcp",
    streamable_http_path="/mcp",
    json_response=True,
    stateless_http=True,
)
```

## Files

```
mcp_server/
├── server.py           # MCP server implementation
├── requirements.txt
├── README.md
└── data/               # Account JSON files go here
    └── *.json
```

## Data Format

Place account JSON files in the `data/` directory:

```json
{
  "tenant_name": "modjo",
  "account_name": "Acme Corp",
  "account_id": 1,
  "calls": [
    {
      "date": "2024-01-15",
      "call_name": "Discovery Call",
      "transcript": "Sales Rep: Hi John...",
      "summary": "..."
    }
  ],
  "emails": [
    {
      "date": "2024-01-16",
      "subject": "Follow-up",
      "content": "Hi John,..."
    }
  ]
}
```

## Tool Responses

### `transcripts`

```json
{
  "found": true,
  "account_name": "Acme Corp",
  "transcripts": [
    {
      "date": "2024-01-15",
      "call_name": "Discovery Call",
      "transcript": "..."
    }
  ]
}
```

### `emails`

```json
{
  "found": true,
  "account_name": "Acme Corp",
  "emails": [
    {
      "date": "2024-01-16",
      "subject": "Follow-up",
      "content": "..."
    }
  ]
}
```

## Setup

```bash
cd mcp_server
pip install -r requirements.txt
```

## Environment Variables

```bash
export DATA_DIR="/path/to/data"      # optional, defaults to ./data
export MCP_SERVER_PORT=8002          # optional, defaults to 8002
```

## Running

```bash
cd mcp_server
python server.py
```

Server available at http://localhost:8002

- MCP endpoint: `POST /mcp`
- Health check: `GET /health` (if enabled)
