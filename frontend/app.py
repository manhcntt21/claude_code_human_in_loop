import time

import requests
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

BACKEND_URL = "http://localhost:8000"

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Human-in-the-Loop AI Agent",
    page_icon="🤖",
    layout="wide",
)

# ─────────────────────────────────────────────────────────────────────────────
# Session state initialisation
# ─────────────────────────────────────────────────────────────────────────────

defaults = {
    "thread_id": None,
    "status": None,
    "draft": "",
    "revision_count": 0,
    "polling": False,
    "topic": "",
    "error": None,
    "graph_error": None,   # error message from a failed background graph task
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────

def api_start(topic: str) -> bool:
    try:
        resp = requests.post(f"{BACKEND_URL}/start", json={"topic": topic}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        st.session_state.thread_id = data["thread_id"]
        st.session_state.topic = topic
        st.session_state.status = "starting"
        st.session_state.polling = True
        st.session_state.draft = ""
        st.session_state.revision_count = 0
        st.session_state.error = None
        return True
    except Exception as exc:
        st.session_state.error = f"Failed to start: {exc}"
        return False


def api_poll() -> None:
    try:
        resp = requests.get(
            f"{BACKEND_URL}/state/{st.session_state.thread_id}", timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        st.session_state.status = data["status"]
        st.session_state.draft = data.get("draft", "")
        st.session_state.revision_count = data.get("revision_count", 0)
        st.session_state.error = None
        if data["status"] == "error":
            st.session_state.graph_error = data.get("error", "Unknown error")
    except Exception as exc:
        st.session_state.error = f"Polling error: {exc}"


def api_feedback(action: str, feedback_text: str = "") -> bool:
    try:
        payload = {
            "thread_id": st.session_state.thread_id,
            "action": action,
            "feedback_text": feedback_text if action == "revise" else None,
        }
        resp = requests.post(f"{BACKEND_URL}/feedback", json=payload, timeout=10)
        resp.raise_for_status()
        st.session_state.status = "running"
        st.session_state.polling = True
        st.session_state.error = None
        return True
    except Exception as exc:
        st.session_state.error = f"Feedback error: {exc}"
        return False


def reset_session() -> None:
    for key in list(defaults.keys()):
        st.session_state[key] = defaults[key]


# ─────────────────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────────────────

st.title("🤖 Human-in-the-Loop AI Content Generator")
st.caption("A multi-agent system (Researcher + Writer) with human review, powered by OpenRouter & LangGraph")
st.divider()

# ── Error banner ──────────────────────────────────────────────────────────────
if st.session_state.error:
    st.error(st.session_state.error)

# ─────────────────────────────────────────────────────────────────────────────
# STATE: No session — show topic input
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.thread_id is None:
    st.subheader("Start a New Session")
    st.write("Enter a topic and the AI team will research it and produce a draft for your review.")

    topic_input = st.text_input(
        "Topic",
        placeholder="e.g. The impact of AI on healthcare in 2025",
        label_visibility="collapsed",
    )

    if st.button("🚀 Generate Content", type="primary", disabled=not topic_input.strip()):
        if api_start(topic_input.strip()):
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# STATE: Polling — graph is running
# ─────────────────────────────────────────────────────────────────────────────
elif st.session_state.status in ("starting", "running") or st.session_state.polling:
    api_poll()

    current_status = st.session_state.status

    if current_status == "interrupted":
        # Draft is ready — stop polling and re-render in review mode
        st.session_state.polling = False
        st.rerun()
    elif current_status == "finished":
        st.session_state.polling = False
        st.rerun()
    elif current_status == "error":
        st.session_state.polling = False
        st.rerun()
    else:
        # Still running — show spinner and auto-refresh
        col_spin, col_info = st.columns([1, 4])
        with col_spin:
            st.markdown("### ⏳")
        with col_info:
            st.subheader("AI Agents are working…")
            if st.session_state.revision_count == 0:
                st.info(
                    "**Step 1:** Researcher is gathering facts, statistics, and trends.\n\n"
                    "**Step 2:** Writer will draft the article from those notes."
                )
            else:
                st.info(
                    f"**Revision {st.session_state.revision_count}** in progress — "
                    "the Writer is incorporating your feedback."
                )
            st.caption(f"Thread ID: `{st.session_state.thread_id}`")

        time.sleep(2)
        st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# STATE: Interrupted — draft ready for human review
# ─────────────────────────────────────────────────────────────────────────────
elif st.session_state.status == "interrupted":
    # Header row
    header_col, meta_col = st.columns([3, 1])
    with header_col:
        st.subheader("📝 Draft Ready for Your Review")
        st.caption(f'Topic: **{st.session_state.topic}** · Thread: `{st.session_state.thread_id}`')
    with meta_col:
        st.metric("Revisions so far", st.session_state.revision_count)

    st.divider()

    # Display the draft
    with st.container(border=True):
        st.markdown(st.session_state.draft)

    st.divider()
    st.subheader("Your Feedback")

    approve_col, revise_col = st.columns(2)

    with approve_col:
        st.markdown("**Looks good? Approve it.**")
        if st.button("✅  Approve Content", type="primary", use_container_width=True):
            if api_feedback("approve"):
                st.success("Content approved! Finalising…")
                st.rerun()

    with revise_col:
        st.markdown("**Need changes? Describe them below.**")
        feedback_text = st.text_area(
            "Your feedback",
            placeholder="e.g. Make the introduction shorter, add more statistics in section 2…",
            height=120,
            label_visibility="collapsed",
        )
        if st.button(
            "↩️  Request Changes",
            type="secondary",
            use_container_width=True,
            disabled=not feedback_text.strip(),
        ):
            if api_feedback("revise", feedback_text.strip()):
                st.info("Feedback submitted. The Writer is revising the draft…")
                st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# STATE: Error — graph task failed
# ─────────────────────────────────────────────────────────────────────────────
elif st.session_state.status == "error":
    st.subheader("Something went wrong")
    st.error(st.session_state.graph_error or "The background agent task failed.")
    st.caption(
        "Common causes: invalid `OPENROUTER_API_KEY`, selected model temporarily "
        "unavailable (502), or network issue. Check your `.env` and server logs."
    )
    if st.button("🔄  Try Again", type="primary"):
        reset_session()
        st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# STATE: Finished — show final approved content
# ─────────────────────────────────────────────────────────────────────────────
elif st.session_state.status == "finished":
    header_col, meta_col = st.columns([3, 1])
    with header_col:
        st.subheader("✅ Final Approved Content")
        st.caption(f'Topic: **{st.session_state.topic}** · Thread: `{st.session_state.thread_id}`')
    with meta_col:
        st.metric("Total Revisions", st.session_state.revision_count)

    st.divider()

    with st.container(border=True):
        st.markdown(st.session_state.draft)

    st.divider()

    if st.button("🔄  Start New Session", type="primary"):
        reset_session()
        st.rerun()
