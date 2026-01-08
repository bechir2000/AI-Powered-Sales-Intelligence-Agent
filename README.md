# ML Engineer Technical Test

Welcome to the Modjo ML Engineer technical test. This test evaluates your ability to **optimize and design AI agents**.

## 🎯 Objective

You are provided with a working but basic agent system. Your goal is to **improve, optimize, and extend** it while demonstrating your ML engineering skills.

---

## 📐 Architecture Overview

The system consists of three services:

```
┌─────────────────┐     HTTP      ┌─────────────────┐     MCP       ┌─────────────────┐
│    Web App      │ ────────────► │     Agent       │ ────────────► │   MCP Server    │
│   (Streamlit)   │               │    (FastAPI)    │               │   (FastMCP)     │
│   Port 8501     │ ◄──────────── │   Port 8001     │ ◄──────────── │   Port 8002     │
└─────────────────┘               └─────────────────┘               └─────────────────┘
       UI                           LangGraph Agent                   Data Tools
```

### 1. Web App (`/webapp`)
- Streamlit frontend
- Account selection dropdown
- Query input field
- Supports both streaming and non-streaming responses

### 2. Agent (`/agent`)
- FastAPI backend exposing the agent
- LangGraph-based agent with two nodes:
  - **Supervisor**: Deterministic orchestrator that fetches data via MCP tools
  - **Final Answer**: GPT-4o-mini generates the response based on retrieved context
- Uses a **fixed plan** to fetch all transcripts and emails

### 3. MCP Server (`/mcp_server`)
- FastMCP server using `streamable_http` transport
- Provides two tools:
  - `transcripts`: Retrieves call transcripts for an account
  - `emails`: Retrieves emails for an account

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### 1. Set Environment Variables

```bash
# For OpenAI (default)
export OPENAI_API_KEY="your-openai-api-key"

# For Google Gemini (alternative)
export GOOGLE_API_KEY="your-google-api-key"
export LLM_PROVIDER="google"  # Set to "google" to use Gemini, defaults to "openai"
```

### 2. Run All Services

Open **three terminals**:

**Terminal 1 - MCP Server:**
```bash
cd mcp_server
source .venv/bin/activate  # or: uv run
python server.py
# Running on http://localhost:8002
```

**Terminal 2 - Agent API:**
```bash
cd agent
source .venv/bin/activate
python api.py
# Running on http://localhost:8001
```

**Terminal 3 - Web App:**
```bash
cd webapp
source .venv/bin/activate
streamlit run app.py
# Opens http://localhost:8501
```

### 3. Test the System

1. Open http://localhost:8501 in your browser
2. Select an account from the dropdown
3. Enter a question (e.g., "What are the main pain points discussed?")
4. Click "Ask Agent"

---

## 📊 Dataset Format

Account data files are JSON with this structure:

```json
{
  "tenant_name": "string",
  "account_name": "string",
  "account_id": 123,
  "calls": [
    {
      "date": "2024-01-15",
      "call_name": "Discovery Call",
      "transcript": "...",
      "summary": "...",
      "crm_fields": [{"key": "value"}]
    }
  ],
  "emails": [
    {
      "date": "2024-01-16",
      "subject": "Follow-up",
      "content": "..."
    }
  ]
}
```

---

## 🔑 LLM Access

You have access to the following models:

| Provider | Models | Notes |
|----------|--------|-------|
| **OpenAI** | All models (GPT-4o, GPT-4o-mini, etc.) | Budget limit: $250 |
| **Google** | All Gemini models | Via GCP project |

Your API keys will be provided separately and deleted after the test.

---

## 📁 Project Structure

```
ml-eng-hiring/
├── README.md              # This file
├── agent/
│   ├── api.py             # FastAPI server
│   ├── main.py            # Agent entry point
│   ├── graph.py           # LangGraph definition
│   ├── config.py          # Configuration & state
│   ├── requirements.txt
│   ├── README.md
│   └── nodes/
│       ├── supervisor.py  # Orchestrator node
│       └── final_answer.py # LLM response node
├── mcp_server/
│   ├── server.py          # MCP server
│   ├── requirements.txt
│   ├── README.md
│   └── data/              # Account JSON files
└── webapp/
    ├── app.py             # Streamlit app
    ├── requirements.txt
    └── README.md
```

---

## 📝 Deliverables

### Required

1. **Working Code**: Your improved version of the system
2. **README**: Clear instructions on how to run your code and reproduce outputs
3. **Explanation**: Document your changes and reasoning

### Questions to Address

1. **What would you do if you had more time for the implementation?**

2. **How would you make it production-ready?**

---

## ⚠️ Notes

- The current implementation is intentionally basic - it's your starting point
- Focus on demonstrating your ML engineering skills
- Quality over quantity - well-documented small improvements beat messy large ones
- Ask questions if something is unclear

Good luck! 🚀

