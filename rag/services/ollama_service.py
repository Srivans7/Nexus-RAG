import json
import logging

import httpx
from django.conf import settings

from .ollama_http_client import OllamaHttpClient, OllamaHttpError
from .rag_exceptions import LLMGenerationError


logger = logging.getLogger(__name__)


class OllamaService:
    """Encapsulates local Ollama chat/completion interactions."""

    def __init__(
        self,
        base_url: str | None = None,
        model_name: str | None = None,
        timeout_seconds: int | None = None,
        http_client: OllamaHttpClient | None = None,
    ):
        self.base_url = (base_url or settings.RAG_OLLAMA_BASE_URL).rstrip('/')
        self.model_name = model_name or settings.RAG_OLLAMA_MODEL
        self.timeout_seconds = timeout_seconds or settings.RAG_OLLAMA_TIMEOUT_SECONDS
        self.http_client = http_client or OllamaHttpClient(
            base_url=self.base_url,
            timeout_seconds=self.timeout_seconds,
        )

    # Model-agnostic stop tokens — prevent looping back into the prompt structure.
    # Avoid model-specific tokens (ChatML, Llama3 etc.) since Ollama templates vary.
    _STOP_SEQUENCES = ['\nQuestion:', '\nContext:', '\nHuman:', '\nPrior conversation:']

    def generate(self, prompt: str) -> str:
        """Send a prompt to Ollama and return plain text model output."""
        payload = {
            'model': self.model_name,
            'prompt': prompt,
            'stream': False,
            'stop': self._STOP_SEQUENCES,
            'options': {
                'temperature': settings.RAG_OLLAMA_TEMPERATURE,
                'top_p': settings.RAG_OLLAMA_TOP_P,
                'repeat_penalty': settings.RAG_OLLAMA_REPEAT_PENALTY,
                'num_predict': settings.RAG_OLLAMA_NUM_PREDICT,
            },
        }

        try:
            response_payload = self.http_client.post_json('/api/generate', payload)
        except OllamaHttpError as exc:
            raise LLMGenerationError(str(exc)) from exc

        answer = response_payload.get('response', '').strip()
        if not answer:
            raise LLMGenerationError('Ollama returned an empty answer.')

        return answer

    def get_installed_models(self) -> list[str]:
        """Return all model names currently installed in local Ollama."""
        payload = self.http_client.get_json('/api/tags')
        models = payload.get('models', [])
        return [item.get('model', '') for item in models if item.get('model')]

    def is_server_running(self) -> bool:
        """Return True if Ollama tag endpoint can be reached successfully."""
        try:
            self.http_client.get_json('/api/tags')
            return True
        except OllamaHttpError:
            return False

    def is_model_available(self, model_name: str | None = None) -> bool:
        """Return True when a model prefix is present in installed Ollama models."""
        target_model = model_name or self.model_name

        try:
            installed_models = self.get_installed_models()
        except OllamaHttpError:
            return False

        return any(name.startswith(target_model) for name in installed_models)

    async def astream_generate(self, prompt: str):
        """Yield model output incrementally using Ollama's streaming API."""
        endpoint = f'{self.base_url}/api/generate'
        payload = {
            'model': self.model_name,
            'prompt': prompt,
            'stream': True,
            'stop': self._STOP_SEQUENCES,
            'options': {
                'temperature': settings.RAG_OLLAMA_TEMPERATURE,
                'top_p': settings.RAG_OLLAMA_TOP_P,
                'repeat_penalty': settings.RAG_OLLAMA_REPEAT_PENALTY,
                'num_predict': settings.RAG_OLLAMA_NUM_PREDICT,
            },
        }
        timeout = httpx.Timeout(
            connect=self.timeout_seconds,
            read=None,
            write=self.timeout_seconds,
            pool=self.timeout_seconds,
        )

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream('POST', endpoint, json=payload) as response:
                    if response.status_code >= 400:
                        body = await response.aread()
                        raise LLMGenerationError(
                            f'Ollama generation failed with status {response.status_code}: {body.decode("utf-8", errors="replace")}'
                        )

                    async for line in response.aiter_lines():
                        if not line:
                            continue

                        try:
                            payload = json.loads(line)
                        except ValueError as exc:
                            raise LLMGenerationError('Ollama returned an invalid streaming payload.') from exc

                        token = payload.get('response', '')
                        if token:
                            yield token

                        if payload.get('done'):
                            break
        except httpx.HTTPError as exc:
            raise LLMGenerationError(f'Failed to reach Ollama service: {exc}') from exc

    def health_check(self) -> dict:
        """Check local Ollama reachability and confirm model availability."""
        try:
            installed_models = self.get_installed_models()
        except OllamaHttpError as exc:
            logger.warning('Ollama health check failed: %s', exc)
            return {
                'status': 'error',
                'message': 'Ollama server is not running',
                'ok': False,
                'ollama': 'disconnected',
                'model': self.model_name,
                'available_models': [],
            }

        model_available = any(name.startswith(self.model_name) for name in installed_models)
        if model_available:
            return {
                'status': f'Ollama · {self.model_name}',
                'ollama': 'connected',
                'ok': True,
                'model': self.model_name,
                'available_models': installed_models,
            }

        return {
            'status': 'error',
            'message': f'Ollama model {self.model_name} is not installed',
            'ok': False,
            'ollama': 'connected',
            'model': self.model_name,
            'available_models': installed_models,
        }
