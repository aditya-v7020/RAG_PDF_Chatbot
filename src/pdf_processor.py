"""
PDF Processing Module

Responsibilities:
1. Extract text from PDFs.
2. Extract embedded images from PDFs.
3. Split text into overlapping chunks.
4. Preserve page / image / source-file metadata on every chunk.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

from src import config


def _clean_pdf_name(pdf_path: str) -> str:
    """Turn a filename into a filesystem- and id-safe prefix."""
    stem = Path(pdf_path).stem
    safe = "".join(c if c.isalnum() else "_" for c in stem)
    return safe[:40]


def extract_text_and_images(pdf_path: str) -> list[dict]:
    """
    Open a PDF and return one dict per page:
        {"page_num": int, "text": str, "images": [file paths]}
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    pages = []

    with fitz.open(pdf_path) as doc:
        prefix = _clean_pdf_name(str(pdf_path))

        for page_index in range(len(doc)):
            page = doc[page_index]
            page_num = page_index + 1
            text = page.get_text("text").strip()

            image_paths = []

            for img_index, img in enumerate(page.get_images(full=True)):
                xref = img[0]

                try:
                    base_image = doc.extract_image(xref)
                except Exception:
                    continue

                width = base_image.get("width", 0)
                height = base_image.get("height", 0)

                if width < config.MIN_IMAGE_WIDTH or height < config.MIN_IMAGE_HEIGHT:
                    continue

                image_bytes = base_image["image"]
                ext = base_image.get("ext", "png")
                filename = f"{prefix}_p{page_num}_{img_index}.{ext}"
                out_path = config.IMAGE_DIR / filename

                # Avoid rewriting existing images on re-processing.
                if not out_path.exists():
                    with open(out_path, "wb") as f:
                        f.write(image_bytes)

                image_paths.append(str(out_path))

            pages.append(
                {
                    "page_num": page_num,
                    "text": text,
                    "images": image_paths,
                }
            )

    return pages


def chunk_pages(
    pages: list,
    source_name: str,
    chunk_size: Optional[int] = None,
    overlap: Optional[int] = None,
) -> list[dict]:
    """
    Split each page's text into overlapping chunks. Pages with no
    extractable text but at least one image still produce a
    placeholder chunk so the image remains discoverable.
    """
    chunk_size = chunk_size or config.CHUNK_SIZE
    overlap = overlap or config.CHUNK_OVERLAP

    # Guard against a misconfigured overlap >= chunk_size, which would
    # make `start` stop advancing and loop forever.
    if overlap >= chunk_size:
        overlap = max(chunk_size // 4, 0)

    chunks = []

    for page in pages:
        text = page["text"]

        if not text:
            if page["images"]:
                chunks.append(
                    _make_chunk(page, "[Image content on this page]", source_name)
                )
            continue

        start = 0
        while start < len(text):
            end = start + chunk_size
            piece = text[start:end]
            chunks.append(_make_chunk(page, piece, source_name))

            if end >= len(text):
                break

            start = end - overlap

    return chunks


def _make_chunk(page: dict, piece_text: str, source_name: str) -> dict:
    raw_id = f"{source_name}_{page['page_num']}_{piece_text[:30]}_{len(piece_text)}"
    chunk_id = hashlib.md5(raw_id.encode("utf-8")).hexdigest()

    return {
        "id": chunk_id,
        "text": piece_text.strip(),
        "page_num": page["page_num"],
        "images": page["images"],
        "source": source_name,
    }


def process_pdf(pdf_path: str) -> list[dict]:
    """Full pipeline: extract text/images, then chunk. Returns chunks."""
    source_name = Path(pdf_path).name
    pages = extract_text_and_images(pdf_path)
    chunks = chunk_pages(pages, source_name=source_name)
    return chunks


class PDFProcessor:
    """Thin OOP wrapper kept for backwards-compatible imports/tests."""

    def process_pdf(self, pdf_path: str) -> list[dict]:
        return process_pdf(pdf_path)

    def extract_text_and_images(self, pdf_path: str) -> list[dict]:
        return extract_text_and_images(pdf_path)

    def chunk_pages(self, pages, source_name: str, chunk_size=None, overlap=None):
        return chunk_pages(pages, source_name, chunk_size, overlap)
