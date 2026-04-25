// Shown before the user has run any analysis. Distinct from "loading" and
// "error" so the page never feels half-blank.

export default function EmptyState() {
  return (
    <div className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center text-slate-500">
      <p>Paste a PGN above and click Analyze to see grounded commentary.</p>
      <p className="mt-1 text-sm">
        Or click <em>Try a sample game</em> for a famous tactical masterclass.
      </p>
    </div>
  );
}
