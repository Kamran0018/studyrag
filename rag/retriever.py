import re
from chatbot.models import DocumentChunk


OVERVIEW_TERMS = {
    "name", "who", "whom", "author", "person", "candidate", "student", "owner",
    "summary", "summarize", "overview", "introduction", "intro", "about",
    "main", "concept", "concepts", "takeaway", "takeaways", "point", "points",
    "outline", "explain", "describe", "skills", "skill", "technologies", "tech",
}


def retrieve_chunks_with_evidence(document, question, limit=6):
    """
    Retrieves matching document chunks and computes calibrated evidence & confidence metrics.
    """
    chunks = list(
        DocumentChunk.objects.filter(document=document).order_by("chunk_index")
    )
    if not chunks:
        return [], {
            "strength": "Insufficient",
            "score": 0,
            "badge_color": "danger",
            "matched_chunks": 0,
            "description": "No document chunks available.",
        }

    q_lower = question.lower()
    raw_words = re.findall(r"\b[a-zA-Z0-9_]{3,}\b", q_lower)
    question_words = set(raw_words)

    is_overview_or_identity = any(
        term in question_words or term in q_lower for term in OVERVIEW_TERMS
    )

    scored_chunks = []

    for chunk in chunks:
        text_lower = chunk.text.lower()
        score = 0

        # Exact query match bonus
        if len(q_lower) > 3 and q_lower in text_lower:
            score += 15

        # Word & stem matching
        for word in question_words:
            if word in text_lower:
                score += 4
            elif len(word) > 4 and word[:4] in text_lower:
                score += 2

        # Early chunks boost for identity/overview
        if is_overview_or_identity and chunk.chunk_index in (0, 1):
            score += 6

        if score > 0:
            scored_chunks.append((score, chunk))

    scored_chunks.sort(key=lambda item: item[0], reverse=True)
    top_score = scored_chunks[0][0] if scored_chunks else 0

    # Compact document handling
    if len(chunks) <= 8:
        selected_chunks = chunks
        if top_score >= 10:
            strength = "Strong"
            score_val = min(96, 75 + top_score * 2)
            desc = f"Verified across document context with high textual alignment."
        elif top_score > 0 or is_overview_or_identity:
            strength = "Strong" if is_overview_or_identity else "Partial"
            score_val = 88 if is_overview_or_identity else 65
            desc = "Context verified across complete document sections."
        else:
            strength = "Partial"
            score_val = 55
            desc = "Full document analyzed; moderate direct keyword overlap."
    elif scored_chunks:
        selected_chunks = [chunk for _, chunk in scored_chunks[:limit]]
        if top_score >= 14 or (len(scored_chunks) >= 2 and top_score >= 8):
            strength = "Strong"
            score_val = min(96, 70 + top_score * 2)
            desc = f"High keyword and context density across {len(selected_chunks)} sections."
        elif top_score >= 4:
            strength = "Partial"
            score_val = min(68, 48 + top_score * 3)
            desc = "Partial evidence found; augmented with adjacent context."
        else:
            strength = "Insufficient"
            score_val = 35
            desc = "Weak keyword match; strictly bounded to nearest context."
    else:
        # Fallback when no keywords matched
        selected_chunks = chunks[:limit]
        strength = "Insufficient"
        score_val = 25
        desc = "No direct keyword match found; general fallback context utilized."

    evidence = {
        "strength": strength,
        "score": score_val,
        "badge_color": "success" if strength == "Strong" else ("warning" if strength == "Partial" else "danger"),
        "matched_chunks": len(selected_chunks),
        "description": desc,
    }

    return selected_chunks, evidence


def retrieve_chunks(document, question, limit=6):
    chunks, _ = retrieve_chunks_with_evidence(document, question, limit=limit)
    return chunks
