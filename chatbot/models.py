
import os
from django.conf import settings
from django.db import models


class Document(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="documents/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    briefing = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.title

    @property
    def chunk_count(self):
        return self.chunks.count()

    @property
    def message_count(self):
        return self.chat_messages.count()

    @property
    def file_size_formatted(self):
        try:
            size = self.file.size
            for unit in ["B", "KB", "MB", "GB"]:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} TB"
        except Exception:
            return ""

    @property
    def file_extension(self):
        name = self.file.name or self.title
        return name.rsplit(".", 1)[-1].upper() if "." in name else "DOC"

    def delete(self, *args, **kwargs):
        try:
            storage, path = self.file.storage, self.file.path
        except Exception:
            storage, path = None, None

        super().delete(*args, **kwargs)

        if storage and path:
            try:
                if storage.exists(path):
                    storage.delete(path)
            except Exception:
                pass


class DocumentChunk(models.Model):
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    text = models.TextField()
    page = models.CharField(max_length=50)
    chunk_index = models.PositiveIntegerField()

    class Meta:
        ordering = ["chunk_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "chunk_index"],
                name="unique_document_chunk",
            )
        ]

    def __str__(self):
        return f"{self.document.title} - Chunk {self.chunk_index}"


class ChatMessage(models.Model):
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="chat_messages",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_messages",
    )
    question = models.TextField()
    answer = models.TextField()
    sources = models.JSONField(default=list, blank=True)
    evidence = models.JSONField(default=dict, blank=True)
    language = models.CharField(max_length=20, default="english")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Chat for {self.document.title}: {self.question[:40]}"

