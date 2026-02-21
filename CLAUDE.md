# **Project Specification: Human-in-the-Loop Agent Team (OpenRouter Edition)**

## **1\. Project Goal**

Build a functional Human-in-the-Loop (HITL) system where a team of AI Agents performs a task, pauses for human review, and resumes based on feedback.

* **Role:** You are a Senior Python Architect.  
* **Focus:** Clean architecture, separation of concerns, and working code.

## **2\. Tech Stack**

* **Backend:** FastAPI (Python 3.10+).  
* **Orchestration:** LangGraph (latest version).  
* **Frontend:** Streamlit (for rapid UI prototyping).  
* **LLM Provider:** **OpenRouter**.  
  * Implementation: Use langchain\_openai.ChatOpenAI but configured with OpenRouter's base URL.  
* **State Management:** langgraph.checkpoint.memory.MemorySaver.

## **3\. Architecture Design & Agent Roles**

### **A. The Shared State (AgentState)**

To ensure effective task division, the agents must share a structured state. Define this in backend/state.py:

from typing import TypedDict, List, Optional, Annotated  
from langgraph.graph.message import add\_messages

class AgentState(TypedDict):  
    topic: str              \# The initial user input  
    research\_data: str      \# Output from Researcher  
    draft: str              \# Output from Writer  
    human\_feedback: Optional\[str\]     \# Input from Human  
    revision\_count: int     \# To prevent infinite loops  
    messages: List\[dict\]    \# Conversation history (optional, for debug)

### **B. The Agent Team (Roles & Prompts)**

Define these in backend/nodes.py. The graph is **Sequential**: Researcher \-\> Writer \-\> Human.

1. **Model Configuration (backend/llm.py)**:  
   * **CRITICAL:** Initialize the LLM using ChatOpenAI. Do NOT use standard OpenAI classes.  
   * **Code Snippet**:  
     from langchain\_openai import ChatOpenAI  
     import os

     def get\_llm():  
         return ChatOpenAI(  
             base\_url="\[https://openrouter.ai/api/v1\](https://openrouter.ai/api/v1)",  
             api\_key=os.getenv("OPENROUTER\_API\_KEY"),  
             model=os.getenv("MODEL\_NAME", "google/gemini-2.0-flash-001") \# Default cost-effective model  
         )

2. **Agent 1: The Researcher**  
   * **Role:** Search for comprehensive information about the topic.  
   * **Task:** Use a search tool (Tavily/DuckDuckGo). If no tool is available, mock the search with detailed placeholder data to prevent crashing.  
   * **Output:** Updates the research\_data key in the state.  
   * **Prompt:** "You are a Lead Researcher. Analyze the request: {topic}. Gather key facts, statistics, and trends. Do not write the final article, just provide structured notes."  
3. **Agent 2: The Writer**  
   * **Role:** Create a polished draft based **only** on the research\_data.  
   * **Task:** If human\_feedback exists, revise the previous draft. If not, write a new one.  
   * **Output:** Updates the draft key in the state.  
   * **Prompt:** "You are a Senior Editor. Write a blog post based on the provided research notes. If feedback exists: {human\_feedback}, you must revise the draft accordingly."  
4. **The Human Node (The "Manager")**  
   * This is a virtual node or interrupt point.  
   * **Logic:** The graph **MUST** interrupt *after* the Writer node completes using interrupt\_before=\["human\_review\_node"\] or interrupt\_after=\["writer"\].

### **C. The API (backend/server.py)**

Must provide REST endpoints to interact with the graph.

* **CORS:** Must be enabled for \* (allow all origins).  
* **Endpoints**:  
  1. POST /start: Input {topic}. Initializes graph using MemorySaver. Returns thread\_id.  
  2. GET /state/{thread\_id}: Returns the current draft, status (waiting/finished), and revision\_count.  
  3. POST /feedback: Accepts {thread\_id, action, feedback\_text}.  
     * **Action "approve":** The graph ends.  
     * **Action "revise":** Updates human\_feedback in state \-\> Resumes graph (routes back to Writer).

### **D. The Frontend (frontend/app.py)**

* **UI Flow**:  
  1. User enters Topic \-\> Calls /start.  
  2. UI polls /state/{thread\_id} every 2 seconds.  
  3. When status is interrupted (meaning Agent has finished writing):  
     * Show the draft in a Markdown box.  
     * Show "Approve" button (Green).  
     * Show "Request Changes" text area \+ button (Red).  
  4. If "Request Changes" is clicked \-\> Calls /feedback \-\> UI goes back to polling (waiting for Writer to revise).

## **4\. Implementation Rules**

1. **Directory Structure**:  
   /project-root  
   ├── /backend  
   │   ├── llm.py         \# OpenRouter configuration (Single source of truth for LLM)  
   │   ├── graph.py       \# Graph definitions  
   │   ├── nodes.py       \# Agent logic & Prompts  
   │   ├── state.py       \# TypedDict  
   │   ├── server.py      \# FastAPI app  
   │   └── tools.py       \# Search tool wrapper  
   ├── /frontend  
   │   └── app.py         \# Streamlit UI  
   ├── requirements.txt  
   └── .env.example

2. **Environment Variables**:  
   * OPENROUTER\_API\_KEY: Your OpenRouter Key.  
   * MODEL\_NAME: e.g., google/gemini-2.0-flash-001, anthropic/claude-3.5-sonnet.  
   * TAVILY\_API\_KEY (optional).