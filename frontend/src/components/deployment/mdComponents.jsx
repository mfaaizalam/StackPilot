// Markdown styling shared by the generated deployment document and supporting notes.
// react-markdown does not render raw HTML, so user notes cannot inject scripts.
export const md = {
  h1: (p) => <h1 className="text-3xl font-semibold tracking-tight text-ink mb-1" {...p} />,
  h2: (p) => <h2 className="text-xl font-semibold text-ink mt-10 mb-3 pb-2 border-b border-line" {...p} />,
  h3: (p) => <h3 className="text-base font-semibold text-ink mt-6 mb-2" {...p} />,
  p: (p) => <p className="text-sm text-ink leading-relaxed mb-3" {...p} />,
  ul: (p) => <ul className="list-disc pl-5 text-sm text-ink space-y-1 mb-3" {...p} />,
  ol: (p) => <ol className="list-decimal pl-5 text-sm text-ink space-y-1.5 mb-3" {...p} />,
  strong: (p) => <strong className="font-semibold text-ink" {...p} />,
  em: (p) => <em className="text-ink-muted" {...p} />,
  code: (p) => <code className="text-[12px] bg-surface-2 rounded px-1 py-0.5 break-words" {...p} />,
  blockquote: (p) => <blockquote className="border-l-4 border-warning/30 bg-warning-soft text-sm text-ink px-4 py-2 mb-4 rounded-r" {...p} />,
  a: (p) => <a className="text-brand underline break-all" target="_blank" rel="noopener noreferrer" {...p} />,
  table: (p) => <div className="overflow-x-auto mb-4"><table className="w-full text-sm border border-line rounded-lg" {...p} /></div>,
  th: (p) => <th className="text-left font-semibold bg-surface-2 border-b border-line px-3 py-2 text-ink" {...p} />,
  td: (p) => <td className="border-b border-line px-3 py-2 text-ink align-top" {...p} />,
  pre: (p) => <pre className="text-xs bg-surface-2 border border-line rounded-lg p-3 overflow-x-auto mb-4" {...p} />,
};
