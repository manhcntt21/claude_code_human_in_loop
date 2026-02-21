from typing import TypedDict, List, Optional


class AgentState(TypedDict):
    topic: str                       # The initial user input
    research_data: str               # Output from Researcher
    draft: str                       # Output from Writer
    human_feedback: Optional[str]    # Input from Human
    revision_count: int              # To prevent infinite loops
    messages: List[dict]             # Conversation history (for debug)
