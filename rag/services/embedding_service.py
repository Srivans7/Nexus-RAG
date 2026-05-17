from django.conf import settings

from ..utils.vector_utils import create_embeddings, get_embedding_model


def _use_gemini_embeddings() -> bool:
    """Use Gemini embedding API when key is set (saves ~600MB RAM vs sentence-transformers)."""
    return bool(getattr(settings, 'RAG_GEMINI_API_KEY', ''))


class EmbeddingService:
    """Reusable service for text embedding operations.

    Uses Gemini text-embedding-004 (dim=768) when RAG_GEMINI_API_KEY is set.
    Falls back to sentence-transformers/all-MiniLM-L6-v2 (dim=384) for local dev.
    """

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.RAG_EMBEDDING_MODEL
        self._gemini = _use_gemini_embeddings()

    @property
    def embedding_dimension(self) -> int:
        if self._gemini:
            from .gemini_embedding_service import GEMINI_EMBEDDING_DIM
            return GEMINI_EMBEDDING_DIM
        model = get_embedding_model(self.model_name)
        if hasattr(model, 'get_embedding_dimension'):
            return int(model.get_embedding_dimension())
        return int(model.get_sentence_embedding_dimension())

    def embed_texts(self, texts: list[str]):
        """Embed multiple chunk texts for bulk FAISS upsert operations."""
        if self._gemini:
            import numpy as np
            from .gemini_embedding_service import embed_with_gemini
            vecs = embed_with_gemini(texts)
            return np.array(vecs, dtype='float32')
        return create_embeddings(texts=texts, model_name=self.model_name)

    def embed_query(self, query: str):
        """Embed a single query string for similarity search."""
        if self._gemini:
            import numpy as np
            from .gemini_embedding_service import embed_with_gemini
            vecs = embed_with_gemini([query])
            return np.array(vecs, dtype='float32')
        return create_embeddings(texts=[query], model_name=self.model_name)
