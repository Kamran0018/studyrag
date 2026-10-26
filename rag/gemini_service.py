import os
from dotenv import load_dotenv
from google import genai

load_dotenv()


def get_gemini_client():
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY missing hai. Project ki .env file check karo."
        )

    return genai.Client(api_key=api_key)


def generate_answer(question, context, language="english", evidence_strength="Strong"):
    client = get_gemini_client()

    language_instruction = ""
    if language.lower() == "hinglish":
        language_instruction = """
### HINGLISH LEARNING MODE (ACTIVE):
- Explain in natural, student-friendly HINGLISH (a conversational mix of Hindi written in Latin/English script with technical terms kept in English).
- Example style: "Is document ke anusaar, candidate ke paas Python aur Django ka accha practical experience hai..."
- Keep all technical terms, code snippets, framework names, metrics, and quotes in clean English.
- Make the explanation engaging, intuitive, and easy for students to grasp.
"""
    else:
        language_instruction = """
### LANGUAGE STANDARD:
- Respond in fluent, executive English.
"""

    evidence_instruction = ""
    if evidence_strength == "Insufficient":
        evidence_instruction = """
### EVIDENCE ADVISORY:
- The textual evidence in the provided context is limited for this specific query.
- Explicitly state what IS and what IS NOT directly mentioned in the document.
- Do NOT guess or hallucinate unverified details.
"""

    prompt = f"""
You are StudyRAG, an elite academic and professional document intelligence assistant.

Your goal is to provide an executive, beautifully structured, and highly professional response using Markdown, strictly grounded in the supplied document context.

{language_instruction}
{evidence_instruction}

### Formatting & Presentation Standards:
1. **Executive Direct Answer**: Begin with a crisp, direct summary (1-2 sentences) directly addressing the query.
2. **Structured Sections & Bullet Points**:
   - Use Markdown section headings (`### Section Title`) for multi-part answers.
   - Organize items with structured bullet points using bold lead-in tags (e.g. `- **Category / Skill / Item**: Description or context`).
   - Use numbered lists for processes, steps, or chronological timelines.
   - Use clean Markdown tables where comparing items, technologies, or attributes.
3. **Visual Polish**: Maintain clean line breaks, concise paragraphs, and prominent highlights for key names, tools, terms, or metrics.
4. **Strict Grounding**: Rely strictly on facts stated in the document context. Never hallucinate or assume unstated details.
5. **Missing Information**: If the requested information is completely absent from the document context, state:
   "Not found in the provided document." and briefly state what relevant context IS available in the document.

DOCUMENT CONTEXT:
{context}

QUESTION:
{question}
"""

    model_name = (os.getenv("GEMINI_CHAT_MODEL") or "").strip() or "gemini-2.5-flash"

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
    )

    return response.text or "No answer was generated."
