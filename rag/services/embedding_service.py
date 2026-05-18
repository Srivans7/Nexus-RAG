import numpy as np
from django.conf import settings

from .gemini_embedding_service import GEMINI_EMBEDDING_DIM, embed_with_gemini


class EmbeddingService:
    """Reusable service for text embedding operations using Gemini text-embedding-004."""

    @property
    def embedding_dimension(self) -> int:
        return GEMINI_EMBEDDING_DIM

    def embed_texts(self, texts: list[str]):
        """Embed multiple chunk texts for bulk FAISS upsert operations."""
        vecs = embed_with_gemini(texts)
        return np.array(vecs, dtype='float32')

    def embed_query(self, query: str):
        """Embed a single query string for similarity search."""
        vecs = embed_with_gemini([query])
        return np.array(vecs, dtype='float32')
