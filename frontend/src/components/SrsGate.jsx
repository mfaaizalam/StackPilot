import { useParams, useNavigate } from "react-router-dom";
import { useLatestSrs } from "../api/queries.js";

// Shared shell for the standalone Diagrams and Costing pages.
// Both panels need the latest SRS (srsId + version), so this loads it
// (cached, shared with SRS Studio) and passes it to `children(doc)`.
export default function SrsGate({ title, children }) {
  const { boardId } = useParams();
  const navigate = useNavigate();
  const { data: doc, isLoading, error } = useLatestSrs(boardId);

  const noSrs = error?.response?.status === 404;
  const otherError = error && !noSrs;

  return (
    <div className="min-h-screen bg-canvas text-ink">
      {/* Page toolbar */}
      <div className="border-b border-line bg-surface sticky top-0 z-10 print:hidden">
        <div className="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between gap-3">
          <h1 className="text-sm font-semibold text-ink">{title}</h1>
          {doc && (
            <span className="text-xs font-medium text-ink-muted bg-surface-2 border border-line rounded-full px-2.5 py-1">
              Based on SRS v{doc.version}
            </span>
          )}
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-8">
        {isLoading && (
          <div className="h-40 bg-surface border border-line rounded-card animate-pulse" />
        )}

        {noSrs && (
          <div className="bg-surface border border-dashed border-ink-muted/40 rounded-card px-6 py-14 text-center">
            <p className="text-base font-medium text-ink">No SRS yet for this project</p>
            <p className="mt-1.5 text-sm text-ink-muted max-w-sm mx-auto">
              {title} are built from the SRS requirements. Generate the SRS first.
            </p>
            <button
              onClick={() => navigate(`/boards/${boardId}/srs`)}
              className="mt-5 text-sm font-medium px-4 py-2.5 rounded-lg bg-brand text-brand-fg hover:bg-brand-hover transition"
            >
              Go to SRS
            </button>
          </div>
        )}

        {otherError && (
          <p className="text-sm text-danger bg-danger-soft border border-danger/20 rounded-card px-4 py-3">
            {error?.response?.data?.detail || "Could not load the SRS for this project."}
          </p>
        )}

        {doc && children(doc)}
      </div>
    </div>
  );
}