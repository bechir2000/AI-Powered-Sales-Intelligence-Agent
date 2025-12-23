# pylint: disable=line-too-long
"""
Agent Main Entry Point

This module provides the main interface to run the agent.
"""

from typing import Optional
from pydantic import BaseModel

from graph import agent
from config import AgentState, RetrievedContext

from typing import AsyncGenerator


class AgentInput(BaseModel):
    """Input schema for the agent."""

    user_query: str
    account_id: int


class AgentOutput(BaseModel):
    """Output schema for the agent."""

    response: str


def run_agent(user_query: str, account_id: int) -> str:
    """
    Run the agent with the given user query and account ID.

    Args:
        user_query: The user's question
        account_id: The account ID to query data for

    Returns:
        The agent's response as a string
    """
    # Initialize the state
    initial_state = {
        "user_query": user_query,
        "account_id": account_id,
        "messages": [],
        "plan": None,
        "context": RetrievedContext(),
        "final_response": "",
    }

    # Run the agent
    result = agent.invoke(initial_state)

    return result["final_response"]


async def run_agent_streaming(user_query: str, account_id: int) -> AsyncGenerator[str, None]:
    """
    Run the agent and stream tokens as they are produced by the final LLM node.
    """
    initial_state = {
        "user_query": user_query,
        "account_id": account_id,
        "messages": [],
        "plan": None,
        "context": RetrievedContext(),
        "final_response": "",
    }

    async for event in agent.astream_events(initial_state):
        # We only forward LLM token chunks from the final answer node
        if event.get("event") == "on_chat_model_stream":
            # Check if this event is from the final_answer node
            metadata = event.get("metadata", {})
            langgraph_node = metadata.get("langgraph_node", "")
            
            if langgraph_node != "final_answer":
                continue
            chunk = event.get("data", {}).get("chunk")
            if chunk is None:
                continue

            content = getattr(chunk, "content", None)
            if content is not None:
                yield content


def main():
    """Main function for testing the agent."""
    import argparse

    parser = argparse.ArgumentParser(description="Run the ML Engineer Agent")
    parser.add_argument("--query", "-q", type=str, required=True, help="User query")
    parser.add_argument(
        "--account-id", "-a", type=int, required=True, help="Account ID"
    )

    args = parser.parse_args()

    print(f"Running agent with query: {args.query}")
    print(f"Account ID: {args.account_id}")
    print("-" * 50)

    response = run_agent(args.query, args.account_id)

    print("Response:")
    print(response)


if __name__ == "__main__":
    main()
