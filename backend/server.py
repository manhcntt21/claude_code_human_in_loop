import asyncio
import uuid
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Load .env before importing graph (which imports llm, which reads env vars)
load_dotenv()

from .graph import graph  # noqa: E402

# ─────────────────────────────────────────────────────────────────────────────
# Per-thread error tracking (populated by background tasks on failure)
# ─────────────────────────────────────────────────────────────────────────────

_thread_errors: dict[str, str] = {}

# ─────────────────────────────────────────────────────────────────────────────
# App setup
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Human-in-the-Loop Agent API",
    description="Multi-agent content generation system with human review powered by LangGraph + OpenRouter.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────────────────────────────────────────

class StartRequest(BaseModel):
    topic: str


class FeedbackRequest(BaseModel):
    thread_id: str
    action: str              # "approve" | "revise"
    feedback_text: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Background graph runners
# ─────────────────────────────────────────────────────────────────────────────

async def _run_graph(topic: str, config: dict) -> None:
    """Start a fresh graph run from the initial state until the first interrupt."""
    thread_id: str = config["configurable"]["thread_id"]
    initial_state = {
        "topic": topic,
        "research_data": "",
        "draft": "",
        "human_feedback": None,
        "revision_count": 0,
        "messages": [],
    }
    try:
        async for _ in graph.astream(initial_state, config, stream_mode="values"):
            pass  # Runs until interrupt_before=["human_review"] fires
    except Exception as exc:
        print(f"[Graph] Error during initial run: {exc}")
        _thread_errors[thread_id] = str(exc)  # expose via /state; do NOT re-raise


async def _resume_graph(config: dict) -> None:
    """Resume a previously interrupted graph run (after human feedback is set)."""
    thread_id: str = config["configurable"]["thread_id"]
    try:
        async for _ in graph.astream(None, config, stream_mode="values"):
            pass  # Runs until next interrupt or END
    except Exception as exc:
        print(f"[Graph] Error during resume: {exc}")
        _thread_errors[thread_id] = str(exc)  # expose via /state; do NOT re-raise


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/start")
async def start(request: StartRequest):
    """
    Initialise a new content-generation session.
    Kicks off the Researcher → Writer pipeline in the background.
    Returns a thread_id the frontend uses for all subsequent calls.
    """
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    # Fire-and-forget: graph runs until interrupt_before=["human_review"]
    asyncio.create_task(_run_graph(request.topic, config))

    return {"thread_id": thread_id}


@app.get("/state/{thread_id}")
async def get_state(thread_id: str):
    """
    Return current graph state for the given thread.
    Status values:
      - "starting"     → graph not yet checkpointed (still spinning up)
      - "running"      → researcher / writer is currently executing
      - "interrupted"  → paused before human_review; draft is ready for review
      - "finished"     → graph completed (approved or max revisions reached)
      - "error"        → background task failed; see the "error" field for details
    """
    config = {"configurable": {"thread_id": thread_id}}

    # Surface any background-task exception immediately
    if thread_id in _thread_errors:
        return {
            "draft": "",
            "status": "error",
            "revision_count": 0,
            "research_data": "",
            "error": _thread_errors[thread_id],
        }

    try:
        state = await graph.aget_state(config)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # No checkpoint yet (graph still starting up)
    if not state or not state.values:
        return {
            "draft": "",
            "status": "starting",
            "revision_count": 0,
            "research_data": "",
        }

    next_nodes = state.next  # tuple of node names waiting to execute

    if "human_review" in next_nodes:
        status = "interrupted"
    elif not next_nodes:
        status = "finished"
    else:
        status = "running"

    return {
        "draft": state.values.get("draft", ""),
        "status": status,
        "revision_count": state.values.get("revision_count", 0),
        "research_data": state.values.get("research_data", ""),
    }


@app.post("/feedback")
async def feedback(request: FeedbackRequest):
    """
    Submit human feedback for the interrupted graph.

    action="approve"  → marks content as approved; graph runs to END.
    action="revise"   → injects feedback_text; graph re-runs the Writer.
    """
    config = {"configurable": {"thread_id": request.thread_id}}

    if request.action == "approve":
        await graph.aupdate_state(config, {"human_feedback": "__APPROVED__"})
        asyncio.create_task(_resume_graph(config))
        return {"status": "approved", "message": "Content approved. Finalising…"}

    elif request.action == "revise":
        if not request.feedback_text or not request.feedback_text.strip():
            raise HTTPException(
                status_code=400,
                detail="feedback_text is required for action='revise'.",
            )
        await graph.aupdate_state(
            config, {"human_feedback": request.feedback_text.strip()}
        )
        asyncio.create_task(_resume_graph(config))
        return {"status": "revising", "message": "Revision requested. Writer is working…"}

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown action '{request.action}'. Use 'approve' or 'revise'.",
        )


@app.get("/health")
async def health():
    return {"status": "ok"}
