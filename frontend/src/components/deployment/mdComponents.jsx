// Markdown styling shared by the generated deployment document and supporting notes.
// react-markdown does not render raw HTML, so user notes cannot inject scripts.
export const md = {
  h1: (p) => <h1 className="text-3xl font-semibold tracking-tight text-neutral-900 mb-1" {...p} />,
  h2: (p) => <h2 className="text-xl font-semibold text-neutral-900 mt-10 mb-3 pb-2 border-b border-neutral-200" {...p} />,
  h3: (p) => <h3 className="text-base font-semibold text-neutral-900 mt-6 mb-2" {...p} />,
  p: (p) => <p className="text-sm text-neutral-700 leading-relaxed mb-3" {...p} />,
  ul: (p) => <ul className="list-disc pl-5 text-sm text-neutral-700 space-y-1 mb-3" {...p} />,
  ol: (p) => <ol className="list-decimal pl-5 text-sm text-neutral-700 space-y-1.5 mb-3" {...p} />,
  strong: (p) => <strong className="font-semibold text-neutral-900" {...p} />,
  em: (p) => <em className="text-neutral-500" {...p} />,
  code: (p) => <code className="text-[12px] bg-neutral-100 rounded px-1 py-0.5 break-words" {...p} />,
  blockquote: (p) => <blockquote className="border-l-4 border-amber-300 bg-amber-50 text-sm text-neutral-700 px-4 py-2 mb-4 rounded-r" {...p} />,
  a: (p) => <a className="text-brand underline break-all" target="_blank" rel="noopener noreferrer" {...p} />,
  table: (p) => <div className="overflow-x-auto mb-4"><table className="w-full text-sm border border-neutral-200 rounded-lg" {...p} /></div>,
  th: (p) => <th className="text-left font-semibold bg-neutral-50 border-b border-neutral-200 px-3 py-2 text-neutral-800" {...p} />,
  td: (p) => <td className="border-b border-neutral-100 px-3 py-2 text-neutral-700 align-top" {...p} />,
  pre: (p) => <pre className="text-xs bg-neutral-50 border border-neutral-200 rounded-lg p-3 overflow-x-auto mb-4" {...p} />,
};
