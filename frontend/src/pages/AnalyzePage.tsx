// Real analyze flow. Composes PgnInput, the three state components, and
// AnalysisView via the useAnalyze hook. Mutation state drives which of
// EmptyState / LoadingState / ErrorState / AnalysisView renders below
// the form.

import { isMockApi } from "../api";
import AnalysisView from "../components/AnalysisView";
import PgnInput from "../components/PgnInput";
import EmptyState from "../components/states/EmptyState";
import ErrorState from "../components/states/ErrorState";
import LoadingState from "../components/states/LoadingState";
import { useAnalyze } from "../hooks/useAnalyze";

export default function AnalyzePage() {
  const analyze = useAnalyze();

  return (
    <section aria-labelledby="analyze-heading" className="space-y-6">
      <header className="space-y-1">
        <h1 id="analyze-heading" className="text-2xl font-semibold tracking-tight">
          Analyze a game
        </h1>
        <p className="text-slate-600">
          Paste a PGN, pick the color you played, and Coach returns grounded commentary citing
          similar master positions.
        </p>
        {isMockApi ? (
          <p className="rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-900">
            Staging deploy: responses come from a local mock until the new backend ships.
          </p>
        ) : null}
      </header>

      <PgnInput onSubmit={(req) => analyze.mutate(req)} isSubmitting={analyze.isPending} />

      <div>
        {analyze.isPending ? (
          <LoadingState />
        ) : analyze.isError ? (
          <ErrorState message={analyze.error.message} onRetry={() => analyze.reset()} />
        ) : analyze.data ? (
          <AnalysisView data={analyze.data} />
        ) : (
          <EmptyState />
        )}
      </div>
    </section>
  );
}
