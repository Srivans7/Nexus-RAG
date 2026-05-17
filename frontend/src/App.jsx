import { useEffect, useState } from 'react';

import { AuthPage } from './components/auth/AuthPage';
import { ChatComposer } from './components/chat/ChatComposer';
import { ChatPanel } from './components/chat/ChatPanel';
import { Sidebar } from './components/layout/Sidebar';
import { useRagChat } from './hooks/useRagChat';
import { useAuth } from './hooks/useAuth';

export default function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(window.innerWidth >= 768);
  const [sidebarView, setSidebarView] = useState('library');
  const [infoBanner, setInfoBanner] = useState('');
  const [chatResetKey, setChatResetKey] = useState(0);
  const [composerHeight, setComposerHeight] = useState(180);

  const { isAuthenticated, user, isLoading, authError, handleGoogleSuccess, logout, updateProfile } = useAuth();
  const {
    askStatus,
    clearError,
    clearHistory,
    deleteSingleChat,
    continueAssistantMessage,
    documents,
    error,
    fetchRecentChats,
    health,
    healthStatus,
    indexedDocumentCount,
    messages,
    openRecentChat,
    recentChats,
    refreshHealth,
    startNewChat,
    submitQuestion,
    uploadFiles,
    uploadStatus,
  } = useRagChat();

  useEffect(() => {
    refreshHealth();
  }, []);

  function handleViewChange(view) {
    setSidebarView(view);
    if (view === 'recent-chats') {
      fetchRecentChats();
    }
  }

  function handleNewChat() {
    startNewChat();
    setChatResetKey((k) => k + 1);
    setInfoBanner('Started a new chat session.');
    setIsSidebarOpen(false);
  }

  async function handleOpenRecentChat(sessionId) {
    const session = await openRecentChat(sessionId);
    if (!session) {
      return;
    }

    setInfoBanner(`Opened chat: ${session.title || 'Untitled chat'}`);
    setIsSidebarOpen(false);
  }

  if (!isAuthenticated) {
    return <AuthPage authError={authError} isLoading={isLoading} onAuthSuccess={handleGoogleSuccess} />;
  }

  return (
    <div className="flex min-h-screen overflow-hidden">
      <Sidebar
        documents={documents}
        health={health}
        indexedDocumentCount={indexedDocumentCount}
        isOpen={isSidebarOpen}
        isAuthenticated={isAuthenticated}
        user={user}
        recentChats={recentChats}
        sidebarView={sidebarView}
        isLoading={isLoading}
        onViewChange={handleViewChange}
        onNewChat={handleNewChat}
        onOpenRecentChat={handleOpenRecentChat}
        onOpenLogin={() => {}}
        onLogout={logout}
        onUpdateProfile={updateProfile}
        onClearHistory={clearHistory}
        onDeleteChat={deleteSingleChat}
        onClose={() => setIsSidebarOpen(false)}
      />

      <main className="relative flex h-screen flex-1 flex-col">
        <header className="glass-panel fixed left-0 right-0 top-0 z-50 flex h-16 items-center justify-between border-b border-white/5 px-4 md:px-10">
          <div className="flex items-center gap-3">
            <button
              className="inline-flex h-10 w-10 items-center justify-center rounded-full text-on-surface-variant transition hover:bg-white/5"
              onClick={() => setIsSidebarOpen((prev) => !prev)}
              title={isSidebarOpen ? 'Close sidebar' : 'Open sidebar'}
              type="button"
            >
              <span className="material-symbols-outlined">{isSidebarOpen ? 'menu_open' : 'menu'}</span>
            </button>
            <div className="flex items-center gap-2.5">
              {/* Nexus AI Logo — click to refresh */}
              <button
                type="button"
                title="Refresh"
                onClick={() => window.location.reload()}
                className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary/20 ring-1 ring-primary/40 transition hover:bg-primary/30 hover:ring-primary/70"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <circle cx="12" cy="12" r="2.5" fill="#a78bfa"/>
                  <circle cx="5" cy="5" r="1.8" fill="#a78bfa" opacity="0.7"/>
                  <circle cx="19" cy="5" r="1.8" fill="#a78bfa" opacity="0.7"/>
                  <circle cx="5" cy="19" r="1.8" fill="#a78bfa" opacity="0.7"/>
                  <circle cx="19" cy="19" r="1.8" fill="#a78bfa" opacity="0.7"/>
                  <line x1="12" y1="12" x2="5" y2="5" stroke="#a78bfa" strokeWidth="1.2" strokeOpacity="0.6"/>
                  <line x1="12" y1="12" x2="19" y2="5" stroke="#a78bfa" strokeWidth="1.2" strokeOpacity="0.6"/>
                  <line x1="12" y1="12" x2="5" y2="19" stroke="#a78bfa" strokeWidth="1.2" strokeOpacity="0.6"/>
                  <line x1="12" y1="12" x2="19" y2="19" stroke="#a78bfa" strokeWidth="1.2" strokeOpacity="0.6"/>
                </svg>
              </button>
              <div>
                <p className="font-geist text-xl font-semibold tracking-tight text-primary">Nexus AI</p>
                <p className="text-xs text-on-surface-variant">
                  Upload, index, and interrogate your knowledge base.
                </p>
              </div>
            </div>
          </div>

          <div className="hidden items-center gap-4 text-sm text-on-surface-variant md:flex">
            <span
              className={`inline-flex cursor-default items-center gap-2 rounded-full border px-3 py-1 ${
                healthStatus === 'loading'
                  ? 'border-white/10 bg-white/5 text-on-surface-variant'
                  : health?.ok
                  ? 'border-secondary/30 bg-secondary/10 text-secondary'
                  : 'border-error/30 bg-error/10 text-error'
              }`}
              title={health?.model ? `Model: ${health.model}` : ''}
            >
              <span className="h-2 w-2 rounded-full bg-current" />
              {healthStatus === 'loading' ? 'Connecting...' : health?.ok ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </header>

        <div
          className={`custom-scrollbar flex-1 overflow-y-auto px-4 pt-20 transition-all duration-300 md:px-10 md:pt-24${isSidebarOpen ? ' md:ml-[280px]' : ''}`}
          style={{ paddingBottom: `${composerHeight + 24}px` }}
        >
          <div className="mx-auto flex w-full max-w-[1120px] flex-col gap-8">
            {error ? (
              <div className="glass-card rounded-2xl border border-error/25 px-5 py-4 text-sm text-error">
                <div className="flex items-start justify-between gap-4">
                  <p>{error}</p>
                  <button className="text-on-surface-variant transition hover:text-on-surface" onClick={clearError} type="button">
                    <span className="material-symbols-outlined text-base">close</span>
                  </button>
                </div>
              </div>
            ) : null}

            {infoBanner ? (
              <div className="glass-card rounded-2xl border border-secondary/25 px-5 py-4 text-sm text-secondary">
                <div className="flex items-start justify-between gap-4">
                  <p>{infoBanner}</p>
                  <button
                    className="text-on-surface-variant transition hover:text-on-surface"
                    onClick={() => setInfoBanner('')}
                    type="button"
                  >
                    <span className="material-symbols-outlined text-base">close</span>
                  </button>
                </div>
              </div>
            ) : null}

            <ChatPanel askStatus={askStatus} messages={messages} onContinueMessage={continueAssistantMessage} />
          </div>
        </div>

        <ChatComposer
          key={chatResetKey}
          askStatus={askStatus}
          health={health}
          indexedDocumentCount={indexedDocumentCount}
          isSidebarOpen={isSidebarOpen}
          isUploading={uploadStatus === 'loading'}
          onFilesSelected={uploadFiles}
          onHeightChange={setComposerHeight}
          onSubmit={submitQuestion}
        />
      </main>
    </div>
  );
}
