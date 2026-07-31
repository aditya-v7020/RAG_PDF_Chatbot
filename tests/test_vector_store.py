"""
Tests for src/vector_store.py.

The real GoogleGenerativeAIEmbeddings class is swapped for FakeEmbeddings
so these tests run fully offline.
"""

import pytest

from src import config
from src.vector_store import VectorStore
from tests.conftest import FakeEmbeddings


@pytest.fixture
def store(tmp_path, monkeypatch):
    # Point the index at a throwaway directory for this test.
    monkeypatch.setattr(config, "FAISS_DIR", tmp_path / "faiss_index")
    config.FAISS_DIR.mkdir(parents=True, exist_ok=True)

    vs = VectorStore()
    monkeypatch.setattr(vs, "embeddings", FakeEmbeddings())
    return vs


def make_chunks():
    return [
        {
            "id": "1",
            "text": "Lionel Messi plays for Inter Miami.",
            "page_num": 3,
            "images": [],
            "source": "football_tutorial.pdf",
        },
        {
            "id": "2",
            "text": "Offside rule explanation for football.",
            "page_num": 7,
            "images": ["data/extracted_images/example.jpeg"],
            "source": "football_tutorial.pdf",
        },
    ]


def test_new_store_is_empty(store):
    assert store.is_empty()
    assert store.count() == 0


def test_add_chunks_indexes_documents(store):
    added = store.add_chunks(make_chunks())
    assert added == 2
    assert not store.is_empty()
    assert store.count() == 2


def test_query_returns_matches_with_metadata(store):
    store.add_chunks(make_chunks())
    results = store.query("Messi", top_k=2)

    assert len(results) > 0
    for r in results:
        assert "text" in r
        assert "page_num" in r
        assert "images" in r
        assert "source" in r


def test_add_chunks_merges_with_existing_index(store):
    store.add_chunks(make_chunks())
    first_count = store.count()

    more_chunks = [
        {
            "id": "3",
            "text": "A second document about training drills.",
            "page_num": 1,
            "images": [],
            "source": "drills.pdf",
        }
    ]
    store.add_chunks(more_chunks)

    assert store.count() == first_count + 1


def test_reset_clears_the_index(store):
    store.add_chunks(make_chunks())
    store.reset()

    assert store.is_empty()
    assert store.count() == 0


def test_query_on_empty_store_returns_empty_list(store):
    assert store.query("anything") == []
