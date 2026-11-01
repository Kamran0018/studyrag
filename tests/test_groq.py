import pytest
from unittest.mock import MagicMock
from rag.groq_service import (
    get_all_groq_api_keys,
    get_groq_client,
    generate_groq_content,
    generate_answer as generate_groq_answer,
    GroqResponseWrapper,
)
from rag.answer_service import answer_document_question


def test_get_all_groq_api_keys_pool(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_key_alpha,gsk_key_beta")
    monkeypatch.setenv("GROQ_API_KEY_3", "gsk_key_gamma")
    keys = get_all_groq_api_keys()
    assert "gsk_key_alpha" in keys
    assert "gsk_key_beta" in keys
    assert "gsk_key_gamma" in keys


def test_get_groq_client_missing_key(monkeypatch):
    monkeypatch.setattr("rag.groq_service.get_all_groq_api_keys", lambda: [])
    with pytest.raises(ValueError, match="GROQ_API_KEY is missing"):
        get_groq_client()


def test_generate_groq_content_failover(monkeypatch):
    import rag.groq_service as groq_mod

    monkeypatch.setattr(groq_mod, "get_all_groq_api_keys", lambda: ["gsk_key1", "gsk_key2"])
    monkeypatch.setattr(groq_mod, "_current_groq_key_idx", 0)

    attempt_keys = []

    class FakeCompletions:
        def __init__(self, key):
            self.key = key

        def create(self, **kwargs):
            attempt_keys.append(self.key)
            if self.key == "gsk_key1":
                raise Exception("429 Too Many Requests: rate_limit_exceeded")
            
            mock_choice = MagicMock()
            mock_choice.message.content = "Success from Groq key2"
            mock_resp = MagicMock()
            mock_resp.choices = [mock_choice]
            return mock_resp

    class FakeGroqClient:
        def __init__(self, api_key):
            self.api_key = api_key
            self.chat = MagicMock()
            self.chat.completions = FakeCompletions(api_key)

    monkeypatch.setattr("groq.Groq", FakeGroqClient)

    resp = generate_groq_content(model="llama-3.3-70b-versatile", contents="Hello world")
    assert resp.text == "Success from Groq key2"
    assert "gsk_key1" in attempt_keys
    assert "gsk_key2" in attempt_keys


def test_generate_groq_answer(monkeypatch):
    import rag.groq_service as groq_mod

    captured_prompt = []

    def fake_generate(model, contents, **kwargs):
        captured_prompt.append(contents)
        return GroqResponseWrapper(text="Test answer from Groq")

    monkeypatch.setattr(groq_mod, "generate_groq_content", fake_generate)

    # Test English
    ans_en = generate_groq_answer("What is quantum?", "Quantum physics context")
    assert ans_en == "Test answer from Groq"
    assert "fluent, clear, executive English" in captured_prompt[0]



@pytest.fixture
def sample_document(db):
    from accounts.models import User
    from chatbot.models import Document, DocumentChunk
    from django.core.files.uploadedfile import SimpleUploadedFile

    user = User.objects.create_user(username="test_groq_user", email="groq@example.com", password="password123")
    uploaded = SimpleUploadedFile("physics_groq.pdf", b"Content for Groq", content_type="application/pdf")
    doc = Document.objects.create(user=user, title="physics_groq.pdf", file=uploaded)
    DocumentChunk.objects.create(
        document=doc,
        text="Quantum mechanics is a fundamental theory in physics.",
        page="1",
        chunk_index=0,
    )
    return doc


@pytest.mark.django_db
def test_answer_document_question_groq(monkeypatch, sample_document):
    monkeypatch.setattr("rag.groq_service.get_all_groq_api_keys", lambda: ["gsk_key1"])
    monkeypatch.setattr(
        "rag.answer_service.generate_groq_answer",
        lambda question, context, language, evidence_strength: "Answer via Groq",
    )

    result = answer_document_question(
        document=sample_document,
        question="What is this document about?",
    )

    assert result["answer"] == "Answer via Groq"
    assert result["evidence"]["provider"] == "groq"
    assert result["evidence"]["model"] in ("openai/gpt-oss-120b", "llama-3.3-70b-versatile")
