from django.contrib import admin

from .models import Document, DocumentChunk, QuestionAnswerLog


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
	list_display = ('id', 'file_name', 'file_type', 'status', 'created_at')
	list_filter = ('file_type', 'status', 'created_at')
	search_fields = ('file_name',)


@admin.register(QuestionAnswerLog)
class QuestionAnswerLogAdmin(admin.ModelAdmin):
	list_display = ('id', 'document', 'created_at')
	search_fields = ('question', 'answer')


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
	list_display = ('id', 'document', 'chunk_index', 'created_at')
	search_fields = ('document__file_name', 'content')
	list_filter = ('created_at',)

# Register your models here.
