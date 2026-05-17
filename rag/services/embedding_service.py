from django.conf import settings

from ..utils.vector_utils import create_embeddings, get_embedding_model


class EmbeddingService:
    """Reusable service for text embedding operations using sentence-transformers."""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.RAG_EMBEDDING_MODEL

    @property
    def embedding_dimension(self) -> int:
        """Return model embedding dimensionality to validate FAISS index shape."""
        model = get_embedding_model(self.model_name)
        if hasattr(model, 'get_embedding_dimension'):
            return int(model.get_embedding_dimension())
        return int(model.get_sentence_embedding_dimension())

    def embed_texts(self, texts: list[str]):
        """Embed multiple chunk texts for bulk FAISS upsert operations."""
        return create_embeddings(texts=texts, model_name=self.model_name)

    def embed_query(self, query: str):
        """Embed a single query string for similarity search."""
        return create_embeddings(texts=[query], model_name=self.model_name)
