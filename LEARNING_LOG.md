# Learning Log — RAG Pipeline

This file records each completed step: what was built, why it matters, what was tested, and what to remember.

---

## Step 0 — Project skeleton only

### What I added
- `pyproject.toml` — project metadata, all runtime and dev dependencies declared in one place
- `.env.example` — documents every environment variable the system will need (no secrets committed)
- `app/`, `pipeline/`, `ui/`, `data/raw/`, `tests/` — empty folders tracked by `.gitkeep` files

### Why this matters
Without a defined folder structure and a `pyproject.toml`, every future file would land in an ad-hoc location. Having the skeleton first means Steps 1–23 can each drop one file into a predictable home. The dependency list in `pyproject.toml` also means anyone can reproduce the environment with a single `pip install -e ".[dev]"`.

### Files changed
- `pyproject.toml`: created — declares project name, Python ≥ 3.11, all runtime dependencies (fastapi, uvicorn, streamlit, pypdf, qdrant-client, httpx, pydantic, python-dotenv, python-multipart), and dev dependencies (pytest, pytest-asyncio)
- `.env.example`: created — documents `OLLAMA_BASE_URL`, `OLLAMA_LLM_MODEL`, `OLLAMA_EMBED_MODEL`, `QDRANT_HOST`, `QDRANT_PORT`, `QDRANT_COLLECTION`, `API_PORT`, `RAW_DATA_DIR`
- `app/.gitkeep`, `pipeline/.gitkeep`, `ui/.gitkeep`, `data/raw/.gitkeep`, `tests/.gitkeep`: created — zero-byte files that force Git to track the otherwise empty directories

### How I tested
- Ran `find . -name ".gitkeep"` and confirmed all five files appeared
- Ran `pip install -e ".[dev]"` and confirmed all packages installed without errors
- Ran `ls app pipeline ui data/raw tests` and confirmed all folders existed

### Notes to future me
- `.env` (the real secrets file) must never be committed — add it to `.gitignore` before Step 1
- The `pyproject.toml` dependency list is intentionally complete for all early steps; nothing needs adding until LangGraph or an evaluation harness
- Next step: create `app/main.py` and boot the FastAPI server

---

## Step 1 — Health-only FastAPI app

### What I added
- `app/main.py` — a minimal FastAPI application with a single `GET /health/live` endpoint that returns `{"status": "ok"}`

### Why this matters
Every future route (upload, query, retrieve, generate) will be added to this same `app` object. Proving the server boots cleanly before adding any logic means the foundation is confirmed working. It also introduces the two key concepts used in every subsequent step: the FastAPI app object and route decorators.

### Files changed
- `app/main.py`: created — imports `FastAPI`, creates the `app` instance with a human-readable title, and registers one GET route at `/health/live`

### How I tested
- Started the server with `uvicorn app.main:app --reload --port 8000`
- Opened `http://localhost:8000/health/live` in the browser and saw `{"status":"ok"}`
- Opened `http://localhost:8000/docs` and saw the Swagger UI listing the health endpoint
- Hit the endpoint with `curl http://localhost:8000/health/live` and confirmed the JSON response

### Notes to future me
- `uvicorn app.main:app` means: file `app/main.py`, object named `app` — the colon separates module path from attribute name
- `--reload` is for development only; remove it in production
- All future routes will be added to this same `app` object in `app/main.py` (or imported routers mounted onto it)
- Next step: create the Streamlit UI shell and verify it can reach the backend

---

## Step 2 — Minimal Streamlit UI shell

### What I added
- `ui/app.py` — a Streamlit page with a title, a backend health check banner (green / red), a question text input, and a placeholder caption for future answer output

### Why this matters
Before wiring real retrieval or generation, verifying that the Streamlit process can reach the FastAPI process over HTTP catches network or port problems early. The text input box with `key="question"` is already set up so future steps can read `st.session_state.question` without changing the widget.

### Files changed
- `ui/app.py`: created — imports `httpx` and `streamlit`, defines `check_backend_health()` which does a 3-second-timeout GET to `/health/live`, then renders a success or error banner, a divider, a text input, and a placeholder caption

### How I tested
- Started FastAPI (`uvicorn app.main:app --reload --port 8000`) and Streamlit (`streamlit run ui/app.py`) in two separate terminals
- Opened `http://localhost:8501` and confirmed the green "Backend is running" banner appeared
- Stopped the FastAPI server, refreshed the Streamlit page, and confirmed the red "Backend is not reachable" banner appeared
- Confirmed the text input box was visible and accepted keyboard input

### Notes to future me
- `BACKEND_URL` is a hard-coded constant for now; it should be read from `.env` (via `pydantic-settings`) once a config module is introduced
- Streamlit reruns the entire script on every interaction — `check_backend_health()` is therefore called on every page load, which is fine for development
- The `key="question"` on the text input is important: it means the value will be accessible as `st.session_state.question` in Step 9 without any widget changes
- Next step: add `POST /upload` to the FastAPI app to accept a PDF file and save it to `data/raw/`
