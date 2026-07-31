"""
Tests for src/chatbot.py — VectorStore and the LLM are both replaced
with fakes so no network access or real API key is required.
"""

import pytest

from src.chatbot import ChatBot, _extract_answer_text
from tests.conftest import FakeLLM


class FakeVectorStoreWithResults:
    def query(self, question, top_k=None):
        return [
            {
                "text": "Lionel Messi is an Argentine footballer.",
                "page_num": 2,
                "images": [],
                "source": "football_tutorial.pdf",
            }
        ]


class FakeVectorStoreEmpty:
    def query(self, question, top_k=None):
        return []


@pytest.fixture
def chatbot_with_results(monkeypatch):
    monkeypatch.setattr(ChatBot, "__init__", lambda self: None)
    bot = ChatBot()
    bot.vector_store = FakeVectorStoreWithResults()
    bot.llm = FakeLLM()
    return bot


@pytest.fixture
def chatbot_empty(monkeypatch):
    monkeypatch.setattr(ChatBot, "__init__", lambda self: None)
    bot = ChatBot()
    bot.vector_store = FakeVectorStoreEmpty()
    bot.llm = FakeLLM()
    return bot


def test_ask_returns_answer_sources_and_documents(chatbot_with_results):
    response = chatbot_with_results.ask("Who is Lionel Messi?")

    assert response["answer"] == "This is a fake answer for testing."
    assert response["sources"] == [2]
    assert response["documents"] == ["football_tutorial.pdf"]
    assert response["images"] == []


def test_ask_with_no_matches_returns_friendly_message(chatbot_empty):
    response = chatbot_empty.ask("Some unrelated question")

    assert "No relevant information" in response["answer"]
    assert response["sources"] == []
    assert response["documents"] == []


def test_extract_answer_text_handles_plain_string():
    assert _extract_answer_text("Hello world") == "Hello world"


def test_extract_answer_text_handles_block_list_with_signature():
    # Reproduces the malformed-output bug: some Gemini 3+ responses return
    # content as a list of blocks (text + internal thinking signature)
    # instead of a plain string.
    content = [
        {"type": "text", "text": "Lionel Messi is an Argentine footballer."},
        {"type": "signature", "extras": {"signature": "ErsWCrgWARFNMg..."}},
    ]
    assert _extract_answer_text(content) == "Lionel Messi is an Argentine footballer."


def test_extract_answer_text_joins_multiple_text_blocks():
    content = [
        {"type": "text", "text": "Part one. "},
        {"type": "text", "text": "Part two."},
    ]
    assert _extract_answer_text(content) == "Part one. Part two."


def test_extract_answer_text_handles_empty_list():
    assert _extract_answer_text([]) == ""


def test_ask_with_block_list_response_returns_clean_text(monkeypatch):
    class BlockListLLM:
        def invoke(self, prompt):
            class Resp:
                content = [
                    {"type": "text", "text": "Clean answer only."},
                    {"type": "signature", "extras": {"signature": "abcd1234"}},
                ]

            return Resp()

    monkeypatch.setattr(ChatBot, "__init__", lambda self: None)
    bot = ChatBot()
    bot.vector_store = FakeVectorStoreWithResults()
    bot.llm = BlockListLLM()

    response = bot.ask("Who is Lionel Messi?")
    assert response["answer"] == "Clean answer only."
    assert "signature" not in response["answer"]


def test_ask_handles_llm_failure_gracefully(chatbot_with_results):
    class BrokenLLM:
        def invoke(self, prompt):
            raise RuntimeError("network down")

    chatbot_with_results.llm = BrokenLLM()
    response = chatbot_with_results.ask("Who is Lionel Messi?")

    assert "language model call failed" in response["answer"]
    # Sources should still be reported even if generation failed.
    assert response["sources"] == [2]
