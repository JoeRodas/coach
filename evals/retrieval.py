"""Retrieval benchmark — Recall@k and MRR for the Phase 1 sentence-transformer
retriever, and eventually for the Phase 2 encoder.

Relevance rule (per query):
- If the query carries explicit `relevant_game_ids`, those are the gold set.
- Otherwise, a retrieved hit is relevant iff its ECO equals the query's ECO
  AND its game_id differs from the query's `source_game_id` (same-game hits
  would be trivial self-matches and are excluded).

Metrics:
- Recall@10, Recall@20 — fraction of queries with ≥1 relevant hit in top-k.
- MRR@20 — mean reciprocal rank of the first relevant hit; 0 if none in top-20.
- Random baseline — for sanity, report the expected Recall@k under uniform
  random retrieval given each query's relevance-pool size.

Usage:
    python -m evals.retrieval --k 20
    python -m evals.retrieval --queries evals/queries.jsonl --save-json
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from coach.config import load_settings
from coach.retrieval import Retriever, load_index

INDEX_PATH = Path("data/index.npz")
INDEX_CLEAN_PATH = Path("data/index_clean.npz")
ENCODER_INDEX_PATH = Path("data/index_encoder.npz")
ENCODER_CHECKPOINT = Path("data/checkpoints/encoder.pt")
QUERIES_PATH = Path("evals/queries.jsonl")
RESULTS_DIR = Path("evals/results")

SYSTEMS = (
    "phase1_sentence_transformer",
    "phase1_sentence_transformer_clean",
    "phase2_encoder",
)
RESULT_PREFIX = {
    "phase1_sentence_transformer": "baseline",
    "phase1_sentence_transformer_clean": "baseline-clean",
    "phase2_encoder": "phase2",
}


@dataclass
class QueryResult:
    query_id: str
    eco: str
    hits_ecos: list[str]
    hits_games: list[str]
    first_relevant_rank: int | None  # 1-based; None if no relevant in top-k
    relevance_pool_size: int


def _eco_of_context(ctx: str) -> str:
    parts = [p.strip() for p in ctx.split("|")]
    if len(parts) < 2:
        return ""
    return parts[1].split(" ", 1)[0]


def _scrub_eco_segment(ctx: str) -> str:
    """Drop the second pipe-segment (the `"{eco} {opening}"` slot)."""
    parts = [p.strip() for p in ctx.split("|")]
    if len(parts) < 4:
        return ctx
    return " | ".join([parts[0]] + parts[2:])


def _load_queries(path: Path) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def _build_eco_lookup() -> dict[str, str]:
    """game_id -> ECO map, sourced from the original (un-scrubbed) Phase 1 index.

    Needed by the clean-mode eval: the leak-scrubbed index has ECO removed
    from `position.context`, so relevance scoring can't recover it from there.
    """
    positions, _ = load_index(INDEX_PATH)
    return {p.game_id: _eco_of_context(p.context) for p in positions}


def _count_relevance_pool(query: dict, positions, eco_of) -> int:
    """How many indexed positions are relevant under the automatic rule."""
    if query["relevant_game_ids"]:
        gids = set(query["relevant_game_ids"])
        return sum(1 for p in positions if p.game_id in gids)
    eco = query["eco"]
    src_game = query["source_game_id"]
    return sum(
        1 for p in positions if eco_of(p) == eco and p.game_id != src_game
    )


def _is_relevant(query: dict, hit, eco_of) -> bool:
    if query["relevant_game_ids"]:
        return hit.position.game_id in set(query["relevant_game_ids"])
    return (
        eco_of(hit.position) == query["eco"]
        and hit.position.game_id != query["source_game_id"]
    )


def _build_retriever(system: str):
    """Returns (retriever, query_text_fn, eco_of_position_fn)."""
    eco_of_ctx = lambda p: _eco_of_context(p.context)
    if system == "phase1_sentence_transformer":
        settings = load_settings()
        r = Retriever(model_name=settings.embedding_model, index_path=INDEX_PATH)
        return r, lambda q: q["query_context"], eco_of_ctx
    if system == "phase1_sentence_transformer_clean":
        settings = load_settings()
        r = Retriever(model_name=settings.embedding_model, index_path=INDEX_CLEAN_PATH)
        # Clean index has ECO scrubbed from contexts, so look it up by game_id
        # against the original index instead.
        eco_lookup = _build_eco_lookup()
        return (
            r,
            lambda q: _scrub_eco_segment(q["query_context"]),
            lambda p: eco_lookup.get(p.game_id, ""),
        )
    if system == "phase2_encoder":
        # Imported lazily so the Phase 1 path doesn't pay the torch import cost.
        from training.retriever import EncoderRetriever
        r = EncoderRetriever(
            checkpoint_path=ENCODER_CHECKPOINT, index_path=ENCODER_INDEX_PATH,
        )
        return r, lambda q: q["fen"], eco_of_ctx
    raise ValueError(f"unknown system: {system}")


def run(k: int, queries_path: Path, save_json: bool, system: str) -> dict:
    retriever, query_fn, eco_of = _build_retriever(system)
    queries = _load_queries(queries_path)
    n_total = len(retriever.positions)

    results: list[QueryResult] = []
    rand_recall_at_k = 0.0
    for q in queries:
        pool = _count_relevance_pool(q, retriever.positions, eco_of)
        hits = retriever.search(query_fn(q), k=k)
        first_rank: int | None = None
        for rank, hit in enumerate(hits, start=1):
            if _is_relevant(q, hit, eco_of):
                first_rank = rank
                break
        results.append(QueryResult(
            query_id=q["query_id"],
            eco=q["eco"],
            hits_ecos=[eco_of(h.position) for h in hits],
            hits_games=[h.position.game_id for h in hits],
            first_relevant_rank=first_rank,
            relevance_pool_size=pool,
        ))
        # random baseline: P(≥1 relevant in k draws w/o replacement)
        # 1 - C(n-pool, k)/C(n, k), approximated via product to avoid big ints
        if pool > 0 and n_total > k:
            p_none = 1.0
            for i in range(k):
                p_none *= max(0.0, (n_total - pool - i) / (n_total - i))
            rand_recall_at_k += 1.0 - p_none

    recall_k = sum(1 for r in results if r.first_relevant_rank is not None) / max(1, len(results))
    recall_10 = sum(
        1 for r in results if r.first_relevant_rank is not None and r.first_relevant_rank <= 10
    ) / max(1, len(results))
    mrr = sum(
        (1.0 / r.first_relevant_rank) if r.first_relevant_rank else 0.0 for r in results
    ) / max(1, len(results))
    rand_recall_k = rand_recall_at_k / max(1, len(results))

    # per-ECO breakdown
    by_eco: dict[str, list[QueryResult]] = defaultdict(list)
    for r in results:
        by_eco[r.eco].append(r)
    eco_rows = []
    for eco, rs in sorted(by_eco.items()):
        hit_rate = sum(1 for r in rs if r.first_relevant_rank is not None) / len(rs)
        eco_rows.append((eco, len(rs), hit_rate))

    report = {
        "date": date.today().isoformat(),
        "system": system,
        "k": k,
        "n_queries": len(results),
        "n_indexed": n_total,
        f"recall@{k}": round(recall_k, 4),
        "recall@10": round(recall_10, 4),
        f"mrr@{k}": round(mrr, 4),
        f"random_recall@{k}": round(rand_recall_k, 4),
    }

    print()
    print(f"=== Retrieval benchmark ({report['system']}) ===")
    print(f"queries: {report['n_queries']}  index: {report['n_indexed']}  k: {k}")
    print(f"Recall@{k}:      {report[f'recall@{k}']:.3f}   (random: {report[f'random_recall@{k}']:.3f})")
    print(f"Recall@10:      {report['recall@10']:.3f}")
    print(f"MRR@{k}:         {report[f'mrr@{k}']:.3f}")
    print()
    print("per-ECO hit-rate (top 12 by query count):")
    for eco, n, rate in sorted(eco_rows, key=lambda r: -r[1])[:12]:
        print(f"  {eco}  n={n:<2}  hit-rate={rate:.2f}")

    if save_json:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        out = RESULTS_DIR / f"{RESULT_PREFIX[system]}-{date.today().isoformat()}.json"
        with open(out, "w") as f:
            json.dump({
                "summary": report,
                "per_query": [
                    {
                        "query_id": r.query_id,
                        "eco": r.eco,
                        "first_relevant_rank": r.first_relevant_rank,
                        "relevance_pool_size": r.relevance_pool_size,
                        "top_ecos": r.hits_ecos[:10],
                    }
                    for r in results
                ],
            }, f, indent=2)
        print(f"\nsaved -> {out}")

    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--k", type=int, default=20)
    p.add_argument("--queries", type=Path, default=QUERIES_PATH)
    p.add_argument("--save-json", action="store_true")
    p.add_argument("--system", choices=SYSTEMS, default=SYSTEMS[0])
    args = p.parse_args()
    run(k=args.k, queries_path=args.queries, save_json=args.save_json, system=args.system)


if __name__ == "__main__":
    main()
