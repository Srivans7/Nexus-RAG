import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { SourceCard } from './SourceCard';

function DocBadge({ name }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-md border border-primary/30 bg-primary/10 px-1.5 py-0.5 font-mono text-[11px] font-semibold text-primary">
      <span className="material-symbols-outlined text-[11px]">description</span>
      {name}
    </span>
  );
}

function AnswerContent({ content, docNames }) {
  const components = {
    code({ children }) {
      const text = String(children);
      if (docNames.has(text)) return <DocBadge name={text} />;
      return (
        <code className="rounded-lg bg-white/5 px-1.5 py-0.5 font-mono text-[13px] text-primary">
          {children}
        </code>
      );
    },
    strong({ children }) {
      return <strong className="font-semibold text-on-surface">{children}</strong>;
    },
    li({ children }) {
      return (
        <li className="flex gap-2 py-0.5">
          <span className="mt-2.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary/60" />
          <span>{children}</span>
        </li>
      );
    },
    ul({ children }) {
      return <ul className="space-y-0.5 pl-1">{children}</ul>;
    },
  };

  return (
    <div className="markdown-body">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
}

export function ChatMessage({ isLastMessage = false, message, onContinueMessage }) {
  const isUser = message.role === 'user';
  const isStreaming = Boolean(message.isLoading || message.isStreaming);
  const canContinue =
    !isUser &&
    isLastMessage &&
    !isStreaming &&
    Boolean(message.content?.trim()) &&
    Array.isArray(message.sources) &&
    message.sources.length > 0;
  const messageTime = new Date(message.timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });
  const docNames = new Set((message.documentReferences || []).map((r) => r.file_name));

  return (
    <div className={`flex flex-col gap-3 ${isUser ? 'items-end' : 'items-start'}`}>
      {!isUser ? (
        <div className="flex items-center gap-2 pl-1">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary-container/70 text-primary">
            <span className="material-symbols-outlined text-[16px]">auto_awesome</span>
          </div>
          <span className="font-geist text-[10px] font-semibold uppercase tracking-[0.24em] text-on-surface-variant">
            {isStreaming ? 'Nexus AI is analyzing' : 'Nexus AI response'}
          </span>
        </div>
      ) : null}

      <div
        className={`max-w-[92%] overflow-hidden rounded-[22px] px-5 py-4 shadow-lg ${
          isUser
            ? 'rounded-tr-md border border-primary/30 bg-primary/75 text-on-primary shadow-glow'
            : `glass-card rounded-tl-md ${message.isError ? 'border border-error/30' : ''}`
        }`}
      >
        {!isUser ? <div className="mb-4 h-[2px] w-64 max-w-full bg-gradient-to-r from-primary via-secondary to-transparent" /> : null}

        {message.isLoading && !message.content ? (
          <div className="space-y-4">
            <div className="h-[2px] w-full overflow-hidden rounded-full bg-surface-container">
              <div className="ai-shimmer h-full w-2/3 animate-shimmer" />
            </div>
            <p className="text-sm text-on-surface-variant">
              Retrieving relevant context and preparing a response...
            </p>
          </div>
        ) : isUser ? (
          <div className="space-y-3">
            {message.attachedDocuments?.length ? (
              <div className="flex flex-wrap gap-2">
                {message.attachedDocuments.map((document) => (
                  <span
                    key={document.id || document.fileName}
                    className="inline-flex items-center gap-1 rounded-full border border-on-primary/25 bg-black/15 px-2.5 py-1 text-[10px] uppercase tracking-[0.12em] text-on-primary/90"
                  >
                    <span className="material-symbols-outlined text-[12px]">description</span>
                    <span className="max-w-[220px] truncate">{document.fileName}</span>
                  </span>
                ))}
              </div>
            ) : null}
            <p className="whitespace-pre-wrap text-[16px] leading-7">{message.content}</p>
          </div>
        ) : (
          <>
            <AnswerContent content={message.content || ''} docNames={docNames} />
            {message.isStreaming ? <span className="ml-1 inline-block animate-pulse text-primary">|</span> : null}
          </>
        )}

      </div>

      {canContinue ? (
        <button
          className="ml-2 inline-flex items-center gap-2 rounded-full border border-white/10 bg-black/20 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-on-surface-variant transition hover:bg-white/10 hover:text-on-surface"
          onClick={() => onContinueMessage?.(message.id)}
          type="button"
        >
          <span className="material-symbols-outlined text-[13px]">more_horiz</span>
          Continue
        </button>
      ) : null}

      <span className="px-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-on-surface-variant/45">
        {messageTime}
      </span>
    </div>
  );
}
