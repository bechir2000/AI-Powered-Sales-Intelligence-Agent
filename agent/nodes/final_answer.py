# pylint: disable=line-too-long
"""
Final Answer Node

This node receives the user query and retrieved context,
then uses GPT-4o-mini to generate the final response.
"""

from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate

import sys

sys.path.append("..")
from config import FINAL_ANSWER_MODEL, AgentState, LLM_PROVIDER


def get_llm():
    """Get the LLM based on the configured provider."""
    if LLM_PROVIDER == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=FINAL_ANSWER_MODEL, temperature=0, streaming=True)
    else:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=FINAL_ANSWER_MODEL, temperature=0, streaming=True)


# System prompt for the final answer LLM
FINAL_ANSWER_SYSTEM_PROMPT = """You are a helpful assistant that answers questions about accounts based on their interaction history.

You have access to the following context about the account:

## Transcripts (Call recordings)
{transcripts}

## Emails
{emails}

Based on this context, answer the user's question accurately and concisely.
If the information needed to answer the question is not available in the context, say so clearly.
When possible, cite the supporting item by mentioning its date and title (email subject or call name).
"""


def final_answer_node(state: AgentState) -> Dict[str, Any]:
    """
    Final answer node - generates the response using GPT-4o-mini.

    This node:
    1. Receives the user query and retrieved context from state
    2. Constructs a prompt with the context
    3. Calls GPT-4o-mini to generate the final answer

    Args:
        state: The current agent state with context

    Returns:
        Updated state with the final response
    """
    user_query = state["user_query"]
    context = state["context"]

    # Prepare the context strings
    transcripts_str = (
        context.transcripts if context.transcripts else "No transcripts available."
    )
    emails_str = context.emails if context.emails else "No emails available."

    # Create the prompt
    prompt = ChatPromptTemplate.from_messages(
        [("system", FINAL_ANSWER_SYSTEM_PROMPT), ("human", "{user_query}")]
    )

    # Initialize the LLM
    llm = get_llm()

    # Create the chain
    chain = prompt | llm

    # Generate the response
    response = chain.invoke(
        {"transcripts": transcripts_str, "emails": emails_str, "user_query": user_query}
    )

    return {"final_response": response.content}
