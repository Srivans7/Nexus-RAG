import { useEffect, useRef, useState } from 'react';

export function ChatComposer({ askStatus, health, indexedDocumentCount, isSidebarOpen, isUploading, onFilesSelected, onHeightChange, onSubmit }) {
  const [question, setQuestion] = useState('');
  const [selectedDocuments, setSelectedDocuments] = useState([]);
  const fileInputRef = useRef(null);
  const composerRef = useRef(null);

  useEffect(() => {
    const el = composerRef.current;
    if (!el || !onHeightChange) return;
    const observer = new ResizeObserver(() => onHeightChange(el.offsetHeight));
    observer.observe(el);
    return () => observer.disconnect();
  }, [onHeightChange]);

  async function handleFileInputChange(event) {
    const selectedFiles = Array.from(event.target.files || []).filter((file) =>
      ['.md', '.txt', '.pdf'].some((extension) => file.name.toLowerCase().endsWith(extension)),
    );

    if (selectedFiles.length) {
      const uploadedDocuments = await onFilesSelected(selectedFiles);
      if (uploadedDocuments?.length) {
        setSelectedDocuments(uploadedDocuments);
      }
    }

    event.target.value = '';
  }

  async function submitCurrentQuestion() {
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || askStatus === 'loading' || !indexedDocumentCount || !selectedDocuments.length) {
      return;
    }

    setQuestion('');
    await onSubmit(trimmedQuestion, { selectedDocuments });
  }

  async function handleSubmit(event) {
    event.preventDefault();
    await submitCurrentQuestion();
  }

  async function handleQuestionKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      await submitCurrentQuestion();
    }
  }

  function removeSelectedDocument(documentId) {
    setSelectedDocuments((currentDocuments) =>
      currentDocuments.filter((document) => document.id !== documentId),
    );
  }

  return (
    <div ref={composerRef} className={`fixed bottom-0 left-0 right-0 bg-gradient-to-t from-background via-background/95 to-transparent px-4 pb-6 pt-10 transition-all duration-300 md:px-10 md:pb-8${isSidebarOpen ? ' md:left-[280px]' : ''}`}>
      <div className="mx-auto max-w-[800px]">
        <form className="glass-card rounded-[28px] p-2 shadow-2xl" onSubmit={handleSubmit}>
          <input
            ref={fileInputRef}
            accept=".md,.txt,.pdf"
            className="hidden"
            multiple
            onChange={handleFileInputChange}
            type="file"
          />

          {selectedDocuments.length ? (
            <div className="mb-2 flex flex-wrap gap-2 px-2 pt-2">
              {selectedDocuments.map((document) => (
                <span
                  key={document.id}
                  className="inline-flex items-center gap-2 rounded-full border border-secondary/30 bg-secondary/10 px-3 py-1 text-[11px] text-secondary"
                >
                  <span className="material-symbols-outlined text-[13px]">description</span>
                  <span className="max-w-[180px] truncate">{document.fileName}</span>
                  <button
                    className="inline-flex h-4 w-4 items-center justify-center rounded-full text-secondary/90 transition hover:bg-secondary/20"
                    onClick={() => removeSelectedDocument(document.id)}
                    title="Remove selected document"
                    type="button"
                  >
                    <span className="material-symbols-outlined text-[12px]">close</span>
                  </button>
                </span>
              ))}
            </div>
          ) : null}

          <div className="flex items-end gap-2 rounded-[22px] border border-white/5 bg-black/20 px-2">
            <button
              className="inline-flex h-12 w-12 items-center justify-center rounded-2xl text-on-surface-variant transition hover:text-primary"
              onClick={() => fileInputRef.current?.click()}
              title="Insert document"
              type="button"
            >
              <span className="material-symbols-outlined">attach_file</span>
            </button>

            <textarea
              className="custom-scrollbar min-h-[56px] max-h-40 flex-1 resize-none bg-transparent px-2 py-4 text-[15px] leading-6 text-on-surface outline-none placeholder:text-on-surface-variant/40"
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={handleQuestionKeyDown}
              placeholder="Ask Nexus AI anything about your documents..."
              rows={1}
              value={question}
            />

            <button
              className="mb-1 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-on-primary shadow-glow transition hover:bg-primary-container disabled:cursor-not-allowed disabled:opacity-60"
              disabled={askStatus === 'loading' || !indexedDocumentCount || !selectedDocuments.length}
              title={
                !indexedDocumentCount
                  ? 'Upload at least one document to start chatting.'
                  : !selectedDocuments.length
                    ? 'Attach at least one document for this question.'
                    : 'Send message'
              }
              type="submit"
            >
              <span className="material-symbols-outlined text-[20px]">
                {askStatus === 'loading' ? 'hourglass_top' : 'send'}
              </span>
            </button>
          </div>
        </form>

        {!indexedDocumentCount ? (
          <p className="mt-3 text-center text-xs text-on-surface-variant">
            Upload at least one document to enable chat.
          </p>
        ) : !selectedDocuments.length ? (
          <p className="mt-3 text-center text-xs text-on-surface-variant">
            Attach document chip(s) to target this question.
          </p>
        ) : null}

        <div className="mt-4 flex flex-wrap items-center justify-center gap-6 text-[11px] font-medium text-on-surface-variant">
          <div className="flex items-center gap-2">
            <span className={`h-1.5 w-1.5 rounded-full ${isUploading ? 'bg-primary shadow-glow' : 'bg-on-surface-variant/40'}`} />
            {isUploading ? 'Uploading documents...' : 'Enter sends. Shift+Enter adds a new line.'}
          </div>
          <div className="flex items-center gap-2">
            <span className={`material-symbols-outlined text-[14px] ${health?.ok ? 'text-secondary' : 'text-error'}`}>
              offline_bolt
            </span>
            {health?.ok ? `${health?.model || 'AI Model'} Ready` : 'AI Unavailable'}
          </div>
        </div>
      </div>
    </div>
  );
}
