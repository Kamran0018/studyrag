import os
from rag.retriever import retrieve_chunks_with_evidence
from rag.groq_service import generate_answer as generate_groq_answer, DEFAULT_GROQ_CHAT_MODEL


def answer_document_question(document, question, language="english", **kwargs):
    """
    Answers a question based on retrieved document chunks using Groq LLM inference.
    """
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

        file_url = ""
        try:
            if chunk.document.file:
                file_url = chunk.document.file.url
        except Exception:
            file_url = ""

        sources.append({
            "filename": chunk.document.title,
            "page": str(chunk.page),
            "chunk_index": chunk.chunk_index,
            "snippet": chunk.text[:350] + ("..." if len(chunk.text) > 350 else ""),
            "text": chunk.text,
            "file_url": file_url,
        })

    context = "\n\n".join(context_parts)
    answer = generate_groq_answer(
        question,
        context,
        language=language,
        evidence_strength=evidence.get("strength", "Strong"),
    )
    evidence["provider"] = "groq"
    evidence["model"] = (os.getenv("GROQ_CHAT_MODEL") or "").strip() or DEFAULT_GROQ_CHAT_MODEL

    return {
        "answer": answer,
        "sources": sources,
        "evidence": evidence,
    }
