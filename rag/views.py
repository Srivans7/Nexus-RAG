import asyncio
import json

from asgiref.sync import sync_to_async
from django.conf import settings
from django.http import HttpResponseNotAllowed, JsonResponse, StreamingHttpResponse
from django.db.models import Count, QuerySet
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ChatSession, Document, QuestionAnswerLog
from .serializers import (
	AskRequestSerializer,
	AskResponseSerializer,
	DocumentSerializer,
	DocumentProcessingResponseSerializer,
	DocumentUploadSerializer,
	QuestionAnswerRequestSerializer,
	QuestionAnswerResponseSerializer,
)
from .services.document_processor import DocumentProcessor
from .services.ollama_service import OllamaService
from .services.qa_service import QuestionAnsweringService
from .services.rag_exceptions import LLMGenerationError, RetrievalError
from .services.rag_pipeline_service import RAGPipelineService


def _log_question_answer(primary_document_id, question: str, answer: str, context_preview: str):
	matched_document = Document.objects.filter(pk=primary_document_id).first() if primary_document_id else None
	QuestionAnswerLog.objects.create(
		document=matched_document,
		question=question,
		answer=answer,
		context_snippet=context_preview,
	)


def _sse_event(event_name: str, payload: dict) -> bytes:
	serialized_payload = json.dumps(payload)
	return f'event: {event_name}\ndata: {serialized_payload}\n\n'.encode('utf-8')


async def _astream_text_chunks(text: str, chunk_size: int = 18):
	for start in range(0, len(text), chunk_size):
		yield text[start:start + chunk_size]
		await asyncio.sleep(0)


@csrf_exempt
async def ask_stream_view(request):
	"""Stream a RAG answer over SSE so the UI can render tokens progressively."""
	if request.method != 'POST':
		return HttpResponseNotAllowed(['POST'])

	try:
		request_payload = json.loads(request.body.decode('utf-8') or '{}')
	except json.JSONDecodeError:
		return JsonResponse({'detail': 'Invalid JSON payload.'}, status=status.HTTP_400_BAD_REQUEST)

	serializer = AskRequestSerializer(data=request_payload)
	if not serializer.is_valid():
		return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

	question = serializer.validated_data['question']
	conversation_id = serializer.validated_data.get('conversation_id')
	document_ids = serializer.validated_data.get('document_ids')
	rag_pipeline_service = RAGPipelineService()

	try:
		pipeline_context = await sync_to_async(rag_pipeline_service.prepare, thread_sensitive=True)(
			question,
			conversation_id,
			document_ids,
		)
	except RetrievalError as exc:
		return JsonResponse({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
	except Exception as exc:
		return JsonResponse(
			{'detail': f'Unexpected ask pipeline failure: {exc}'},
			status=status.HTTP_500_INTERNAL_SERVER_ERROR,
		)

	async def event_stream():
		answer_fragments: list[str] = []
		has_streamed_model_output = False

		try:
			yield _sse_event(
				'start',
				{
					'conversation_id': str(pipeline_context['conversation_id']),
					'sources': pipeline_context['sources'],
					'document_references': pipeline_context['document_references'],
				},
			)

			try:
				async for token in rag_pipeline_service.ollama_service.astream_generate(pipeline_context['prompt']):
					has_streamed_model_output = True
					answer_fragments.append(token)
					yield _sse_event('token', {'token': token})
			except LLMGenerationError as exc:
				if not has_streamed_model_output and settings.RAG_ENABLE_LLM_FALLBACK:
					fallback_answer = rag_pipeline_service._build_grounded_summary(
						question=question,
						source_chunks=pipeline_context.get('source_chunks', []),
					)
					async for token in _astream_text_chunks(fallback_answer):
						answer_fragments.append(token)
						yield _sse_event('token', {'token': token})
				else:
					yield _sse_event('error', {'detail': str(exc)})
					return

			answer = ''.join(answer_fragments).strip()
			if not answer:
				yield _sse_event('error', {'detail': 'Ollama returned an empty answer.'})
				return

			answer = rag_pipeline_service.sanitize_answer(
				question=question,
				answer=answer,
				source_chunks=pipeline_context.get('source_chunks', []),
			)

			await sync_to_async(_log_question_answer, thread_sensitive=True)(
				pipeline_context['primary_document_id'],
				question,
				answer,
				pipeline_context['context_preview'],
			)
			await sync_to_async(rag_pipeline_service.conversation_memory_service.save_turn, thread_sensitive=True)(
				pipeline_context['session'],
				question,
				answer,
				pipeline_context['sources'],
			)
			yield _sse_event(
				'complete',
				{
					'conversation_id': str(pipeline_context['conversation_id']),
					'answer': answer,
					'sources': pipeline_context['sources'],
					'document_references': pipeline_context['document_references'],
					'primary_document_id': pipeline_context['primary_document_id'],
				},
			)
		except Exception as exc:
			yield _sse_event('error', {'detail': f'Streaming failed unexpectedly: {exc}'})
			return

	response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
	response['Cache-Control'] = 'no-cache'
	response['X-Accel-Buffering'] = 'no'
	return response


class FileUploadAPIView(APIView):
	"""Accepts a document upload and stores metadata in the database."""

	def post(self, request):
		serializer = DocumentUploadSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		document = serializer.save()
		return Response(DocumentSerializer(document).data, status=status.HTTP_201_CREATED)


class DocumentProcessingAPIView(APIView):
	"""Processes a previously uploaded document into extracted text."""

	def post(self, request, document_id: int):
		try:
			document = Document.objects.get(pk=document_id)
		except Document.DoesNotExist:
			return Response({'detail': 'Document not found.'}, status=status.HTTP_404_NOT_FOUND)

		try:
			processed_document, processed_chunks = DocumentProcessor.process(document)
		except Exception as exc:
			return Response(
				{
					'detail': 'Document processing failed.',
					'error': str(exc),
				},
				status=status.HTTP_400_BAD_REQUEST,
			)

		response_payload = {
			'document': DocumentSerializer(processed_document).data,
			'chunks': [
				{
					'id': chunk.id,
					'chunk_index': chunk.chunk_index,
					'content': chunk.content,
					'metadata': chunk.metadata,
					'created_at': chunk.created_at,
				}
				for chunk in processed_chunks
			],
		}
		response_serializer = DocumentProcessingResponseSerializer(response_payload)
		return Response(response_serializer.data, status=status.HTTP_200_OK)


class QuestionAnswerAPIView(APIView):
	"""Answers questions by retrieving context from processed documents."""

	def post(self, request):
		serializer = QuestionAnswerRequestSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		question = serializer.validated_data['question']
		document_id = serializer.validated_data.get('document_id')

		document_queryset: QuerySet[Document] = Document.objects.filter(status=Document.Status.PROCESSED)

		if document_id is not None:
			document_queryset = document_queryset.filter(pk=document_id)

		documents = list(document_queryset)
		if not documents:
			return Response(
				{'detail': 'No processed documents found for answering questions.'},
				status=status.HTTP_400_BAD_REQUEST,
			)

		answer, context, matched_document_id = QuestionAnsweringService.answer(question, documents)

		matched_document = Document.objects.filter(pk=matched_document_id).first() if matched_document_id else None
		QuestionAnswerLog.objects.create(
			document=matched_document,
			question=question,
			answer=answer,
			context_snippet=context,
		)

		response_payload = {
			'answer': answer,
			'context': context,
			'document_id': matched_document_id,
		}
		response_serializer = QuestionAnswerResponseSerializer(response_payload)
		return Response(response_serializer.data, status=status.HTTP_200_OK)


class AskAPIView(APIView):
	"""Runs the full RAG pipeline and generates an answer via local Ollama."""

	def post(self, request):
		serializer = AskRequestSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		question = serializer.validated_data['question']
		conversation_id = serializer.validated_data.get('conversation_id')
		document_ids = serializer.validated_data.get('document_ids')
		rag_pipeline_service = RAGPipelineService()

		try:
			result = rag_pipeline_service.ask(
				question=question,
				conversation_id=conversation_id,
				document_ids=document_ids,
			)
		except RetrievalError as exc:
			return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
		except LLMGenerationError as exc:
			return Response({'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
		except Exception as exc:
			return Response(
				{'detail': f'Unexpected ask pipeline failure: {exc}'},
				status=status.HTTP_500_INTERNAL_SERVER_ERROR,
			)

		_log_question_answer(
			result.get('primary_document_id'),
			question,
			result['answer'],
			result.get('context_preview', ''),
		)

		response_payload = {
			'conversation_id': result['conversation_id'],
			'answer': result['answer'],
			'sources': result['sources'],
			'document_references': result['document_references'],
		}
		response_serializer = AskResponseSerializer(response_payload)
		return Response(response_serializer.data, status=status.HTTP_200_OK)


class OllamaHealthAPIView(APIView):
	"""Reports LLM backend connectivity and model availability."""

	def get(self, request):
		from .services.rag_pipeline_service import _get_llm_service
		health = _get_llm_service().health_check()
		status_code = status.HTTP_200_OK if health.get('ok') else status.HTTP_503_SERVICE_UNAVAILABLE
		return Response(health, status=status_code)


class ChatSessionListAPIView(APIView):
	"""Returns recent chat sessions ordered by last activity."""

	def get(self, request):
		sessions = (
			ChatSession.objects
			.prefetch_related('messages')
			.annotate(message_count=Count('messages'))
			.filter(message_count__gt=0)
			.order_by('-updated_at')[:50]
		)
		data = [
			{
				'id': str(session.id),
				'title': session.title or 'Untitled chat',
				'message_count': session.message_count,
				'updated_at': session.updated_at.isoformat(),
				'created_at': session.created_at.isoformat(),
				'preview': (
					session.messages.filter(role='user').last().content[:80]
					if session.messages.filter(role='user').exists() else ''
				),
			}
			for session in sessions
		]
		return Response(data, status=status.HTTP_200_OK)

	def delete(self, request):
		"""Delete all chat sessions and their messages."""
		ChatSession.objects.all().delete()
		return Response({'detail': 'All chat history cleared.'}, status=status.HTTP_200_OK)


def _build_document_references_from_sources(sources: list[dict]) -> list[dict]:
	"""Aggregate source metadata to lightweight document references for UI rendering."""
	grouped: dict[int, dict] = {}
	for source in sources or []:
		document_id = source.get('document_id')
		if document_id is None:
			continue
		entry = grouped.setdefault(
			document_id,
			{
				'document_id': document_id,
				'file_name': source.get('file_name', ''),
				'chunk_indexes': set(),
				'max_score': 0.0,
			},
		)
		chunk_index = source.get('chunk_index')
		if isinstance(chunk_index, int):
			entry['chunk_indexes'].add(chunk_index)
		score = source.get('score', 0.0)
		if isinstance(score, (int, float)):
			entry['max_score'] = max(entry['max_score'], float(score))

	result = []
	for entry in grouped.values():
		result.append(
			{
				'document_id': entry['document_id'],
				'file_name': entry['file_name'],
				'chunk_indexes': sorted(entry['chunk_indexes']),
				'max_score': entry['max_score'],
			}
		)
	return result


class ChatSessionDetailAPIView(APIView):
	"""Returns one session with all messages so UI can reopen prior chats."""

	def get(self, request, session_id):
		session = ChatSession.objects.prefetch_related('messages').filter(id=session_id).first()
		if session is None:
			return Response({'detail': 'Chat session not found.'}, status=status.HTTP_404_NOT_FOUND)

		messages = []
		for message in session.messages.all().order_by('created_at', 'id'):
			sources = message.sources or []
			messages.append(
				{
					'id': f'{message.role}-{message.id}',
					'role': message.role,
					'content': message.content,
					'sources': sources,
					'document_references': _build_document_references_from_sources(sources),
					'timestamp': message.created_at.isoformat(),
				}
			)

		return Response(
			{
				'id': str(session.id),
				'title': session.title or 'Untitled chat',
				'created_at': session.created_at.isoformat(),
				'updated_at': session.updated_at.isoformat(),
				'messages': messages,
			},
			status=status.HTTP_200_OK,
		)

	def delete(self, request, session_id):
		"""Delete a single chat session and its messages."""
		session = ChatSession.objects.filter(id=session_id).first()
		if session is None:
			return Response({'detail': 'Chat session not found.'}, status=status.HTTP_404_NOT_FOUND)

		session.delete()
		return Response({'detail': 'Chat session deleted.'}, status=status.HTTP_200_OK)
