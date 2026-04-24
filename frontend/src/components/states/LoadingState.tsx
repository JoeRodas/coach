// Distinct loading state — not a generic spinner. Tells the user what the
// system is doing right now (engine eval first, then retrieval, then
// generation), even though under the hood it's a single round-trip.

export default function LoadingState() {
  return (
    <output aria-live="polite" className="block rounded-lg border border-slate-200 bg-white p-6">
      <div className="flex items-center gap-3">
        <span aria-hidden="true" className="h-3 w-3 animate-pulse rounded-full bg-indigo-500" />
        <p className="text-slate-700">
          Analyzing the game — checking critical moments and retrieving similar master positions…
        </p>
      </div>
    </output>
  );
}
