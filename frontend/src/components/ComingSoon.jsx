// Placeholder card for features that aren't built yet.
// Used by the Analysis tab in SRS Studio and by ComingSoonPage.
export default function ComingSoon({ title, description }) {
  return (
    <div className="bg-surface border border-dashed border-ink-muted/40 rounded-card px-6 py-16 text-center print:hidden">
      <span className="inline-block text-[11px] font-medium uppercase tracking-wide text-ink-muted bg-surface-2 border border-line rounded-full px-2.5 py-1 mb-3">
        Coming soon
      </span>
      {title && <p className="text-base font-medium text-ink">{title}</p>}
      {description && (
        <p className="mt-1.5 text-sm text-ink-muted max-w-sm mx-auto">{description}</p>
      )}
    </div>
  );
}