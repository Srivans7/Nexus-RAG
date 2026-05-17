from django.db import transaction

from ..models import Document, DocumentChunk
from ..utils.file_processing import FileProcessingError, DocumentProcessingUtility
from .faiss_vector_store_service import FaissVectorStoreService


class DocumentProcessor:
    """Coordinates document text extraction and status transitions."""

    @staticmethod
    def process(document: Document):
        vector_store_service = FaissVectorStoreService()
        document.status = Document.Status.PROCESSING
        document.processing_error = ''
        document.save(update_fields=['status', 'processing_error', 'updated_at'])

        try:
            with transaction.atomic():
                extracted_text, chunk_payloads = DocumentProcessingUtility.process_file(document.original_file.path)

                # Replace old chunks to keep processing idempotent.
                DocumentChunk.objects.filter(document=document).delete()
                DocumentChunk.objects.bulk_create(
                    [
                        DocumentChunk(
                            document=document,
                            chunk_index=payload['chunk_index'],
                            content=payload['content'],
                            metadata=payload['metadata'],
                        )
                        for payload in chunk_payloads
                    ]
                )

                document.extracted_text = extracted_text
                document.status = Document.Status.PROCESSED
                document.save(update_fields=['extracted_text', 'status', 'updated_at'])

                # Keep chunk query ordered and deterministic before vector upsert.
                chunks = list(document.chunks.order_by('chunk_index'))

                # Persist embeddings + vectors into local FAISS for semantic retrieval.
                vector_store_service.upsert_document_chunks(document_id=document.id, chunks=chunks)
        except FileProcessingError as exc:
            # Keep the error message for troubleshooting and observability.
            document.status = Document.Status.FAILED
            document.processing_error = str(exc)
            document.save(update_fields=['status', 'processing_error', 'updated_at'])
            raise
        except Exception as exc:
            document.status = Document.Status.FAILED
            document.processing_error = f'Unexpected processing failure: {exc}'
            document.save(update_fields=['status', 'processing_error', 'updated_at'])
            raise

        chunks = list(document.chunks.order_by('chunk_index'))
        return document, chunks
