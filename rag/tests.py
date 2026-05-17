import json
import uuid
from unittest.mock import ANY, Mock, patch

from asgiref.sync import async_to_sync
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import ChatMessage, ChatSession, Document, DocumentChunk
from .services.conversation_memory_service import ConversationMemoryService
from .services.ollama_http_client import OllamaHttpError
from .services.ollama_service import OllamaService
from .services.rag_exceptions import LLMGenerationError, RetrievalError
from .services.rag_pipeline_service import RAGPipelineService


class RAGPipelineServiceTests(TestCase):
	def setUp(self):
		self.document = Document.objects.create(
			file_name='guide.md',
			file_type=Document.FileType.MARKDOWN,
			status=Document.Status.PROCESSED,
			extracted_text='Deployment guide for production.',
			original_file='documents/guide.md',
		)
		self.chunk = DocumentChunk.objects.create(
			document=self.document,
			chunk_index=0,
			content='Use gunicorn with a reverse proxy in production.',
			metadata={'chunk_size': 53},
		)
		self.second_document = Document.objects.create(
			file_name='runbook.md',
			file_type=Document.FileType.MARKDOWN,
			status=Document.Status.PROCESSED,
			extracted_text='Runbook for system recovery.',
			original_file='documents/runbook.md',
		)
		self.second_chunk = DocumentChunk.objects.create(
			document=self.second_document,
			chunk_index=0,
			content='Restart the worker tier before reindexing FAISS.',
			metadata={'chunk_size': 49},
		)

	def test_pipeline_returns_answer_and_sources(self):
		mock_vector_store = Mock()
		mock_vector_store.similarity_search.return_value = [
			{'document_id': self.document.id, 'chunk_index': 0, 'score': 0.88}
		]

		mock_prompt_builder = Mock()
		mock_prompt_builder.build.return_value = 'prompt content'

		mock_ollama = Mock()
		mock_ollama.generate.return_value = 'Generated answer from llama3.'

		service = RAGPipelineService(
			vector_store_service=mock_vector_store,
			prompt_builder_service=mock_prompt_builder,
			ollama_service=mock_ollama,
		)

		result = service.ask('How should I deploy?')

		self.assertIn('answer', result)
		self.assertEqual(result['answer'], 'Generated answer from llama3.')
		self.assertEqual(len(result['sources']), 1)
		self.assertEqual(result['sources'][0]['document_id'], self.document.id)
		self.assertEqual(result['sources'][0]['chunk_index'], 0)
		self.assertIn('conversation_id', result)
		self.assertEqual(len(result['document_references']), 1)
		self.assertEqual(result['document_references'][0]['file_name'], 'guide.md')

	def test_prepare_returns_prompt_and_fallback_context(self):
		mock_vector_store = Mock()
		mock_vector_store.similarity_search.return_value = [
			{'document_id': self.document.id, 'chunk_index': 0, 'score': 0.88}
		]

		mock_prompt_builder = Mock()
		mock_prompt_builder.build.return_value = 'prompt content'

		service = RAGPipelineService(
			vector_store_service=mock_vector_store,
			prompt_builder_service=mock_prompt_builder,
			ollama_service=Mock(),
		)

		result = service.prepare('How should I deploy?')

		self.assertEqual(result['prompt'], 'prompt content')
		self.assertEqual(len(result['sources']), 1)
		self.assertIn('fallback_answer', result)
		self.assertIn('document_references', result)

	def test_prepare_uses_keyword_fallback_when_vector_returns_no_hits(self):
		mock_vector_store = Mock()
		mock_vector_store.similarity_search.return_value = []

		service = RAGPipelineService(
			vector_store_service=mock_vector_store,
			prompt_builder_service=Mock(build=Mock(return_value='prompt content')),
			ollama_service=Mock(),
		)

		result = service.prepare('How should I deploy using reverse proxy?')

		self.assertTrue(result['sources'])
		self.assertIn('guide.md', [source['file_name'] for source in result['sources']])

	def test_prepare_uses_selected_documents_only(self):
		mock_vector_store = Mock()
		mock_vector_store.similarity_search.return_value = [
			{'document_id': self.second_document.id, 'chunk_index': 0, 'score': 0.77}
		]

		service = RAGPipelineService(
			vector_store_service=mock_vector_store,
			prompt_builder_service=Mock(build=Mock(return_value='prompt content')),
			ollama_service=Mock(),
		)

		service.prepare('How do I recover?', document_ids=[self.second_document.id])

		mock_vector_store.similarity_search.assert_called_once_with(
			query='How do I recover?',
			top_k=ANY,
			allowed_document_ids=[self.second_document.id],
		)

	def test_prepare_includes_conversation_history_from_prior_turns(self):
		first_vector_store = Mock()
		first_vector_store.similarity_search.return_value = [
			{'document_id': self.document.id, 'chunk_index': 0, 'score': 0.88}
		]
		prompt_builder = Mock()
		prompt_builder.build.return_value = 'prompt content'
		ollama_service = Mock()
		ollama_service.generate.return_value = 'Use gunicorn.'

		service = RAGPipelineService(
			vector_store_service=first_vector_store,
			prompt_builder_service=prompt_builder,
			ollama_service=ollama_service,
		)

		first_result = service.ask('How should I deploy?')

		second_vector_store = Mock()
		second_vector_store.similarity_search.return_value = [
			{'document_id': self.second_document.id, 'chunk_index': 0, 'score': 0.8}
		]
		second_prompt_builder = Mock()
		second_prompt_builder.build.return_value = 'follow-up prompt'

		follow_up_service = RAGPipelineService(
			vector_store_service=second_vector_store,
			prompt_builder_service=second_prompt_builder,
			ollama_service=Mock(),
		)

		follow_up_service.prepare(
			question='What about recovery?',
			conversation_id=first_result['conversation_id'],
		)

		self.assertTrue(second_prompt_builder.build.called)
		conversation_history = second_prompt_builder.build.call_args.kwargs['conversation_history']
		self.assertIn('How should I deploy?', conversation_history)
		self.assertIn('Use gunicorn.', conversation_history)

	@override_settings(RAG_ENABLE_LLM_FALLBACK=True)
	def test_pipeline_falls_back_when_ollama_unavailable(self):
		mock_vector_store = Mock()
		mock_vector_store.similarity_search.return_value = [
			{'document_id': self.document.id, 'chunk_index': 0, 'score': 0.81}
		]

		mock_prompt_builder = Mock()
		mock_prompt_builder.build.return_value = 'prompt content'

		mock_ollama = Mock()
		mock_ollama.generate.side_effect = LLMGenerationError('Ollama unavailable')

		service = RAGPipelineService(
			vector_store_service=mock_vector_store,
			prompt_builder_service=mock_prompt_builder,
			ollama_service=mock_ollama,
		)

		result = service.ask('How should I deploy?')

		self.assertIn('Best answer from the selected document(s):', result['answer'])
		self.assertEqual(len(result['sources']), 1)

	def test_sanitize_answer_rewrites_prompt_dump_output(self):
		service = RAGPipelineService(
			vector_store_service=Mock(),
			prompt_builder_service=Mock(),
			ollama_service=Mock(),
		)

		dump_like_answer = (
			'Sure! Here is context.\n\n'
			'Conversation History: No prior conversation history.\n\n'
			'Context: [1] Document: guide.md (document_id=1, chunk_index=0)\n'
			'Content: Use gunicorn with a reverse proxy in production.'
		)

		rewritten = service.sanitize_answer(
			question='How should I deploy?',
			answer=dump_like_answer,
			source_chunks=[
				{
					'document_id': self.document.id,
					'file_name': self.document.file_name,
					'chunk_index': 0,
					'score': 0.9,
					'content': 'Use gunicorn with a reverse proxy in production. Keep workers tuned.',
				}
			],
		)

		self.assertIn('Best answer from the selected document(s):', rewritten)
		self.assertNotIn('Conversation History:', rewritten)
		self.assertNotIn('document_id=', rewritten)


class AskAPIViewTests(TestCase):
	def setUp(self):
		self.client = APIClient()

	@patch('rag.views.RAGPipelineService.ask')
	def test_ask_endpoint_returns_answer_and_sources(self, mock_ask):
		mock_ask.return_value = {
			'conversation_id': uuid.uuid4(),
			'answer': 'Answer from RAG',
			'sources': [
				{
					'document_id': 1,
					'file_name': 'guide.md',
					'chunk_index': 0,
					'score': 0.9,
				}
			],
			'document_references': [
				{
					'document_id': 1,
					'file_name': 'guide.md',
					'chunk_indexes': [0],
					'max_score': 0.9,
				}
			],
			'context_preview': 'preview',
			'primary_document_id': None,
		}

		response = self.client.post('/api/ask/', {'question': 'What is deployment?'}, format='json')

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['answer'], 'Answer from RAG')
		self.assertEqual(len(response.data['sources']), 1)
		self.assertEqual(len(response.data['document_references']), 1)
		self.assertIn('conversation_id', response.data)

	@patch('rag.views.RAGPipelineService.ask')
	def test_ask_endpoint_handles_retrieval_error(self, mock_ask):
		mock_ask.side_effect = RetrievalError('No chunks found')

		response = self.client.post('/api/ask/', {'question': 'What is deployment?'}, format='json')

		self.assertEqual(response.status_code, 400)
		self.assertEqual(response.data['detail'], 'No chunks found')

	@patch('rag.views.RAGPipelineService.ask')
	def test_ask_endpoint_handles_generation_error(self, mock_ask):
		mock_ask.side_effect = LLMGenerationError('Ollama failed')

		response = self.client.post('/api/ask/', {'question': 'What is deployment?'}, format='json')

		self.assertEqual(response.status_code, 502)
		self.assertEqual(response.data['detail'], 'Ollama failed')

	def test_ask_endpoint_validates_missing_question(self):
		response = self.client.post('/api/ask/', {}, format='json')

		self.assertEqual(response.status_code, 400)
		self.assertIn('question', response.data)

	def _consume_stream(self, response):
		async def collect_async_stream():
			chunks = []
			async for chunk in response.streaming_content:
				chunks.append(chunk.decode('utf-8') if isinstance(chunk, bytes) else chunk)
			return ''.join(chunks)

		if hasattr(response.streaming_content, '__aiter__'):
			return async_to_sync(collect_async_stream)()

		return b''.join(response.streaming_content).decode('utf-8')

	@patch('rag.views.RAGPipelineService')
	def test_ask_stream_endpoint_streams_tokens_and_sources(self, mock_pipeline_class):
		async def fake_stream(prompt):
			self.assertEqual(prompt, 'prompt content')
			yield 'Answer'
			yield ' stream'

		mock_pipeline = Mock()
		mock_pipeline.prepare.return_value = {
			'session': ChatSession.objects.create(),
			'conversation_id': uuid.uuid4(),
			'prompt': 'prompt content',
			'sources': [
				{
					'document_id': 1,
					'file_name': 'guide.md',
					'chunk_index': 0,
					'score': 0.9,
				}
			],
			'document_references': [
				{
					'document_id': 1,
					'file_name': 'guide.md',
					'chunk_indexes': [0],
					'max_score': 0.9,
				}
			],
			'context_preview': 'preview',
			'primary_document_id': None,
			'fallback_answer': 'fallback answer',
		}
		mock_pipeline.ollama_service = Mock()
		mock_pipeline.ollama_service.astream_generate = fake_stream
		mock_pipeline.conversation_memory_service = Mock()
		mock_pipeline.sanitize_answer = Mock(side_effect=lambda **kwargs: kwargs['answer'])
		mock_pipeline_class.return_value = mock_pipeline

		response = self.client.post('/api/ask/stream/', {'question': 'What is deployment?'}, format='json')

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response['Content-Type'], 'text/event-stream')

		streamed_body = self._consume_stream(response)
		self.assertIn('event: start', streamed_body)
		self.assertIn('event: token', streamed_body)
		self.assertIn('event: complete', streamed_body)
		self.assertIn('Answer stream', streamed_body)
		self.assertIn('document_references', streamed_body)

	@patch('rag.views.RAGPipelineService')
	def test_ask_stream_endpoint_returns_retrieval_error(self, mock_pipeline_class):
		mock_pipeline = Mock()
		mock_pipeline.prepare.side_effect = RetrievalError('No chunks found')
		mock_pipeline_class.return_value = mock_pipeline

		response = self.client.post('/api/ask/stream/', {'question': 'What is deployment?'}, format='json')

		self.assertEqual(response.status_code, 400)
		self.assertEqual(json.loads(response.content)['detail'], 'No chunks found')


class ConversationMemoryServiceTests(TestCase):
	def test_save_turn_persists_session_messages(self):
		session = ChatSession.objects.create(title='Deploy thread')
		service = ConversationMemoryService()

		service.save_turn(
			session=session,
			question='How should I deploy?',
			answer='Use gunicorn. [1]',
			sources=[{'document_id': 1, 'file_name': 'guide.md', 'chunk_index': 0, 'score': 0.9}],
		)

		self.assertEqual(ChatMessage.objects.filter(session=session).count(), 2)
		self.assertEqual(ChatMessage.objects.filter(session=session, role=ChatMessage.Role.USER).count(), 1)
		self.assertEqual(ChatMessage.objects.filter(session=session, role=ChatMessage.Role.ASSISTANT).count(), 1)


class OllamaServiceTests(TestCase):
	def test_health_check_returns_unavailable_payload_when_server_is_down(self):
		mock_http_client = Mock()
		mock_http_client.get_json.side_effect = OllamaHttpError('connection failed')

		service = OllamaService(http_client=mock_http_client)
		health = service.health_check()

		self.assertEqual(health['status'], 'error')
		self.assertEqual(health['message'], 'Ollama server is not running')
		self.assertEqual(health['ollama'], 'disconnected')
		self.assertFalse(health['ok'])

	def test_health_check_returns_model_missing_when_llama3_not_installed(self):
		mock_http_client = Mock()
		mock_http_client.get_json.return_value = {
			'models': [
				{'model': 'mistral:latest'},
			]
		}

		service = OllamaService(http_client=mock_http_client, model_name='llama3')
		health = service.health_check()

		self.assertEqual(health['status'], 'error')
		self.assertEqual(health['ollama'], 'connected')
		self.assertIn('not installed', health['message'])
		self.assertFalse(health['ok'])

	def test_health_check_returns_healthy_when_llama3_available(self):
		mock_http_client = Mock()
		mock_http_client.get_json.return_value = {
			'models': [
				{'model': 'llama3:latest'},
			]
		}

		service = OllamaService(http_client=mock_http_client, model_name='llama3')
		health = service.health_check()

		self.assertEqual(health['status'], 'Ollama · llama3')
		self.assertEqual(health['ollama'], 'connected')
		self.assertTrue(health['ok'])


class OllamaHealthAPIViewTests(TestCase):
	def setUp(self):
		self.client = APIClient()

	@patch('rag.services.rag_pipeline_service._get_llm_service')
	def test_health_endpoint_returns_503_when_unavailable(self, mock_get_llm_service):
		mock_get_llm_service.return_value.health_check.return_value = {
			'status': 'error',
			'message': 'Ollama server is not running',
			'ollama': 'disconnected',
			'ok': False,
		}

		response = self.client.get('/api/health/ollama/')

		self.assertEqual(response.status_code, 503)
		self.assertEqual(response.data['status'], 'error')
		self.assertEqual(response.data['message'], 'Ollama server is not running')

	@patch('rag.services.rag_pipeline_service._get_llm_service')
	def test_health_endpoint_returns_200_when_healthy(self, mock_get_llm_service):
		mock_get_llm_service.return_value.health_check.return_value = {
			'status': 'OpenRouter · google/gemma-4-26b-a4b-it:free',
			'ollama': 'connected',
			'ok': True,
		}

		response = self.client.get('/api/health/ollama/')

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['status'], 'OpenRouter · google/gemma-4-26b-a4b-it:free')
		self.assertEqual(response.data['ollama'], 'connected')
