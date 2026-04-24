// Scaffold stub — real metrics content (top-K precision card, p95 latency
// time-series, model version, admin-secret gating) lands alongside the
// §6.7 backend endpoint in a later PR.

export default function MetricsPage() {
  return (
    <section aria-labelledby="metrics-heading" className="space-y-4">
      <h1 id="metrics-heading" className="text-2xl font-semibold tracking-tight">
        Admin · Metrics
      </h1>
      <p className="text-slate-600">
        Real metrics content lands when the backend <code>/api/admin/metrics</code> endpoint is
        implemented alongside the retrieval eval harness.
      </p>
    </section>
  );
}
