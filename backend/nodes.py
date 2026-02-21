from .state import AgentState
from .llm import get_llm
from .tools import search


# ─────────────────────────────────────────────────────────────────────────────
# Agent 1 – Researcher
# ─────────────────────────────────────────────────────────────────────────────

def researcher_node(state: AgentState) -> dict:
    """
    Gathers information about the topic and stores structured research notes
    in the `research_data` key of the state.
    """
    llm = get_llm()
    topic = state["topic"]

    print(f"[Researcher] Researching topic: {topic}")

    search_results = search(topic)

    prompt = f"""You are a Lead Researcher. Analyze the following request: {topic}

Here is the available research data gathered from external sources:
{search_results}

Based on this information, produce well-structured research notes that include:
1. Key Facts – the most important factual points about the topic.
2. Important Statistics – quantitative data, figures, market sizes, growth rates.
3. Current Trends – what is happening right now in this space.
4. Key Insights – deeper observations or expert opinions.
5. Potential Article Angles – 2-3 compelling directions for the final article.

Do NOT write the article itself. Only provide organised research notes.
Be comprehensive, accurate, and specific."""

    response = llm.invoke(prompt)
    research_data = response.content

    print(f"[Researcher] Research complete ({len(research_data)} chars)")

    return {
        "research_data": research_data,
        "messages": state.get("messages", [])
        + [{"role": "researcher", "content": research_data}],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Agent 2 – Writer
# ─────────────────────────────────────────────────────────────────────────────

def writer_node(state: AgentState) -> dict:
    """
    Writes (or revises) a blog-post draft based on research_data.
    If human_feedback is present (and not the approval sentinel), it revises
    the previous draft according to that feedback.
    """
    llm = get_llm()
    topic = state["topic"]
    research_data = state.get("research_data", "")
    human_feedback = state.get("human_feedback")
    draft = state.get("draft", "")
    revision_count = state.get("revision_count", 0)

    print(f"[Writer] Writing draft (revision_count={revision_count})")

    if human_feedback and human_feedback != "__APPROVED__":
        # ── Revision mode ──────────────────────────────────────────────────
        prompt = f"""You are a Senior Editor. You have received feedback on your draft and must revise it.

Topic: {topic}

Research Notes:
{research_data}

Previous Draft:
{draft}

Human Feedback: {human_feedback}

Please revise the draft to fully address the feedback provided.
Maintain a professional, engaging tone and keep the article well-structured.
Format the output in Markdown with proper headings and sections."""
        revision_count += 1
    else:
        # ── Initial draft mode ─────────────────────────────────────────────
        prompt = f"""You are a Senior Editor. Write a comprehensive blog post based on the research notes below.

Topic: {topic}

Research Notes:
{research_data}

Write a well-structured, engaging blog post that:
1. Opens with a compelling introduction that hooks the reader.
2. Covers all key aspects from the research with clear headings.
3. Incorporates relevant statistics and facts naturally.
4. Includes practical takeaways or insights for the reader.
5. Closes with a strong conclusion summarising the key points.

Format the output in Markdown. Aim for ~600–900 words."""

    response = llm.invoke(prompt)
    new_draft = response.content

    print(f"[Writer] Draft complete ({len(new_draft)} chars)")

    return {
        "draft": new_draft,
        "revision_count": revision_count,
        "messages": state.get("messages", [])
        + [{"role": "writer", "content": new_draft}],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Human Review Node (virtual interrupt point)
# ─────────────────────────────────────────────────────────────────────────────

def human_review_node(state: AgentState) -> dict:
    """
    Virtual node representing the human review step.

    The graph is compiled with interrupt_before=["human_review"], so execution
    PAUSES before this node runs.  After the human provides feedback via the
    API (updating `human_feedback` in state), the graph resumes and this node
    executes — it is a no-op; all routing logic lives in the conditional edge.
    """
    print(f"[Human Review] Routing with feedback: {state.get('human_feedback', 'none')}")
    return {}
