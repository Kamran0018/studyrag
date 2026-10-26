
def chunk_pages(pages, chunk_size=900, overlap=150):
    """
    Split extracted document pages into overlapping text chunks.

    Each page must contain:
    - page: page number or section name
    - text: extracted text
    - filename: source filename
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and < chunk_size.")

    chunks = []

    for page_data in pages:
        text = page_data.get("text", "").strip()

        if not text:
            continue

        start = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append({
                    "text": chunk_text,
                    "filename": page_data["filename"],
                    "page": page_data["page"],
                })

            if end == len(text):
                break

            start = end - overlap

    return chunks
