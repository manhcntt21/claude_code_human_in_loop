import os
from dotenv import load_dotenv
from langchain_openrouter import ChatOpenRouter

load_dotenv()


def get_llm() -> ChatOpenRouter:
    """
    Returns a ChatOpenAI instance configured for OpenRouter.
    CRITICAL: Uses ChatOpenAI (not standard OpenAI classes) with OpenRouter's base URL.
    """
    return ChatOpenRouter(
        model=os.getenv("MODEL_NAME", "google/gemini-2.0-flash-001"),
    )
