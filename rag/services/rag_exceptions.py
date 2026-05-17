class RAGServiceError(Exception):
    """Base exception for recoverable RAG pipeline failures."""


class RetrievalError(RAGServiceError):
    """Raised when context retrieval from vector search fails."""


class LLMGenerationError(RAGServiceError):
    """Raised when Ollama cannot generate a valid completion."""
