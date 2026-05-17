import { useRef, useState } from 'react';

export function UploadDropzone({ documents, isUploading, onFilesSelected }) {
  const inputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);

  function handleFiles(fileList) {
    const acceptedFiles = Array.from(fileList || []).filter((file) =>
      ['.md', '.txt', '.pdf'].some((extension) => file.name.toLowerCase().endsWith(extension)),
    );

    if (acceptedFiles.length) {
      onFilesSelected(acceptedFiles);
    }
  }

  return (
    <section className="space-y-4">
      <div
        className={`glass-card rounded-[28px] border-2 border-dashed p-8 text-center transition ${
          isDragging ? 'border-primary/80 bg-primary/10' : 'border-outline-variant/30'
        }`}
        onClick={() => inputRef.current?.click()}
        onDragEnter={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={(event) => {
          event.preventDefault();
          setIsDragging(false);
        }}
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault();
          setIsDragging(false);
          handleFiles(event.dataTransfer.files);
        }}
        role="button"
        tabIndex={0}
      >
        <input
          ref={inputRef}
          accept=".md,.txt,.pdf"
          className="hidden"
          multiple
          onChange={(event) => handleFiles(event.target.files)}
          type="file"
        />

        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-surface-container-high text-primary shadow-glow">
          <span className={`material-symbols-outlined text-[30px] ${isUploading ? 'animate-pulse' : ''}`}>
            cloud_upload
          </span>
        </div>
        <h2 className="font-geist text-2xl font-semibold tracking-tight text-on-surface">
          Drag & drop files to chat
        </h2>
        <p className="mt-2 text-sm text-on-surface-variant">
          Supports .pdf, .md, .txt files. Upload triggers indexing and processing automatically.
        </p>

        <div className="mt-6 inline-flex items-center gap-2 rounded-full border border-white/10 bg-black/20 px-4 py-2 text-xs text-on-surface-variant">
          <span className={`h-2 w-2 rounded-full ${isUploading ? 'animate-pulse bg-primary shadow-glow' : 'bg-secondary shadow-cyan'}`} />
          {isUploading ? 'Uploading and processing...' : 'Ready to ingest documents'}
        </div>
      </div>

      {documents.length ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {documents.slice(0, 6).map((document) => (
            <div key={document.id} className="glass-card rounded-2xl px-4 py-3">
              <div className="mb-2 flex items-center gap-2 text-secondary">
                <span className="material-symbols-outlined text-base">description</span>
                <span className="truncate font-mono text-xs">{document.fileName}</span>
              </div>
              <p className="text-sm text-on-surface-variant">
                {document.chunkCount} chunks indexed
              </p>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}
