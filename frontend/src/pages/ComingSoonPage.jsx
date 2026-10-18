import ComingSoon from "../components/ComingSoon.jsx";

// Standalone page for sidebar sections that aren't built yet (SDD, Analysis, People, Settings).
export default function ComingSoonPage({ title, description }) {
  return (
    <div className="min-h-screen bg-canvas">
      <div className="border-b border-line bg-surface sticky top-0 z-10 print:hidden">
        <div className="max-w-5xl mx-auto px-6 h-14 flex items-center">
          <h1 className="text-sm font-semibold text-ink">{title}</h1>
        </div>
      </div>
      <div className="max-w-5xl mx-auto px-6 py-8">
        <ComingSoon title={title} description={description} />
      </div>
    </div>
  );
}