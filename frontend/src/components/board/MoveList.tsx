// Two-column SAN move list. Renders pairs of (white, black) moves with
// move numbers. Pure presentational; no interaction yet (PR-7 will add
// click-to-jump for review).

interface Props {
  history: string[];
}

export default function MoveList({ history }: Props) {
  if (history.length === 0) {
    return <p className="text-sm text-slate-500">No moves yet.</p>;
  }

  // Group into [whiteMove, blackMove?] pairs.
  const pairs: Array<[string, string | undefined]> = [];
  for (let i = 0; i < history.length; i += 2) {
    pairs.push([history[i] as string, history[i + 1]]);
  }

  return (
    <ol className="space-y-1 text-sm">
      {pairs.map((pair, i) => (
        <li
          key={`${i}-${pair[0]}-${pair[1] ?? ""}`}
          className="grid grid-cols-[2rem_1fr_1fr] gap-2 font-mono"
        >
          <span className="text-slate-400">{i + 1}.</span>
          <span>{pair[0]}</span>
          <span>{pair[1] ?? ""}</span>
        </li>
      ))}
    </ol>
  );
}
