import pytest

from rag.chunker import chunk_pages


def test_chunker_preserves_source():
    pages = [{
        "page": 3,
        "filename": "notes.pdf",
        "text": "A" * 2000,
    }]

    chunks = chunk_pages(pages)

    assert len(chunks) == 3
    assert all(len(chunk["text"]) <= 900 for chunk in chunks)
    assert all(chunk["filename"] == "notes.pdf" for chunk in chunks)
    assert all(chunk["page"] == 3 for chunk in chunks)


def test_empty_pages():
    assert chunk_pages([]) == []
    assert chunk_pages([{
        "page": 1,
        "filename": "empty.pdf",
        "text": "   ",
    }]) == []


def test_invalid_chunk_settings():
    with pytest.raises(ValueError):
        chunk_pages([], chunk_size=0)

    with pytest.raises(ValueError):
        chunk_pages([], chunk_size=100, overlap=100)