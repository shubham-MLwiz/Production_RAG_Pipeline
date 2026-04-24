# Production-Grade RAG System for PDF Knowledge Bases

> **Goal:** Build a production-ready Retrieval-Augmented Generation (RAG) system that ingests one or more PDFs, indexes them offline, and serves grounded, auditable answers through a secure, observable runtime API.
>
> This README is intentionally written as an **implementation spec** for GitHub Copilot (or a human developer) to scaffold the codebase and fill in the details.

---

## 1) What this project is

This project implements a **production-grade RAG system** with:

- **Strong input and output security**
- **Multi-turn conversational memory and query rewriting**
- **Semantic caching** to skip repeated work
- **Intent routing** for different query types and prompt strategies
- **Hybrid retrieval** (dense + sparse) with reranking
- **Self-grading retrieval / corrective RAG loop**
- **Citation enrichment** with source section/page grounding
- **Observability and tracing** across every stage
- **Offline indexing pipeline** for PDF ingestion and re-indexing
- **Evaluation framework** with golden datasets and LLM-as-judge

Primary use case for initial implementation:

- Ingest **one PDF**
- Chunk, embed, and index it offline
- Serve answers over an API
- Return **grounded responses with citations**
- Refuse gracefully when evidence is insufficient

---

## 2) High-level architecture

The system has **two major planes**:

### A. Runtime Query Pipeline
Handles user queries in real time.

### B. Offline Data Indexing Pipeline
Prepares documents for retrieval independently of query-time latency.

---

## 3) Functional requirements

### 3.1 Input Security
Before any user content touches the model:

- Full input sanitization
- Prompt injection detection
- Role hijacking detection
- System prompt leak protection
- Request normalization and policy checks

### 3.2 Conversational Memory
Support multi-turn conversations by:

- Storing recent turns in a sliding window memory
- Rewriting follow-up questions into **standalone queries**
- Preserving relevant context without overloading prompts

### 3.3 Semantic Cache
For repeated or near-duplicate questions:

- Search a semantic cache before full pipeline execution
- If cache hit is above threshold, return cached response with metadata
- If cache miss, continue through normal pipeline and optionally cache result

### 3.4 Intent Routing
Classify incoming queries and route to the best prompt / retrieval strategy.

Examples of intents:

- **factual_qa** — answer directly from retrieved evidence
- **summary** — summarize part or all of the document
- **compare** — compare sections or entities in the PDF
- **extract** — extract specific facts/fields/tables
- **procedural** — answer workflow / step-based questions
- **unknown** — safe fallback strategy

### 3.5 Hybrid Retrieval
Use multiple retrieval signals:

- Dense retrieval using embeddings
- Sparse retrieval using BM25 / keyword search
- Reciprocal Rank Fusion (RRF) or weighted fusion
- Metadata filtering
- Optional entity / section filtering
- Cross-encoder reranking for final ordering

### 3.6 Self-Grading Retrieval (Corrective RAG)
The system must evaluate whether retrieved evidence is sufficient.

Decision logic:

1. **Fully answered** → generate final response
2. **Partially answered / gaps detected** → decompose, re-retrieve, merge context, then generate
3. **Insufficient evidence** → refuse honestly and gracefully

### 3.7 Citation Enrichment
Every factual claim should be grounded to retrievable evidence:

- Page number
- Chunk / section identifier
- Source file name
- Snippet or exact supporting span when feasible

### 3.8 Output Security
Before returning a response:

- PII redaction where needed
- Unsafe request refusal
- Hallucination / unsupported-claim checks
- Response validation and schema validation

### 3.9 Observability
Capture tracing and metrics for every stage:

- request received
- input guard result
- rewrite result
- cache hit/miss
- router decision
- retriever candidates
- reranker output
- grading decision
- generation latency
- final response validation

### 3.10 Evaluation
Maintain an evaluation framework with:

- Golden datasets
- Ground truth answers / expected citations
- Offline regression evaluation
- Multiple LLM judges where appropriate
- Triangulated scoring (answer quality, faithfulness, citation quality, refusal correctness)

---

## 4) End-to-end flow

### 4.1 Runtime query pipeline

Recommended runtime flow:

1. **Input Guard**
   - Sanitize text
   - Detect injection attempts, role hijacking, jailbreak patterns
   - Block or mark unsafe content

2. **Conversation Memory / Query Rewriting**
   - Convert follow-up question into standalone query
   - Use recent conversation window

3. **Semantic Cache Lookup**
   - Check whether a semantically similar question was answered already
   - Return cached answer if confidence threshold is met

4. **Intent Router**
   - Classify query into intent class
   - Select retrieval strategy, prompt template, and answer style

5. **Hybrid Retrieval**
   - Dense vector retrieval
   - Sparse BM25 retrieval
   - Fuse results
   - Apply metadata/entity filters

6. **Reranker**
   - Cross-encoder rescoring for top-k candidates

7. **CRAG / Retrieval Grading**
   - Grade retrieval quality and evidence sufficiency
   - If sufficient → generate answer
   - If ambiguous → decompose query, re-retrieve, merge evidence
   - If insufficient → refuse gracefully

8. **Generation**
   - Use intent-specific prompt
   - Generate concise answer grounded in evidence

9. **Citation Enrichment**
   - Attach page/section/source citations to claims or paragraphs

10. **Output Guard**
   - Validate content
   - Redact PII if required
   - Refuse unsafe outputs
   - Ensure only supported claims are returned

11. **Response**
   - Return answer + citations + trace metadata (internal or debug mode)

---

### 4.2 Offline data indexing pipeline

Recommended offline indexing flow:

1. **Raw Document Intake**
   - Accept PDF (initial target), optionally DOCX/HTML/TXT/MD later

2. **Format Detection + Routing**
   - Route by MIME type / extension

3. **Extraction**
   - Prefer text-layer extraction for machine-readable PDFs
   - OCR fallback for scanned PDFs
   - Preserve page number and section metadata
   - Attempt table-aware extraction where possible

4. **Preprocessing**
   - Clean whitespace
   - Normalize Unicode
   - Remove headers/footers/boilerplate where identifiable
   - Preserve structural markers such as headings and page boundaries

5. **Deduplication / Canonicalization**
   - Hash chunks and avoid duplicate storage
   - Maintain document version hashes for reindexing

6. **Chunking**
   - Create semantically coherent chunks
   - Preserve page spans and section lineage
   - Recommended chunk size: 400–900 tokens with overlap tuned empirically

7. **Embedding**
   - Generate dense embeddings for each chunk

8. **Sparse Index Build**
   - Tokenize and index chunk text for BM25 or equivalent sparse search

9. **Payload / Metadata Indexing**
   - Store:
     - document_id
     - source_file
     - page_number_start / end
     - section_title
     - chunk_id
     - chunk_text
     - content_hash
     - created_at
     - version

10. **Index Publication**
   - Publish to vector DB and sparse retrieval layer
   - Mark active dataset version

---

## 5) Repository structure

Below is the intended structure inferred from the image and extended for implementation clarity.

```text
production-rag-system/
├── app/
│   ├── main.py                     # FastAPI entrypoint, startup/shutdown hooks, CORS, health
│   ├── config.py                   # Settings, environment variables, model/provider config
│   ├── models.py                   # Pydantic request/response schemas
│   └── Dockerfile                  # Runtime container image
│
├── routes/
│   ├── query.py                    # Main /api/query endpoint
│   ├── search.py                   # Retrieval debug/search endpoint
│   └── health.py                   # Readiness/liveness/dependency checks
│
├── services/
│   ├── rag_pipeline.py             # End-to-end runtime orchestration
│   ├── semantic_cache.py           # Semantic cache lookup and write-back
│   ├── conversation.py             # Conversation memory, history window, query rewriting
│   ├── query_router.py             # Intent classification and prompt strategy selection
│   ├── document_grader.py          # Grades retrieval sufficiency / corrective RAG decisioning
│   └── query_decomposer.py         # Break ambiguous queries into sub-questions
│
├── retrieval/
│   ├── hybrid_retriever.py         # Dense + sparse retrieval fusion
│   ├── reranker.py                 # Cross-encoder reranking
│   ├── filters.py                  # Metadata/entity/date filters
│   └── citation_mapper.py          # Maps answer spans to source citations
│
├── agents/
│   ├── crag.py                     # Corrective RAG loop
│   └── adaptive_router.py          # Advanced routing / tool use decisions
│
├── tools/
│   ├── vector_search.py            # Qdrant wrapper
│   ├── web_search.py               # Optional future extension (disabled by default)
│   └── code_search.py              # Optional future extension for code corpora
│
├── prompts/
│   ├── __init__.py
│   ├── templates.py                # Prompt templates by intent
│   ├── grading.py                  # Judge / grading prompts
│   ├── safety.py                   # Input/output guard prompts (if LLM-assisted)
│   └── rewrite.py                  # Query rewriting prompts
│
├── security/
│   ├── input_guard.py              # Sanitization, prompt injection detection, role hijack checks
│   ├── content_filter.py           # Policy checks and unsafe request handling
│   └── output_guard.py             # Output validation, PII redaction, unsupported claim checks
│
├── pipeline/
│   ├── ingest.py                   # Offline ingestion orchestration
│   ├── extractors/
│   │   ├── pdf_extractor.py        # Text-layer PDF extraction
│   │   ├── html_extractor.py       # Optional future support
│   │   ├── docx_extractor.py       # Optional future support
│   │   ├── image_extractor.py      # OCR wrapper for scanned pages
│   │   └── text_extractor.py       # Plain text fallback
│   ├── preprocessor.py             # Cleanup, normalization, boilerplate stripping
│   ├── deduplicator.py             # Content hashing and duplicate detection
│   ├── chunker.py                  # Semantic / recursive chunking
│   ├── embedder.py                 # Embedding generation
│   ├── indexer.py                  # Writes to vector + sparse indexes
│   └── dataset_registry.py         # Dataset versions and activation
│
├── evaluation/
│   ├── golden/                     # Gold questions/answers/citations
│   ├── runners/                    # Offline evaluation scripts
│   ├── judges/                     # LLM judge wrappers
│   └── metrics.py                  # Faithfulness, recall, answer quality, refusal quality
│
├── observability/
│   ├── tracing.py                  # OpenTelemetry / structured tracing
│   ├── logging.py                  # JSON logging helpers
│   └── metrics.py                  # Prometheus metrics or equivalent
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── data/
│   ├── raw/                        # Input documents (local dev only)
│   ├── processed/                  # Intermediate parsed artifacts
│   └── samples/
│
├── scripts/
│   ├── ingest_pdf.py               # CLI to ingest a single PDF
│   ├── reindex.py                  # CLI for reindexing
│   └── eval.py                     # CLI for evaluation runs
│
├── docker-compose.yml              # Local development dependencies
├── docker-compose.prod.yml         # Production compose reference
├── pyproject.toml                  # Python dependencies and tooling
├── .env.example                    # Example environment variables
└── README.md
```

---

## 6) Core runtime contracts

### 6.1 Query request schema

```json
{
  "query": "What does the policy say about document retention?",
  "conversation_id": "optional-session-id",
  "message_id": "optional-message-id",
  "top_k": 8,
  "filters": {
    "document_id": "optional-doc-id",
    "page_range": [1, 20],
    "section": "optional-section-title"
  },
  "debug": false
}
```

### 6.2 Query response schema

```json
{
  "answer": "The document states that records must be retained for 7 years...",
  "citations": [
    {
      "source_file": "example.pdf",
      "document_id": "doc_001",
      "page_start": 12,
      "page_end": 12,
      "section_title": "Retention Policy",
      "chunk_id": "chunk_12_03",
      "snippet": "Records must be retained for 7 years..."
    }
  ],
  "status": "answered",
  "intent": "factual_qa",
  "cache": {
    "hit": false,
    "score": 0.0
  },
  "trace_id": "uuid",
  "safety": {
    "input_blocked": false,
    "output_redacted": false
  }
}
```

Possible `status` values:

- `answered`
- `refused_insufficient_evidence`
- `refused_unsafe_request`
- `needs_clarification`

---

## 7) Suggested technology stack

These choices align with the image and are practical defaults for a production implementation.

#### 7.1 API / application layer
- **FastAPI** for the backend API
- **Pydantic** for request/response validation
- **Uvicorn / Gunicorn** for serving

#### 7.2 Retrieval and storage
- **Qdrant** for vector storage and payload indexes
- **BM25 / sparse retrieval layer** (can be local BM25, Elasticsearch/OpenSearch, or Qdrant sparse if desired)
- **Redis** for semantic cache and sliding conversation memory

#### 7.3 Messaging / tracing
- **Kafka or Redpanda** for trace/event streaming (optional but useful for larger systems)
- If that is too heavy for v1, start with structured logs and OpenTelemetry only

#### 7.4 LLM / embedding layer
- LLM provider abstraction supporting at least one provider
- Embedding model abstraction
- Cross-encoder reranker model

#### 7.5 Frontend
- Optional **Streamlit** or **React** frontend
- Keep frontend decoupled from runtime API

#### 7.6 Deployment
- Dockerized services
- Health checks
- Non-root containers
- GPU optional for OCR / reranker / local model serving

---

## 8) Recommended implementation details

### 8.1 Input guard design

Implement `security/input_guard.py` with checks for:

- Prompt injection patterns
- Role hijack phrases such as “ignore previous instructions”
- Attempts to reveal system prompt or hidden chain-of-thought
- Malformed or adversarial Unicode / control characters
- Overly long or suspicious requests

Return:

```python
class InputGuardResult(BaseModel):
    allowed: bool
    reasons: list[str]
    normalized_query: str
    risk_score: float
```

If `allowed == False`, short-circuit with safe refusal.

---

### 8.2 Conversation memory

Implement in `services/conversation.py`:

- Store recent conversation turns in Redis by `conversation_id`
- Limit to a configurable sliding window (e.g., last 5–10 turns)
- Rewrite follow-up questions into standalone questions before retrieval
- Persist both original and rewritten forms for debugging

---

### 8.3 Semantic cache

Implement in `services/semantic_cache.py`:

- Compute embedding for rewritten query
- Compare against cached question embeddings
- On hit above threshold, return cached answer if:
  - source dataset version matches
  - answer policy/version matches
  - cached answer not expired

Cache key metadata should include:

- normalized query
- query embedding
- answer
- citations
- model version
- dataset version
- created_at / ttl

---

### 8.4 Intent router

Implement `services/query_router.py` with a lightweight classifier.

The router output should include:

```python
class RouteDecision(BaseModel):
    intent: str
    prompt_template: str
    retrieval_mode: str
    use_decomposition: bool
    confidence: float
```

Possible retrieval modes:

- `hybrid_default`
- `summary_heavy`
- `precise_extraction`
- `section_scoped`

---

### 8.5 Hybrid retriever

Implement `retrieval/hybrid_retriever.py`:

1. Dense search against Qdrant
2. Sparse search against BM25 / equivalent
3. Reciprocal Rank Fusion or weighted fusion
4. Metadata filtering
5. Return top-N candidates

Output contract:

```python
class RetrievedChunk(BaseModel):
    chunk_id: str
    document_id: str
    source_file: str
    text: str
    page_start: int
    page_end: int
    section_title: str | None = None
    dense_score: float | None = None
    sparse_score: float | None = None
    fused_score: float | None = None
```

---

### 8.6 Reranker

Implement `retrieval/reranker.py`:

- Input: query + retrieved candidates
- Output: reranked top-k chunks with `rerank_score`
- Keep both pre-rerank and post-rerank rankings for observability

---

### 8.7 Retrieval grader / CRAG

Implement `services/document_grader.py` and `agents/crag.py`:

The grader should classify the retrieval result into:

- `correct`
- `ambiguous`
- `insufficient`

Behavior:

- `correct` → answer generation
- `ambiguous` → query decomposition + re-retrieve + merge context
- `insufficient` → graceful refusal

A decomposition loop may:

- break a question into sub-questions
- retrieve evidence for each sub-question
- merge and deduplicate evidence
- re-grade merged evidence

---

### 8.8 Citation enrichment

Implement `retrieval/citation_mapper.py`:

- Every retrieved chunk must carry page + section metadata
- During generation, track which chunks were used
- Attach citations at paragraph level or claim group level
- Prefer exact supporting spans/snippets where feasible

Target format:

```text
Answer paragraph... [Source: example.pdf, p.12, “Retention Policy”]
```

or structured JSON as shown earlier.

---

### 8.9 Output guard

Implement `security/output_guard.py` with:

- PII redaction
- Unsupported claim detection
- Safe refusal for prohibited content
- Schema validation
- Optional answer length / formatting normalization

If unsupported claims are detected, either:

- revise the answer from evidence only, or
- refuse with `refused_insufficient_evidence`

---

### 8.10 Observability

Instrument each stage with:

- `trace_id`
- start/end timestamps
- duration_ms
- selected model / retriever config
- top_k values
- cache hit/miss
- grader outcome
- refusal reason if any

Recommended logs:

```json
{
  "trace_id": "...",
  "stage": "hybrid_retrieval",
  "duration_ms": 84,
  "dense_k": 20,
  "sparse_k": 20,
  "final_k": 8,
  "document_ids": ["doc_001"]
}
```

---

## 9) Offline indexing for a single PDF (initial v1 scope)

This repository should support a simple initial workflow for **one PDF**.

### 9.1 CLI usage

```bash
python scripts/ingest_pdf.py --file ./data/raw/example.pdf --document-id doc_001
```

Expected behavior:

1. Detect file format
2. Extract text page by page
3. OCR only if text layer is missing
4. Clean and normalize text
5. Chunk into retrieval units
6. Generate embeddings
7. Build/update sparse index
8. Upsert chunks + metadata into Qdrant
9. Register dataset version

---

### 9.2 Minimum metadata to preserve

Each chunk must keep:

- `document_id`
- `source_file`
- `page_start`
- `page_end`
- `section_title` (if detected)
- `chunk_id`
- `chunk_text`
- `token_count`
- `content_hash`
- `dataset_version`

---

### 9.3 Chunking recommendations for PDFs

For a PDF-focused implementation:

- Respect page boundaries
- Preserve heading hierarchy when possible
- Avoid splitting tables across chunks unless necessary
- Use overlap to keep context continuity
- Keep chunk sizes relatively stable for good reranking behavior

Suggested defaults:

- `chunk_size_tokens = 700`
- `chunk_overlap_tokens = 120`
- `top_k_retrieve = 20`
- `top_k_rerank = 8`

These values should remain configurable.

---

## 10) API endpoints

### 10.1 `POST /api/query`
Main RAG endpoint.

Behavior:

- secure input
- rewrite query
- semantic cache lookup
- route intent
- retrieve/rerank/grade
- generate cited answer
- output validation

### 10.2 `POST /api/search`
Debug / retrieval inspection endpoint.

Returns:

- rewritten query
- dense candidates
- sparse candidates
- fused ranking
- reranked results
- grader decision

### 10.3 `GET /health/live`
Liveness probe.

### 10.4 `GET /health/ready`
Readiness probe checking dependencies:

- vector DB reachable
- Redis reachable
- model backend reachable

---

## 11) Configuration

Provide `.env.example` with variables such as:

```env
APP_ENV=dev
APP_PORT=8000
LOG_LEVEL=INFO

VECTOR_DB_URL=http://qdrant:6333
VECTOR_COLLECTION=rag_chunks

REDIS_URL=redis://redis:6379/0

LLM_PROVIDER=openai
LLM_MODEL=gpt-4.1-mini
EMBEDDING_MODEL=text-embedding-3-large
RERANK_MODEL=BAAI/bge-reranker-base

CACHE_SIMILARITY_THRESHOLD=0.93
MAX_CHAT_HISTORY_TURNS=8
TOP_K_RETRIEVE=20
TOP_K_RERANK=8
CHUNK_SIZE_TOKENS=700
CHUNK_OVERLAP_TOKENS=120

ENABLE_OCR_FALLBACK=true
ENABLE_WEB_SEARCH=false
ENABLE_DEBUG_ENDPOINTS=true
```

Keep provider-specific secrets in environment variables or a secret manager.

---

## 12) Suggested implementation plan

### Phase 1 — Thin vertical slice
Implement the smallest useful version:

- PDF ingestion for one file
- extraction → chunking → embedding → indexing
- `/api/query`
- dense retrieval only
- cited generation
- basic refusal on insufficient evidence

### Phase 2 — Production core
Add:

- input/output guards
- Redis memory
- semantic cache
- hybrid retrieval (dense + sparse)
- reranker
- observability and tracing

### Phase 3 — Corrective RAG
Add:

- retrieval grading
- query decomposition
- re-retrieval loop
- improved citation mapping

### Phase 4 — Evaluation & hardening
Add:

- golden datasets
- automated regression evaluation
- load testing
- failure injection
- deployment hardening

---

## 13) Acceptance criteria

The implementation should satisfy the following:

### Ingestion
- Can ingest at least one PDF end-to-end
- Preserves page metadata for all chunks
- Re-indexing the same file does not create uncontrolled duplicates

### Retrieval
- Returns relevant chunks for factual questions
- Uses hybrid retrieval and reranking when enabled
- Supports metadata filtering by document and page range

### Generation
- Answers only from retrieved evidence
- Returns citations for factual claims
- Refuses when evidence is insufficient

### Security
- Blocks obvious prompt injection and role hijacking attempts
- Prevents system prompt leakage
- Applies output validation and PII redaction where configured

### Observability
- Every query has a trace ID
- Logs capture per-stage latency and decisions
- Debug endpoint exposes retrieval internals safely in non-prod mode

### Evaluation
- Golden test set can be executed offline
- Reports answer quality, faithfulness, citation correctness, and refusal correctness

---

## 14) Testing strategy

### Unit tests
Cover:

- input guard behavior
- query rewriting logic
- cache hit/miss logic
- fusion scoring
- reranking adapter
- citation mapping
- output guard

### Integration tests
Cover:

- ingest one PDF and query it end-to-end
- insufficient-evidence refusal flow
- semantic cache short-circuit
- ambiguous query → decomposition loop

### E2E tests
Cover:

- containerized local deployment
- health checks
- query latency sanity checks

---

## 15) Suggested developer notes for Copilot

GitHub Copilot should implement this repository with the following design principles:

1. **Strong typing everywhere** using Pydantic/dataclasses
2. **Provider abstraction** for LLM, embeddings, reranker, cache, and vector DB
3. **No stage should be tightly coupled** to a specific vendor
4. **All stages are observable** with structured logs and trace IDs
5. **All user-facing answers must be grounded** in retrieved evidence
6. **Safe refusal is a first-class output**, not an error case
7. **Offline indexing and runtime query serving are decoupled**
8. **Config-driven behavior**, not hardcoded constants
9. **Every module should be independently testable**
10. **Graceful fallback behavior** when OCR, reranker, or external services are unavailable

---

## 16) Example answer style

Desired answer characteristics:

- concise but complete
- directly answers the question first
- includes citations
- clearly distinguishes evidence from inference
- refuses honestly if evidence is missing

Example:

```text
The policy requires records to be retained for 7 years from the date of creation. It also states that records related to ongoing litigation must be preserved until the matter is closed. [Source: policy.pdf, p.12, “Retention Policy”]
```

Example refusal:

```text
I could not find sufficient evidence in the indexed document to answer that confidently. Please provide another source document or narrow the question to a specific section/page range.
```

---

## 17) Future extensions

Not required for v1, but the architecture should allow:

- multi-document corpora
- tenant isolation / multi-user auth
- table extraction improvements
- image-aware PDF understanding
- web search augmentation
- knowledge graph enrichment
- human feedback loops
- active learning for evaluation gaps
- streaming responses
- frontend chat UI

---

## 18) Assumptions and inferred details

The image provided a strong blueprint, but several details were not fully explicit. The following assumptions were made while drafting this README:

1. **Vector database** is assumed to be **Qdrant** because the image explicitly mentions Qdrant.
2. **Cache and conversational memory** are assumed to use **Redis** because the image references Redis for HNSW semantic cache and sliding window memory.
3. **Tracing/event system** is assumed to be **Kafka/Redpanda-like** because the image mentions a trace store / session logs / latency tracking component, but the exact product name is not fully clear from the image.
4. **API framework** is assumed to be **FastAPI** because the image explicitly mentions FastAPI.
5. **Frontend** is assumed optional and decoupled (Streamlit/React) because the image mentions frontend choices but the core system does not require them.
6. **Sparse retrieval** is described as **BM25 or equivalent** because the image implies dense + BM25 + RRF fusion, but the exact sparse engine is not fully specified.
7. **Reranking** is assumed to use a **cross-encoder** because the image explicitly references cross-encoder rescoring.
8. **Corrective RAG / CRAG loop** is modeled as `correct / ambiguous / insufficient` because that decisioning appears in the runtime flow diagram.
9. **OCR fallback** is assumed for scanned PDFs because the image mentions OCR fallback / text-layer-first extraction.
10. **Evaluation** is expanded beyond the image using the supporting text you provided (golden datasets, multiple LLM judges, triangulated results).
11. **Security layers** are expanded from your supporting text into distinct input and output guards because that separation is important in production systems.
12. **Single-PDF v1 scope** was added intentionally so GitHub Copilot can implement a usable first version quickly before generalizing to multi-document corpora.
13. **Module names and file names** were normalized for implementation clarity where the image text was too small or partially ambiguous.
14. **Exact model names** are intentionally left configurable rather than hardcoded.

---

## 19) Clarifications that would improve the final implementation

If you want a more exact version of this README, please provide any of the following details:

1. Your preferred **LLM provider(s)**
2. Your preferred **embedding model**
3. Your preferred **reranker model**
4. Whether you want **local models** or **hosted APIs**
5. Whether sparse retrieval should be **BM25 in-process**, **Elasticsearch/OpenSearch**, or another system
6. Whether citations should be **paragraph-level**, **sentence-level**, or **chunk-level**
7. Whether the system should support **streaming responses** in v1
8. Whether the initial document is **text PDF**, **scanned PDF**, or mixed

---

## 20) Build target for Copilot

**Implementation target:** Create a working v1 of this repository that ingests a single PDF and exposes `/api/query` with grounded, cited answers, hybrid retrieval hooks, security guards, observability scaffolding, and an extensible architecture for a full production-grade RAG system.
