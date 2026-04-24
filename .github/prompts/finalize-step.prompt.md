---
description: Finalize a completed learning step by updating progress files and proposing git metadata
agent: agent
---

Finalize the most recently completed learning step.

Use these files as the source of truth:
- `LEARNING_PATH.md`
- `LEARNING_LOG.md`
- the implementation files changed in the completed step

## Tasks
1. Update `LEARNING_PATH.md`
   - mark the completed step as done
   - do not mark future steps as done
   - if helpful, add the checkpoint/tag name such as `step-04`

2. Update `LEARNING_LOG.md`
   - append a new section for the completed step
   - use this structure:

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

3. Generate a proposed commit message using this format:

```text
step-XX: short summary
```

4. Generate a proposed annotated tag using this format:

```text
step-XX
```

5. Output the exact git commands I should run next.

## Git command style
Use this exact style unless the branch name must change:

```bash
git add .
git commit -m "step-XX: short summary"
git tag -a step-XX -m "Completed Step XX: short description"
git push origin main
git push origin step-XX
```

## Rules
- Do not invent tests that were not actually run.
- Do not invent functionality that was not implemented.
- Keep the learning log factual and concise.
- Explain changed files in plain English.
- Do not assume git commands were already executed.
- Ask for review or confirm that the user should review the generated commit message and tag before running the commands.

## Required response structure
Respond in this order:

### 1. Finalized step
State which step is being finalized.

### 2. Updated `LEARNING_PATH.md`
Show the relevant edited portion.

### 3. Updated `LEARNING_LOG.md`
Show the newly appended section.

### 4. Proposed commit message
Provide one commit message.

### 5. Proposed tag
Provide one annotated tag name and description.

### 6. Git commands to run
Provide the exact commands.

### 7. What we will build next
Exactly one next step from `LEARNING_PATH.md`.
