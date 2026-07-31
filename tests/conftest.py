"""
Shared pytest fixtures.

Tests never call the real Gemini API: a fake embeddings/LLM class is
substituted in, so the suite runs offline and without a real API key.
"""

import os
import sys
from pathlib import Path

import pytest
from langchain_core.embeddings import Embeddings

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("GOOGLE_API_KEY", "test-key-not-real")


class FakeEmbeddings(Embeddings):
    """Deterministic, offline stand-in for GoogleGenerativeAIEmbeddings."""

    def _vec(self, text: str) -> list[float]:
        # A tiny deterministic "embedding" based on character codes so
        # that identical text always maps to the same vector.
        h = sum(ord(c) for c in text) or 1
        return [((h * (i + 1)) % 97) / 97 for i in range(8)]

    def embed_documents(self, texts):
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)


class FakeLLMResponse:
    def __init__(self, content):
        self.content = content


class FakeLLM:
    def invoke(self, prompt: str):
        return FakeLLMResponse("This is a fake answer for testing.")


@pytest.fixture
def sample_pdf_path():
    path = Path(__file__).resolve().parent.parent / "data" / "pdfs" / "football_tutorial.pdf"
    if not path.exists():
        pytest.skip("Sample PDF not present in data/pdfs/")
    return str(path)
