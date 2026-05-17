export function SourceCard({ source }) {
  return (
    <article className="rounded-xl border border-white/10 bg-black/25 px-3 py-2.5 transition hover:bg-black/35">
      <div className="mb-1.5 flex items-center gap-2 text-secondary">
        <span className="material-symbols-outlined text-[14px]">article</span>
        <span className="truncate font-mono text-[10px] font-semibold">
          {source.file_name}
        </span>
        <span className="ml-auto shrink-0 rounded-full bg-secondary/15 px-1.5 py-0.5 font-mono text-[9px] text-secondary/80">
          chunk {source.chunk_index}
        </span>
      </div>
      {source.snippet ? (
        <p className="line-clamp-2 text-[11px] italic leading-5 text-on-surface-variant/70">
          &ldquo;{source.snippet}&rdquo;
        </p>
      ) : null}
      <p className="mt-1.5 text-[10px] text-on-surface-variant/40">
        doc #{source.document_id} · relevance {(source.score * 100).toFixed(0)}%
      </p>
    </article>
  );
}
