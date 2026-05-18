"""Gemini text embedding service — auto-detects available model, zero RAM."""
import functools
import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

_MODELS_LIST_URL = 'https://generativelanguage.googleapis.com/v1/models'

# Ordered by preference; the first model found available in the API will be used.
_PREFERRED_MODELS = [
    'gemini-embedding-exp-03-07',
    'text-embedding-005',
    'text-embedding-004',
    'embedding-001',
]

# Module-level fallback (overridden at runtime by get_embedding_dim())
GEMINI_EMBEDDING_DIM = 768


@functools.lru_cache(maxsize=1)
def _detect_embedding_model(api_key: str):
    """Query the Generative Language API to find the best available embedding model.

    Returns (embed_url, model_name, output_dimension).
    Result is cached per process so the models-list call happens only once.
    """
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(_MODELS_LIST_URL, params={'key': api_key})
            resp.raise_for_status()
            models = resp.json().get('models', [])

        available = {
            m['name'].split('/')[-1]: m
            for m in models
            if 'embedContent' in m.get('supportedGenerationMethods', [])
        }
        logger.info('Gemini embedding models available: %s', list(available.keys()))

        for name in _PREFERRED_MODELS:
            if name in available:
                dim = available[name].get('outputDimensionality', 768)
                url = (
                    f'https://generativelanguage.googleapis.com/v1/models/'
                    f'{name}:embedContent'
                )
                logger.info('Selected embedding model: %s (dim=%d)', name, dim)
                return url, name, dim

        # Fallback: first model the API reports as supporting embedContent
        if available:
            name, meta = next(iter(available.items()))
            dim = meta.get('outputDimensionality', 768)
            url = (
                f'https://generativelanguage.googleapis.com/v1/models/'
                f'{name}:embedContent'
            )
            logger.warning('No preferred model found; using fallback: %s (dim=%d)', name, dim)
            return url, name, dim

    except Exception as exc:
        logger.error('Embedding model detection failed: %s', exc)

    # Hard fallback — try v1beta path for text-embedding-004
    return (
        'https://generativelanguage.googleapis.com/v1beta/models/'
        'text-embedding-004:embedContent',
        'text-embedding-004',
        768,
    )


def get_embedding_dim() -> int:
    """Return the output dimension of the selected embedding model."""
    api_key = settings.RAG_GEMINI_API_KEY
    if not api_key:
        return GEMINI_EMBEDDING_DIM
    _, _, dim = _detect_embedding_model(api_key)
    return dim


def embed_with_gemini(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts using the best available Gemini embedding model."""
    api_key = settings.RAG_GEMINI_API_KEY
    if not api_key:
        raise RuntimeError('RAG_GEMINI_API_KEY is not set.')

    embed_url, model_name, _ = _detect_embedding_model(api_key)

    embeddings = []
    with httpx.Client(timeout=30) as client:
        for text in texts:
            resp = client.post(
                embed_url,
                params={'key': api_key},
                json={
                    'model': f'models/{model_name}',
                    'content': {'parts': [{'text': text}]},
                },
            )
            resp.raise_for_status()
            embeddings.append(resp.json()['embedding']['values'])
    return embeddings
