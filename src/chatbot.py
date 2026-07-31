"""
RAG orchestration: retrieve relevant chunks from the vector store,
then ask the LLM to answer strictly from that context.
"""

from __future__ import annotations

import time

from src.llm import get_llm
from src.vector_store import VectorStore

# Gemini occasionally returns 503 UNAVAILABLE / "high demand" when its
# servers are temporarily overloaded (common on the free tier). These
# are transient, so a short retry-with-backoff resolves most of them
# without bothering the user.
_RETRYABLE_MARKERS = ("503", "UNAVAILABLE", "overloaded", "high demand")
_MAX_RETRIES = 3
_BASE_DELAY_SECONDS = 2

SYSTEM_PROMPT_TEMPLATE = """You are an intelligent assistant that answers questions about the
uploaded document(s).

Rules:
1. Answer ONLY using the information in the provided context.
2. Do NOT invent or assume facts that are not present in the context.
3. If the answer is not present in the context, reply exactly with:
   "The information is not available in the document."
4. Keep answers concise, clear, and well-formatted.

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:"""


def _extract_answer_text(content) -> str:
    """
    Normalize an LLM response's `.content` into a plain string.

    Newer Gemini models can return `content` as a list of content
    blocks (e.g. a "text" block plus internal "thinking"/"signature"
    metadata) instead of a plain string. This pulls out only the
    human-readable text, regardless of which shape the SDK returns.
    """
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts).strip()

    return str(content).strip()


class ChatBot:
    def __init__(self):
        self.vector_store = VectorStore()
        self.llm = get_llm()

    def _invoke_with_retry(self, prompt: str) -> str:
        """
        Call the LLM, retrying with exponential backoff if Gemini
        reports a transient overload (503 UNAVAILABLE / "high demand").
        Non-transient errors (bad API key, invalid model, etc.) are
        raised immediately instead of being retried pointlessly.
        """
        last_exc: Exception | None = None

        for attempt in range(_MAX_RETRIES):
            try:
                response = self.llm.invoke(prompt)
                return _extract_answer_text(response.content)
            except Exception as exc:  # noqa: BLE001 - inspected below
                last_exc = exc
                is_transient = any(marker in str(exc) for marker in _RETRYABLE_MARKERS)
                if not is_transient or attempt == _MAX_RETRIES - 1:
                    raise
                time.sleep(_BASE_DELAY_SECONDS * (2 ** attempt))

        raise last_exc  # pragma: no cover - unreachable, satisfies type checkers

    def ask(self, question: str) -> dict:
        """
        Answer a question using retrieval-augmented generation.

        Returns:
            {
                "answer": str,
                "sources": list[int],   # page numbers
                "images": list[str],    # image file paths
                "documents": list[str], # source PDF filenames
            }
        """
        results = self.vector_store.query(question)

        if not results:
            return {
                "answer": (
                    "No relevant information was found. Make sure you've "
                    "processed a PDF first using the sidebar."
                ),
                "sources": [],
                "images": [],
                "documents": [],
            }

        context = "\n\n---\n\n".join(result["text"] for result in results)
        prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context, question=question)

        try:
            answer = self._invoke_with_retry(prompt)
            if not answer:
                answer = "The model returned an empty response."
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI
            if any(marker in str(exc) for marker in _RETRYABLE_MARKERS):
                answer = (
                    "Gemini's servers are temporarily overloaded (this is on "
                    "Google's end, not your setup). It was retried "
                    f"{_MAX_RETRIES} times automatically — please wait a "
                    "moment and ask again."
                )
            else:
                answer = f"The language model call failed: {exc}"

        pages = sorted({result["page_num"] for result in results})
        images = sorted({img for result in results for img in result["images"]})
        documents = sorted({result["source"] for result in results})

        return {
            "answer": answer,
            "sources": pages,
            "images": images,
            "documents": documents,
        }
