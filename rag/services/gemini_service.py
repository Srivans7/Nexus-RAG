"""Gemini cloud LLM service — drop-in replacement for OllamaService.

Set RAG_GEMINI_API_KEY in .env or environment.
Set RAG_LLM_BACKEND=gemini to force Gemini, or keep auto mode.
"""

import asyncio
import logging

import httpx
from django.conf import settings

from .rag_exceptions import LLMGenerationError

logger = logging.getLogger(__name__)

_GEMINI_API_BASE = 'https://generativelanguage.googleapis.com/v1beta'


class GeminiService:
    """Calls Gemini generateContent endpoint."""

    def __init__(self):
        self.api_key = settings.RAG_GEMINI_API_KEY
        self.model_name = settings.RAG_GEMINI_MODEL
        if not self.api_key:
            raise LLMGenerationError(
                'RAG_GEMINI_API_KEY is not set. '
                'Add your Gemini API key in .env to enable Gemini backend.'
            )

    def _model_endpoint(self) -> str:
        return f'{_GEMINI_API_BASE}/{self._model_path()}:generateContent?key={self.api_key}'

    def _model_path(self) -> str:
        model = (self.model_name or '').strip()
        if model.startswith('models/'):
            return model
        return f'models/{model}'

    def generate(self, prompt: str) -> str:
        payload = {
            'contents': [
                {
                    'role': 'user',
                    'parts': [{'text': prompt}],
                }
            ],
            'generationConfig': {
                'temperature': settings.RAG_OLLAMA_TEMPERATURE,
                'topP': settings.RAG_OLLAMA_TOP_P,
                'maxOutputTokens': settings.RAG_OLLAMA_NUM_PREDICT,
            },
        }

        try:
            with httpx.Client(timeout=60) as client:
                response = client.post(self._model_endpoint(), json=payload)
                if response.status_code >= 400:
                    raise LLMGenerationError(
                        f'Gemini API error {response.status_code}: {response.text[:250]}'
                    )
                data = response.json()
        except httpx.HTTPError as exc:
            raise LLMGenerationError(f'Gemini request failed: {exc}') from exc

        candidates = data.get('candidates', [])
        if not candidates:
            raise LLMGenerationError('Gemini returned no candidates.')

        parts = candidates[0].get('content', {}).get('parts', [])
        content = ''.join(part.get('text', '') for part in parts).strip()
        if not content:
            raise LLMGenerationError('Gemini returned empty content.')

        logger.info('Gemini answered using model: %s', self.model_name)
        return content

    async def astream_generate(self, prompt: str):
        """WSGI-safe async wrapper around blocking generate()."""
        content = await asyncio.get_running_loop().run_in_executor(None, self.generate, prompt)
        yield content

    def health_check(self) -> dict:
        if not self.api_key:
            return {
                'status': 'error',
                'message': 'RAG_GEMINI_API_KEY is not configured',
                'ok': False,
                'backend': 'gemini',
                'model': self.model_name,
            }

        url = f'{_GEMINI_API_BASE}/models?key={self.api_key}'
        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(url)
                if response.status_code == 200:
                    return {
                        'status': f'Gemini · {self.model_name}',
                        'message': f'Gemini API ready — model: {self.model_name}',
                        'ok': True,
                        'backend': 'gemini',
                        'model': self.model_name,
                    }
                return {
                    'status': 'error',
                    'message': f'Gemini API returned {response.status_code}',
                    'ok': False,
                    'backend': 'gemini',
                    'model': self.model_name,
                }
        except httpx.HTTPError as exc:
            return {
                'status': 'error',
                'message': f'Gemini unreachable: {exc}',
                'ok': False,
                'backend': 'gemini',
                'model': self.model_name,
            }
