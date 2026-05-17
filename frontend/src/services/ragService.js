import { API_BASE_URL } from './config';
import { normalizeApiError } from './errorService';
import httpClient from './httpClient';

const STREAM_IDLE_TIMEOUT_MS = Number(import.meta.env.VITE_STREAM_IDLE_TIMEOUT_MS || 120000);

function buildAskPayload(question, { conversationId, documentIds } = {}) {
  const payload = { question };

  if (conversationId) {
    payload.conversation_id = conversationId;
  }

  if (Array.isArray(documentIds) && documentIds.length) {
    payload.document_ids = documentIds;
  }

  return payload;
}

function getEventBlocks(buffer) {
  const normalizedBuffer = buffer.replace(/\r\n/g, '\n');
  const blocks = normalizedBuffer.split('\n\n');
  return {
    completeBlocks: blocks.slice(0, -1),
    remainder: blocks.at(-1) || '',
  };
}

function parseEventBlock(block) {
  let event = 'message';
  const dataLines = [];

  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim();
    }

    if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trimStart());
    }
  }

  if (!dataLines.length) {
    return null;
  }

  try {
    return {
      event,
      data: JSON.parse(dataLines.join('\n')),
    };
  } catch {
    return {
      event,
      data: {
        detail: 'Invalid stream payload from server.',
      },
    };
  }
}

async function buildStreamError(response) {
  const contentType = response.headers.get('content-type') || '';

  if (contentType.includes('application/json')) {
    const payload = await response.json();
    if (typeof payload?.detail === 'string' && payload.detail.trim()) {
      throw new Error(payload.detail);
    }

    if (typeof payload?.error === 'string' && payload.error.trim()) {
      throw new Error(payload.error);
    }

    if (payload && typeof payload === 'object') {
      for (const value of Object.values(payload)) {
        if (Array.isArray(value) && value.length && typeof value[0] === 'string') {
          throw new Error(value[0]);
        }
      }
    }

    throw new Error('Streaming request failed.');
  }

  const message = await response.text();
  throw new Error(message || 'Streaming request failed.');
}

export async function askQuestion(question, { conversationId, documentIds } = {}) {
  const response = await httpClient.post('/api/ask/', buildAskPayload(question, { conversationId, documentIds }));
  return response.data;
}

export async function streamAskQuestion(question, { conversationId, documentIds, onEvent, signal } = {}) {
  const payload = buildAskPayload(question, { conversationId, documentIds });
  const response = await fetch(`${API_BASE_URL}/api/ask/stream/`, {
    method: 'POST',
    headers: {
      Accept: 'text/event-stream',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok) {
    await buildStreamError(response);
  }

  if (!response.body) {
    throw new Error('Streaming is not supported by this browser.');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  async function readWithIdleTimeout() {
    return Promise.race([
      reader.read(),
      new Promise((_, reject) => {
        setTimeout(() => {
          reject(new Error('Streaming timed out while waiting for response chunks.'));
        }, STREAM_IDLE_TIMEOUT_MS);
      }),
    ]);
  }

  try {
    while (true) {
      const { done, value } = await readWithIdleTimeout();
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done });

      const { completeBlocks, remainder } = getEventBlocks(buffer);
      buffer = remainder;

      for (const block of completeBlocks) {
        const parsedEvent = parseEventBlock(block);
        if (parsedEvent) {
          onEvent?.(parsedEvent);
        }
      }

      if (done) {
        break;
      }
    }

    if (buffer.trim()) {
      const parsedEvent = parseEventBlock(buffer);
      if (parsedEvent) {
        onEvent?.(parsedEvent);
      }
    }
  } finally {
    await reader.cancel().catch(() => undefined);
  }
}

export async function getChatSessions() {
  const response = await httpClient.get('/api/chat-sessions/');
  return response.data;
}

export async function getChatSession(sessionId) {
  const response = await httpClient.get(`/api/chat-sessions/${sessionId}/`);
  return response.data;
}

export async function deleteChatSession(sessionId) {
  const response = await httpClient.delete(`/api/chat-sessions/${sessionId}/`);
  return response.data;
}

export async function clearChatHistory() {
  const response = await httpClient.delete('/api/chat-sessions/');
  return response.data;
}

export async function getOllamaHealth() {
  try {
    const response = await httpClient.get('/api/health/ollama/', {
      validateStatus: (status) => status >= 200 && status < 600,
    });

    if (response?.data) {
      return response.data;
    }

    throw new Error('Health check failed.');
  } catch (error) {
    throw new Error(normalizeApiError(error, 'Health check failed.'));
  }
}
