"""Generate a seed retrieval-benchmark query set from the current Phase 1 index.

This is a *bootstrap* set. Ground-truth relevance is automatic: a retrieved
position is relevant if it shares the query's ECO code and is from a different
game. That is a proxy — same opening doesn't guarantee same idea — but it is
stable, deterministic, and sufficient to establish a Phase 1 baseline that the
Phase 2 encoder can be compared against.

To add hand-annotated queries later, append lines to `evals/queries.jsonl`
with explicit `relevant_game_ids` — the benchmark will use those if present
and fall back to ECO-matching otherwise.

Query anonymization: each query synthesizes a fresh context string with
placeholder player names. This keeps the retrieval task about structural
features (ECO, opening, FEN tokens) rather than player-name token overlap.

Usage:
    python -m evals.generate_queries --per-eco 2 --min-games 3 --seed 17
"""
from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

from coach.retrieval import load_index

INDEX_PATH = Path("data/index.npz")
OUT_PATH = Path("evals/queries.jsonl")


def _parse_context(ctx: str) -> dict[str, str]:
    """Pull ECO and opening back out of the indexed context string."""
    parts = [p.strip() for p in ctx.split("|")]
    if len(parts) < 4:
        return {"eco": "", "opening": "", "move_phase": "", "fen": ""}
    eco_opening = parts[1].split(" ", 1)
    eco = eco_opening[0] if eco_opening else ""
    opening = eco_opening[1] if len(eco_opening) > 1 else ""
    return {"eco": eco, "opening": opening, "move_phase": parts[2], "fen": parts[3]}


def _anonymized_context(info: dict[str, str]) -> str:
    """Rebuild a context string with placeholder player names."""
    return (
        f"QueryPlayerA vs QueryPlayerB | {info['eco']} {info['opening']} | "
        f"{info['move_phase']} | {info['fen']}"
    )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--per-eco", type=int, default=2, help="queries per eligible ECO")
    p.add_argument("--min-games", type=int, default=3,
                   help="ECO needs at least this many distinct games to qualify")
    p.add_argument("--min-positions", type=int, default=10,
                   help="ECO needs at least this many indexed positions")
    p.add_argument("--seed", type=int, default=17)
    p.add_argument("--out", type=Path, default=OUT_PATH)
    args = p.parse_args()

    rng = random.Random(args.seed)
    positions, _ = load_index(INDEX_PATH)

    by_eco: dict[str, list[int]] = defaultdict(list)
    for i, pos in enumerate(positions):
        info = _parse_context(pos.context)
        eco = info["eco"]
        if eco:
            by_eco[eco].append(i)

    queries = []
    for eco, idxs in sorted(by_eco.items()):
        if len(idxs) < args.min_positions:
            continue
        games = {positions[i].game_id for i in idxs}
        if len(games) < args.min_games:
            continue
        picks = rng.sample(idxs, k=min(args.per_eco, len(idxs)))
        for pick in picks:
            pos = positions[pick]
            info = _parse_context(pos.context)
            # relevance pool: same ECO, *different* game (avoid trivial self-hit)
            qid = f"{eco}-{pos.game_id[:8]}-{pos.ply}"
            queries.append({
                "query_id": qid,
                "fen": pos.fen,
                "query_context": _anonymized_context(info),
                "source_game_id": pos.game_id,
                "eco": eco,
                "opening": info["opening"],
                "ply": pos.ply,
                # empty relevant_game_ids → use ECO-match fallback in benchmark
                "relevant_game_ids": [],
            })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        for q in queries:
            f.write(json.dumps(q) + "\n")

    print(f"wrote {len(queries)} queries covering {len({q['eco'] for q in queries})} ECOs "
          f"-> {args.out}")


if __name__ == "__main__":
    main()
