from django.urls import path

from .views import AskAPIView, ChatSessionDetailAPIView, ChatSessionListAPIView, DocumentProcessingAPIView, FileUploadAPIView, OllamaHealthAPIView, QuestionAnswerAPIView


urlpatterns = [
    path('upload/', FileUploadAPIView.as_view(), name='file-upload'),
    path('documents/<int:document_id>/process/', DocumentProcessingAPIView.as_view(), name='document-process'),
    path('question-answer/', QuestionAnswerAPIView.as_view(), name='question-answer'),
    path('ask/', AskAPIView.as_view(), name='ask'),
    path('health/ollama/', OllamaHealthAPIView.as_view(), name='ollama-health'),
    path('chat-sessions/', ChatSessionListAPIView.as_view(), name='chat-sessions'),
    path('chat-sessions/<uuid:session_id>/', ChatSessionDetailAPIView.as_view(), name='chat-session-detail'),
]
