// Placeholder card for features that aren't built yet.
// Used by the Analysis tab in SRS Studio and by ComingSoonPage.
export default function ComingSoon({ title, description }) {
  return (
    <div className="bg-white border border-dashed border-neutral-300 rounded-2xl px-6 py-16 text-center print:hidden">
      <span className="inline-block text-[11px] font-medium uppercase tracking-wide text-neutral-500 bg-neutral-100 border border-neutral-200 rounded-full px-2.5 py-1 mb-3">
        Coming soon
      </span>
      {title && <p className="text-base font-medium text-neutral-900">{title}</p>}
      {description && (
        <p className="mt-1.5 text-sm text-neutral-500 max-w-sm mx-auto">{description}</p>
      )}
    </div>
  );
}