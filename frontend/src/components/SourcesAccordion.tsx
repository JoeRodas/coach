// Expandable list of master games the analysis is grounded in. Default
// collapsed so the analysis text reads first; expanded via the native
// <details> element for free keyboard support and aria-expanded handling.

import type { RetrievedGame } from "../types/api";

interface Props {
  sources: RetrievedGame[];
}

export default function SourcesAccordion({ sources }: Props) {
  if (sources.length === 0) return null;

  return (
    <details className="rounded-lg border border-slate-200 bg-white">
      <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-slate-700 hover:bg-slate-50">
        Sources ({sources.length} master {sources.length === 1 ? "game" : "games"})
      </summary>
      <ul className="divide-y divide-slate-100 border-t border-slate-200">
        {sources.map((s) => (
          <li key={s.gameId} className="px-4 py-3">
            <div className="flex items-baseline justify-between gap-3">
              <p className="font-mono text-sm text-slate-700">{s.gameId}</p>
              <span className="font-mono text-xs text-slate-500">
                similarity {(s.similarity * 100).toFixed(0)}%
              </span>
            </div>
            <p className="mt-1 text-sm text-slate-600">{s.excerpt}</p>
            {s.themes.length > 0 ? (
              <ul className="mt-2 flex flex-wrap gap-1">
                {s.themes.map((t) => (
                  <li
                    key={t}
                    className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700"
                  >
                    {t}
                  </li>
                ))}
              </ul>
            ) : null}
            {s.sourceUrl ? (
              <a
                href={s.sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-2 inline-block text-sm text-indigo-700 underline hover:text-indigo-900"
              >
                View game ↗
              </a>
            ) : null}
          </li>
        ))}
      </ul>
    </details>
  );
}
