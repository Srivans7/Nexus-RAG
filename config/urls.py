"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from rag.views import AskAPIView, ChatSessionDetailAPIView, ChatSessionListAPIView, DocumentProcessingAPIView, FileUploadAPIView, LLMHealthAPIView, ask_stream_view
from rag.auth_views import google_oauth_login, get_current_user, logout, update_profile

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/google/', google_oauth_login, name='api-auth-google'),
    path('api/auth/user/', get_current_user, name='api-auth-user'),
    path('api/auth/logout/', logout, name='api-auth-logout'),
    path('api/auth/profile/', update_profile, name='api-auth-profile'),
    path('api/upload/', FileUploadAPIView.as_view(), name='api-upload'),
    path('api/process/<int:document_id>/', DocumentProcessingAPIView.as_view(), name='api-process'),
    path('api/ask/', AskAPIView.as_view(), name='api-ask'),
    path('api/ask/stream/', ask_stream_view, name='api-ask-stream'),
    path('api/health/llm/', LLMHealthAPIView.as_view(), name='api-llm-health'),
    path('api/chat-sessions/', ChatSessionListAPIView.as_view(), name='api-chat-sessions'),
    path('api/chat-sessions/<uuid:session_id>/', ChatSessionDetailAPIView.as_view(), name='api-chat-session-detail'),
    path('api/rag/', include('rag.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
