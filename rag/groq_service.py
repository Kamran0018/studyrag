import json
import os
import threading
from dotenv import load_dotenv

load_dotenv()

_groq_key_lock = threading.Lock()
_current_groq_key_idx = 0

DEFAULT_GROQ_CHAT_MODEL = "openai/gpt-oss-120b"
FALLBACK_GROQ_CHAT_MODELS = [
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
    "llama-3.3-70b-versatile",
]


class GroqResponseWrapper:
    """
    Standardized response wrapper matching the interface expected across StudyRAG services.
    Provides .text and .raw_response.
    """
    def __init__(self, text, raw_response=None):
        self.text = text or ""
        self.raw_response = raw_response


def get_all_groq_api_keys():
    """
    Collects all unique Groq API keys configured in the environment.
    Supports:
    - Multiple GROQ_API_KEY lines directly parsed from .env
    - Comma-separated in GROQ_API_KEYS or GROQ_API_KEY
    - Numbered keys: GROQ_API_KEY_1, GROQ_API_KEY_2, etc.
    """
    keys = []

    # 1. Parse directly from .env file to support multiple GROQ_API_KEY entries
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
                    if k.startswith("GROQ_API_KEY") and v:
                        for part in v.split(","):
                            cleaned = part.strip().strip("'\"")
                            if cleaned and cleaned not in keys:
                                keys.append(cleaned)
        except Exception as e:
            print("Error reading .env directly in Groq key pool:", repr(e))

    # 2. Check os.environ
    for env_k, env_v in os.environ.items():
        if env_k.startswith("GROQ_API_KEY") and env_v:
            for part in env_v.split(","):
                cleaned = part.strip().strip("'\"")
                if cleaned and cleaned not in keys:
                    keys.append(cleaned)

    return keys


def get_groq_client(api_key=None):
    from groq import Groq

    if not api_key:
        keys = get_all_groq_api_keys()
        if not keys:
            raise ValueError(
                "GROQ_API_KEY is missing. Please configure it in your .env file."
            )
        api_key = keys[0]

    return Groq(api_key=api_key)


def generate_groq_content(model=None, contents=None, messages=None, config=None, json_mode=False):
    """
    Executes a Groq API call with automatic multi-key failover and quota pooling.
    If the current key hits a rate limit (429 / rate_limit_exceeded),
    it immediately switches to the next available API key in the pool and retries.
    """
    global _current_groq_key_idx
    from groq import Groq

    keys = get_all_groq_api_keys()
    if not keys:
        raise ValueError(
            "GROQ_API_KEY is missing. Please configure it in your .env file."
        )

    if not model:
        model = (os.getenv("GROQ_CHAT_MODEL") or "").strip() or DEFAULT_GROQ_CHAT_MODEL

    if messages is None:
        if isinstance(contents, str):
            messages = [{"role": "user", "content": contents}]
        elif isinstance(contents, list):
            messages = contents
        else:
            messages = [{"role": "user", "content": str(contents or "")}]

    # Support json_mode from config or boolean
    if config and isinstance(config, dict):
        if config.get("response_mime_type") == "application/json":
            json_mode = True

    response_format = {"type": "json_object"} if json_mode else None

    last_exception = None
    num_keys = len(keys)

    with _groq_key_lock:
        start_idx = _current_groq_key_idx % num_keys

    for attempt in range(num_keys):
        idx = (start_idx + attempt) % num_keys
        api_key = keys[idx]
        masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"

        try:
            client = Groq(api_key=api_key)
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": 0.2 if json_mode else 0.4,
            }
            if response_format:
                kwargs["response_format"] = response_format

            completion = client.chat.completions.create(**kwargs)
            text_result = completion.choices[0].message.content or ""

            # Advance index for round-robin load distribution
            with _groq_key_lock:
                _current_groq_key_idx = (idx + 1) % num_keys

            return GroqResponseWrapper(text=text_result, raw_response=completion)

        except Exception as err:
            err_str = str(err)
            last_exception = err

            # If the model was deprecated or not found on Groq, try fallback models
            if "model_not_found" in err_str.lower() or "not found" in err_str.lower() or "decommissioned" in err_str.lower():
                for fallback in FALLBACK_GROQ_CHAT_MODELS:
                    if fallback != model:
                        try:
                            kwargs["model"] = fallback
                            completion = client.chat.completions.create(**kwargs)
                            text_result = completion.choices[0].message.content or ""
                            with _groq_key_lock:
                                _current_groq_key_idx = (idx + 1) % num_keys
                            return GroqResponseWrapper(text=text_result, raw_response=completion)
                        except Exception as fb_err:
                            last_exception = fb_err
                            continue

            # Check if this error looks like a rate limit / quota exhaustion
            is_rate_limit = (
                "429" in err_str
                or "rate_limit" in err_str.lower()
                or "quota" in err_str.lower()
                or "tokens per minute" in err_str.lower()
                or "requests per minute" in err_str.lower()
            )

            if num_keys > 1 and attempt < num_keys - 1 and is_rate_limit:
                next_idx = (idx + 1) % num_keys
                next_key = keys[next_idx]
                next_masked = next_key[:8] + "..." + next_key[-4:] if len(next_key) > 12 else "***"
                print(
                    f"⚠️ [StudyRAG Groq Key Pool] Key #{idx + 1} ({masked_key}) rate-limited: {err}. "
                    f"Auto-switching to Key #{next_idx + 1} ({next_masked})..."
                )
                continue
            else:
                raise last_exception

    raise last_exception


def generate_answer(question, context, language="english", evidence_strength="Strong"):
    """
    Generates a structured, citation-grounded response using Groq.
    Maintains complete parity with StudyRAG formatting standards.
    """
    language_instruction = """
### STRICT LANGUAGE STANDARD:
- Respond in fluent, clear, executive English only.
- Under NO circumstances use Hindi, Hinglish, or mixed-language phrasing (e.g. never use "ke", "mein", "aur", "mutabik", "hai", or "(Hinglish)").
- All headings, sections, explanations, bullet points, and tables must be strictly in fluent English.
"""

    evidence_instruction = ""
    if evidence_strength == "Insufficient":
        evidence_instruction = """
### EVIDENCE ADVISORY:
- The textual evidence in the provided context is limited for this specific query.
- Explicitly state what IS and what IS NOT directly mentioned in the document.
- Do NOT guess or hallucinate unverified details.
"""

    prompt = f"""You are StudyRAG, an elite academic and professional document intelligence assistant powered by Groq ultra-low-latency inference.

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

    model_name = (os.getenv("GROQ_CHAT_MODEL") or "").strip() or DEFAULT_GROQ_CHAT_MODEL

    response = generate_groq_content(
        model=model_name,
        contents=prompt,
    )

    return response.text or "No answer was generated."


def generate_groq_briefing(chunks_text):
    """
    Generates an executive briefing for a document using Groq JSON mode.
    """
    prompt = f"""You are StudyRAG, an elite academic and professional document intelligence engine.
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
{chunks_text}
"""

    model_name = (os.getenv("GROQ_CHAT_MODEL") or "").strip() or DEFAULT_GROQ_CHAT_MODEL

    response = generate_groq_content(
        model=model_name,
        contents=prompt,
        json_mode=True,
    )

    return json.loads(response.text)
