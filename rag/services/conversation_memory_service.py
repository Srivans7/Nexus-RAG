from uuid import UUID

from langchain_classic.memory import ConversationBufferWindowMemory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from ..models import ChatMessage, ChatSession


class DjangoChatMessageHistory(BaseChatMessageHistory):
    """Database-backed LangChain chat history for persisted RAG conversations."""

    def __init__(self, session: ChatSession):
        self.session = session

    @property
    def messages(self) -> list[BaseMessage]:
        messages: list[BaseMessage] = []

        for message in self.session.messages.all():
            if message.role == ChatMessage.Role.USER:
                messages.append(HumanMessage(content=message.content))
            else:
                messages.append(
                    AIMessage(
                        content=message.content,
                        additional_kwargs={'sources': message.sources or []},
                    )
                )

        return messages

    def add_message(self, message: BaseMessage) -> None:
        if isinstance(message, HumanMessage):
            role = ChatMessage.Role.USER
            sources = []
        elif isinstance(message, AIMessage):
            role = ChatMessage.Role.ASSISTANT
            sources = message.additional_kwargs.get('sources', [])
        else:
            role = ChatMessage.Role.ASSISTANT
            sources = []

        ChatMessage.objects.create(
            session=self.session,
            role=role,
            content=message.content,
            sources=sources,
        )

    def clear(self) -> None:
        self.session.messages.all().delete()


class ConversationMemoryService:
    """Creates LangChain memory views over persisted chat sessions."""

    def __init__(self, window_size: int = 6):
        self.window_size = window_size

    def get_or_create_session(self, conversation_id: UUID | None = None) -> ChatSession:
        if conversation_id is None:
            return ChatSession.objects.create()

        session, _ = ChatSession.objects.get_or_create(id=conversation_id)
        return session

    def build_memory(self, session: ChatSession) -> ConversationBufferWindowMemory:
        return ConversationBufferWindowMemory(
            chat_memory=DjangoChatMessageHistory(session),
            memory_key='chat_history',
            input_key='question',
            return_messages=False,
            k=self.window_size,
        )

    def load_history(self, session: ChatSession, document_ids: list | None = None) -> str:
        """Return formatted conversation history, optionally filtered to turns that
        involved the same documents as the current query.  This prevents answers
        about document A from bleeding into questions about document B."""
        messages = list(session.messages.order_by('created_at', 'id'))
        if not messages:
            return ''

        # Pair up (Human, AI) turns
        pairs: list[tuple] = []
        i = 0
        while i < len(messages) - 1:
            human_msg = messages[i]
            ai_msg = messages[i + 1]
            if human_msg.role == 'user' and ai_msg.role == 'assistant':
                pairs.append((human_msg, ai_msg))
                i += 2
            else:
                i += 1

        if not pairs:
            return ''

        # If document_ids provided, only keep turns that involved those docs.
        if document_ids:
            doc_id_set = set(document_ids)
            pairs = [
                (h, a) for h, a in pairs
                if doc_id_set & {s.get('document_id') for s in (a.sources or [])}
            ]

        if not pairs:
            return ''

        # Return the last k turns only.
        recent = pairs[-(self.window_size // 2):]
        lines = []
        for human_msg, ai_msg in recent:
            lines.append(f'Human: {human_msg.content}')
            lines.append(f'AI: {ai_msg.content}')
        return '\n'.join(lines)

    def save_turn(self, session: ChatSession, question: str, answer: str, sources: list[dict] | None = None) -> None:
        history = DjangoChatMessageHistory(session)
        history.add_message(HumanMessage(content=question))
        history.add_message(AIMessage(content=answer, additional_kwargs={'sources': sources or []}))

        if not session.title:
            session.title = question[:255]
            session.save(update_fields=['title', 'updated_at'])
        else:
            session.save(update_fields=['updated_at'])
