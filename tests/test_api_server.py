"""
Tests for api_server.py.

The vector store / chatbot are monkeypatched with lightweight fakes so
the suite runs fully offline, exactly like the rest of the test suite.
"""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

import api_server
from src import config


class FakeStore:
    def __init__(self):
        self.docs = {}

    def add_chunks(self, chunks):
        for c in chunks:
            self.docs.setdefault(c["source"], []).append(c)
        return len(chunks)

    def delete_source(self, name):
        return len(self.docs.pop(name, []))

    def reset(self):
        self.docs = {}


class FakeBot:
    def ask(self, question):
        return {
            "answer": f"Fake answer for: {question}",
            "sources": [1],
            "images": [],
            "documents": ["fake.pdf"],
        }


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PDF_DIR", tmp_path / "pdfs")
    monkeypatch.setattr(config, "IMAGE_DIR", tmp_path / "images")
    monkeypatch.setattr(config, "MANIFEST_PATH", tmp_path / "manifest.json")
    config.PDF_DIR.mkdir(parents=True, exist_ok=True)
    config.IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(config, "get_google_api_key", lambda: "test-key-not-real")
    monkeypatch.setattr(api_server, "get_vector_store", lambda: FakeStore())
    monkeypatch.setattr(api_server, "get_chatbot", lambda: FakeBot())
    monkeypatch.setattr(
        api_server,
        "process_pdf",
        lambda path: [
            {"id": "1", "text": "hello world", "page_num": 1, "images": [], "source": "x"}
        ],
    )

    return TestClient(api_server.app)


def _pdf_bytes() -> bytes:
    return b"%PDF-1.4\n%fake pdf content for tests\n"


def test_setup_endpoint_reports_ready(client):
    resp = client.get("/api/setup")
    assert resp.status_code == 200
    assert resp.json()["ready"] is True


def test_upload_rejects_non_pdf(client):
    resp = client.post(
        "/api/documents",
        files={"files": ("notes.txt", io.BytesIO(b"just text"), "text/plain")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["results"][0]["ok"] is False
    assert "not a PDF" in body["results"][0]["message"]


def test_upload_sanitizes_path_traversal_filename(client):
    resp = client.post(
        "/api/documents",
        files={
            "files": ("../../../../etc/passwd.pdf", io.BytesIO(_pdf_bytes()), "application/pdf")
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["results"][0]["ok"] is True
    saved_name = body["results"][0]["name"]
    # Must never contain a path separator or traversal sequence.
    assert "/" not in saved_name and ".." not in saved_name
    # The file must land inside the configured PDF_DIR, nowhere else.
    assert (config.PDF_DIR / saved_name).exists()


def test_upload_rejects_empty_file(client):
    resp = client.post(
        "/api/documents",
        files={"files": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
    )
    body = resp.json()
    assert body["results"][0]["ok"] is False
    assert "empty" in body["results"][0]["message"]


def test_document_lifecycle(client):
    upload = client.post(
        "/api/documents",
        files={"files": ("report.pdf", io.BytesIO(_pdf_bytes()), "application/pdf")},
    )
    assert upload.json()["results"][0]["ok"] is True

    listed = client.get("/api/documents").json()
    assert any(d["name"] == "report.pdf" for d in listed)

    deleted = client.delete("/api/documents/report.pdf")
    assert deleted.status_code == 200
    assert deleted.json()["manifest"] == []

    missing = client.delete("/api/documents/does_not_exist.pdf")
    assert missing.status_code == 404


def test_chat_rejects_empty_question(client):
    resp = client.post("/api/chat", json={"question": "   "})
    assert resp.status_code == 400


def test_chat_rejects_overlong_question(client):
    resp = client.post("/api/chat", json={"question": "x" * (api_server.MAX_QUESTION_LENGTH + 1)})
    assert resp.status_code == 400


def test_chat_returns_answer(client):
    resp = client.post("/api/chat", json={"question": "What is this about?"})
    assert resp.status_code == 200
    body = resp.json()
    assert "Fake answer" in body["answer"]
    assert body["documents"] == ["fake.pdf"]


def test_dashboard_endpoint(client):
    resp = client.get("/api/dashboard")
    assert resp.status_code == 200
    body = resp.json()
    assert "document_count" in body
    assert "total_chunks" in body
