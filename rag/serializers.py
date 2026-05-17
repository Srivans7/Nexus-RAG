from pathlib import Path

from rest_framework import serializers

from .models import Document, DocumentChunk


class DocumentSerializer(serializers.ModelSerializer):
    """Read serializer for document metadata."""

    class Meta:
        model = Document
        fields = [
            'id',
            'file_name',
            'file_type',
            'status',
            'processing_error',
            'created_at',
            'updated_at',
        ]


class DocumentChunkSerializer(serializers.ModelSerializer):
    """Read serializer for processed text chunks."""

    class Meta:
        model = DocumentChunk
        fields = ['id', 'chunk_index', 'content', 'metadata', 'created_at']


class DocumentProcessingResponseSerializer(serializers.Serializer):
    """Response schema for processing endpoint output."""

    document = DocumentSerializer()
    chunks = DocumentChunkSerializer(many=True)


class DocumentUploadSerializer(serializers.ModelSerializer):
    """Validates and creates uploaded documents."""

    class Meta:
        model = Document
        fields = ['id', 'original_file', 'file_name', 'file_type', 'status', 'created_at']
        read_only_fields = ['id', 'file_name', 'file_type', 'status', 'created_at']

    def validate_original_file(self, value):
        # Restrict accepted types to supported RAG source formats.
        allowed_extensions = {'.md': Document.FileType.MARKDOWN, '.txt': Document.FileType.TEXT, '.pdf': Document.FileType.PDF}
        suffix = Path(value.name).suffix.lower()
        if suffix not in allowed_extensions:
            raise serializers.ValidationError('Unsupported file type. Allowed: .md, .txt, .pdf')
        self.context['file_type'] = allowed_extensions[suffix]
        return value

    def create(self, validated_data):
        source_file = validated_data['original_file']
        validated_data['file_name'] = source_file.name
        validated_data['file_type'] = self.context['file_type']
        return super().create(validated_data)


class QuestionAnswerRequestSerializer(serializers.Serializer):
    """Validates question answering request payload."""

    question = serializers.CharField(max_length=2000)
    document_id = serializers.IntegerField(required=False)


class QuestionAnswerResponseSerializer(serializers.Serializer):
    """Standard response payload for QA endpoint."""

    answer = serializers.CharField()
    context = serializers.CharField(allow_blank=True)
    document_id = serializers.IntegerField(allow_null=True)


class AskRequestSerializer(serializers.Serializer):
    """Validates ask endpoint payload for end-to-end RAG generation."""

    question = serializers.CharField(max_length=2000)
    conversation_id = serializers.UUIDField(required=False)
    document_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=False,
    )


class AskSourceSerializer(serializers.Serializer):
    """Structured source metadata returned with generated answer."""

    document_id = serializers.IntegerField()
    file_name = serializers.CharField()
    chunk_index = serializers.IntegerField()
    score = serializers.FloatField()
    snippet = serializers.CharField(required=False, default='')


class AskDocumentReferenceSerializer(serializers.Serializer):
    """Deduplicated document references that contributed to an answer."""

    document_id = serializers.IntegerField()
    file_name = serializers.CharField()
    chunk_indexes = serializers.ListField(child=serializers.IntegerField())
    max_score = serializers.FloatField()


class AskResponseSerializer(serializers.Serializer):
    """Response schema for RAG ask endpoint."""

    conversation_id = serializers.UUIDField()
    answer = serializers.CharField()
    sources = AskSourceSerializer(many=True)
    document_references = AskDocumentReferenceSerializer(many=True)


class ChatSessionSerializer(serializers.Serializer):
	"""Read serializer for conversation session metadata."""

	id = serializers.UUIDField()
	created_at = serializers.DateTimeField()
	updated_at = serializers.DateTimeField()
