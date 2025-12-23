# Web Application

Streamlit frontend for the Account Intelligence Agent.

## Features

- Account selection dropdown
- Text input for queries
- Streaming toggle (on/off)
- Clean, minimal white UI

## Files

```
webapp/
├── app.py              # Streamlit application
├── requirements.txt
└── README.md
```

## Setup

```bash
cd webapp
pip install -r requirements.txt
```

## Environment Variables

```bash
export API_URL="http://localhost:8001"  # optional, this is default
```

## Running

**Important**: Make sure the Agent API is running first!

```bash
cd webapp
streamlit run app.py
```

Opens at http://localhost:8501

## Usage

1. Select an account from the dropdown
2. Type your question in the text area
3. (Optional) Enable "Stream response" toggle
4. Click "🚀 Ask Agent"
5. View the response

## API Integration

The frontend calls these Agent API endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/accounts` | GET | Fetch account list for dropdown |
| `/api/query` | POST | Non-streaming query |
| `/api/query/stream` | POST | Streaming query (SSE) |
