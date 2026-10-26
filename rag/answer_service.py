from rag.retriever import retrieve_chunks_with_evidence
from rag.gemini_service import generate_answer


def answer_document_question(document, question, language="english"):
    question = question.strip()

    if not question:
        return {
            "answer": "Please enter a question.",
            "sources": [],
            "evidence": {
                "strength": "Insufficient",
                "score": 0,
                "badge_color": "danger",
                "matched_chunks": 0,
                "description": "Empty question entered.",
            },
        }

    chunks, evidence = retrieve_chunks_with_evidence(document, question)

    if not chunks:
        return {
            "answer": "Not found in the provided document.",
            "sources": [],
            "evidence": evidence,
        }

    context_parts = []
    sources = []

    for chunk in chunks:
        context_parts.append(
            f"[Source: {chunk.document.title}, "
            f"Page/Section: {chunk.page}]\n{chunk.text}"
        )

        sources.append({
            "filename": chunk.document.title,
            "page": chunk.page,
            "chunk_index": chunk.chunk_index,
        })

    context = "\n\n".join(context_parts)
    answer = generate_answer(
        question,
        context,
        language=language,
        evidence_strength=evidence.get("strength", "Strong"),
    )

    return {
        "answer": answer,
        "sources": sources,
        "evidence": evidence,
    }
