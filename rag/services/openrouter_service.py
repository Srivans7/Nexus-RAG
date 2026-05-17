"""OpenRouter cloud LLM service — drop-in replacement for OllamaService / GroqService.

Sign up free at https://openrouter.ai (generous free tier with many models).
Set RAG_OPENROUTER_API_KEY in your environment or .env file.
Set RAG_LLM_BACKEND=openrouter to activate.

Free models to try (set RAG_OPENROUTER_MODEL):
  - meta-llama/llama-3.1-8b-instruct:free
  - google/gemma-3-1b-it:free
  - mistralai/mistral-7b-instruct:free
"""
import logging

import httpx
from django.conf import settings

from .rag_exceptions import LLMGenerationError

logger = logging.getLogger(__name__)

_OPENROUTER_API_BASE = 'https://openrouter.ai/api/v1'

# Ordered fallback list — first model that returns a valid response wins.
_FALLBACK_MODELS = [
    'google/gemma-4-26b-a4b-it:free',
    'google/gemma-4-31b-it:free',
    'nvidia/nemotron-3-nano-30b-a3b:free',
    'liquid/lfm-2.5-1.2b-instruct:free',
]


class OpenRouterService:
    """Calls OpenRouter's OpenAI-compatible chat completions API."""

    def __init__(self):
        self.api_key = settings.RAG_OPENROUTER_API_KEY
        self.model_name = settings.RAG_OPENROUTER_MODEL
        if not self.api_key:
            raise LLMGenerationError(
                'RAG_OPENROUTER_API_KEY is not set. '
                'Get a free key at https://openrouter.ai and add it to your environment.'
            )

    def _headers(self) -> dict:
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'http://localhost:8000',
            'X-Title': 'Nexus AI RAG',
        }

    # ------------------------------------------------------------------ #
    # Public interface (mirrors OllamaService / GroqService)              #
    # ------------------------------------------------------------------ #

    def generate(self, prompt: str) -> str:
        """Blocking generation — tries each fallback model until one succeeds."""
        models_to_try = [self.model_name] + [m for m in _FALLBACK_MODELS if m != self.model_name]
        last_error = None
        for model in models_to_try:
            payload = {
                'model': model,
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': settings.RAG_OLLAMA_TEMPERATURE,
                'max_tokens': settings.RAG_OLLAMA_NUM_PREDICT,
                'stream': False,
            }
            try:
                with httpx.Client(timeout=60) as client:
                    response = client.post(
                        f'{_OPENROUTER_API_BASE}/chat/completions',
                        headers=self._headers(),
                        json=payload,
                    )
                    if response.status_code >= 400:
                        last_error = f'OpenRouter API error {response.status_code}: {response.text[:200]}'
                        logger.warning('Model %s failed (%s), trying next...', model, last_error)
                        continue
                    data = response.json()
                    choices = data.get('choices', [])
                    if not choices:
                        last_error = f'Model {model} returned empty choices'
                        logger.warning('%s, trying next...', last_error)
                        continue
                    content = (choices[0]['message']['content'] or '').strip()
                    if not content:
                        last_error = f'Model {model} returned empty content'
                        logger.warning('%s, trying next...', last_error)
                        continue
                    logger.info('OpenRouter answered using model: %s', model)
                    return content
            except httpx.HTTPError as exc:
                last_error = str(exc)
                logger.warning('Model %s HTTP error: %s, trying next...', model, exc)
                continue
        raise LLMGenerationError(f'All OpenRouter models failed. Last error: {last_error}')

    def health_check(self) -> dict:
        """Check OpenRouter API reachability."""
        if not self.api_key:
            return {
                'status': 'error',
                'message': 'RAG_OPENROUTER_API_KEY is not configured',
                'ok': False,
                'backend': 'openrouter',
                'model': self.model_name,
            }
        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(
                    f'{_OPENROUTER_API_BASE}/models',
                    headers=self._headers(),
                )
                if response.status_code == 200:
                    return {
                        'status': f'OpenRouter · {self.model_name}',
                        'message': f'OpenRouter ready — model: {self.model_name}',
                        'ok': True,
                        'backend': 'openrouter',
                        'model': self.model_name,
                    }
                return {
                    'status': 'error',
                    'message': f'OpenRouter API returned {response.status_code}',
                    'ok': False,
                    'backend': 'openrouter',
                    'model': self.model_name,
                }
        except httpx.HTTPError as exc:
            return {
                'status': 'error',
                'message': f'OpenRouter unreachable: {exc}',
                'ok': False,
                'backend': 'openrouter',
                'model': self.model_name,
            }

    async def astream_generate(self, prompt: str):
        """Async generator — runs blocking generate() in a thread executor (WSGI-safe)."""
        import asyncio
        content = await asyncio.get_running_loop().run_in_executor(None, self.generate, prompt)
        yield content
