"""Groq cloud LLM service — drop-in replacement for OllamaService.

Sign up free at https://console.groq.com (14,400 requests/day free tier).
Set RAG_GROQ_API_KEY in your environment or .env file.
Set RAG_LLM_BACKEND=groq to activate.

Why Groq: runs llama3-8b at ~500 tokens/sec on their hardware — no local RAM needed.
"""
import logging

import httpx
from django.conf import settings

from .rag_exceptions import LLMGenerationError

logger = logging.getLogger(__name__)

_GROQ_API_BASE = 'https://api.groq.com/openai/v1'


class GroqService:
    """Streams responses from Groq's free OpenAI-compatible API."""

    def __init__(self):
        self.api_key = settings.RAG_GROQ_API_KEY
        self.model_name = settings.RAG_GROQ_MODEL
        if not self.api_key:
            raise LLMGenerationError(
                'RAG_GROQ_API_KEY is not set. '
                'Get a free key at https://console.groq.com and add it to your environment.'
            )

    # ------------------------------------------------------------------ #
    # Public interface (mirrors OllamaService)                            #
    # ------------------------------------------------------------------ #

    def generate(self, prompt: str) -> str:
        """Blocking generation — used by the sync ask endpoint."""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        payload = {
            'model': self.model_name,
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': settings.RAG_OLLAMA_TEMPERATURE,
            'max_tokens': settings.RAG_OLLAMA_NUM_PREDICT,
            'stream': False,
        }
        try:
            with httpx.Client(timeout=60) as client:
                response = client.post(
                    f'{_GROQ_API_BASE}/chat/completions',
                    headers=headers,
                    json=payload,
                )
                if response.status_code >= 400:
                    raise LLMGenerationError(
                        f'Groq API error {response.status_code}: {response.text}'
                    )
                data = response.json()
                return data['choices'][0]['message']['content'].strip()
        except httpx.HTTPError as exc:
            raise LLMGenerationError(f'Groq request failed: {exc}') from exc

    async def astream_generate(self, prompt: str):
        """Async streaming generator — used by the SSE stream endpoint."""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        payload = {
            'model': self.model_name,
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': settings.RAG_OLLAMA_TEMPERATURE,
            'max_tokens': settings.RAG_OLLAMA_NUM_PREDICT,
            'stream': True,
        }
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(connect=15, read=None, write=15, pool=15)) as client:
                async with client.stream(
                    'POST',
                    f'{_GROQ_API_BASE}/chat/completions',
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.status_code >= 400:
                        body = await response.aread()
                        raise LLMGenerationError(
                            f'Groq API error {response.status_code}: {body.decode("utf-8", errors="replace")}'
                        )
                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line or not line.startswith('data: '):
                            continue
                        data_str = line[len('data: '):]
                        if data_str == '[DONE]':
                            break
                        try:
                            import json
                            chunk = json.loads(data_str)
                            token = chunk['choices'][0]['delta'].get('content', '')
                            if token:
                                yield token
                        except (ValueError, KeyError):
                            continue
        except httpx.HTTPError as exc:
            raise LLMGenerationError(f'Groq streaming failed: {exc}') from exc

    def health_check(self) -> dict:
        """Check Groq API reachability."""
        if not self.api_key:
            return {
                'status': 'error',
                'message': 'RAG_GROQ_API_KEY is not configured',
                'ok': False,
            }
        try:
            headers = {'Authorization': f'Bearer {self.api_key}'}
            with httpx.Client(timeout=10) as client:
                response = client.get(f'{_GROQ_API_BASE}/models', headers=headers)
                if response.status_code == 200:
                    return {
                        'status': 'ready',
                        'message': f'Groq API ready — model: {self.model_name}',
                        'ok': True,
                        'backend': 'groq',
                        'model': self.model_name,
                    }
                return {
                    'status': 'error',
                    'message': f'Groq API returned {response.status_code}',
                    'ok': False,
                }
        except httpx.HTTPError as exc:
            return {
                'status': 'error',
                'message': f'Cannot reach Groq API: {exc}',
                'ok': False,
            }
