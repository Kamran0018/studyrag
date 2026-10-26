
from pathlib import Path

from pypdf import PdfReader
from docx import Document as DocxDocument


def load_pdf(file_path):
    """Extract text from a PDF, preserving its page numbers."""
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported by load_pdf().")

    reader = PdfReader(str(path))
    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()

        if text:
            pages.append({
                "page": page_number,
                "text": text,
                "filename": path.name,
            })

    if not pages:
        raise ValueError(
            "No extractable text found. This PDF may be empty "
            "or scanned. OCR is not supported yet."
        )

    return pages


def load_docx(file_path):
    """Extract DOCX paragraphs, grouped into numbered sections."""
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    if path.suffix.lower() != ".docx":
        raise ValueError("Only DOCX files are supported by load_docx().")

    document = DocxDocument(str(path))
    sections = []
    current_paragraphs = []
    section_number = 1

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()

        if not text:
            continue

        current_paragraphs.append(text)

        # Group paragraphs into manageable sections.
        if sum(len(p) for p in current_paragraphs) >= 900:
            sections.append({
                "page": f"section {section_number}",
                "text": "\n".join(current_paragraphs),
                "filename": path.name,
            })
            section_number += 1
            current_paragraphs = []

    if current_paragraphs:
        sections.append({
            "page": f"section {section_number}",
            "text": "\n".join(current_paragraphs),
            "filename": path.name,
        })

    if not sections:
        raise ValueError("No readable paragraphs found in this DOCX file.")

    return sections


def load_document(file_path):
    """Load a PDF or DOCX based on its extension."""
    path = Path(file_path)
    extension = path.suffix.lower()

    if extension == ".pdf":
        return load_pdf(path)

    if extension == ".docx":
        return load_docx(path)

    raise ValueError("Unsupported file type. Upload a PDF or DOCX file.")
