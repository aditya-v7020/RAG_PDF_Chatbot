"""
Vector Store — FAISS index backed by Gemini embeddings.

Supports incrementally adding documents: processing a second PDF
merges its chunks into the existing index instead of replacing it.
"""

from __future__ import annotations

import logging
import shutil

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from src import config

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self):
        api_key = config.get_google_api_key()

        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY not found. Add it to your .env file "
                "(see .env.example)."
            )

        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=config.EMBEDDING_MODEL,
            google_api_key=api_key,
        )

        self.db: FAISS | None = None
        self._load_if_exists()

    def _load_if_exists(self) -> None:
        index_file = config.FAISS_DIR / "index.faiss"

        if not index_file.exists():
            return

        try:
            self.db = FAISS.load_local(
                str(config.FAISS_DIR),
                self.embeddings,
                allow_dangerous_deserialization=True,
            )
        except Exception as exc:
            # A stale/incompatible index shouldn't crash the app; log
            # and continue with an empty store so the user can rebuild.
            logger.warning("Could not load existing FAISS index, starting fresh: %s", exc)
            self.db = None

    # Gemini's embedding endpoint rejects requests over a fixed batch
    # size. Large PDFs can easily produce more chunks than that in one
    # go, so chunks are embedded in fixed-size batches and merged.
    _EMBED_BATCH_SIZE = 90

    def add_chunks(self, chunks: list[dict]) -> int:
        """
        Embed and index a list of chunks. If an index already exists,
        the new chunks are merged into it rather than replacing it, so
        multiple PDFs can be indexed side by side.

        Returns the number of chunks added.
        """
        if not chunks:
            return 0

        documents = [
            Document(
                page_content=chunk["text"],
                metadata={
                    "page_num": chunk["page_num"],
                    "images": chunk["images"],
                    "source": chunk.get("source", "unknown"),
                },
            )
            for chunk in chunks
        ]

        new_db: FAISS | None = None
        for start in range(0, len(documents), self._EMBED_BATCH_SIZE):
            batch = documents[start : start + self._EMBED_BATCH_SIZE]
            batch_db = FAISS.from_documents(batch, self.embeddings)
            if new_db is None:
                new_db = batch_db
            else:
                new_db.merge_from(batch_db)

        if self.db is None:
            self.db = new_db
        else:
            self.db.merge_from(new_db)

        self.db.save_local(str(config.FAISS_DIR))

        return len(documents)

    def delete_source(self, source_name: str) -> int:
        """
        Remove every chunk that came from a given source PDF.

        Returns the number of chunks removed. FAISS has no native
        "delete by metadata" call, so this rebuilds the index from the
        surviving documents.
        """
        if self.is_empty():
            return 0

        docstore = self.db.docstore
        all_ids = list(self.db.index_to_docstore_id.values())

        keep_docs = []
        removed = 0
        for doc_id in all_ids:
            doc = docstore.search(doc_id)
            if getattr(doc, "metadata", {}).get("source") == source_name:
                removed += 1
            else:
                keep_docs.append(doc)

        if removed == 0:
            return 0

        if keep_docs:
            rebuilt: FAISS | None = None
            for start in range(0, len(keep_docs), self._EMBED_BATCH_SIZE):
                batch = keep_docs[start : start + self._EMBED_BATCH_SIZE]
                batch_db = FAISS.from_documents(batch, self.embeddings)
                if rebuilt is None:
                    rebuilt = batch_db
                else:
                    rebuilt.merge_from(batch_db)
            self.db = rebuilt
            self.db.save_local(str(config.FAISS_DIR))
        else:
            self.reset()

        return removed

    def is_empty(self) -> bool:
        return self.db is None

    def count(self) -> int:
        if self.is_empty():
            return 0
        return self.db.index.ntotal

    def query(self, question: str, top_k: int | None = None) -> list[dict]:
        top_k = top_k or config.TOP_K_RESULTS

        if self.is_empty():
            return []

        try:
            results = self.db.similarity_search(question, k=top_k)
        except Exception as exc:
            logger.error("Vector store query error: %s", exc)
            return []

        return [
            {
                "text": result.page_content,
                "page_num": result.metadata.get("page_num", "Unknown"),
                "images": result.metadata.get("images", []),
                "source": result.metadata.get("source", "unknown"),
            }
            for result in results
        ]

    def reset(self) -> None:
        """Delete the on-disk index and clear the in-memory store."""
        if config.FAISS_DIR.exists():
            shutil.rmtree(config.FAISS_DIR)

        config.FAISS_DIR.mkdir(parents=True, exist_ok=True)
        self.db = None
