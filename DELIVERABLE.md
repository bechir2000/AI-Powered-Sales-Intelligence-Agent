# How to run
Open **three terminals**:

**Terminal 1 - MCP Server:**
```bash
cd mcp_server
python3 -m venv .venv
source .venv/bin/activate  # or: .venv\Scripts\Activate.ps1 on Windows Powershell
pip install -r requirements.txt
python3 server.py
# Running on http://localhost:8002
```

**Terminal 2 - Agent API:**
```bash
cd agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 api.py
# Running on http://localhost:8001
```

**Terminal 3 - Web App:**
```bash
cd webapp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
# Opens http://localhost:8501
```

# Identified Issues in the Initial System

During analysis, several high-impact limitations were identified:

## 1. Fixed Execution Plan:
The agent always fetched **all transcripts and all emails**, regardless of the user query.

**Example:**

User: "What is the latest email?"

System: Fetches ALL emails + ALL transcripts

Result: Long wait times and high token costs

## 2. No Query Understanding
The agent had no mechanism to understand user intent or determine which data sources were actually needed.

## 3. Inefficient Data Loading
Complete datasets with full content were loaded even for trivial queries that only needed metadata (dates, subjects, summaries).

## 4. No Out-of-Scope Handling
Unrelated queries like "Who are you?" still triggered expensive MCP tool calls unnecessarily.

## 5. Simulated Streaming
The streaming endpoint waited for the complete response, then artificially chunked it.

# Implemented Improvements

## 0. Agent Graph Refactor (Router Node)
The agent graph was refactored to explicitly separate **routing**, **retrieval**, and **answer generation** into distinct nodes:

START → router → supervisor → final_answer → END
          └────────────► final_answer (out-of-scope) → END

- **Router node**: Interprets the user query and produces a structured retrieval specification.
- **Supervisor node**: Executes MCP tool calls based on the routing decision.
- **Final answer node**: Generates the response using the retrieved context (or directly for out-of-scope queries).

## 1. Query-Aware Routing (LLM + Deterministic Fallback)

A dedicated **router node** was introduced at the start of the agent graph.
This node analyzes the user query and produces a structured retrieval specification that determines:
- whether transcripts are needed
- whether emails are needed
- Whether metadata-only mode is sufficient
- Whether the query is out-of-scope (no MCP calls needed)

### Routing Strategy

**Primary: LLM-Based Routing**
- For ambiguous queries
- Contextual understanding
- Graceful degradation if LLM fails

**Fallback: Regex-Based Routing**
- Pattern matching for clear queries
- Handles common patterns
- Zero latency, zero cost

### Impact Examples
Prompt: "What is the latest email received?"

**Before:**
→ Fetch ALL transcripts + ALL emails

**After:**
→ Fetch only latest email (metadata only)

**Benefits:** Significantly reduced token usage, faster response times, and lower costs per query.


## 2. Metadata-Only Mode

Introduced `metadata_only` parameter to avoid fetching full content when not needed.
### What is Metadata?

**For Transcripts:** Date, call name, summary, CRM fields (without full transcript text)  
**For Emails:** Date, subject (without email content)

## Examples

**Metadata-Only Query:**

Prompt: "What are the last 2 emails received ?"

→ Returns: Date + Subject only

Prompt: "How many emails received in August 2025 ?"

-> Returns only metadata (date and subject) of the emails of August 2025.

**Full Content Query:**

Prompt: "What is the content of the last 2 emails?"

→ Returns: Date + Subject + Full content

**Benefits:** Dramatic token reduction for list/count queries and maintaining accuracy.

## 3. Out-of-scope Query handling
The router identifies queries unrelated to account interaction history and routes them
directly to the final answer node, completely skipping data retrieval.

**Examples:**

"Who are you?" → Direct response, no MCP calls

"What's the weather?" → Out-of-scope message

"Tell me a joke" → Direct response

**Benefits:** Eliminates unnecessary MCP calls, and prevents wasted API costs.


## 4. True Token-Level Streaming

### Problem with Initial Implementation

The streaming endpoint used **fake streaming**:
1. Wait for complete response (several seconds)
2. Chunk the finished text
3. Send chunks rapidly

### Solution
Implemented true streaming using LangGraph's `astream_events()`
In some cases, the UI may occasionally stall.

# What I Would Do With More Time

## 1. RAG-Based Retrieval (Semantic Search)

**Problem:** Current routing (regex + LLM) may miss semantically similar queries.

**Example Scenarios Where RAG Would Excel:**

### Semantic Query Understanding
**Query:** "What did the client say about budget constraints?"
- **Current approach:** Might miss something, if budget constraints are mentioned in an email, but it is not the main subject of the email.
- **RAG approach:** Semantic embeddings capture meaning regardless of exact wording

**Query:** "Show me discussions about technical integration challenges"
- **Current approach:** returns all discussions, then the LLM analyses them to extract the technical challenges.
- **RAG approach:** Finds relevant chunks mentioning "API setup issues", "NetSuite connection problems"...


## 2. Memory and Caching
Users often ask follow-up questions about the same data, triggering redundant MCP calls.
The idea is to introduce a cache to avoid redundant MCP calls.

**Example:**
- User asks "Show me emails from last week" (fetches 10 emails)
- User follows up "What was the subject of the third one?" (currently re-fetches same 10 emails)

## 3. Evaluation and Quality Monitoring

To systematically evaluate the agent’s behavior, I would introduce an automated evaluation layer using tools such as **DeepEval**.

This would allow us to:
- Validate that routing decisions select the correct data sources (emails vs transcripts).
- Measure answer quality against expected outputs for a curated set of queries.
- Detect regressions when changing prompts, models, or routing logic.

Example evaluation dimensions:
- **Faithfulness**: Does the model avoid hallucinating information not present in the data?
- **Routing accuracy**: Did the router avoid unnecessary data retrieval?
- **Cost efficiency**: Tokens consumed per query (before vs after optimizations).

# How would I make it production-ready?

## 1. Formatting output of MCP
**Problem:** Raw MCP outputs can be verbose, consuming unnecessary tokens in the final LLM prompt.

**Solution:**
- Keep MCP outputs structured (JSON).
- Add a lightweight "formatter/compactor" step in the agent before the final LLM call
to format the output, so that the LLM in the final node consumes less tokens.

**Example:** Raw JSON output might be 500 tokens, compacted bullet format could be 150 tokens.

## 2. Smart retrieval
As we mentioned before, when we get a bigger dataset in production, the smart thing is to go with RAG method.
When we are dealing with +100 accounts with its different emails and transcripts, instead of returning whole emails and transcripts with their metadata, we just return the snippet or the part of the email or transcript that is related to the prompt.

## 3. Add rate/cost control
To prevent runaway costs, we implement multiple control layers. 

At the user level, we enforce reasonable query limits per minute and hourly token budgets to prevent consuming excessive resources. 

At the query level, cap the maximum context size and response length (like capping `top_k`). 

Budget monitoring should track spending and trigger alerts when approaching monthly allocations, automatically enabling cost-saving measures like switching to more efficient models or forcing metadata-only mode when necessary.

## 4. Observability and monitoring
**Metrics to Track:**
  - Token usage (router, MCP, final LLM)
  - Cache hit rate (if caching implemented)
  - Queries per minute
  - Average tokens per query
  - Cost per query (token cost + compute)

## 5. Security & Safety

**Problem:** In production environments, unrestricted access to account data poses significant security and compliance risks.
**Solution:** Implement authentication and authorization controls.
- All API requests should require valid API key validation. Implement role-based access control to restrict which users can query which accounts.
- Maintain audit trails tracking who accessed what data and when for compliance requirements.
- 
