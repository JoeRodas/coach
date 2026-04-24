# Phase 2 — Custom embeddings, batch pipeline, pgvector

**Goal.** Replace Phase 1's sentence-transformer retrieval (text over FEN + headers)
with a **trained position encoder** that beats it on a held-out retrieval
benchmark. Prove it with numbers in the Phase 2 writeup — recall@10, MRR before
vs after.

## Critical path

1. **Training data pipeline** (`pipelines/ingest.py`) — downloads a month of
   Lichess Elite Database games (2400+ rated), filters by ELO, subsamples
   plies, Stockfish-labels, writes Parquet shards of
   `(fen, score_cp, game_id, ply, white_elo, black_elo, side_to_move)`.
2. **Retrieval benchmark** (`evals/retrieval.py`) — 500 hand/curated annotated
   positions. Metrics: recall@10, MRR. Measured *first* against the current
   sentence-transformer baseline, before the new encoder exists. This gates
   whether the new model is actually better.
3. **Position encoder** (`training/encoder.py`) — small transformer over
   8×8×12 board tensor, ~1–2 M params. Trained with SimCLR-style InfoNCE
   contrastive loss. Positive pairs: adjacent plies from the same game, OR
   positions with near-identical Stockfish eval AND same piece count.
4. **Swap retrieval backend** — replace `coach.retrieval.Retriever`
   (sentence-transformer + cosine over `.npz`) with new encoder + pgvector.
   Keep `coach.agent` untouched — same `search(fen, k) -> [SearchHit]` API.
5. **pgvector in prod** — Fly.io Postgres add-on, `vector(128)` column, HNSW
   index. Dev: Postgres-in-Docker.

## Parallel (not blocking the writeup)

- **Weakness classifier** — logistic regression on hand-crafted features
  (centipawn loss by phase, opening ECO bins, piece-activity deltas). Label
  derived from Stockfish pattern across the game. Ship as
  `get_weakness_profile(user_id)` tool; agent can call it when user asks
  "what should I study." Gated on having ≥N user games.

## Out of scope (Phase 3)

- BERT weakness classifier
- XGBoost puzzle ranker
- Full annotated eval harness (500 positions with ground-truth alt moves)

## Decisions

| Choice | Picked | Why not alternatives |
|---|---|---|
| Orchestrator | **Apache Airflow** | On Slack's JD by name. Prefect/Dagster nicer DX but weaker resume signal. |
| Dataset source | **Lichess Elite DB** (nikonoel) | Full Lichess dump is ~200 GB/month; Elite is pre-filtered to 2400+, ~1–5 GB/month. Enough positions, saner scale. |
| Storage format | **Parquet** (local FS dev, S3 later) | Columnar, typed, stable, readable by pandas + pyarrow + Spark. |
| Training framework | **Raw PyTorch** (no Lightning) | Smaller surface area, easier to deploy, fewer moving parts for a 1–2 M param model. |
| Encoder arch | **4-layer transformer, 128 hidden, 4 heads** | Small enough for CPU inference in the web app; big enough to learn positional structure. |
| Positive pairs | **Adjacent plies + eval-matched positions** | Adjacent plies give positional continuity; eval-matched gives tactical similarity across games. Both needed. |
| Loss | **InfoNCE with in-batch negatives** | Simple, strong baseline. Temperature τ=0.1 to start. |
| Vector DB | **pgvector** | Already in Fly's ecosystem, HNSW index is production-grade, stays with Postgres so we don't add a new dependency class. |
| Eval set | **500 positions**, ~100 hand-annotated by Joe + 400 from public annotation sets | Matches the Phase 3 spec; built once, reused. |

## Scale guardrails (so the laptop doesn't melt)

First-pass ingestion defaults:
- **5,000 games** × ~15 positions-per-game kept = ~75k training positions
- **Stockfish depth 8** (not 15) — ~0.2 s/position, ~4 hours single-threaded or ~30 min on 8 cores
- Scale to 1 M positions *after* the encoder beats baseline on the benchmark

## Next-session entry points

- `python -m pipelines.ingest --month 2026-02 --max-games 5000 --depth 8` —
  produces `data/training/shard-*.parquet` ready for the encoder.
- Before running: stand up the **retrieval benchmark baseline** in parallel
  (annotate ~100 positions, measure current recall@10 against the 8,847-position
  Phase 1 index). Without the baseline, "the encoder beats sentence-transformers"
  is an unverifiable claim.

## Benchmark correction (2026-04-24)

The first Phase 1 baseline (recall@20=0.688) was inflated by an **ECO leak**:
`format_context()` in `src/coach/retrieval.py` embeds `"{eco} {opening}"` (e.g.
`"A01 Nimzo-Larsen Attack"`) literally into both the indexed docs and the
query string, and the benchmark's automatic relevance rule is *same ECO*. The
sentence-transformer was partly string-matching the ground truth.

Fix: `scripts/build_clean_index.py` re-embeds the index with that segment
stripped; `evals/retrieval.py --system phase1_sentence_transformer_clean` also
scrubs the query and uses a `game_id → ECO` lookup from the original index
for relevance scoring. Numbers head-to-head on the same 80 queries, k=20:

| system | recall@20 | recall@10 | mrr@20 |
|---|---|---|---|
| Phase 1 leaky | 0.688 | 0.613 | 0.477 |
| Phase 1 clean | 0.050 | 0.013 | 0.004 |
| Phase 2 encoder (2 / 5 epochs) | 0.287 | 0.188 | 0.128 |
| random baseline | 0.222 | — | — |

Takeaway: sentence-transformers over FEN-as-text are at or below random on
this task. The encoder gate is **met**, even under-trained — but the story for
the writeup is "fair baseline barely clears random, encoder outperforms by
~6×," not "encoder beats a strong text baseline." Saved results:
`evals/results/baseline-2026-04-23.json` (leaky),
`baseline-clean-2026-04-24.json`, `phase2-2026-04-24.json`.
