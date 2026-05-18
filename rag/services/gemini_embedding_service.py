"""Gemini text embedding service — zero RAM, free API (1500 req/day)."""
import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

_GEMINI_EMBED_URL = (
    'https://generativelanguage.googleapis.com/v1/models/'
    'text-embedding-004:embedContent'
)
GEMINI_EMBEDDING_DIM = 768


def embed_with_gemini(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts using Gemini text-embedding-004 (dim=768)."""
    api_key = settings.RAG_GEMINI_API_KEY
    if not api_key:
        raise RuntimeError('RAG_GEMINI_API_KEY is not set.')

    embeddings = []
    with httpx.Client(timeout=30) as client:
        for text in texts:
            resp = client.post(
                _GEMINI_EMBED_URL,
                params={'key': api_key},
                json={
                    'model': 'models/text-embedding-004',
                    'content': {'parts': [{'text': text}]},
                },
            )
            resp.raise_for_status()
            embeddings.append(resp.json()['embedding']['values'])
    return embeddings
