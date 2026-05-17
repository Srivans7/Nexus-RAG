import { useEffect, useMemo, useReducer, useRef } from 'react';

import {
  askQuestion,
  getChatSession,
  getChatSessions,
  deleteChatSession,
  clearChatHistory,
  getOllamaHealth,
  normalizeApiError,
  processDocument,
  streamAskQuestion,
  uploadDocument,
} from '../services/api';

const initialState = {
  conversationId: null,
  documents: [],
  messages: [],
  recentChats: [],
  uploadStatus: 'idle',
  askStatus: 'idle',
  healthStatus: 'idle',
  health: null,
  error: '',
};

function chatReducer(state, action) {
  switch (action.type) {
    case 'set-recent-chats':
      return { ...state, recentChats: action.payload };
    case 'clear-error':
      return { ...state, error: '' };
    case 'set-error':
      return { ...state, error: action.payload };
    case 'set-upload-status':
      return { ...state, uploadStatus: action.payload, error: '' };
    case 'set-ask-status':
      return { ...state, askStatus: action.payload, error: '' };
    case 'set-health-status':
      return { ...state, healthStatus: action.payload };
    case 'set-health':
      return { ...state, health: action.payload };
    case 'set-conversation-id':
      return { ...state, conversationId: action.payload };
    case 'set-messages':
      return { ...state, messages: action.payload };
    case 'add-document':
      return {
        ...state,
        documents: [action.payload, ...state.documents],
      };
    case 'add-message':
      return {
        ...state,
        messages: [...state.messages, action.payload],
      };
    case 'replace-message':
      return {
        ...state,
        messages: state.messages.map((message) =>
          message.id === action.payload.id ? { ...message, ...action.payload.updates } : message,
        ),
      };
    case 'append-message-content':
      return {
        ...state,
        messages: state.messages.map((message) =>
          message.id === action.payload.id
            ? {
                ...message,
                content: `${message.content}${action.payload.content}`,
                ...action.payload.updates,
              }
            : message,
        ),
      };
    case 'reset-chat':
      return {
        ...state,
        conversationId: null,
        messages: [],
        askStatus: 'idle',
        error: '',
      };
    default:
      return state;
  }
}

function createMessage(payload) {
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    timestamp: new Date().toISOString(),
    documentReferences: [],
    sources: [],
    ...payload,
  };
}

function getReadableError(error, fallbackMessage) {
  return normalizeApiError(error, fallbackMessage);
}

export function useRagChat() {
  const [state, dispatch] = useReducer(chatReducer, initialState);
  const activeStreamRef = useRef(null);

  useEffect(() => {
    return () => {
      activeStreamRef.current?.abort();
    };
  }, []);

  async function refreshHealth() {
    dispatch({ type: 'set-health-status', payload: 'loading' });
    try {
      const health = await getOllamaHealth();
      dispatch({ type: 'set-health', payload: health });
      dispatch({ type: 'set-health-status', payload: 'success' });
    } catch (error) {
      dispatch({ type: 'set-health-status', payload: 'error' });
      dispatch({
        type: 'set-health',
        payload: {
          ok: false,
          status: 'unreachable',
          detail: getReadableError(error, 'Health check failed.'),
        },
      });
    }
  }

  async function uploadFiles(files) {
    if (!files.length) {
      return [];
    }

    dispatch({ type: 'set-upload-status', payload: 'loading' });

    try {
      const addedDocuments = [];

      for (const file of files) {
        const uploadedDocument = await uploadDocument(file);
        const processedDocument = await processDocument(uploadedDocument.id);
        const normalizedDocument = {
          id: processedDocument.document.id,
          fileName: processedDocument.document.file_name,
          status: processedDocument.document.status,
          chunkCount: processedDocument.chunks.length,
        };

        dispatch({
          type: 'add-document',
          payload: normalizedDocument,
        });

        addedDocuments.push(normalizedDocument);
      }

      dispatch({ type: 'set-upload-status', payload: 'success' });
      return addedDocuments;
    } catch (error) {
      dispatch({ type: 'set-upload-status', payload: 'error' });
      dispatch({
        type: 'set-error',
        payload: getReadableError(error, 'Upload or processing failed.'),
      });
      return [];
    }
  }

  async function submitQuestion(question, options = {}) {
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion) {
      return;
    }

    const selectedDocuments = options.selectedDocuments || [];
    const selectedDocumentIds = selectedDocuments
      .map((document) => document.id)
      .filter((documentId) => documentId !== null && documentId !== undefined);

    if (!selectedDocumentIds.length) {
      dispatch({
        type: 'set-error',
        payload: 'Attach at least one document for this question.',
      });
      return;
    }

    const userMessage = createMessage({
      role: 'user',
      content: trimmedQuestion,
      attachedDocuments: selectedDocuments,
    });
    const pendingAssistantMessage = createMessage({
      role: 'assistant',
      content: '',
      isLoading: true,
    });

    dispatch({ type: 'add-message', payload: userMessage });
    dispatch({ type: 'add-message', payload: pendingAssistantMessage });
    dispatch({ type: 'set-ask-status', payload: 'loading' });

    const abortController = new AbortController();
    activeStreamRef.current?.abort();
    activeStreamRef.current = abortController;

    const requestOptions = {
      conversationId: state.conversationId,
      documentIds: selectedDocumentIds,
    };

    try {
      let streamCompleted = false;
      let receivedStreamToken = false;
      await streamAskQuestion(trimmedQuestion, {
        ...requestOptions,
        signal: abortController.signal,
        onEvent: ({ event, data }) => {
          if (event === 'start') {
            if (data.conversation_id) {
              dispatch({ type: 'set-conversation-id', payload: data.conversation_id });
            }
            dispatch({
              type: 'replace-message',
              payload: {
                id: pendingAssistantMessage.id,
                updates: {
                  documentReferences: data.document_references || [],
                  sources: data.sources || [],
                },
              },
            });
            return;
          }

          if (event === 'token') {
            receivedStreamToken = true;
            dispatch({
              type: 'append-message-content',
              payload: {
                id: pendingAssistantMessage.id,
                content: data.token || '',
                updates: {
                  isLoading: false,
                  isStreaming: true,
                },
              },
            });
            return;
          }

          if (event === 'complete') {
            streamCompleted = true;
            if (data.conversation_id) {
              dispatch({ type: 'set-conversation-id', payload: data.conversation_id });
            }
            dispatch({
              type: 'replace-message',
              payload: {
                id: pendingAssistantMessage.id,
                updates: {
                  content: data.answer,
                  documentReferences: data.document_references || [],
                  sources: data.sources || [],
                  isLoading: false,
                  isStreaming: false,
                },
              },
            });
            return;
          }

          if (event === 'error') {
            throw new Error(data.detail || 'Streaming failed.');
          }
        },
      });

      if (!streamCompleted) {
        const response = await askQuestion(trimmedQuestion, requestOptions);

        dispatch({
          type: 'replace-message',
          payload: {
            id: pendingAssistantMessage.id,
            updates: {
              content: response.answer,
              documentReferences: response.document_references || [],
              sources: response.sources || [],
              isLoading: false,
              isStreaming: false,
            },
          },
        });

        if (response.conversation_id) {
          dispatch({ type: 'set-conversation-id', payload: response.conversation_id });
        }
      }

      dispatch({ type: 'set-ask-status', payload: 'success' });
    } catch (error) {
      if (error?.name === 'AbortError') {
        return;
      }

      if (receivedStreamToken) {
        try {
          const response = await askQuestion(trimmedQuestion, requestOptions);

          dispatch({
            type: 'replace-message',
            payload: {
              id: pendingAssistantMessage.id,
              updates: {
                content: response.answer,
                documentReferences: response.document_references || [],
                sources: response.sources || [],
                isLoading: false,
                isStreaming: false,
                isError: false,
              },
            },
          });

          if (response.conversation_id) {
            dispatch({ type: 'set-conversation-id', payload: response.conversation_id });
          }

          dispatch({ type: 'set-ask-status', payload: 'success' });
          return;
        } catch (recoveryError) {
          error = recoveryError;
        }
      }

      try {
        const response = await askQuestion(trimmedQuestion, requestOptions);

        dispatch({
          type: 'replace-message',
          payload: {
            id: pendingAssistantMessage.id,
            updates: {
              content: response.answer,
              documentReferences: response.document_references || [],
              sources: response.sources || [],
              isLoading: false,
              isStreaming: false,
              isError: false,
            },
          },
        });

        if (response.conversation_id) {
          dispatch({ type: 'set-conversation-id', payload: response.conversation_id });
        }

        dispatch({ type: 'set-ask-status', payload: 'success' });
        return;
      } catch (fallbackError) {
        error = fallbackError;
      }

      dispatch({
        type: 'replace-message',
        payload: {
          id: pendingAssistantMessage.id,
          updates: {
            content: getReadableError(error, 'Question answering failed.'),
            isLoading: false,
            isError: true,
          },
        },
      });
      dispatch({ type: 'set-ask-status', payload: 'error' });
      dispatch({
        type: 'set-error',
        payload: getReadableError(error, 'Question answering failed.'),
      });
    } finally {
      if (activeStreamRef.current === abortController) {
        activeStreamRef.current = null;
      }
    }
  }

  const indexedDocumentCount = useMemo(() => state.documents.length, [state.documents.length]);

  async function fetchRecentChats() {
    try {
      const sessions = await getChatSessions();
      const validSessions = (sessions || []).filter((session) => Number(session.message_count || 0) > 0);
      dispatch({ type: 'set-recent-chats', payload: validSessions });
    } catch {
      // silently ignore — recent chats are non-critical
    }
  }

  async function openRecentChat(sessionId) {
    try {
      dispatch({ type: 'clear-error' });
      const session = await getChatSession(sessionId);
      dispatch({ type: 'set-conversation-id', payload: session.id });
      dispatch({ type: 'set-messages', payload: session.messages || [] });
      dispatch({ type: 'set-ask-status', payload: 'success' });
      return session;
    } catch (error) {
      dispatch({
        type: 'set-error',
        payload: getReadableError(error, 'Could not open this chat session.'),
      });
      return null;
    }
  }

  async function clearHistory() {
    try {
      await clearChatHistory();
      dispatch({ type: 'set-recent-chats', payload: [] });
      dispatch({ type: 'reset-chat' });
      return true;
    } catch (error) {
      dispatch({
        type: 'set-error',
        payload: getReadableError(error, 'Could not clear chat history.'),
      });
      return false;
    }
  }

  async function deleteSingleChat(sessionId) {
    try {
      await deleteChatSession(sessionId);
      const updatedChats = state.recentChats.filter((chat) => chat.id !== sessionId);
      dispatch({ type: 'set-recent-chats', payload: updatedChats });
      return true;
    } catch (error) {
      dispatch({
        type: 'set-error',
        payload: getReadableError(error, 'Could not delete this chat.'),
      });
      return false;
    }
  }

  async function continueAssistantMessage(messageId) {
    const targetIndex = state.messages.findIndex((message) => message.id === messageId);
    if (targetIndex < 0) {
      return;
    }

    const targetMessage = state.messages[targetIndex];
    if (!targetMessage || targetMessage.role !== 'assistant') {
      return;
    }

    const previousUserMessage = [...state.messages]
      .slice(0, targetIndex)
      .reverse()
      .find((message) => message.role === 'user');

    const sourceDocuments = (targetMessage.sources || [])
      .map((source) => ({ id: source.document_id, fileName: source.file_name || 'Selected document' }))
      .filter((document) => document.id !== null && document.id !== undefined);

    const dedupedDocuments = sourceDocuments.filter(
      (document, index, collection) => collection.findIndex((item) => item.id === document.id) === index,
    );

    const baseQuestion = previousUserMessage?.content || 'Continue the previous answer';
    const continuationPrompt = `Continue your previous answer for this question in full detail: "${baseQuestion}". Do not restart from the beginning; continue from where you stopped.`;

    await submitQuestion(continuationPrompt, { selectedDocuments: dedupedDocuments });
  }

  return {
    ...state,
    indexedDocumentCount,
    uploadFiles,
    submitQuestion,
    refreshHealth,
    fetchRecentChats,
    openRecentChat,
    clearHistory,
    deleteSingleChat,
    continueAssistantMessage,
    startNewChat: () => dispatch({ type: 'reset-chat' }),
    clearError: () => dispatch({ type: 'clear-error' }),
  };
}
