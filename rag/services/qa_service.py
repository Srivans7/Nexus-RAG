from ..models import Document, DocumentChunk
from .faiss_vector_store_service import FaissVectorStoreService


class QuestionAnsweringService:
    """Retrieves semantic context from FAISS and builds a concise answer payload."""

    @staticmethod
    def answer(question: str, documents: list[Document]):
        if not documents:
            return 'No processed documents available to answer this question.', '', None

        vector_store_service = FaissVectorStoreService()
        allowed_document_ids = [document.id for document in documents]
        search_hits = vector_store_service.similarity_search(
            query=question,
            top_k=3,
            allowed_document_ids=allowed_document_ids,
        )

        if not search_hits:
            fallback_document = documents[0]
            fallback_chunk = (
                DocumentChunk.objects.filter(document=fallback_document)
                .order_by('chunk_index')
                .first()
            )
            fallback_context = fallback_chunk.content if fallback_chunk else fallback_document.extracted_text[:400]
            return (
                'I could not find a strong semantic match in the processed documents. '
                'Please refine your question or upload more specific content.',
                fallback_context,
                fallback_document.id,
            )

        best_hit = search_hits[0]
        matched_chunk = (
            DocumentChunk.objects.filter(
                document_id=best_hit['document_id'],
                chunk_index=best_hit['chunk_index'],
            )
            .order_by('chunk_index')
            .first()
        )
        if matched_chunk:
            context = matched_chunk.content
        else:
            fallback_document = Document.objects.filter(pk=best_hit['document_id']).first()
            context = fallback_document.extracted_text[:400] if fallback_document else ''

        answer = (
            'Top semantic match from the vector index suggests this relevant context: '
            f'{context}'
        )
        return answer, context, best_hit['document_id']
