from django.contrib import admin
from .models import Document, DocumentChunk, ChatMessage


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "chunk_count", "message_count", "uploaded_at")
    search_fields = ("title", "user__username")
    list_filter = ("uploaded_at",)


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ("document", "page", "chunk_index", "preview_text")
    search_fields = ("document__title", "text")
    list_filter = ("document",)

    def preview_text(self, obj):
        return obj.text[:80] + ("..." if len(obj.text) > 80 else "")
    preview_text.short_description = "Content Preview"


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("document", "user", "preview_question", "created_at")
    search_fields = ("document__title", "user__username", "question", "answer")
    list_filter = ("created_at", "document")

    def preview_question(self, obj):
        return obj.question[:80] + ("..." if len(obj.question) > 80 else "")
    preview_question.short_description = "Question"
