# Copilot Instructions — Learning-First, Tiny-Step Implementation for Local PDF RAG

Use this file as the main repository-wide instruction document for GitHub Copilot in this repository.

---

## Mission

Build this repository in **tiny, verifiable, learning-friendly steps** so the developer can:
- understand each change
- run each step locally
- verify each step manually
- revisit the repository later and recover the mental model quickly

The priority order is:
1. **Learning clarity**
2. **Small safe increments**
3. **Verifiable progress**
4. **Only then speed**

This repository is a **local-first RAG system for text PDFs** using:
- **FastAPI** for backend API
- **Streamlit** for UI
- **Ollama** for local LLM + local embeddings
- **Qdrant** for vector storage
- **PyMuPDF (`fitz`)** for PDF text extraction — preferred over `pypdf` or `pdfplumber` because it uses the C-based MuPDF engine, correctly reconstructs character-spaced text, preserves reading order across multi-column layouts, and natively detects tables via `page.find_tables()` (v1.23+); AGPL license is acceptable for non-commercial use
- **Custom orchestration first**
- **LangGraph later only when the workflow becomes meaningfully stateful or branching**

---

## Project-wide development philosophy

- Build one concept at a time.
- Prefer the **smallest working version** first.
- Make every step easy to inspect manually.
- Avoid overwhelming the learner with too much code.
- Do not scaffold advanced architecture too early.
- Keep the codebase understandable by a human reading it after a long break.
- Optimize for **teachability**, not cleverness.

---

## Non-negotiable implementation rules

1. **Only implement one small feature at a time.**
2. **Do not scaffold the full production architecture at once.**
3. **Do not create more than 2–4 files in a single step** unless explicitly requested.
4. **Before writing code, explain the step in plain English**:
   - what is being added
   - why it matters
   - how the files connect
5. **After writing code, explain the code in beginner-friendly language**.
6. **Prefer the simplest working version first**, even if not yet production-grade.
7. **Do not add optional abstractions too early.**
8. **Do not introduce LangGraph until the custom pipeline is already understandable and working.**
9. **Do not add caching, reranking, memory, routing, hybrid retrieval, or self-grading early unless the current learning step explicitly asks for it.**
10. **Every implementation step must end with exact manual test instructions.**
11. **Every finalized step must also update the learning-tracking files** described below.

---

## Definition of a good step

A good step:
- can be understood in less than 15 minutes
- changes a very small number of files
- has a visible result
- is easy to test manually
- introduces only one or two new concepts

A bad step:
- adds too many modules at once
- mixes retrieval, API, UI, evaluation, and security together
- creates future-facing architecture without a visible result
- hides logic behind abstractions before the learner understands the basics

---

## Current stack and learning boundaries

### Early implementation phase
Use:
- **FastAPI**
- **Streamlit**
- **Ollama**
- **Qdrant**
- **Text PDFs only**
- **Chunk-level citations**
- **Custom orchestration**

### Do not add yet unless the current step explicitly requires it
- OCR
- authentication
- multi-user design
- distributed tracing systems
- background workers
- LangGraph
- semantic cache
- reranking
- hybrid retrieval
- CRAG / self-grading
- agent frameworks

---

## Preferred coding style

- Use small functions.
- Use descriptive names.
- Add short, practical comments.
- Keep classes minimal unless clearly needed.
- Prefer explicit code over magic abstractions.
- Use Pydantic for request/response models when API schemas are needed.
- Keep side effects isolated.
- Prefer readability over cleverness.
- Avoid premature optimization.

---

## Repository growth policy

Only add a new top-level folder when it becomes necessary.

### Allowed early folders
- `app/`
- `routes/`
- `services/`
- `pipeline/`
- `ui/`
- `data/`
- `tests/`

### Avoid creating too early
- `agents/`
- `evaluation/`
- `observability/`
- `security/`
- `prompts/` (application prompt templates, not the `.github/prompts/` customization folder)

These can be added later when the learner is ready.

---

## Source of truth for implementation order

Use `LEARNING_PATH.md` as the **canonical implementation order**.

### If asked to implement the next step
- always implement the **smallest incomplete step** from `LEARNING_PATH.md`
- if a step is still too large, split it into smaller sub-steps automatically
- do not jump ahead to future architecture

### If asked to explain before coding
- do not write code first
- explain the design visually and conceptually
- wait for the user

### If the user says “too much code”
- reduce scope
- refactor into a smaller slice
- prefer one file over many

### If a feature is requested too early
If the user requests a complex feature too early (for example semantic cache, reranker, CRAG, LangGraph routing):
1. briefly explain why it is advanced
2. propose the smallest prerequisite step
3. implement only the prerequisite unless the user explicitly asks otherwise

---

## Required output format for every implementation step

When implementing a step, always respond in this order:

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

---

## Mandatory learning-tracking workflow

A step is **not fully complete** until the repository learning artifacts are updated.

After a step is implemented and the user indicates it is working or ready to finalize, also update:
1. `LEARNING_PATH.md`
2. `LEARNING_LOG.md`

Do not update these prematurely if the step is still in-progress or broken.

---

## Rules for updating LEARNING_PATH.md

When finalizing a completed step:
- mark the completed step as done
- do **not** mark future steps as done
- if helpful, add the tag/checkpoint name beside the step, such as `step-04`
- preserve the existing order of the roadmap
- do not rewrite unrelated steps

Example style:
- [x] Step 4 — Extract text from text PDF (`tag: step-04`)
- [ ] Step 5 — Chunk extracted text

---

## Rules for updating LEARNING_LOG.md

When finalizing a completed step, append a new entry using this structure:

```md
## Step X — Step title

### What I added
- item
- item

### Why this matters
Short explanation.

### Files changed
- `path/to/file.py`: explanation of what changed
- `path/to/other_file.py`: explanation of what changed

### How I tested
- exact manual verification step
- exact manual verification step

### Notes to future me
- what is still missing
- what to watch for
- what the next step should be
```

### Important rules for LEARNING_LOG.md
- keep the log factual and concise
- do not invent behavior that was not implemented
- do not invent tests that were not run
- explain changed files in plain English
- optimize for future readability by the learner

---

## Git workflow rules

The preferred workflow for this repository is:
- **linear branch**
- **one commit per learning step**
- **one tag per completed step**

### Commit rules
For every finalized step, propose a commit message using this format:

```text
step-XX: short summary
```

Example:
```text
step-04: extract text from uploaded PDF
```

### Tag rules
For every finalized step, also propose an annotated git tag:

```text
step-XX
```

Example:
```bash
git tag -a step-04 -m "Completed Step 4: PDF text extraction"
```

### Important Git safety rule
- Suggest git commands and commit/tag text.
- **Do not assume git actions were already executed.**
- The user should review the commit message and tag before finalizing.
- Prefer proposing commands rather than silently assuming repository state.

---

## What to do when finalizing a step

When the user asks to finalize a step, do the following:
1. Update `LEARNING_PATH.md`
2. Append a new section to `LEARNING_LOG.md`
3. Suggest a commit message
4. Suggest an annotated tag
5. Output the exact git commands the user can run next

Use this command style:

```bash
git add .
git commit -m "step-XX: short summary"
git tag -a step-XX -m "Completed Step XX: short description"
git push origin main
git push origin step-XX
```

If the branch is not `main`, adapt accordingly.

---

## Learning-first explanation style

Whenever explaining code:
- assume the user is learning
- explain why the code exists, not just what it does
- connect each file to the bigger pipeline
- point out any tradeoff made for simplicity
- mention what would likely be improved later in a production version

---

## Architecture progression rule

Use this progression unless the user explicitly overrides it:

### Early phase
- upload PDF
- extract text
- chunk text
- embed with Ollama
- index in Qdrant
- retrieve chunks
- answer from chunks
- show citations in Streamlit

### Middle phase
- refusal when evidence is weak
- conversation memory
- semantic cache
- hybrid retrieval
- reranker
- input/output guards

### Later phase
- LangGraph introduction
- intent routing
- CRAG / self-grading
- observability
- evaluation harness

---

## Golden principle

**Make the codebase teachable.**

The learner should be able to:
- read each step
- run each step
- verify each step
- understand why it exists
- revisit the repository later and recover the mental model quickly

If there is any conflict between speed and clarity, choose **clarity**.
