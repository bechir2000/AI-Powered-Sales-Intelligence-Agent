# pylint: disable=line-too-long
"""
Agent Graph Definition

This module defines the LangGraph workflow for the agent.
The graph follows the structure:
    __start__ → supervisor → final_answer → __end__

The supervisor node:
- Uses a pre-determined plan (fetch all transcripts and emails)
- Calls MCP tools directly to retrieve context

The final_answer node:
- Uses GPT-4o-mini to generate the response based on the context
"""

from langgraph.graph import StateGraph, END, START

from config import AgentState
from nodes import supervisor_node, final_answer_node, router_node


def create_agent_graph() -> StateGraph:
    """
    Create and compile the agent graph.

    The graph structure is:
        __start__ → supervisor → final_answer → __end__

    Returns:
        The compiled agent graph
    """

    def route_after_router(state: AgentState) -> str:
        spec = state.get("retrieval_spec") or {}
        if spec.get("out_of_scope"):
            return "final_answer"
        return "supervisor"
    

    # Initialize the graph with our state
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("router", router_node)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("final_answer", final_answer_node)

    # Define the edges
    workflow.add_edge(START, "router")

    workflow.add_conditional_edges(
        "router",
        route_after_router,
        {
            "supervisor": "supervisor",
            "final_answer": "final_answer",
        },
    )
    
    workflow.add_edge("supervisor", "final_answer")

    # final_answer → END
    workflow.add_edge("final_answer", END)

    # Compile the graph
    graph = workflow.compile()

    return graph


# Create the agent instance
agent = create_agent_graph()
