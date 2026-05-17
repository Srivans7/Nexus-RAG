import logging
from dataclasses import dataclass

import requests
from django.conf import settings
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logger = logging.getLogger(__name__)


@dataclass
class OllamaHttpError(Exception):
    """Represents a recoverable Ollama transport failure."""

    message: str

    def __str__(self) -> str:
        return self.message


class OllamaHttpClient:
    """Low-level requests client with retry-safe Ollama connectivity."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: int | None = None,
        max_retries: int | None = None,
        backoff_factor: float | None = None,
    ):
        self.base_url = (base_url or settings.RAG_OLLAMA_BASE_URL).rstrip('/')
        self.timeout_seconds = timeout_seconds or settings.RAG_OLLAMA_TIMEOUT_SECONDS
        self.max_retries = max_retries if max_retries is not None else 2
        self.backoff_factor = backoff_factor if backoff_factor is not None else 0.4
        self.session = self._build_session()

    def _build_session(self) -> requests.Session:
        retry_policy = Retry(
            total=self.max_retries,
            connect=self.max_retries,
            read=self.max_retries,
            status=self.max_retries,
            backoff_factor=self.backoff_factor,
            allowed_methods=frozenset({'GET', 'POST'}),
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False,
        )

        adapter = HTTPAdapter(max_retries=retry_policy)
        session = requests.Session()
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def get_json(self, path: str) -> dict:
        endpoint = f'{self.base_url}{path}'
        logger.debug('Calling Ollama GET endpoint: %s', endpoint)

        try:
            response = self.session.get(endpoint, timeout=self.timeout_seconds)
        except requests.RequestException as exc:
            logger.warning('Ollama GET request failed: %s', exc)
            raise OllamaHttpError(f'Failed to reach Ollama service: {exc}') from exc

        if response.status_code >= 400:
            logger.warning('Ollama GET endpoint returned error status %s', response.status_code)
            raise OllamaHttpError(
                f'Ollama returned status {response.status_code}: {response.text}'
            )

        try:
            return response.json()
        except ValueError as exc:
            logger.warning('Ollama GET endpoint returned non-JSON payload')
            raise OllamaHttpError('Ollama returned a non-JSON response.') from exc

    def post_json(self, path: str, payload: dict) -> dict:
        endpoint = f'{self.base_url}{path}'
        logger.debug('Calling Ollama POST endpoint: %s', endpoint)

        try:
            response = self.session.post(endpoint, json=payload, timeout=self.timeout_seconds)
        except requests.RequestException as exc:
            logger.warning('Ollama POST request failed: %s', exc)
            raise OllamaHttpError(f'Failed to reach Ollama service: {exc}') from exc

        if response.status_code >= 400:
            logger.warning('Ollama POST endpoint returned error status %s', response.status_code)
            raise OllamaHttpError(
                f'Ollama returned status {response.status_code}: {response.text}'
            )

        try:
            return response.json()
        except ValueError as exc:
            logger.warning('Ollama POST endpoint returned non-JSON payload')
            raise OllamaHttpError('Ollama returned a non-JSON response.') from exc
