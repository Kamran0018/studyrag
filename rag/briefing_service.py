import json
import os
from rag.gemini_service import get_gemini_client


def generate_document_briefing(document):
    """
    Generates an executive briefing for a document including:
    - 4-5 line executive summary
    - 4-6 key concepts
    - Key definitions
    - 5 tailored suggested study/interview questions
    """
    chunks = document.chunks.all().order_by("chunk_index")[:10]
    if not chunks.exists():
        return {}

    context = "\n\n".join([f"[{c.chunk_index}] {c.text}" for c in chunks])

    client = get_gemini_client()
    model_name = (os.getenv("GEMINI_CHAT_MODEL") or "").strip() or "gemini-2.5-flash"

    prompt = f"""
You are StudyRAG, an elite academic and professional document intelligence engine.
Analyze this document and generate a structured executive briefing.

Return ONLY a valid JSON object matching this exact schema:
{{
  "summary": "A concise, high-impact 4-5 line summary explaining what this document is, who/what it concerns, and its main purpose.",
  "key_concepts": ["Concept 1", "Concept 2", "Concept 3", "Concept 4"],
  "key_definitions": [
    {{"term": "Term Name", "definition": "Brief, accurate definition from context"}}
  ],
  "suggested_questions": [
    "Thoughtful question 1 based on specific details",
    "Thoughtful question 2 based on specific details",
    "Thoughtful question 3 based on specific details",
    "Thoughtful question 4 based on specific details",
    "Thoughtful question 5 based on specific details"
  ]
}}

DOCUMENT CONTEXT:
{context}
"""

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config={
                "response_mime_type": "application/json"
            }
        )
        data = json.loads(response.text)
        return data
    except Exception as e:
        print("Failed to generate briefing:", repr(e))
        return {
            "summary": f"Document indexed with {document.chunks.count()} knowledge chunks. Ready for citation-backed inquiry.",
            "key_concepts": ["Core Subject Matter", "Key Points", "Study Material"],
            "key_definitions": [],
            "suggested_questions": [
                "Summarize the key takeaways of this document.",
                "What are the main topics and concepts discussed?",
                "List the critical skills or definitions mentioned.",
                "Explain the primary conclusions.",
                "Generate 3 practice questions from this material."
            ]
        }
