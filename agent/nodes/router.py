import re
from typing import Any, Dict, Optional, Tuple
from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate

from config import LLM_PROVIDER, FINAL_ANSWER_MODEL, AgentState

# ---------------------------
# LLM Router
# ---------------------------
class RetrievalSpec(BaseModel):
    use_transcripts: bool
    use_emails: bool
    metadata_only: bool = True
    start_date: Optional[str] = None  # YYYY-MM-DD
    end_date: Optional[str] = None    # YYYY-MM-DD
    top_k: Optional[int] = None       # most recent K
    out_of_scope: bool = False


def get_llm():
    """Get the LLM based on the configured provider."""
    if LLM_PROVIDER == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=FINAL_ANSWER_MODEL, temperature=0, streaming=True)
    else:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=FINAL_ANSWER_MODEL, temperature=0, streaming=True)


def route_sources(user_query: str) -> Tuple[bool, bool]:
    """
    Decide which sources to fetch based on keywords.
    Returns: (needs_transcripts, needs_emails)

    Fail-open rule:
      - If unsure, fetch BOTH.
    """
    q = (user_query or "").lower()

    # Strong email indicators
    email_patterns = [
        r"\bemail(s)?\b",
        r"\bmail(s)?\b",
        r"\binbox\b",
        r"\bsubject\b",
        r"\bfollow[- ]?up\b",
        r"\breply|replied|respond(ed|ing)?\b",
        r"\bwrote\b",
        r"\bmessage(s)?\b",
    ]

    # Strong call/transcript indicators
    call_patterns = [
        r"\bcall(s)?\b",
        r"\bmeeting(s)?\b",
        r"\bdemo\b",
        r"\bdiscovery\b",
        r"\btranscript(s)?\b",
        r"\brecording(s)?\b",
        r"\bwhat was said\b",
        r"\bdiscuss(ed|ion|ing)?\b",
        r"\bpain point(s)?\b",
        r"\bobjection(s)?\b",
    ]

    email_hit = any(re.search(p, q) for p in email_patterns)
    call_hit = any(re.search(p, q) for p in call_patterns)

    if email_hit and not call_hit:
        return (False, True)
    if call_hit and not email_hit:
        return (True, False)

    # Ambiguous or no keywords -> fetch both (safe)
    return (True, True)

ROUTER_PROMPT = """You are a routing assistant. Convert the user query into a retrieval plan for MCP tools.

Tools:
- transcripts(account_id, start_date?, end_date?, top_k?, metadata_only?)
- emails(account_id, start_date?, end_date?, top_k?, metadata_only?)

Rules:
- If query is about calls/meetings/demos/what was said -> use_transcripts=true
- If query is about emails/messages/subject/agreement/contract -> use_emails=true
- If the question is not about the account interaction history, out_of_scope=true, set use_transcripts=false, use_emails=false
- If ambiguous/broad -> use both
- Default metadata_only=true (smaller payload)
- If user asks for verbatim/quotes/full text -> metadata_only=false

Time constraint interpretation (IMPORTANT):
  * If user mentions ANY time period (month, week, date range, "last X days", "since Y", etc.):
    - Convert to start_date and/or end_date in YYYY-MM-DD format
    - Examples:
      • "last month" → start_date="2025-11-01", end_date="2025-11-30"
      • "last week" → start_date="2025-12-11", end_date="2025-12-18"
      • "since December 1st" → start_date="2025-12-01", end_date=null
      • "in November" → start_date="2025-11-01", end_date="2025-11-30"
      • "between Dec 1 and Dec 15" → start_date="2025-12-01", end_date="2025-12-15"
  
  * "latest/most recent" queries without specific time periods:
    - Use top_k instead of dates
    - Example: "latest email" → top_k=1, no dates
  
  * If NO time constraint mentioned at all:
    - Keep start_date=null, end_date=null, top_k=null
    - Example: "what are the pain points" → no time filters

CRITICAL: Prefer start_date/end_date for explicit time periods. Use top_k only for "latest N items" without date context.

Return ONLY a JSON object matching:
{{
  "use_transcripts": true/false,
  "use_emails": true/false,
  "metadata_only": true/false,
  "start_date": "YYYY-MM-DD" or null,
  "end_date": "YYYY-MM-DD" or null,
  "top_k": number or null
  "out_of_scope": true/false
}}
"""

def llm_route(user_query: str) -> RetrievalSpec:
    prompt = ChatPromptTemplate.from_messages(
        [("system", ROUTER_PROMPT), ("human", "{q}")]
    )
    llm = get_llm().with_structured_output(RetrievalSpec)
    return (prompt | llm).invoke({"q": user_query})


def sanitize(spec: RetrievalSpec) -> RetrievalSpec:
    # clamp top_k
    if spec.top_k is not None:
        try:
            spec.top_k = max(1, min(int(spec.top_k), 10))
        except (TypeError, ValueError):
            spec.top_k = None

    # simple ISO date validation
    iso = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    if spec.start_date and not iso.match(spec.start_date):
        spec.start_date = None
    if spec.end_date and not iso.match(spec.end_date):
        spec.end_date = None
    return spec

def router_node(state: AgentState) -> Dict[str, Any]:
    """
    Main router node that determines the optimal data retrieval strategy.
    
    This is the first node in the agent graph. It analyzes the user query
    and produces a retrieval specification that guides subsequent data fetching.
    """
    user_query = state["user_query"]

    try:
        spec = sanitize(llm_route(user_query))
        print("[router] source=llm ", spec)
    except Exception:
        need_transcripts, need_emails = route_sources(user_query)
        spec = RetrievalSpec(
            use_transcripts=need_transcripts,
            use_emails=need_emails,
            metadata_only=True,
        )
        print("[router] source=static ", spec)
    # store as a dictionary
    return {"retrieval_spec": spec.model_dump()}