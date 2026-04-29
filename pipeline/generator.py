"""
pipeline/generator.py

Generates an answer from retrieved chunks using a local Ollama LLM.

Process:
  1. Build a prompt that contains the retrieved chunk texts as numbered context passages.
  2. POST to Ollama's /api/generate endpoint (non-streaming) to get the full answer.
  3. Return the answer text.

The prompt instructs the LLM to answer ONLY from the provided context passages.
This is the core RAG constraint: grounding the answer in retrieved evidence rather
than in the model's own training data.
"""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "llama3.1")

# Prompt template.
# The two placeholders are:
#   {context}  — numbered passages built from retrieved chunks
#   {question} — the user's question
_PROMPT_TEMPLATE = """\
You are a helpful assistant. Answer the question using ONLY the context passages provided below.
If the context does not contain enough information to answer, say exactly:
"I don't have enough information in the provided context to answer that."

Context passages:
{context}

Question: {question}

Answer:"""


def _build_context(chunks: list[dict]) -> str:
    """
    Format retrieved chunks into a numbered context block.

    Each passage is prefixed with its number and page for traceability.
    Example:
        [1] (page 12) The regulation states that...
        [2] (page 45) Furthermore, the policy...
    """
    lines = []
    for i, chunk in enumerate(chunks, start=1):
        lines.append(f"[{i}] (page {chunk['page']}) {chunk['text']}")
    return "\n\n".join(lines)


def generate_answer(question: str, chunks: list[dict]) -> str:
    """
    Generate an answer for a question given a list of retrieved chunks.

    Args:
        question: The user's question string.
        chunks:   List of chunk dicts as returned by pipeline.retriever.retrieve().
                  Each dict must contain at least 'text' and 'page'.

    Returns:
        The LLM's answer as a plain string.
    """
    context = _build_context(chunks)
    prompt = _PROMPT_TEMPLATE.format(context=context, question=question)

    # stream=False means Ollama waits for the full response before returning.
    # This is simpler than handling a streaming response for now.
    response = httpx.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={
            "model": OLLAMA_LLM_MODEL,
            "prompt": prompt,
            "stream": False,
        },
        timeout=120,  # generation can take up to 2 min on CPU
    )
    response.raise_for_status()

    # /api/generate returns {"response": "...", "done": true, ...}
    return response.json()["response"].strip()
