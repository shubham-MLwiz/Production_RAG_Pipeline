---
description: Implement exactly one learning step in the smallest possible way
agent: agent
---

Implement exactly one step from `LEARNING_PATH.md`.

## Primary goal
Make the **smallest possible change** that advances the project by exactly one learning step.

## Rules
- Work only on the **smallest incomplete step** from `LEARNING_PATH.md` unless I explicitly name a different step.
- Keep this step tiny. If the step is too large, split it into smaller sub-steps automatically.
- Modify at most **3-4 files** unless absolutely necessary.
- Explain the step before coding.
- Explain the code after coding.
- Do **not** scaffold future steps.
- Do **not** add optional abstractions not needed for this step.
- Avoid clever abstractions in code.
- Keep orchestration custom and simple.
- Do not introduce LangGraph early.
- Do not add cache, reranker, memory, hybrid retrieval, or CRAG unless the current learning step explicitly requires it.

## Required response structure
Respond in this exact order:

### 1. Step title
A short title like: `Step 4 — Extract text from uploaded PDF`

### 2. What we are building
2–5 bullet points in simple language.

### 3. Why this step exists
Explain why this step matters in the overall RAG pipeline.

### 4. Files to create or modify
List only the files needed for this step.

### 5. Implementation
Write the code.

### 6. How it works
Explain each file and the key functions.

### 7. How to run it
Provide exact commands.

### 8. How to test it manually
Give specific manual verification steps.

### 9. What we will build next
Exactly one next step.

## Important boundaries
- Do **not** update `LEARNING_PATH.md` yet.
- Do **not** update `LEARNING_LOG.md` yet.
- Do **not** propose commit/tag commands yet unless I explicitly ask to finalize the step.
- If the requested step is not yet testable, say so clearly.
- Optimize for learning clarity first.

## Notebook update requirement

After implementing a step, **always append new cells to `notebooks/pipeline_verification.ipynb`** to cover the step's verification.

### Rules for notebook cells
- Add a `markdown` header cell that names the step, states its prerequisites, and lists expected outputs.
- For every new API endpoint: add a Python cell that calls it via `httpx` and runs `check()` assertions on the response.
- For every artifact written to disk (JSON files, etc.): add a Python cell that reads the file and asserts its structure.
- For expected error cases (missing file → 404, wrong type → 400, etc.): add a separate cell per error case.
- Prefix each cell's first line with a comment showing the equivalent `curl` command where applicable.
- Keep cells independently runnable — re-use the `BACKEND_URL`, `TEST_PDF`, `stem`, and `PROJECT_ROOT` variables defined in Section 1.
- Do **not** add cells for future steps. Only add cells for the step being implemented.
- Slow steps (e.g. embedding generation) must include a `⚠️` warning in the markdown cell stating approximate runtime and noting that results are cached on disk.
