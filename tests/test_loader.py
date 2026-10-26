import pytest
from docx import Document
from pypdf import PdfWriter

from rag.loader import load_document, load_pdf, load_docx


def test_missing_file():
    with pytest.raises(FileNotFoundError):
        load_document("missing.pdf")


def test_unsupported_extension(tmp_path):
    file_path = tmp_path / "notes.txt"
    file_path.write_text("Sample text")

    with pytest.raises(ValueError, match="Unsupported file type"):
        load_document(file_path)


def test_empty_pdf(tmp_path):
    file_path = tmp_path / "empty.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)

    with file_path.open("wb") as file:
        writer.write(file)

    with pytest.raises(ValueError, match="No extractable text"):
        load_pdf(file_path)


def test_docx_loading(tmp_path):
    file_path = tmp_path / "notes.docx"
    document = Document()
    document.add_paragraph("StudyRAG test paragraph")
    document.save(file_path)

    sections = load_docx(file_path)

    assert len(sections) == 1
    assert sections[0]["filename"] == "notes.docx"
    assert sections[0]["page"] == "section 1"
    assert "StudyRAG test paragraph" in sections[0]["text"]