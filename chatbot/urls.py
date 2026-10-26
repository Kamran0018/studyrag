from django.urls import path
from . import views

urlpatterns = [
    path("upload/", views.document_upload, name="document_upload"),
    path("document/<int:document_id>/chat/", views.document_chat, name="document_chat"),
    path("document/<int:document_id>/regenerate-briefing/", views.document_regenerate_briefing, name="document_regenerate_briefing"),
    path("document/<int:document_id>/delete/", views.document_delete, name="document_delete"),
    path("document/<int:document_id>/clear-history/", views.document_clear_history, name="document_clear_history"),
    path("document/<int:document_id>/chunk/<int:chunk_index>/", views.document_chunk_detail, name="document_chunk_detail"),
]
