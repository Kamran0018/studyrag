import os
import threading
from dotenv import load_dotenv
from google import genai

load_dotenv()

_key_lock = threading.Lock()
_current_key_idx = 0


def get_all_api_keys():
    """
    Collects all unique Google Gemini API keys configured in the environment.
    Supports:
    - Multiple GOOGLE_API_KEY lines directly parsed from .env
    - Comma-separated in GOOGLE_API_KEYS or GOOGLE_API_KEY
    - Numbered keys: GOOGLE_API_KEY_1, GOOGLE_API_KEY_2, etc.
    """
    keys = []

    # 1. Parse directly from .env file to support multiple GOOGLE_API_KEY entries
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if k.startswith("GOOGLE_API_KEY") and v:
                        for part in v.split(","):
                            cleaned = part.strip().strip("'\"")
                            if cleaned and cleaned not in keys:
                                keys.append(cleaned)
        except Exception as e:
            print("Error reading .env directly in StudyRAG key pool:", repr(e))

    # 2. Check os.environ
    for env_k, env_v in os.environ.items():
        if env_k.startswith("GOOGLE_API_KEY") and env_v:
            for part in env_v.split(","):
                cleaned = part.strip().strip("'\"")
                if cleaned and cleaned not in keys:
                    keys.append(cleaned)

    return keys


def get_gemini_client(api_key=None):
    if not api_key:
        keys = get_all_api_keys()
        if not keys:
            raise ValueError(
                "GOOGLE_API_KEY missing hai. Project ki .env file check karo."
            )
        api_key = keys[0]

    return genai.Client(api_key=api_key)


def generate_gemini_content(model, contents, config=None):
    """
    Executes a Gemini API call with automatic multi-key failover and quota pooling.
    If the current key hits a rate limit (429 / RESOURCE_EXHAUSTED / quota limit),
    it immediately switches to the next available API key in the pool and retries.
    """
    global _current_key_idx
    keys = get_all_api_keys()

    if not keys:
        raise ValueError(
            "GOOGLE_API_KEY missing hai. Project ki .env file check karo."
        )

    last_exception = None
    num_keys = len(keys)

    with _key_lock:
        start_idx = _current_key_idx % num_keys

    for attempt in range(num_keys):
        idx = (start_idx + attempt) % num_keys
        api_key = keys[idx]
        masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"

        try:
            client = genai.Client(api_key=api_key)
            kwargs = {"model": model, "contents": contents}
            if config:
                kwargs["config"] = config

            response = client.models.generate_content(**kwargs)

            # Advance index for round-robin load distribution
            with _key_lock:
                _current_key_idx = (idx + 1) % num_keys

            return response

        except Exception as err:
            err_str = str(err)
            is_quota_error = (
                "429" in err_str
                or "RESOURCE_EXHAUSTED" in err_str
                or "quota" in err_str.lower()
                or "rate" in err_str.lower()
            )

            last_exception = err

            if is_quota_error and num_keys > 1 and attempt < num_keys - 1:
                next_idx = (idx + 1) % num_keys
                next_key = keys[next_idx]
                next_masked = next_key[:8] + "..." + next_key[-4:] if len(next_key) > 12 else "***"
                print(
                    f"⚠️ [StudyRAG Key Pool] Key #{idx + 1} ({masked_key}) rate limit hit. "
                    f"Auto-switching to Key #{next_idx + 1} ({next_masked})..."
                )
                continue
            else:
                raise err

    raise last_exception


def generate_answer(question, context, language="english", evidence_strength="Strong"):
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

    response = generate_gemini_content(
        model=model_name,
        contents=prompt,
    )

    return response.text or "No answer was generated."
