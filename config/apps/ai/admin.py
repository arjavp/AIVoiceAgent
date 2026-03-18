from django.contrib import admin
from .models import VoiceWorkflow, KnowledgeBaseDocument, Ticket, DraftEmail

@admin.register(VoiceWorkflow)
class VoiceWorkflowAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'user__username']

@admin.register(KnowledgeBaseDocument)
class KnowledgeBaseDocumentAdmin(admin.ModelAdmin):
    list_display = ['filename', 'file_type', 'chunk_count', 'file_size', 'user', 'uploaded_at']
    list_filter = ['file_type', 'uploaded_at']
    search_fields = ['filename', 'description']
    readonly_fields = ['uploaded_at', 'chunk_count']

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'status', 'priority', 'created_by', 'created_at']
    list_filter = ['status', 'priority', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']

@admin.register(DraftEmail)
class DraftEmailAdmin(admin.ModelAdmin):
    list_display = ['id', 'subject', 'recipient', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['subject', 'body', 'recipient']
    readonly_fields = ['id', 'created_at']
