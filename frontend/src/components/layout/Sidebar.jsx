import { useState } from 'react';
import { ProfileEditModal } from '../auth/ProfileEditModal';

export function Sidebar({
  documents,
  health,
  indexedDocumentCount,
  isOpen,
  isAuthenticated,
  user,
  onClose,
  onLogout,
  onNewChat,
  onOpenLogin,
  onOpenRecentChat,
  onUpdateProfile,
  onClearHistory,
  onDeleteChat,
  onViewChange,
  recentChats,
  sidebarView,
  isLoading,
}) {
  const [showProfileEdit, setShowProfileEdit] = useState(false);
  const [showClearHistoryConfirm, setShowClearHistoryConfirm] = useState(false);
  const [openModal, setOpenModal] = useState(null); // 'account' or 'help'
  const navItems = [
    { id: 'library', icon: 'description', label: 'Documents' },
    { id: 'recent-chats', icon: 'forum', label: 'Recent Chats' },
    { id: 'account', icon: 'account_circle', label: 'Account' },
    { id: 'help', icon: 'help', label: 'Help Center' },
  ];

  return (
    <>
      <div
        className={`fixed inset-0 z-30 bg-black/50 backdrop-blur-sm transition md:hidden ${
          isOpen ? 'opacity-100' : 'pointer-events-none opacity-0'
        }`}
        onClick={onClose}
      />

      <aside
        className={`glass-panel fixed left-0 top-16 z-40 flex h-[calc(100vh-4rem)] w-[280px] flex-col gap-4 border-r border-white/5 p-4 transition-transform duration-300 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* New Chat */}
        <button
          className="rounded-2xl bg-primary px-5 py-4 font-geist text-sm font-semibold text-on-primary shadow-glow transition hover:bg-primary-container"
          onClick={onNewChat}
          type="button"
        >
          + New Chat
        </button>

        {/* Nav */}
        <nav className="space-y-1 px-1">
          <p className="px-3 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-[0.22em] text-on-surface-variant/50">
            Navigation
          </p>
          {navItems.map((item) => {
            const active = sidebarView === item.id;
            return (
              <button
                key={item.id}
                className={`w-full rounded-2xl px-4 py-3 text-left text-sm font-medium transition ${
                  active
                    ? 'bg-primary-container/90 text-on-primary-container'
                    : 'text-on-surface-variant hover:bg-white/5 hover:text-on-surface'
                }`}
                onClick={() => {
                  if (item.id === 'account' || item.id === 'help') {
                    setOpenModal(item.id);
                  } else {
                    onViewChange(item.id);
                  }
                }}
                type="button"
              >
                <div className="flex items-center gap-3">
                  <span className="material-symbols-outlined text-base">{item.icon}</span>
                  {item.label}
                </div>
              </button>
            );
          })}
        </nav>

        {/* Panel content area */}
        <div className="custom-scrollbar flex-1 overflow-y-auto px-1">
          {sidebarView === 'library' && (
            <LibraryPanel documents={documents} health={health} indexedDocumentCount={indexedDocumentCount} />
          )}
          {sidebarView === 'recent-chats' && (
            <RecentChatsPanel 
              recentChats={recentChats} 
              onOpenRecentChat={onOpenRecentChat}
              onClearHistory={() => setShowClearHistoryConfirm(true)}
              onDeleteChat={onDeleteChat}
            />
          )}
          {sidebarView === 'account' && (
            <AccountPanel
              isAuthenticated={isAuthenticated}
              user={user}
              health={health}
              onOpenLogin={onOpenLogin}
              onLogout={onLogout}
              onEditProfile={() => setShowProfileEdit(true)}
            />
          )}
          {sidebarView === 'help' && <HelpPanel />}
        </div>
      </aside>

      {showProfileEdit && (
        <ProfileEditModal
          user={user}
          isLoading={isLoading}
          onClose={() => setShowProfileEdit(false)}
          onSave={onUpdateProfile}
        />
      )}

      {showClearHistoryConfirm && (
        <div className="auth-dialog-overlay" role="alertdialog" aria-modal="true">
          <div className="auth-dialog-card max-w-md">
            <div className="space-y-4">
              <div>
                <h2 className="font-geist text-2xl font-semibold text-on-surface">
                  Clear All History?
                </h2>
                <p className="mt-2 text-sm text-on-surface-variant">
                  This will permanently delete all your chat sessions and messages. This action cannot be undone.
                </p>
              </div>

              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setShowClearHistoryConfirm(false)}
                  className="flex-1 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-medium text-on-surface-variant transition hover:bg-white/10"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={async () => {
                    await onClearHistory();
                    setShowClearHistoryConfirm(false);
                  }}
                  className="flex-1 rounded-2xl border border-error/30 bg-error/10 px-4 py-3 text-sm font-medium text-error transition hover:bg-error/20"
                >
                  Delete All
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {openModal === 'account' && (
        <div
          className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
          onClick={() => setOpenModal(null)}
        >
          <div
            className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="w-full max-w-md m-4 rounded-[28px] border border-white/10 bg-black/80 backdrop-blur-xl p-6 glass-panel">
              <div className="flex items-start justify-between gap-4 mb-6">
                <h2 className="font-geist text-2xl font-semibold text-on-surface">Account</h2>
                <button
                  className="rounded-full border border-white/10 bg-white/5 p-2 text-on-surface-variant transition hover:text-on-surface"
                  onClick={() => setOpenModal(null)}
                  type="button"
                >
                  <span className="material-symbols-outlined text-base">close</span>
                </button>
              </div>
              <AccountPanel
                isAuthenticated={isAuthenticated}
                user={user}
                health={health}
                onOpenLogin={onOpenLogin}
                onLogout={onLogout}
                onEditProfile={() => setShowProfileEdit(true)}
                onClearHistory={() => setShowClearHistoryConfirm(true)}
              />
            </div>
          </div>
        </div>
      )}

      {openModal === 'help' && (
        <div
          className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
          onClick={() => setOpenModal(null)}
        >
          <div
            className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="w-full max-w-2xl m-4 rounded-[28px] border border-white/10 bg-black/80 backdrop-blur-xl p-6 glass-panel custom-scrollbar max-h-[80vh] overflow-y-auto">
              <div className="flex items-start justify-between gap-4 mb-6">
                <h2 className="font-geist text-2xl font-semibold text-on-surface">Help Center</h2>
                <button
                  className="rounded-full border border-white/10 bg-white/5 p-2 text-on-surface-variant transition hover:text-on-surface flex-shrink-0"
                  onClick={() => setOpenModal(null)}
                  type="button"
                >
                  <span className="material-symbols-outlined text-base">close</span>
                </button>
              </div>
              <HelpPanel />
            </div>
          </div>
        </div>
      )}
    </>
  );
}

/* ── Library ── */
function LibraryPanel({ documents, health, indexedDocumentCount }) {
  return (
    <div className="glass-card rounded-3xl p-4 mt-2">
      <div className="mb-3 flex items-center justify-between text-xs text-on-surface-variant">
        <span>{indexedDocumentCount} documents indexed</span>
        <span
          className={`inline-flex h-2.5 w-2.5 rounded-full ${
            health?.ok ? 'bg-secondary shadow-cyan' : 'bg-error'
          }`}
        />
      </div>
      <div className="space-y-2">
        {documents.length ? (
          documents.map((doc) => (
            <div key={doc.id} className="rounded-2xl bg-black/20 px-3 py-3 text-sm text-on-surface-variant">
              <div className="mb-1 flex items-center gap-2 text-secondary">
                <span className="material-symbols-outlined text-base">article</span>
                <span className="truncate font-medium">{doc.fileName}</span>
              </div>
              <p className="text-xs text-on-surface-variant/70">
                {doc.chunkCount} chunks · {doc.status}
              </p>
            </div>
          ))
        ) : (
          <p className="rounded-2xl border border-dashed border-white/10 px-3 py-4 text-sm text-on-surface-variant/70">
            No uploaded documents yet.
          </p>
        )}
      </div>
    </div>
  );
}

/* ── Recent Chats ── */
function RecentChatsPanel({ recentChats, onOpenRecentChat, onClearHistory, onDeleteChat }) {
  const [contextMenu, setContextMenu] = useState(null);
  const [selectedChatId, setSelectedChatId] = useState(null);

  const handleContextMenu = (e, sessionId) => {
    e.preventDefault();
    setSelectedChatId(sessionId);
    setContextMenu({ x: e.clientX, y: e.clientY });
  };

  const handleDeleteChat = async () => {
    if (selectedChatId) {
      await onDeleteChat?.(selectedChatId);
      setContextMenu(null);
      setSelectedChatId(null);
    }
  };

  if (!recentChats.length) {
    return (
      <div className="mt-2 rounded-2xl border border-dashed border-white/10 px-3 py-6 text-center text-sm text-on-surface-variant/70">
        No previous chats yet. Start a conversation to see history here.
      </div>
    );
  }

  return (
    <div className="mt-2 space-y-2">
      {recentChats.map((session) => (
        <button
          key={session.id}
          className="w-full rounded-2xl bg-black/20 px-3 py-3 text-left text-sm text-on-surface-variant transition hover:bg-white/5"
          onClick={() => onOpenRecentChat?.(session.id)}
          onContextMenu={(e) => handleContextMenu(e, session.id)}
          type="button"
        >
          <div className="flex items-center gap-2 text-on-surface">
            <span className="material-symbols-outlined text-base text-primary">chat</span>
            <span className="truncate font-medium">{session.title || 'Untitled chat'}</span>
          </div>
          <p className="mt-0.5 line-clamp-2 text-xs text-on-surface-variant/60">
            {session.preview || 'Open to continue this conversation.'}
          </p>
        </button>
      ))}

      {recentChats.length > 0 && (
        <button
          onClick={onClearHistory}
          type="button"
          className="mt-4 w-full rounded-2xl border border-error/30 bg-error/10 px-4 py-3 text-left text-sm font-medium text-error transition hover:bg-error/20"
        >
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-base">delete_sweep</span>
            Clear History
          </div>
        </button>
      )}

      {contextMenu && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setContextMenu(null)}
          />
          <div
            className="fixed z-50 rounded-2xl border border-white/10 bg-black/80 backdrop-blur-xl shadow-lg"
            style={{
              top: `${contextMenu.y}px`,
              left: `${contextMenu.x}px`,
            }}
          >
            <button
              onClick={handleDeleteChat}
              className="w-full px-4 py-3 text-left text-sm font-medium text-error transition hover:bg-error/10 rounded-2xl flex items-center gap-2"
              type="button"
            >
              <span className="material-symbols-outlined text-base">delete</span>
              Delete Chat
            </button>
          </div>
        </>
      )}
    </div>
  );
}

/* ── Account ── */
function AccountPanel({ isAuthenticated, user, health, onOpenLogin, onLogout, onEditProfile, onClearHistory }) {
  const backendLabel =
    health?.backend
      ? health.backend.charAt(0).toUpperCase() + health.backend.slice(1)
      : 'AI Backend';
  const modelLabel = health?.model || 'Unknown model';

  if (isAuthenticated && user) {
    return (
      <div className="mt-2 space-y-3">
        {/* Avatar */}
        <div className="flex flex-col items-center gap-2 rounded-3xl bg-black/20 px-4 py-5">
          {user.avatar_url ? (
            <img
              src={user.avatar_url}
              alt={user.name}
              className="h-16 w-16 rounded-full border border-primary/30 shadow-glow"
            />
          ) : (
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary-container text-on-primary-container shadow-glow">
              <span className="material-symbols-outlined text-[32px]">person</span>
            </div>
          )}
          <p className="font-geist text-base font-semibold text-on-surface">{user.name}</p>
          <p className="text-xs text-on-surface-variant">{user.email}</p>
        </div>

        {/* Profile Info */}
        <div className="rounded-2xl bg-black/20 px-4 py-4 space-y-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-on-surface-variant/50">
            Profile Information
          </p>
          <div className="space-y-2 text-sm text-on-surface-variant">
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined text-base text-primary">person</span>
              <span>{user.name}</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined text-base text-primary">email</span>
              <span>{user.email}</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined text-base text-primary">memory</span>
              <span>{backendLabel} · {modelLabel}</span>
            </div>
          </div>
        </div>

        <button
          className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-left text-sm font-medium text-on-surface-variant transition hover:bg-white/5"
          onClick={onEditProfile}
          type="button"
        >
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-base">edit</span>
            Edit Profile
          </div>
        </button>

        <button
          className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-left text-sm font-medium text-on-surface-variant transition hover:bg-white/5"
          onClick={onClearHistory}
          type="button"
        >
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-base">delete_sweep</span>
            Clear All History
          </div>
        </button>

        {/* Sign Out */}
        <button
          className="w-full rounded-2xl border border-error/30 bg-error/10 px-4 py-3 text-left text-sm font-medium text-error transition hover:bg-error/20"
          onClick={onLogout}
          type="button"
        >
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-base">logout</span>
            Sign Out
          </div>
        </button>
      </div>
    );
  }

  return (
    <div className="mt-2 space-y-3">
      {/* Avatar */}
      <div className="flex flex-col items-center gap-2 rounded-3xl bg-black/20 px-4 py-5">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary-container text-on-primary-container shadow-glow">
          <span className="material-symbols-outlined text-[32px]">person</span>
        </div>
        <p className="font-geist text-base font-semibold text-on-surface">Guest User</p>
        <p className="text-xs text-on-surface-variant">Local session</p>
      </div>

      {/* Profile Info */}
      <div className="rounded-2xl bg-black/20 px-4 py-4 space-y-3">
        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-on-surface-variant/50">
          Profile Information
        </p>
        <div className="space-y-2 text-sm text-on-surface-variant">
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-base text-primary">badge</span>
            <span>Guest User</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-base text-primary">devices</span>
            <span>Local Device</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-base text-primary">memory</span>
            <span>{backendLabel} · {modelLabel}</span>
          </div>
        </div>
      </div>

      <button
        className="w-full rounded-2xl border border-primary/30 bg-primary/10 px-4 py-3 text-left text-sm font-medium text-primary transition hover:bg-primary/20"
        onClick={onOpenLogin}
        type="button"
      >
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined text-base">login</span>
          Sign In with Google
        </div>
      </button>

      {/* Help text */}
      <p className="rounded-2xl bg-secondary/10 px-4 py-3 text-xs text-secondary/80">
        Sign in to save your conversations across devices and access your profile.
      </p>
    </div>
  );
}

/* ── Help Center ── */
function HelpPanel() {
  const steps = [
    { icon: 'upload_file', title: 'Upload a Document', desc: 'Click the paperclip in the chat bar and select a .md, .txt, or .pdf file.' },
    { icon: 'auto_awesome', title: 'Automatic Indexing', desc: 'Your document is chunked, embedded, and indexed into FAISS automatically.' },
    { icon: 'chat', title: 'Ask Questions', desc: 'Type any question in the chat. Nexus AI retrieves relevant passages and answers using Gemini.' },
    { icon: 'source', title: 'View Sources', desc: 'Every answer shows the exact document chunks used so you can verify accuracy.' },
    { icon: 'library_books', title: 'Multi-Document', desc: 'Upload multiple files and attach several documents to a single question.' },
    { icon: 'forum', title: 'Conversation Memory', desc: 'Follow-up questions are answered with full conversation context preserved.' },
  ];

  return (
    <div className="mt-2 space-y-3">
      <div className="rounded-2xl bg-black/20 px-4 py-4">
        <p className="mb-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-on-surface-variant/50">
          How to use Nexus AI
        </p>
        <div className="space-y-3">
          {steps.map((step, i) => (
            <div key={i} className="flex gap-3">
              <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-xl bg-primary-container text-on-primary-container">
                <span className="material-symbols-outlined text-[14px]">{step.icon}</span>
              </div>
              <div>
                <p className="text-xs font-semibold text-on-surface">{step.title}</p>
                <p className="text-[11px] leading-5 text-on-surface-variant/80">{step.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>


      {/* Contact */}
      <div className="rounded-2xl border border-white/5 bg-black/20 px-4 py-4">
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-on-surface-variant/50">
          Contact Us
        </p>
        <a
          href="mailto:srivanskatriyar7@gmail.com"
          className="inline-flex items-center gap-2 text-sm text-secondary hover:underline"
        >
          <span className="material-symbols-outlined text-base">mail</span>
          srivanskatriyar7@gmail.com
        </a>
      </div>
    </div>
  );
}
