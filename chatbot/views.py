import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from rag.answer_service import answer_document_question
from rag.briefing_service import generate_document_briefing
from rag.chunker import chunk_pages
from rag.loader import load_document
from .models import Document, DocumentChunk, ChatMessage


DEFAULT_SAMPLE_PROMPTS = [
    "Summarize the key concepts and main ideas.",
    "What are the most important takeaways from this document?",
    "List the critical definitions and formulas mentioned.",
    "Generate 3 practice exam questions based on this material.",
]


@login_required
def document_upload(request):
    if request.method == "POST":
        uploaded_file = request.FILES.get("file")

        if not uploaded_file:
            messages.error(request, "Please select a file to upload.")
            return redirect("document_upload")

        extension = uploaded_file.name.lower().rsplit(".", 1)[-1]
        if extension not in ("pdf", "docx"):
            messages.error(request, "Only PDF (.pdf) and DOCX (.docx) files are supported.")
            return redirect("document_upload")

        if uploaded_file.size > 10 * 1024 * 1024:
            messages.error(request, "Maximum allowed file size is 10 MB.")
            return redirect("document_upload")

        document = None
        try:
            document = Document.objects.create(
                user=request.user,
                title=uploaded_file.name,
                file=uploaded_file,
            )

            pages = load_document(document.file.path)
            chunks = chunk_pages(pages)

            if not chunks:
                document.delete()
                messages.error(request, "No readable text content found in the uploaded document.")
                return redirect("document_upload")

            chunk_objects = [
                DocumentChunk(
                    document=document,
                    text=chunk["text"],
                    page=str(chunk["page"]),
                    chunk_index=index,
                )
                for index, chunk in enumerate(chunks)
            ]
            DocumentChunk.objects.bulk_create(chunk_objects)

            # Generate smart briefing
            try:
                document.briefing = generate_document_briefing(document)
                document.save(update_fields=["briefing"])
            except Exception as e:
                print("Briefing generation deferred:", e)

            messages.success(
                request,
                f"'{document.title}' indexed successfully! "
                f"({len(pages)} sections/pages, {len(chunks)} knowledge chunks)",
            )
            return redirect("document_chat", document_id=document.id)

        except (ValueError, FileNotFoundError) as error:
            if document and document.id:
                document.delete()
            messages.error(request, f"Document processing failed: {error}")
            return redirect("document_upload")
        except Exception as error:
            if document and document.id:
                document.delete()
            messages.error(request, f"Unexpected error during indexing: {error}")
            return redirect("document_upload")

    documents = Document.objects.filter(user=request.user).order_by("-uploaded_at")

    # Aggregate stats for stat strip
    total_chunks = sum(d.chunk_count for d in documents)
    total_messages = sum(d.message_count for d in documents)

    return render(
        request,
        "chatbot/upload.html",
        {
            "documents": documents,
            "total_chunks": total_chunks,
            "total_messages": total_messages,
        },
    )


@login_required
def document_chat(request, document_id):
    document = get_object_or_404(Document, id=document_id, user=request.user)

    # Ensure document has a smart briefing
    if not document.briefing or not document.briefing.get("summary"):
        try:
            document.briefing = generate_document_briefing(document)
            document.save(update_fields=["briefing"])
        except Exception as e:
            print("Auto briefing generation skipped:", e)

    if request.method == "POST":
        is_ajax = (
            request.headers.get("x-requested-with") == "XMLHttpRequest"
            or "application/json" in request.headers.get("Accept", "")
            or request.content_type == "application/json"
        )

        question = ""
        language = "english"
        if request.content_type == "application/json":
            try:
                data = json.loads(request.body.decode("utf-8"))
                question = data.get("question", "").strip()
                language = data.get("language", "english").strip().lower()
            except Exception:
                question = ""
        else:
            question = request.POST.get("question", "").strip()
            language = request.POST.get("language", "english").strip().lower()

        if language not in ("english", "hinglish"):
            language = "english"

        if not question:
            if is_ajax:
                return JsonResponse({"success": False, "error": "Please enter a question."}, status=400)
            messages.error(request, "Please enter a question.")
            return redirect("document_chat", document_id=document.id)

        try:
            result = answer_document_question(document, question, language=language)
            evidence = result.get("evidence", {})
            chat_msg = ChatMessage.objects.create(
                document=document,
                user=request.user,
                question=question,
                answer=result.get("answer", "No answer was returned."),
                sources=result.get("sources", []),
                evidence=evidence,
                language=language,
            )

            if is_ajax:
                return JsonResponse({
                    "success": True,
                    "message_id": chat_msg.id,
                    "question": chat_msg.question,
                    "answer": chat_msg.answer,
                    "sources": chat_msg.sources,
                    "evidence": chat_msg.evidence,
                    "language": chat_msg.language,
                    "created_at": chat_msg.created_at.strftime("%b %d, %Y, %I:%M %p"),
                })

            messages.success(request, "Response generated.")
            return redirect("document_chat", document_id=document.id)

        except Exception as error:
            error_text = str(error)
            print("StudyRAG answer error:", repr(error))

            if "429" in error_text or "RESOURCE_EXHAUSTED" in error_text or "quota" in error_text.lower():
                error_message = (
                    "Gemini API quota exceeded. Please wait for the quota "
                    "to reset or check your Google AI Studio limits."
                )
                status_code = 429
            else:
                error_message = (
                    "Answer generate nahi hua. Please check your API "
                    "configuration and try again."
                )
                status_code = 500

            if is_ajax:
                return JsonResponse(
                    {"success": False, "error": error_message},
                    status=status_code,
                )

            messages.error(request, error_message)
            return redirect("document_chat", document_id=document.id)

    chat_messages = document.chat_messages.all().order_by("created_at")

    # Use suggested questions from smart briefing if available
    briefing = document.briefing or {}
    sample_prompts = briefing.get("suggested_questions") or DEFAULT_SAMPLE_PROMPTS

    return render(
        request,
        "chatbot/chat.html",
        {
            "document": document,
            "briefing": briefing,
            "chat_messages": chat_messages,
            "sample_prompts": sample_prompts,
        },
    )


@login_required
@require_POST
def document_regenerate_briefing(request, document_id):
    document = get_object_or_404(Document, id=document_id, user=request.user)
    try:
        document.briefing = generate_document_briefing(document)
        document.save(update_fields=["briefing"])
        messages.success(request, "Smart Document Briefing regenerated successfully.")
    except Exception as e:
        messages.error(request, f"Failed to regenerate briefing: {e}")
    return redirect("document_chat", document_id=document.id)


@login_required
@require_POST
def document_delete(request, document_id):
    document = get_object_or_404(Document, id=document_id, user=request.user)
    title = document.title
    document.delete()
    messages.success(request, f"Document '{title}' was deleted successfully.")
    return redirect("document_upload")


@login_required
@require_POST
def document_clear_history(request, document_id):
    document = get_object_or_404(Document, id=document_id, user=request.user)
    document.chat_messages.all().delete()
    messages.success(request, "Chat history cleared successfully.")
    return redirect("document_chat", document_id=document.id)


@login_required
def document_chunk_detail(request, document_id, chunk_index):
    document = get_object_or_404(Document, id=document_id, user=request.user)
    try:
        chunk = DocumentChunk.objects.get(document=document, chunk_index=chunk_index)
        return JsonResponse({
            "success": True,
            "page": str(chunk.page),
            "chunk_index": chunk.chunk_index,
            "text": chunk.text,
            "document_title": document.title,
            "file_url": document.file.url if document.file else "",
        })
    except DocumentChunk.DoesNotExist:
        return JsonResponse({
            "success": False,
            "error": f"Chunk #{chunk_index} not found for this document.",
        }, status=404)
