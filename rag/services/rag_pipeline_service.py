from django.conf import settings
import re

from ..models import Document, DocumentChunk
from .conversation_memory_service import ConversationMemoryService
from .faiss_vector_store_service import FaissVectorStoreService
from .ollama_service import OllamaService
from .prompt_builder_service import PromptBuilderService
from .rag_exceptions import LLMGenerationError, RetrievalError


def _get_llm_service():
    """Return the LLM service based on RAG_LLM_BACKEND setting.

    When backend is 'auto', tries Gemini first (if key is set),
    then OpenRouter, then falls back to Ollama.
    """
    backend = getattr(settings, 'RAG_LLM_BACKEND', 'auto')

    if backend == 'gemini':
        from .gemini_service import GeminiService
        return GeminiService()

    if backend == 'groq':
        from .groq_service import GroqService
        return GroqService()

    if backend == 'openrouter':
        from .openrouter_service import OpenRouterService
        return OpenRouterService()

    if backend == 'ollama':
        return OllamaService()

    # backend == 'auto': Gemini -> OpenRouter -> Ollama
    if getattr(settings, 'RAG_GEMINI_API_KEY', ''):
        try:
            from .gemini_service import GeminiService
            import logging
            logging.getLogger(__name__).info('Auto-backend: using Gemini.')
            return GeminiService()
        except Exception:
            pass

    if getattr(settings, 'RAG_OPENROUTER_API_KEY', ''):
        try:
            from .openrouter_service import OpenRouterService
            import logging
            logging.getLogger(__name__).info('Auto-backend: using OpenRouter.')
            return OpenRouterService()
        except Exception:
            pass
    import logging
    logging.getLogger(__name__).info('Auto-backend: using Ollama.')
    return OllamaService()


class RAGPipelineService:
    """Orchestrates retrieval, prompt building, and LLM answer generation."""

    def __init__(
        self,
        vector_store_service: FaissVectorStoreService | None = None,
        conversation_memory_service: ConversationMemoryService | None = None,
        prompt_builder_service: PromptBuilderService | None = None,
        ollama_service: OllamaService | None = None,
    ):
        self.vector_store_service = vector_store_service or FaissVectorStoreService()
        self.conversation_memory_service = conversation_memory_service or ConversationMemoryService()
        self.prompt_builder_service = prompt_builder_service or PromptBuilderService()
        self.ollama_service = ollama_service or _get_llm_service()

    def ask(self, question: str, conversation_id=None, document_ids: list[int] | None = None) -> dict:
        """Execute full RAG flow and return generated answer with source metadata."""
        pipeline_context = self.prepare(
            question=question,
            conversation_id=conversation_id,
            document_ids=document_ids,
        )

        try:
            raw_answer = self.ollama_service.generate(prompt=pipeline_context['prompt'])
            answer = self.sanitize_answer(
                question=question,
                answer=raw_answer,
                source_chunks=pipeline_context.get('source_chunks', []),
            )
        except LLMGenerationError:
            if not settings.RAG_ENABLE_LLM_FALLBACK:
                raise
            # Show extracted content from the document rather than a useless retry message.
            answer = self._build_grounded_summary(
                question=question,
                source_chunks=pipeline_context.get('source_chunks', []),
            )

        self.conversation_memory_service.save_turn(
            session=pipeline_context['session'],
            question=question,
            answer=answer,
            sources=pipeline_context['sources'],
        )

        return {
            'conversation_id': pipeline_context['conversation_id'],
            'answer': answer,
            'sources': pipeline_context['sources'],
            'document_references': pipeline_context['document_references'],
            'context_preview': pipeline_context['context_preview'],
            'primary_document_id': pipeline_context['primary_document_id'],
        }

    def prepare(self, question: str, conversation_id=None, document_ids: list[int] | None = None) -> dict:
        """Resolve retrieval context once so sync and streaming flows share the same pipeline."""
        session = self.conversation_memory_service.get_or_create_session(conversation_id=conversation_id)
        processed_document_queryset = Document.objects.filter(status=Document.Status.PROCESSED)

        if document_ids:
            processed_document_queryset = processed_document_queryset.filter(id__in=document_ids)

        processed_document_ids = list(processed_document_queryset.values_list('id', flat=True))
        if not processed_document_ids:
            if document_ids:
                raise RetrievalError('None of the selected documents are available for retrieval.')
            raise RetrievalError('No processed documents are available for retrieval.')

        search_hits = self.vector_store_service.similarity_search(
            query=question,
            top_k=settings.RAG_RETRIEVAL_TOP_K,
            allowed_document_ids=processed_document_ids,
        )
        keyword_hits = self._keyword_fallback_hits(
            question=question,
            allowed_document_ids=processed_document_ids,
            top_k=settings.RAG_RETRIEVAL_TOP_K,
        )
        search_hits = self._merge_search_hits(
            question=question,
            semantic_hits=search_hits,
            keyword_hits=keyword_hits,
            top_k=settings.RAG_RETRIEVAL_TOP_K,
        )

        if not search_hits:
            raise RetrievalError('No relevant context chunks were retrieved from FAISS.')

        source_chunks = self._hydrate_chunks(search_hits)
        if not source_chunks:
            raise RetrievalError('Retrieved vector hits could not be mapped to chunk content.')

        conversation_history = self.conversation_memory_service.load_history(
            session,
            document_ids=processed_document_ids,
        )
        prompt = self.prompt_builder_service.build(
            question=question,
            context_chunks=source_chunks,
            conversation_history=conversation_history,
        )

        document_references = self._build_document_references(source_chunks)
        return {
            'session': session,
            'conversation_id': session.id,
            'prompt': prompt,
            'sources': [
                {
                    'document_id': chunk['document_id'],
                    'file_name': chunk['file_name'],
                    'chunk_index': chunk['chunk_index'],
                    'score': chunk['score'],
                    'snippet': ' '.join(chunk['content'].split())[:160],
                }
                for chunk in source_chunks
            ],
            'document_references': document_references,
            'context_preview': '\n\n'.join(chunk['content'] for chunk in source_chunks[:2]),
            'primary_document_id': source_chunks[0]['document_id'] if source_chunks else None,
            'fallback_answer': self._build_grounded_summary(
                question=question,
                source_chunks=source_chunks,
            ),
            'source_chunks': source_chunks,
        }

    def sanitize_answer(self, question: str, answer: str, source_chunks: list[dict]) -> str:
        """Normalize low-quality generations into concise grounded output."""
        normalized = (answer or '').strip()
        if not normalized:
            return self._build_grounded_summary(question=question, source_chunks=source_chunks)

        if self._looks_like_prompt_dump(normalized):
            return self._build_grounded_summary(question=question, source_chunks=source_chunks)

        # Light cleanup for better readability.
        normalized = re.sub(r'\n{3,}', '\n\n', normalized)
        return normalized

    @staticmethod
    def _looks_like_prompt_dump(answer: str) -> bool:
        lower_answer = answer.lower().strip()

        # These strings are unambiguous signs the model echoed internal metadata.
        hard_markers = [
            'document_id=',
            'chunk_index=',
            'here\'s a revised version of the conversation history',
        ]
        if any(marker in lower_answer for marker in hard_markers):
            return True

        # These labels are only suspicious when they appear as standalone line
        # headers (i.e. prompt structure leaked into the output), not mid-sentence.
        line_label_markers = [
            'conversation history:',
            'previous conversation:',
            'excerpt:',
        ]
        lines = lower_answer.splitlines()
        for line in lines:
            stripped = line.strip()
            if any(stripped.startswith(label) for label in line_label_markers):
                return True
            # A bare "Context:" or "Question:" line with nothing else on it
            # indicates the model re-emitted the prompt template.
            if stripped in ('context:', 'question:', 'answer:', 'content:'):
                return True

        if lower_answer.startswith('[1] document:') or lower_answer.startswith('document:'):
            return True

        # Only flag as a dump if the answer literally re-emits the numbered chunk
        # header format ([2] Document: ...) multiple times — a single mention of
        # a document name in a real answer is fine.
        return lower_answer.count('[') >= 3 and lower_answer.count('] document:') >= 2

    def _build_grounded_summary(self, question: str, source_chunks: list[dict]) -> str:
        """Generate a readable extractive answer when model output quality is poor."""
        if not source_chunks:
            return 'I could not find that in the selected document(s).'

        question_lower = question.lower().strip()
        if any(token in question_lower for token in ['author', 'candidate name', 'whose', 'who is this', 'name?']):
            first_line = next(
                (
                    line.strip()
                    for line in source_chunks[0]['content'].splitlines()
                    if line.strip()
                ),
                '',
            )
            if first_line:
                return f'The document appears to be about **{first_line}**.'

        if any(token in question_lower for token in ['tell me about this document', 'about this document', 'what is this document', 'resume']) and source_chunks:
            first_line = next(
                (
                    line.strip()
                    for line in source_chunks[0]['content'].splitlines()
                    if line.strip()
                ),
                'the candidate',
            )
            combined_text = '\n'.join(chunk['content'] for chunk in source_chunks[:4])
            sections = []
            for section_name in ['Education', 'Projects', 'Experience & Certifications', 'Technical Skills']:
                if section_name.lower() in combined_text.lower():
                    sections.append(section_name)

            if sections:
                section_text = ', '.join(sections[:-1]) + (f' and {sections[-1]}' if len(sections) > 1 else sections[0])
                return f'This document appears to be the resume of **{first_line}**. It covers {section_text}.'

        if 'project' in question_lower:
            project_lines = []
            seen_projects = set()
            for chunk in source_chunks[:6]:
                for raw_line in chunk['content'].splitlines():
                    line = ' '.join(raw_line.split()).strip('• ').strip()
                    if '|' not in line or len(line) < 8:
                        continue
                    title = line.split('|', 1)[0].strip()
                    if not title or title.lower() in seen_projects:
                        continue
                    seen_projects.add(title.lower())
                    project_lines.append(f'- **{title}**: {line.split("|", 1)[1].strip()}')

            if project_lines:
                return 'Projects mentioned in the document:\n\n' + '\n'.join(project_lines[:6])

        max_chunks = source_chunks[:4]
        sentence_candidates: list[tuple[int, int, str]] = []
        seen = set()
        question_tokens = self._question_tokens(question)

        for chunk_position, chunk in enumerate(max_chunks):
            parts = re.split(r'(?<=[.!?])\s+|\n+', chunk['content'])
            for part in parts:
                cleaned = ' '.join(part.split()).strip()
                if len(cleaned) < 25:
                    continue

                key = cleaned.lower()
                if key in seen:
                    continue

                seen.add(key)
                sentence_tokens = {
                    token
                    for token in re.findall(r'[a-zA-Z0-9+.#_-]+', cleaned.lower())
                    if len(token) > 2
                }
                overlap_score = len(question_tokens & sentence_tokens)
                prefix_bonus = 3 if any(cleaned.lower().startswith(f'{token}:') for token in question_tokens) else 0
                score = overlap_score * 10 + prefix_bonus - chunk_position
                sentence_candidates.append((score, chunk_position, cleaned))

        if not sentence_candidates:
            return 'I could not find that in the selected document(s).'

        # For broad questions ("explain", "summarise", "all") show more points.
        is_broad = any(token in question.lower() for token in ['explain', 'all', 'summary', 'summarize', 'overview', 'describe', 'brief'])
        limit = 10 if is_broad else 4
        summary_points = [
            sentence
            for _, _, sentence in sorted(
                sentence_candidates,
                key=lambda item: (-item[0], item[1]),
            )[:limit]
        ]
        summary = '\n'.join(f'- {point}' for point in summary_points)

        cited_sources = ', '.join(f'[{index}]' for index, _ in enumerate(max_chunks, start=1))
        is_summary_question = any(token in question.lower() for token in ['summary', 'summarize', 'what this', 'overview'])
        title = 'Summary from the selected document(s):' if is_summary_question else 'Best answer from the selected document(s):'

        return f"{title}\n\n{summary}\n\nSources: {cited_sources}"

    @staticmethod
    def _merge_search_hits(question: str, semantic_hits: list[dict], keyword_hits: list[dict], top_k: int) -> list[dict]:
        """Blend lexical and semantic hits so short factual questions retrieve the right chunk."""
        question_lower = question.lower()
        should_blend = not semantic_hits or any(
            marker in question_lower
            for marker in [
                'author',
                'name',
                'candidate',
                'resume',
                'document',
                'project',
                'projects',
                'experience',
                'skills',
            ]
        )

        if not should_blend:
            return semantic_hits[:top_k]

        merged: list[dict] = []
        seen = set()

        for hit in keyword_hits + semantic_hits:
            key = (hit['document_id'], hit['chunk_index'])
            if key in seen:
                continue
            seen.add(key)
            merged.append(hit)
            if len(merged) >= top_k:
                break

        return merged

    @staticmethod
    def _question_tokens(question: str) -> set[str]:
        stop_words = {
            'the', 'this', 'that', 'tell', 'about', 'what', 'which', 'who', 'why', 'how',
            'can', 'you', 'does', 'from', 'with', 'into', 'your', 'document', 'brief',
            'explain', 'please', 'there', 'any', 'all', 'is', 'are', 'was', 'were',
        }
        return {
            token
            for token in re.findall(r'[a-zA-Z0-9+.#_-]+', question.lower())
            if len(token) > 2 and token not in stop_words
        }

    @staticmethod
    def _build_document_references(source_chunks: list[dict]) -> list[dict]:
        references_by_document: dict[int, dict] = {}

        for chunk in source_chunks:
            reference = references_by_document.setdefault(
                chunk['document_id'],
                {
                    'document_id': chunk['document_id'],
                    'file_name': chunk['file_name'],
                    'chunk_indexes': [],
                    'max_score': chunk['score'],
                },
            )
            reference['chunk_indexes'].append(chunk['chunk_index'])
            reference['max_score'] = max(reference['max_score'], chunk['score'])

        return [
            {
                **reference,
                'chunk_indexes': sorted(set(reference['chunk_indexes'])),
            }
            for reference in references_by_document.values()
        ]

    @staticmethod
    def _hydrate_chunks(search_hits: list[dict]) -> list[dict]:
        """Expand vector hits into chunk text payloads for prompt construction."""
        hydrated = []

        for hit in search_hits:
            chunk = (
                DocumentChunk.objects.select_related('document')
                .filter(
                    document_id=hit['document_id'],
                    chunk_index=hit['chunk_index'],
                )
                .first()
            )
            if not chunk:
                continue

            hydrated.append(
                {
                    'document_id': chunk.document_id,
                    'file_name': chunk.document.file_name,
                    'chunk_index': chunk.chunk_index,
                    'score': hit['score'],
                    'content': chunk.content,
                }
            )

        return hydrated

    @staticmethod
    def _keyword_fallback_hits(question: str, allowed_document_ids: list[int], top_k: int) -> list[dict]:
        """Fallback retriever using lexical overlap when vector search has no hits."""
        if not allowed_document_ids:
            return []

        tokens = {
            token
            for token in re.findall(r'[a-zA-Z0-9]+', question.lower())
            if len(token) > 2
        }

        candidate_chunks = list(
            DocumentChunk.objects.filter(document_id__in=allowed_document_ids)
            .select_related('document')
            .order_by('document_id', 'chunk_index')[:300]
        )

        if not candidate_chunks:
            return []

        if 'project' in tokens or 'projects' in tokens:
            for chunk in candidate_chunks:
                if 'projects' not in chunk.content.lower():
                    continue

                project_window = [
                    window_chunk
                    for window_chunk in candidate_chunks
                    if window_chunk.document_id == chunk.document_id
                    and chunk.chunk_index <= window_chunk.chunk_index <= chunk.chunk_index + 3
                ]
                if project_window:
                    return [
                        {
                            'document_id': window_chunk.document_id,
                            'chunk_index': window_chunk.chunk_index,
                            'score': 0.72,
                        }
                        for window_chunk in project_window[:top_k]
                    ]

        scored_chunks: list[tuple[int, DocumentChunk]] = []
        for chunk in candidate_chunks:
            chunk_tokens = {
                token
                for token in re.findall(r'[a-zA-Z0-9]+', chunk.content.lower())
                if len(token) > 2
            }
            overlap_score = len(tokens & chunk_tokens) if tokens else 0
            scored_chunks.append((overlap_score, chunk))

        scored_chunks.sort(key=lambda item: (item[0], -item[1].chunk_index), reverse=True)

        best_chunks = [chunk for score, chunk in scored_chunks if score > 0][:top_k]
        if not best_chunks:
            best_chunks = [chunk for _, chunk in scored_chunks[:top_k]]

        # Use a bounded pseudo-score for consistent downstream rendering.
        return [
            {
                'document_id': chunk.document_id,
                'chunk_index': chunk.chunk_index,
                'score': 0.55,
            }
            for chunk in best_chunks
        ]
