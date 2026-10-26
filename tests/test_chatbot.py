import io
import json
import pytest
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from accounts.models import User
from chatbot.models import Document, DocumentChunk, ChatMessage


@pytest.fixture
def user_a(db):
    return User.objects.create_user(username="student_a", email="student_a@example.com", password="password123")


@pytest.fixture
def user_b(db):
    return User.objects.create_user(username="student_b", email="student_b@example.com", password="password123")


@pytest.fixture
def sample_document(db, user_a):
    file_content = b"Mock document content"
    uploaded = SimpleUploadedFile("physics_notes.pdf", file_content, content_type="application/pdf")
    doc = Document.objects.create(user=user_a, title="physics_notes.pdf", file=uploaded)
    DocumentChunk.objects.create(
        document=doc,
        text="Quantum mechanics is a fundamental theory in physics.",
        page="1",
        chunk_index=0,
    )
    return doc


@pytest.mark.django_db
def test_document_properties(sample_document):
    assert sample_document.chunk_count == 1
    assert sample_document.message_count == 0
    assert sample_document.file_extension == "PDF"
    assert "physics_notes.pdf" in str(sample_document)


@pytest.mark.django_db
def test_upload_view_requires_login(client):
    url = reverse("document_upload")
    response = client.get(url)
    assert response.status_code == 302
    assert "login" in response.url


@pytest.mark.django_db
def test_upload_invalid_extension(client, user_a):
    client.force_login(user_a)
    url = reverse("document_upload")
    bad_file = SimpleUploadedFile("malicious.exe", b"binary content", content_type="application/octet-stream")
    response = client.post(url, {"file": bad_file}, follow=True)
    assert response.status_code == 200
    assert Document.objects.filter(title="malicious.exe").count() == 0


@pytest.mark.django_db
@patch("chatbot.views.load_document")
@patch("chatbot.views.chunk_pages")
def test_upload_valid_document_creates_chunks(mock_chunk, mock_load, client, user_a):
    mock_load.return_value = [{"page": 1, "filename": "test.pdf", "text": "Sample text"}]
    mock_chunk.return_value = [{"page": 1, "filename": "test.pdf", "text": "Sample text", "chunk_index": 0}]

    client.force_login(user_a)
    url = reverse("document_upload")
    valid_file = SimpleUploadedFile("test.pdf", b"%PDF-1.4 mock content", content_type="application/pdf")
    response = client.post(url, {"file": valid_file})

    assert response.status_code == 302
    doc = Document.objects.filter(user=user_a, title="test.pdf").first()
    assert doc is not None
    assert doc.chunks.count() == 1
    assert doc.chunks.first().text == "Sample text"


@pytest.mark.django_db
def test_chat_page_render(client, user_a, sample_document):
    client.force_login(user_a)
    url = reverse("document_chat", kwargs={"document_id": sample_document.id})
    response = client.get(url)
    assert response.status_code == 200
    assert sample_document.title in response.content.decode("utf-8")


@pytest.mark.django_db
def test_user_cannot_access_other_users_document(client, user_b, sample_document):
    client.force_login(user_b)
    url = reverse("document_chat", kwargs={"document_id": sample_document.id})
    response = client.get(url)
    assert response.status_code == 404


@pytest.mark.django_db
@patch("chatbot.views.answer_document_question")
def test_chat_ajax_flow(mock_answer, client, user_a, sample_document):
    mock_answer.return_value = {
        "answer": "Quantum mechanics describes microscopic physical phenomena.",
        "sources": [{"filename": "physics_notes.pdf", "page": "1", "chunk_index": 0}],
        "evidence": {
            "strength": "Strong",
            "score": 90,
            "badge_color": "success",
            "matched_chunks": 1,
            "description": "High keyword and context density.",
        },
    }

    client.force_login(user_a)
    url = reverse("document_chat", kwargs={"document_id": sample_document.id})
    payload = {"question": "What is quantum mechanics?", "language": "hinglish"}

    response = client.post(
        url,
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Quantum mechanics" in data["answer"]
    assert len(data["sources"]) == 1
    assert data["language"] == "hinglish"
    assert data["evidence"]["strength"] == "Strong"

    # Verify message was saved to database
    msg = ChatMessage.objects.filter(document=sample_document).first()
    assert msg is not None
    assert msg.question == "What is quantum mechanics?"
    assert msg.user == user_a
    assert msg.language == "hinglish"
    assert msg.evidence["strength"] == "Strong"


@pytest.mark.django_db
@patch("chatbot.views.generate_document_briefing")
def test_regenerate_briefing(mock_briefing, client, user_a, sample_document):
    mock_briefing.return_value = {
        "summary": "Updated physics summary.",
        "key_concepts": ["Quantum Mechanics", "Wave-Particle Duality"],
        "key_definitions": [{"term": "Photon", "definition": "Quantum of light"}],
        "suggested_questions": ["What is a photon?"],
    }

    client.force_login(user_a)
    url = reverse("document_regenerate_briefing", kwargs={"document_id": sample_document.id})
    response = client.post(url)
    assert response.status_code == 302

    sample_document.refresh_from_db()
    assert sample_document.briefing["summary"] == "Updated physics summary."
    assert "Photon" in sample_document.briefing["key_definitions"][0]["term"]


@pytest.mark.django_db
def test_clear_chat_history(client, user_a, sample_document):
    ChatMessage.objects.create(
        document=sample_document,
        user=user_a,
        question="Q1",
        answer="A1",
    )
    assert sample_document.chat_messages.count() == 1

    client.force_login(user_a)
    url = reverse("document_clear_history", kwargs={"document_id": sample_document.id})
    response = client.post(url)
    assert response.status_code == 302
    assert sample_document.chat_messages.count() == 0


@pytest.mark.django_db
def test_delete_document(client, user_a, sample_document):
    client.force_login(user_a)
    url = reverse("document_delete", kwargs={"document_id": sample_document.id})
    response = client.post(url)
    assert response.status_code == 302
    assert Document.objects.filter(id=sample_document.id).count() == 0
