// Move-by-move list of engine-eval drops, color-coded by severity. A chart
// is the obvious upgrade later (per spec §6.1) but a list is informative,
// accessible, and ships with zero new dependencies.

import type { EvalDrop } from "../types/api";

const SEVERITY_STYLE: Record<EvalDrop["severity"], string> = {
  minor: "bg-yellow-50 border-yellow-200 text-yellow-900",
  major: "bg-orange-50 border-orange-200 text-orange-900",
  blunder: "bg-red-50 border-red-200 text-red-900",
};

const SEVERITY_LABEL: Record<EvalDrop["severity"], string> = {
  minor: "Minor",
  major: "Major",
  blunder: "Blunder",
};

function formatEval(cp: number): string {
  if (Math.abs(cp) >= 10000) return cp > 0 ? "+M" : "-M";
  const sign = cp > 0 ? "+" : "";
  return `${sign}${(cp / 100).toFixed(2)}`;
}

interface Props {
  drops: EvalDrop[];
}

export default function EvalDropList({ drops }: Props) {
  if (drops.length === 0) {
    return <p className="text-sm text-slate-500">No significant eval drops detected.</p>;
  }

  return (
    <ul className="space-y-2">
      {drops.map((d) => (
        <li
          key={`${d.ply}-${d.san}`}
          className={`flex items-baseline gap-3 rounded-md border px-3 py-2 text-sm ${SEVERITY_STYLE[d.severity]}`}
        >
          <span className="w-12 font-mono text-xs uppercase tracking-wide opacity-70">
            {SEVERITY_LABEL[d.severity]}
          </span>
          <span className="font-mono">
            {Math.floor(d.ply / 2) + 1}
            {d.ply % 2 === 0 ? "." : "..."} {d.san}
          </span>
          <span className="ml-auto font-mono opacity-80">
            {formatEval(d.evalBefore)} → {formatEval(d.evalAfter)}
          </span>
        </li>
      ))}
    </ul>
  );
}
