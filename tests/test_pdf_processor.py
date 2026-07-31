"""Tests for src/pdf_processor.py — uses the bundled sample PDF."""

from src.pdf_processor import chunk_pages, extract_text_and_images, process_pdf


def test_extract_text_and_images_returns_pages(sample_pdf_path):
    pages = extract_text_and_images(sample_pdf_path)

    assert isinstance(pages, list)
    assert len(pages) > 0

    first_page = pages[0]
    assert "page_num" in first_page
    assert "text" in first_page
    assert "images" in first_page
    assert first_page["page_num"] == 1


def test_extract_text_and_images_missing_file_raises():
    try:
        extract_text_and_images("data/pdfs/does_not_exist.pdf")
        assert False, "Expected FileNotFoundError"
    except FileNotFoundError:
        pass


def test_chunk_pages_produces_chunks_with_metadata(sample_pdf_path):
    pages = extract_text_and_images(sample_pdf_path)
    chunks = chunk_pages(pages, source_name="football_tutorial.pdf")

    assert len(chunks) > 0

    for chunk in chunks:
        assert chunk["id"]
        assert isinstance(chunk["page_num"], int)
        assert chunk["source"] == "football_tutorial.pdf"
        assert isinstance(chunk["images"], list)


def test_chunk_ids_are_unique(sample_pdf_path):
    pages = extract_text_and_images(sample_pdf_path)
    chunks = chunk_pages(pages, source_name="football_tutorial.pdf")

    ids = [c["id"] for c in chunks]
    assert len(ids) == len(set(ids))


def test_process_pdf_end_to_end(sample_pdf_path):
    chunks = process_pdf(sample_pdf_path)
    assert len(chunks) > 0
