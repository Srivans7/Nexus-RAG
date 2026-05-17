import uuid

from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
	"""Extended user profile for Google OAuth integration."""

	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
	google_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
	avatar_url = models.URLField(blank=True, null=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self) -> str:
		return f'Profile for {self.user.email}'


class Document(models.Model):
	"""Stores uploaded source files and their processed text content."""

	class Status(models.TextChoices):
		UPLOADED = 'uploaded', 'Uploaded'
		PROCESSING = 'processing', 'Processing'
		PROCESSED = 'processed', 'Processed'
		FAILED = 'failed', 'Failed'

	class FileType(models.TextChoices):
		MARKDOWN = 'md', 'Markdown'
		TEXT = 'txt', 'Text'
		PDF = 'pdf', 'PDF'

	original_file = models.FileField(upload_to='documents/')
	file_name = models.CharField(max_length=255)
	file_type = models.CharField(max_length=10, choices=FileType.choices)
	status = models.CharField(
		max_length=20,
		choices=Status.choices,
		default=Status.UPLOADED,
	)
	extracted_text = models.TextField(blank=True)
	processing_error = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self) -> str:
		return f'{self.file_name} ({self.status})'


class DocumentChunk(models.Model):
	"""Stores chunked text units produced from processed documents."""

	document = models.ForeignKey(
		Document,
		on_delete=models.CASCADE,
		related_name='chunks',
	)
	chunk_index = models.PositiveIntegerField()
	content = models.TextField()
	metadata = models.JSONField(default=dict, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['chunk_index']
		constraints = [
			models.UniqueConstraint(
				fields=['document', 'chunk_index'],
				name='unique_document_chunk_index',
			)
		]

	def __str__(self) -> str:
		return f'{self.document.file_name} chunk {self.chunk_index}'


class QuestionAnswerLog(models.Model):
	"""Persists Q&A interactions for observability and future analytics."""

	document = models.ForeignKey(
		Document,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='qa_logs',
	)
	question = models.TextField()
	answer = models.TextField()
	context_snippet = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self) -> str:
		doc_label = self.document.file_name if self.document else 'All documents'
		return f'Q&A for {doc_label}'


class ChatSession(models.Model):
	"""Represents a persisted conversation thread for memory-aware RAG."""

	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	title = models.CharField(max_length=255, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-updated_at']

	def __str__(self) -> str:
		return self.title or f'Chat session {self.pk}'


class ChatMessage(models.Model):
	"""Stores conversational turns for LangChain-backed memory reconstruction."""

	class Role(models.TextChoices):
		USER = 'user', 'User'
		ASSISTANT = 'assistant', 'Assistant'

	session = models.ForeignKey(
		ChatSession,
		on_delete=models.CASCADE,
		related_name='messages',
	)
	role = models.CharField(max_length=20, choices=Role.choices)
	content = models.TextField()
	sources = models.JSONField(default=list, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['created_at', 'id']

	def __str__(self) -> str:
		return f'{self.session_id} {self.role}'
