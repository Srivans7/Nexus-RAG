import json
from pathlib import Path

from django.conf import settings

from .embedding_service import EmbeddingService
from ..models import DocumentChunk
from ..utils.vector_utils import (
    load_faiss_database,
    save_faiss_database,
    similarity_search,
)


class FaissVectorStoreService:
    """Encapsulates local FAISS persistence and vector similarity retrieval."""

    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        index_path: str | Path | None = None,
        metadata_path: str | Path | None = None,
    ):
        self.embedding_service = embedding_service or EmbeddingService()
        self.index_path = Path(index_path or settings.RAG_FAISS_INDEX_FILE)
        self.metadata_path = Path(metadata_path or settings.RAG_FAISS_META_FILE)
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)

    def upsert_document_chunks(self, document_id: int, chunks: list[DocumentChunk]) -> None:
        """Create embeddings for chunks and upsert vectors into local FAISS storage."""
        if not chunks:
            self.remove_document_vectors(document_id)
            return

        chunk_texts = [chunk.content for chunk in chunks]
        embeddings = self.embedding_service.embed_texts(chunk_texts)
        actual_dimension = int(embeddings.shape[1])

        embedding_dimension = self.embedding_service.embedding_dimension
        index = self._safe_load_index(preferred_dimension=embedding_dimension, fallback_dimension=actual_dimension)
        metadata = self._load_metadata()

        import numpy as np
        vector_ids = np.array(
            [self._build_vector_id(document_id, chunk.chunk_index) for chunk in chunks],
            dtype='int64',
        )

        try:
            # Remove old vectors with same logical IDs before adding refreshed records.
            index.remove_ids(vector_ids)
            index.add_with_ids(embeddings, vector_ids)
        except (AssertionError, ValueError):
            # FAISS can raise empty-message AssertionError on dimension mismatch.
            # When embeddings model/dimension changes, rebuild local index + metadata.
            index, metadata = self._reset_store(actual_dimension)
            index.add_with_ids(embeddings, vector_ids)

        for chunk in chunks:
            vector_id = self._build_vector_id(document_id, chunk.chunk_index)
            metadata[str(vector_id)] = {
                'document_id': document_id,
                'chunk_index': chunk.chunk_index,
            }

        self._save_metadata(metadata)
        save_faiss_database(index, self.index_path)

    def remove_document_vectors(self, document_id: int) -> None:
        """Delete all vectors and metadata entries associated with one document."""
        embedding_dimension = self.embedding_service.embedding_dimension
        index = self._safe_load_index(preferred_dimension=embedding_dimension)
        metadata = self._load_metadata()

        ids_to_remove = [
            int(vector_id)
            for vector_id, payload in metadata.items()
            if payload.get('document_id') == document_id
        ]
        if ids_to_remove:
            import numpy as np
            index.remove_ids(np.array(ids_to_remove, dtype='int64'))

        filtered_metadata = {
            vector_id: payload
            for vector_id, payload in metadata.items()
            if payload.get('document_id') != document_id
        }

        self._save_metadata(filtered_metadata)
        save_faiss_database(index, self.index_path)

    def similarity_search(self, query: str, top_k: int = 5, allowed_document_ids: list[int] | None = None):
        """Search FAISS by query and return ranked chunk references."""
        embedding_dimension = self.embedding_service.embedding_dimension
        index = self._safe_load_index(preferred_dimension=embedding_dimension)
        if index.ntotal == 0:
            return []

        query_embedding = self.embedding_service.embed_query(query)
        metadata = self._load_metadata()

        # When filtering by specific documents, search the full index so that
        # allowed-doc chunks are never missed due to global ranking. For
        # unrestricted queries, a generous multiplier is enough.
        if allowed_document_ids:
            candidate_count = index.ntotal
        else:
            candidate_count = max(top_k * 3, top_k)
        raw_hits = similarity_search(index, query_embedding, top_k=candidate_count)

        results = []
        allowed_set = set(allowed_document_ids or [])
        for hit in raw_hits:
            payload = metadata.get(str(hit['vector_id']))
            if not payload:
                continue

            document_id = int(payload['document_id'])
            if allowed_set and document_id not in allowed_set:
                continue

            results.append(
                {
                    'document_id': document_id,
                    'chunk_index': int(payload['chunk_index']),
                    'score': float(hit['score']),
                }
            )
            if len(results) >= top_k:
                break

        return results

    def _load_metadata(self) -> dict:
        if not self.metadata_path.exists():
            return {}
        with self.metadata_path.open('r', encoding='utf-8') as metadata_file:
            return json.load(metadata_file)

    def _save_metadata(self, metadata: dict) -> None:
        with self.metadata_path.open('w', encoding='utf-8') as metadata_file:
            json.dump(metadata, metadata_file, indent=2)

    def _safe_load_index(self, preferred_dimension: int, fallback_dimension: int | None = None):
        """Load index, falling back to a rebuild when stored dimension is incompatible."""
        try:
            return load_faiss_database(self.index_path, preferred_dimension)
        except ValueError:
            if fallback_dimension is not None and fallback_dimension != preferred_dimension:
                return load_faiss_database(self.index_path, fallback_dimension)
            _, _ = self._reset_store(preferred_dimension)
            return load_faiss_database(self.index_path, preferred_dimension)

    def _reset_store(self, embedding_dimension: int):
        """Reinitialize index + metadata after embedding dimension drift."""
        import faiss

        base_index = faiss.IndexFlatIP(embedding_dimension)
        index = faiss.IndexIDMap2(base_index)
        metadata = {}
        self._save_metadata(metadata)
        save_faiss_database(index, self.index_path)
        return index, metadata

    @staticmethod
    def _build_vector_id(document_id: int, chunk_index: int) -> int:
        # Stable deterministic ID enables safe replace/remove operations.
        return int(document_id * 1_000_000 + chunk_index)
