// Renders a successful AnalysisResponse: three grounded paragraphs, the
// expandable Sources accordion, the eval-drop list, and (if present) the
// weakness pattern. aria-live="polite" so screen readers announce when
// new analysis lands.

import type { AnalysisResponse } from "../types/api";
import EvalDropList from "./EvalDropList";
import SourcesAccordion from "./SourcesAccordion";

interface Props {
  data: AnalysisResponse;
}

export default function AnalysisView({ data }: Props) {
  const paragraphs = data.analysis.split(/\n\n+/).filter((p) => p.trim().length > 0);

  return (
    <article aria-live="polite" aria-atomic="false" className="space-y-6">
      <section aria-labelledby="commentary-heading" className="space-y-3">
        <h2 id="commentary-heading" className="text-lg font-semibold tracking-tight">
          Commentary
        </h2>
        <div className="space-y-3 text-slate-800">
          {paragraphs.map((p) => (
            <p key={p.slice(0, 32)}>{p}</p>
          ))}
        </div>
      </section>

      {data.weakness ? (
        <section
          aria-labelledby="weakness-heading"
          className="rounded-lg border border-indigo-200 bg-indigo-50 p-4 text-indigo-900"
        >
          <h2 id="weakness-heading" className="text-sm font-semibold uppercase tracking-wide">
            Pattern of mistakes
          </h2>
          <p className="mt-1 font-medium">{data.weakness.theme}</p>
          <p className="mt-1 text-sm">{data.weakness.rationale}</p>
          <p className="mt-1 text-xs opacity-70">
            confidence {(data.weakness.confidence * 100).toFixed(0)}%
          </p>
        </section>
      ) : null}

      <section aria-labelledby="drops-heading" className="space-y-3">
        <h2 id="drops-heading" className="text-lg font-semibold tracking-tight">
          Critical moments
        </h2>
        <EvalDropList drops={data.evalDrops} />
      </section>

      <section aria-labelledby="sources-heading" className="space-y-3">
        <h2 id="sources-heading" className="text-lg font-semibold tracking-tight">
          Grounded in
        </h2>
        <SourcesAccordion sources={data.sources} />
      </section>

      <footer className="text-xs text-slate-500">
        Model {data.modelVersion} · {data.latencyMs} ms
      </footer>
    </article>
  );
}
