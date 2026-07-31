"""
RAG PDF Chatbot — FastAPI backend.

This replaces Streamlit purely as a *UI layer*. Every piece of actual
logic (PDF parsing, chunking, embeddings, FAISS vector store, Gemini
LLM calls) still lives in `src/` and is completely untouched — this
file only exposes that logic over HTTP so the React frontend can call
it.

Run with:
    uvicorn api_server:app --reload --port 8000
"""

from __future__ import annotations

import json
import logging
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel

from src import config
from src.chatbot import ChatBot
from src.pdf_processor import process_pdf
from src.vector_store import VectorStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("rag_pdf_chatbot.api")

app = FastAPI(title="RAG PDF Chatbot API", version=config.VERSION)

# Local dev: the React app runs on a different port (Vite's 5173), so
# CORS must be open for it to call this API from the browser. The
# frontend never sends cookies/credentials (see frontend/src/api/client.js),
# so allow_credentials is left off — combining a wildcard origin with
# credentials is both unnecessary here and rejected by browsers for any
# future credentialed request.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Catch-all so an unexpected error returns a clean JSON error instead
    of crashing the worker or leaking a raw traceback to the client.
    """
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected server error occurred. Please try again."},
    )


# ---------------------------------------------------------------------
# Upload validation
# ---------------------------------------------------------------------
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB per file
MAX_FILES_PER_REQUEST = 20
_UNSAFE_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def _safe_pdf_filename(raw_name: str) -> str:
    """
    Turn an untrusted uploaded filename into something safe to place
    under config.PDF_DIR: strip any directory components (blocks path
    traversal like '../../etc/passwd.pdf'), strip characters that are
    invalid/unsafe on common filesystems, and guarantee a '.pdf'
    extension so files can't be written with an arbitrary/executable
    extension.
    """
    name = Path(raw_name or "").name  # drop any path components
    name = _UNSAFE_FILENAME_CHARS.sub("_", name).strip(" .")

    if not name:
        name = "upload.pdf"

    if not name.lower().endswith(".pdf"):
        name = f"{name}.pdf"

    return name

# Serve extracted images (e.g. GET /images/TensorFlow_p1_0.jpeg) so the
# React app can render them directly with an <img> tag.
config.IMAGE_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/images", StaticFiles(directory=str(config.IMAGE_DIR)), name="images")


# ---------------------------------------------------------------------
# Process-wide singletons.
#
# The original Streamlit app kept one VectorStore/ChatBot per browser
# session (st.session_state). This app is meant to be run locally by a
# single user, so a simple module-level singleton is the direct
# equivalent — it's rebuilt (invalidated) any time the index changes,
# exactly like the Streamlit version popped "chatbot" from session
# state after every upload/delete/reset.
# ---------------------------------------------------------------------
_vector_store: Optional[VectorStore] = None
_chatbot: Optional[ChatBot] = None
_singleton_lock = threading.Lock()
_manifest_lock = threading.Lock()


def get_vector_store() -> VectorStore:
    global _vector_store
    with _singleton_lock:
        if _vector_store is None:
            _vector_store = VectorStore()
        return _vector_store


def invalidate_chatbot() -> None:
    global _chatbot
    with _singleton_lock:
        _chatbot = None


def get_chatbot() -> ChatBot:
    global _chatbot
    with _singleton_lock:
        if _chatbot is None:
            _chatbot = ChatBot()
        return _chatbot


def load_manifest() -> list[dict]:
    with _manifest_lock:
        if config.MANIFEST_PATH.exists():
            try:
                return json.loads(config.MANIFEST_PATH.read_text())
            except Exception:
                logger.warning("Manifest file was unreadable/corrupt; treating as empty.")
                return []
        return []


def save_manifest(entries: list[dict]) -> None:
    with _manifest_lock:
        config.MANIFEST_PATH.write_text(json.dumps(entries, indent=2))


def image_url(path_str: str) -> str:
    """Turn an absolute on-disk image path into a URL the frontend can load."""
    return f"/images/{Path(path_str).name}"


# ---------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------
MAX_QUESTION_LENGTH = 4000


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[Union[int, str]]
    documents: List[str]
    images: List[str]


class DocumentEntry(BaseModel):
    name: str
    chunks: int
    added_at: str


# ---------------------------------------------------------------------
# Setup / status  (mirrors config.check_setup() shown in the sidebar)
# ---------------------------------------------------------------------
@app.get("/api/setup")
def get_setup():
    issues = config.check_setup()
    return {
        "ready": not issues,
        "issues": issues,
        "llm_model": config.LLM_MODEL,
        "embedding_model": config.EMBEDDING_MODEL,
        "version": config.VERSION,
    }


# ---------------------------------------------------------------------
# Documents  (mirrors the sidebar's Document Manager)
# ---------------------------------------------------------------------
@app.get("/api/documents", response_model=List[DocumentEntry])
def get_documents():
    return load_manifest()


@app.post("/api/documents")
async def upload_documents(files: List[UploadFile] = File(...)):
    issues = config.check_setup()
    if issues:
        raise HTTPException(status_code=400, detail="; ".join(issues))

    if not files:
        raise HTTPException(status_code=400, detail="No files were uploaded.")

    if len(files) > MAX_FILES_PER_REQUEST:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files in one request (max {MAX_FILES_PER_REQUEST}).",
        )

    manifest = load_manifest()
    results = []

    for uploaded_file in files:
        original_name = uploaded_file.filename or "upload.pdf"
        safe_name = _safe_pdf_filename(original_name)

        is_pdf_type = (uploaded_file.content_type or "").lower() in (
            "application/pdf",
            "application/x-pdf",
        )
        if not is_pdf_type and not original_name.lower().endswith(".pdf"):
            results.append(
                {
                    "name": original_name,
                    "ok": False,
                    "message": f"'{original_name}' is not a PDF file.",
                }
            )
            continue

        content = await uploaded_file.read()
        await uploaded_file.close()

        if not content:
            results.append(
                {"name": safe_name, "ok": False, "message": f"'{original_name}' is empty."}
            )
            continue

        if len(content) > MAX_UPLOAD_BYTES:
            results.append(
                {
                    "name": safe_name,
                    "ok": False,
                    "message": (
                        f"'{original_name}' exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)}MB "
                        "upload limit."
                    ),
                }
            )
            continue

        dest_path = config.PDF_DIR / safe_name
        try:
            dest_path.write_bytes(content)
        except OSError as exc:
            logger.error("Could not save upload '%s': %s", safe_name, exc)
            results.append(
                {"name": safe_name, "ok": False, "message": f"Could not save '{original_name}': {exc}"}
            )
            continue

        try:
            # PDF parsing is CPU-bound and synchronous; run it off the
            # event loop thread so one large upload doesn't stall every
            # other in-flight request (chat, dashboard, etc.).
            chunks = await run_in_threadpool(process_pdf, str(dest_path))
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI
            logger.warning("Failed to parse '%s': %s", safe_name, exc)
            results.append(
                {
                    "name": safe_name,
                    "ok": False,
                    "message": f"Failed to read '{original_name}': {exc}",
                }
            )
            continue

        if not chunks:
            results.append(
                {
                    "name": safe_name,
                    "ok": False,
                    "message": f"No extractable text or images were found in '{original_name}'.",
                }
            )
            continue

        try:
            store = get_vector_store()
            # Embedding + FAISS indexing is also blocking network/CPU work.
            added = await run_in_threadpool(store.add_chunks, chunks)
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI
            logger.error("Indexing failed for '%s': %s", safe_name, exc)
            results.append(
                {
                    "name": safe_name,
                    "ok": False,
                    "message": f"Indexing failed for '{original_name}': {exc}",
                }
            )
            continue

        manifest = [d for d in manifest if d["name"] != safe_name]
        manifest.append(
            {
                "name": safe_name,
                "chunks": added,
                "added_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
        )
        results.append(
            {
                "name": safe_name,
                "ok": True,
                "message": f"Indexed '{safe_name}' ({added} chunks).",
            }
        )

    save_manifest(manifest)
    invalidate_chatbot()

    return {"manifest": manifest, "results": results}


@app.delete("/api/documents/{name}")
def delete_document(name: str):
    manifest = load_manifest()

    if not any(d["name"] == name for d in manifest):
        raise HTTPException(status_code=404, detail=f"'{name}' is not an indexed document.")

    try:
        store = get_vector_store()
        store.delete_source(name)
    except Exception as exc:  # noqa: BLE001 - surfaced to the UI
        logger.error("Could not remove '%s': %s", name, exc)
        raise HTTPException(status_code=500, detail=f"Could not remove '{name}': {exc}")

    manifest = [d for d in manifest if d["name"] != name]
    save_manifest(manifest)
    invalidate_chatbot()

    return {"manifest": manifest}


@app.post("/api/documents/reset")
def reset_documents():
    global _vector_store

    try:
        store = get_vector_store()
        store.reset()
    except ValueError:
        # No API key configured — there was nothing indexed to begin with.
        pass
    except Exception as exc:  # noqa: BLE001 - surfaced to the UI
        logger.error("Reset failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Reset failed: {exc}")

    save_manifest([])
    with _singleton_lock:
        _vector_store = None
    invalidate_chatbot()

    return {"manifest": []}


# ---------------------------------------------------------------------
# Dashboard  (mirrors the "📊 Dashboard" tab)
# ---------------------------------------------------------------------
@app.get("/api/dashboard")
def get_dashboard():
    docs = load_manifest()
    total_chunks = sum(d.get("chunks", 0) for d in docs)

    total_images = 0
    if config.IMAGE_DIR.exists():
        total_images = len(
            [f for f in config.IMAGE_DIR.iterdir() if f.is_file() and not f.name.startswith(".")]
        )

    return {
        "documents": docs,
        "document_count": len(docs),
        "total_chunks": total_chunks,
        "total_images": total_images,
    }


# ---------------------------------------------------------------------
# Chat  (mirrors the "💬 Chat" tab)
# ---------------------------------------------------------------------
@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    issues = config.check_setup()
    if issues:
        raise HTTPException(status_code=400, detail="; ".join(issues))

    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question must not be empty.")
    if len(question) > MAX_QUESTION_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Question is too long (max {MAX_QUESTION_LENGTH} characters).",
        )

    try:
        bot = get_chatbot()
        response = bot.ask(question)
    except Exception as exc:  # noqa: BLE001 - surfaced to the UI
        logger.error("Chat failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Chat failed: {exc}")

    return {
        "answer": response["answer"],
        "sources": response["sources"],
        "documents": response["documents"],
        "images": [image_url(p) for p in response["images"]],
    }


@app.get("/")
def root():
    return {"status": "ok", "service": "RAG PDF Chatbot API", "version": config.VERSION}
