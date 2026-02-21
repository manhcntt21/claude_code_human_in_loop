from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import AgentState
from .nodes import researcher_node, writer_node, human_review_node


# ─────────────────────────────────────────────────────────────────────────────
# Routing logic
# ─────────────────────────────────────────────────────────────────────────────

def route_human_review(state: AgentState) -> str:
    """
    Conditional edge called AFTER human_review_node executes.
    Decides whether to end the graph or send the draft back to the Writer.
    """
    feedback = state.get("human_feedback")
    revision_count = state.get("revision_count", 0)

    if feedback == "__APPROVED__":
        print("[Router] Content approved → END")
        return "end"

    if revision_count >= 5:
        print(f"[Router] Max revisions reached ({revision_count}) → END")
        return "end"

    if not feedback:
        # Should not happen in normal flow; end gracefully.
        print("[Router] No feedback found → END")
        return "end"

    print(f"[Router] Revision requested (count={revision_count}) → writer")
    return "writer"


# ─────────────────────────────────────────────────────────────────────────────
# Graph construction
# ─────────────────────────────────────────────────────────────────────────────

# Single shared MemorySaver — persists all thread state in memory.
_memory = MemorySaver()


def create_graph():
    workflow = StateGraph(AgentState)

    # Register nodes
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("human_review", human_review_node)

    # Sequential flow: researcher → writer → human_review
    workflow.set_entry_point("researcher")
    workflow.add_edge("researcher", "writer")
    workflow.add_edge("writer", "human_review")

    # After human_review: either END or back to writer for revision
    workflow.add_conditional_edges(
        "human_review",
        route_human_review,
        {
            "end": END,
            "writer": "writer",
        },
    )

    # Compile with MemorySaver checkpointing.
    # Graph pauses BEFORE executing "human_review", waiting for human input.
    return workflow.compile(
        checkpointer=_memory,
        interrupt_before=["human_review"],
    )


# Module-level singleton — shared across all API requests.
graph = create_graph()
