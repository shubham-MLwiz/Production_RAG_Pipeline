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

---

## Step 3 — PDF upload endpoint

### What I added
- `POST /upload` route in `app/main.py` that accepts a single PDF file via multipart form upload
- Extension validation — returns HTTP 400 if the uploaded file is not a `.pdf`
- Saves the file to `data/raw/` using `shutil.copyfileobj` (streaming, no full file in memory)
- Returns `filename`, `saved_to` path, and `size_bytes` read back from disk after writing

### Why this matters
The entire RAG pipeline begins here. Before any text can be extracted, chunked, embedded, or indexed, a PDF must land on disk in a known location. Every step from Step 4 onwards reads files from `data/raw/`.

### Files changed
- `app/main.py`: added `shutil`, `Path`, `HTTPException`, and `UploadFile` imports; added `RAW_DATA_DIR` constant with `mkdir` guard; added the `upload_pdf` function registered at `POST /upload`

### How I tested
- Started the server with `uvicorn app.main:app --reload --port 8000`
- Used Swagger UI at `http://localhost:8000/docs` to upload a real PDF and confirmed a 200 response with `filename`, `saved_to`, and `size_bytes`
- Ran `ls data/raw/` and confirmed the PDF appeared on disk
- Uploaded a `.txt` file and confirmed a 400 response with `"Only .pdf files are accepted."`
- Tested via `curl -X POST http://localhost:8000/upload -F "file=@/path/to/file.pdf"` and confirmed the JSON response

### Notes to future me
- The filename is taken directly from `file.filename` — if two PDFs share the same name the second will overwrite the first; a deduplication strategy (e.g. UUID prefix) can be added later
- `RAW_DATA_DIR` is a hard-coded `Path` constant for now; it will eventually be read from `.env` via a config module
- `shutil.copyfileobj` streams the upload in chunks so large PDFs do not blow up memory
- Next step: read the saved PDF with `pypdf`, extract text page by page, and write a JSON file with one entry per page

---

## Step 4 — Extract text from a text PDF

### What I added
- `pipeline/extractor.py` — reads a PDF page by page using `pypdf` and returns a list of `{"page": N, "text": "..."}` dicts; also writes the result to `data/extracted/<stem>.json`
- `POST /extract/{filename}` endpoint in `app/main.py` — receives a filename, looks it up in `data/raw/`, calls the extractor, and returns page count plus output path

### Why this matters
Text extraction is the first real transformation in the RAG pipeline. Before this step the PDF is just an opaque binary file. After this step the text is in a structured, human-readable JSON format that every subsequent step (chunking, embedding, indexing) can consume. Storing it as JSON means you can inspect what the model will actually see without running any more code.

### Files changed
- `pipeline/extractor.py`: created — `extract_text_from_pdf(pdf_path)` opens the PDF with `PdfReader`, iterates pages with 1-based numbering, calls `page.extract_text()`, strips whitespace, builds the list, and writes `data/extracted/<stem>.json`
- `app/main.py`: added import of `extract_text_from_pdf`; added `POST /extract/{filename}` route with `.pdf` extension check and 404 guard for missing files

### How I tested
- Started FastAPI with `uvicorn app.main:app --reload --port 8000`
- Uploaded a real multi-page PDF via `POST /upload` using Swagger UI at `http://localhost:8000/docs`
- Called `POST /extract/{filename}` from Swagger UI (used the "Try it out" feature to avoid URL-encoding issues with spaces in the filename)
- Confirmed response showed correct `pages_extracted` count and `output_file` path
- Opened `data/extracted/<stem>.json` and verified the array contained one entry per page with readable text
- Tested the 404 path by trying to extract a filename that had not been uploaded yet
- Tested the 400 path by passing a non-`.pdf` filename

### Notes to future me
- `pypdf` only extracts the text layer baked into the PDF — scanned/image PDFs will return empty strings; OCR is a future step
- Spaces in PDF filenames require URL-encoding (`%20`) in curl; Swagger UI handles this automatically and is the easiest way to test endpoints with spaces in path parameters
- The JSON file on disk is the hand-off point to Step 5 — the chunker will read from `data/extracted/`
- `EXTRACTED_DIR` is hard-coded; it will eventually move to a config module alongside `RAW_DATA_DIR`
- Next step: split each page's text into overlapping chunks and save them as `data/chunks/<stem>.json`

---

## Step 5 — Chunk extracted text

### What I added
- `pipeline/chunker.py` — splits extracted page text into fixed-size, overlapping word-level chunks; each chunk carries its source page number and a global `chunk_index`; writes output to `data/chunks/<stem>.json`
- `POST /chunk/{filename}` endpoint in `app/main.py` — accepts a PDF filename, resolves the stem, calls `chunk_extracted_file`, and returns total chunk count and output path
- Also switched the PDF extraction library from `pypdf` to **PyMuPDF (`fitz`)** after discovering that `pypdf` merges words in character-spaced PDFs; PyMuPDF correctly reconstructs spaces and handles tables natively

### Why this matters
Embedding models and LLMs have token-length limits — a full PDF page can exceed them. Splitting into small, overlapping chunks means each unit fits inside the model's context window. The overlap (50 words by default) prevents a meaningful sentence from being cut cleanly at a chunk boundary. Attaching the page number to every chunk is what will make chunk-level citations possible later.

### Files changed
- `pipeline/chunker.py`: created — `_split_into_chunks(text, chunk_size, overlap)` slides a word-level window across the text; `chunk_extracted_file(stem)` loads `data/extracted/<stem>.json`, calls the splitter per page, accumulates a flat chunk list with a global `chunk_index`, and writes `data/chunks/<stem>.json`; constants `CHUNK_SIZE=200` and `CHUNK_OVERLAP=50` are at the top of the file for easy tuning
- `app/main.py`: added import of `chunk_extracted_file`; added `POST /chunk/{filename}` route with `.pdf` extension guard and `FileNotFoundError` → HTTP 404 conversion
- `pipeline/extractor.py`: replaced `pypdf` (`PdfReader` / `page.extract_text()`) with `pymupdf` (`fitz.open()` / `page.get_text("text")`) to fix merged-word output
- `pyproject.toml`: replaced `pypdf>=4.2.0` with `pymupdf>=1.24.0`

### How I tested
- Ran `POST /extract/test_file.pdf` via Swagger UI after switching to pymupdf; confirmed words in `data/extracted/test_file.json` were properly spaced
- Ran `POST /chunk/test_file.pdf` via Swagger UI; confirmed response showed `total_chunks: 1129` for a 544-page PDF (well above 1 chunk/page ratio, confirming chunking is working correctly)
- Inspected `data/chunks/test_file.json` and confirmed consecutive chunks share the last ~50 words, `page` numbers advance correctly, and no chunk exceeds ~200 words
- Ran extraction and chunking directly in Python via `.venv/bin/python3 -c "..."` — confirmed 544 pages extracted and 1129 chunks produced
- Tested the 404 error path by calling `/chunk/nonexistent.pdf`

### Notes to future me
- **PDF library comparison** — three libraries were evaluated during this step:
  - `pypdf`: simplest API, but merges words in character-spaced PDFs (no spaces reconstructed) — not usable for this document type
  - `pdfplumber`: better than `pypdf` for spacing, but table detection is heuristic and fragile with borderless or complex tables
  - `pymupdf (fitz)`: best overall — uses the C-based MuPDF engine, correctly reconstructs character-spaced text, preserves multi-column reading order, and has native table detection via `page.find_tables()` (v1.23+); AGPL license is acceptable for non-commercial use; **this is now the project standard**
- `CHUNK_SIZE=200` and `CHUNK_OVERLAP=50` are word-count-based; 200 words ≈ 250–300 tokens, safely within any local embedding model's limit; these can be tuned in `chunker.py` without touching other files
- `chunk_index` is a global counter across all pages, not per-page — this means every chunk has a unique ID which will be important when upserting into Qdrant
- Next step: call Ollama's local embedding model once per chunk and save the resulting vectors alongside chunk metadata
