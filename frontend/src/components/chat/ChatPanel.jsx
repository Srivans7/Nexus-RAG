import { useEffect, useRef } from 'react';
import { ChatMessage } from './ChatMessage';

export function ChatPanel({ askStatus, messages, onContinueMessage }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, askStatus]);
  if (!messages.length) {
    return (
      <section className="mx-auto flex min-h-[320px] w-full max-w-[800px] flex-col items-center justify-center rounded-[32px] border border-white/5 bg-black/10 px-8 py-24 text-center">
        <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-surface-container-high text-primary shadow-glow">
          <span className="material-symbols-outlined text-[34px]">hub</span>
        </div>
        <h3 className="font-geist text-3xl font-semibold tracking-tight text-on-surface">
          Synthetic Intelligence Workspace
        </h3>
        <p className="mt-3 max-w-2xl text-sm leading-7 text-on-surface-variant">
          Upload your markdown, text, or PDF files, then ask grounded questions against the indexed knowledge base.
        </p>
      </section>
    );
  }

  return (
    <section className="mx-auto flex w-full max-w-[820px] flex-col gap-7">
      {messages.map((message) => (
        <ChatMessage
          key={message.id}
          message={message}
          isLastMessage={messages[messages.length - 1]?.id === message.id}
          onContinueMessage={onContinueMessage}
        />
      ))}

      {askStatus === 'loading' ? (
        <div className="text-center text-xs uppercase tracking-[0.22em] text-on-surface-variant/50">
          Retrieving context from FAISS and generating answer...
        </div>
      ) : null}

      <div ref={bottomRef} />
    </section>
  );
}
