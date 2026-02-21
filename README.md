
# Claude Code — Human-in-the-Loop

A small example project demonstrating a human-in-the-loop multi-agent content generation system.
The system runs a background LangGraph pipeline (Researcher → Writer), pauses for human review, and then continues to finalise or revise content based on human feedback. The frontend is a Streamlit app that interacts with a FastAPI backend.

## Key features

- Background multi-agent pipeline (Researcher and Writer) powered by LangGraph.
- Human review interrupt: the graph pauses and waits for human approval or revision.
- Simple Streamlit frontend for interacting with the system and submitting feedback.
- FastAPI backend exposing lightweight endpoints to start sessions, poll state, and submit feedback.

## Tech stack

- Python >= 3.11
- FastAPI + Uvicorn (backend)
- Streamlit (frontend)
- LangChain / LangGraph for agent orchestration
- HTTPX / requests for API interaction
- dotenv for environment configuration

Dependencies are declared in `pyproject.toml` and `requirements.txt`.

## Quickstart (macOS / zsh)

1. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the repository root. Minimal example:

```env
# OpenRouter or other provider credentials the project expects
OPENROUTER_API_KEY=your_openrouter_api_key_here
MODEL_NAME=google/gemini-2.0-flash-001
```

4. Run the backend (FastAPI)

```bash
uvicorn backend.server:app --reload --host 0.0.0.0 --port 8000
```

5. Run the frontend (Streamlit)

```bash
streamlit run frontend/app.py
```

Open the Streamlit UI in your browser (usually http://localhost:8501) and use it to start a session. The frontend communicates with the backend at `http://localhost:8000` by default.

## Backend API

The backend exposes these endpoints (see `backend/server.py`):

- POST /start → body: {"topic": "..."}
	- Starts a new session and returns `{ "thread_id": "..." }`.
- GET /state/{thread_id}
	- Returns the current graph state for a thread. Status values: `starting`, `running`, `interrupted`, `finished`, `error`.
- POST /feedback → body: {"thread_id": "...", "action": "approve"|"revise", "feedback_text": "..."}
	- Submit human feedback. `approve` continues to finalize; `revise` injects feedback and resumes revisions.
- GET /health
	- Lightweight health check.

## Project layout

- `main.py` — tiny entrypoint / demo.
- `backend/` — FastAPI app, graph orchestration, LLM wiring.
	- `backend/server.py` — API endpoints and background graph runners.
	- `backend/llm.py` — LLM factory (OpenRouter/ChatOpenRouter usage).
	- `backend/graph.py`, `nodes.py`, `state.py`, `tools.py` — pipeline logic.
- `frontend/app.py` — Streamlit UI that starts sessions, polls state, and submits feedback.

## Environment & configuration

- The code uses `python-dotenv` to load environment variables. Provide keys such as `OPENROUTER_API_KEY` and optionally `MODEL_NAME`.
- `pyproject.toml` indicates Python >= 3.11 and lists core dependencies.

## Troubleshooting

- If Streamlit can't reach the backend, verify `BACKEND_URL` in `frontend/app.py` (defaults to `http://localhost:8000`).
- If the LLM calls fail, confirm `OPENROUTER_API_KEY` and `MODEL_NAME` in `.env`.
- Check backend logs for graph errors: background task exceptions are exposed via the `/state/{thread_id}` response under `error` when status is `error`.

## Development notes

- The backend runs the graph in background asyncio tasks and records per-thread errors in memory. For production use, consider persistent state and robust error monitoring.
- The project uses `uvicorn` for local development. Containerisation or process managers are recommended for production.

## Next steps / suggestions

- Add tests for the graph runner and API endpoints.
- Add CI to perform linting and basic smoke tests (start backend and run a simple start→poll flow).

---

If you'd like, I can also:

- Add a small test script that starts the backend and performs a basic session (start → poll until interrupted). 
- Create an example `.env.example` file and a minimal CONTRIBUTING guide.

Please tell me which extras you'd like and I'll implement them.
