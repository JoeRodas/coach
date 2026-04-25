# Coach — Requirements (Phase 2 handoff for Claude Code)

**Product:** Coach, a conversational chess coach.
**Live URL:** https://chesscoach.nuezmiami.com
**Owner:** Joseph Rodas (Nuez IA)
**Status as of this document:** Phase 1 shipped. Phase 2 is the scope of work below.

---

## How to use this document

This is a handoff spec for Claude Code. Read it end-to-end before writing any code. Then:

1. Run `ls` at the repo root and read `CLAUDE.md` if one exists. If not, create one that summarizes this document.
2. Read the actual Phase 1 codebase before proposing changes. Do not assume file layout from this doc — verify it.
3. Work phase by phase, component by component, in the order listed in §5. Do not jump ahead.
4. Open a PR per component. Each PR must pass its acceptance criteria in §7 before moving on.
5. When ambiguous, ask rather than guess. Over-scoping Phase 2 into Phase 3 work is the single biggest failure mode for this project.

---

## 1. What Coach is

A user pastes a single PGN game and optionally a question (e.g. "where did I go wrong"). Coach returns a grounded, three-paragraph analysis that identifies the largest engine-evaluation drops, retrieves thematically similar positions from a master-game corpus, and explains what the user missed in natural language.

The differentiator vs. plain Stockfish analysis is **grounding**: every explanation cites specific positions from master games that exhibit the same theme, rather than generating from the LLM's parametric memory alone.

The differentiator vs. chess.com's Game Review is **interpretability + retrieval transparency**: users can see which master games informed each point of the analysis.

---

## 2. Current state (Phase 1 — already shipped, do not rebuild)

Externally visible:

- Landing page at https://chesscoach.nuezmiami.com with a PGN textarea, a color selector (White / Black), an optional question field, and an "Analyze" button.
- "Try a sample game" seeds the textarea with a pre-loaded game.
- Deployment: Fly.io.

Internally (verify before editing):

- FastAPI backend serving the analysis endpoint.
- Stockfish for per-move engine evaluation.
- Off-the-shelf sentence-transformer embeddings over a hand-curated corpus of ~500 master games indexed as PGN text chunks.
- Claude API for generation, conditioned on the retrieved corpus snippets and the engine-evaluation drops.
- A simple vanilla HTML/JS frontend (not React).

Phase 2 keeps the Phase 1 user-facing flow intact. Every change below should be backward-compatible with the existing `/analyze`-style endpoint. Do not break the live site while rebuilding around it.

---

## 3. Phase 2 goals

Phase 2 converts Coach from "impressive solo project" into "credible end-to-end ML system." The four goals, in priority order:

1. **Rebuild the frontend in React + TypeScript** with an admin metrics page.
2. **Replace off-the-shelf embeddings with a custom PyTorch position-embedding model** trained with contrastive learning.
3. **Stand up an Airflow ingestion pipeline** over Lichess open data with pgvector as the storage layer.
4. **Ship a retrieval evaluation harness** that produces measurable numbers on every change, plus a simple logistic-regression weakness classifier.

Non-goals for Phase 2 (explicit):

- No BERT fine-tuning.
- No XGBoost ranker.
- No user accounts, saved games, or history.
- No mobile app.
- No realtime streaming of analysis.

These belong in Phase 3 and later. If a design decision in Phase 2 forecloses a Phase 3 option, flag it; otherwise defer.

---

## 4. Tech stack (authoritative)

| Layer | Choice | Why |
|---|---|---|
| Backend | FastAPI (Python 3.11+) | Already in use |
| Frontend | React 18 + TypeScript (Vite) | Resume-critical; also the right tool |
| Database | PostgreSQL 16 with `pgvector` extension | Already decided; production-grade vector search |
| ML framework | PyTorch 2.x | Already decided; training + inference |
| Pipeline | Apache Airflow | Already decided; industry-standard |
| Engine | Stockfish (existing) | Already in use |
| LLM | Anthropic Claude API via `anthropic` SDK | Already in use |
| Hosting | Fly.io (web) + managed Postgres | Existing |
| Package management | `uv` or `pip-tools` for Python; `pnpm` for JS | Pick one per language and stick with it |
| Tests | `pytest` for Python; `vitest` for TS | Standard |
| Lint/format | `ruff` + `black` for Python; `biome` for TS | Fast, one tool each |

Do not introduce new dependencies without a one-line justification in the PR description.

---

## 5. Repository layout (target)

```
coach/
├── CLAUDE.md                     # Your working instructions (create on first pass)
├── REQUIREMENTS.md               # This file
├── README.md                     # Public-facing; demo GIF + architecture diagram
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py               # FastAPI entrypoint
│   │   ├── api/                  # Route handlers
│   │   │   ├── analyze.py
│   │   │   ├── admin.py          # /admin/metrics — Phase 2 new
│   │   │   └── health.py
│   │   ├── services/
│   │   │   ├── engine.py         # Stockfish wrapper
│   │   │   ├── retrieval.py      # pgvector queries
│   │   │   ├── embeddings.py     # Custom PyTorch model inference
│   │   │   ├── classifier.py     # Weakness LR model
│   │   │   └── generator.py      # Claude API prompt + call
│   │   ├── db/
│   │   │   ├── session.py        # Async SQLAlchemy engine
│   │   │   ├── models.py         # ORM: Position, Game, Evaluation, EvalResult
│   │   │   └── init_db.py        # pgvector extension, indexes
│   │   └── schemas/              # Pydantic request/response models
│   └── tests/
├── ml/
│   ├── train_embeddings.py       # Contrastive training loop
│   ├── models/
│   │   └── position_encoder.py   # PyTorch nn.Module
│   ├── data/
│   │   ├── lichess_loader.py     # PGN → tensor pipeline
│   │   └── augmentations.py      # Board-symmetry augments
│   ├── eval/
│   │   ├── retrieval_harness.py  # top-K precision, latency, error rate
│   │   └── annotated_positions.json  # Held-out set, hand-labeled themes
│   └── checkpoints/              # Gitignored; artifacts live in S3/Fly volume
├── pipeline/
│   ├── dags/
│   │   └── lichess_ingest.py     # Airflow DAG
│   └── tasks/
│       ├── fetch.py              # Download one month of Lichess games
│       ├── parse.py              # PGN → positions
│       ├── embed.py              # Call embedding service
│       └── upsert.py             # Write to pgvector
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── pages/
│       │   ├── AnalyzePage.tsx   # PGN input + analysis output
│       │   └── MetricsPage.tsx   # /admin/metrics dashboard
│       ├── components/
│       │   ├── PgnInput.tsx
│       │   ├── AnalysisView.tsx
│       │   └── MetricsChart.tsx
│       ├── api/client.ts         # Typed fetch wrapper
│       └── types/api.ts          # Shared types (see §8)
├── infra/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── fly.toml
│   └── migrations/               # Alembic or raw SQL
└── scripts/
    ├── seed_annotated_positions.py
    └── bootstrap_dev.sh
```

If the existing Phase 1 layout diverges from this, migrate incrementally. Do not do a big-bang restructure; Coach is live and users are hitting it.

---

## 6. Detailed requirements

### 6.1 Frontend rebuild (React + TypeScript)

**Why first:** the live site currently has a plain HTML form. Rebuilding the frontend first means every subsequent backend change can be validated end-to-end in the new UI as you go.

**Requirements:**

- Vite + React 18 + TypeScript + `@tanstack/react-query` for server state.
- Tailwind CSS for styling. No design-system library.
- Single-page app with two routes:
  - `/` — the analyze flow (parity with Phase 1).
  - `/admin/metrics` — the metrics dashboard (§6.7).
- All API calls go through a typed client in `src/api/client.ts`. No untyped `fetch` anywhere.
- Shared types (`AnalysisRequest`, `AnalysisResponse`, `MetricsSnapshot`, etc.) live in `src/types/api.ts` and are kept in sync with the backend Pydantic schemas by convention — if schemas drift, tests fail.
- PGN textarea validates client-side: non-empty, passes a minimal PGN regex. Server still does real validation.
- Loading state, error state, and empty state each have a distinct UI. No generic spinner over the whole page.
- Analysis output renders the three grounded paragraphs, an expandable "Sources" section showing which master games were retrieved (with Lichess links if applicable), and the engine-eval drop highlights as a small chart or annotated move list.
- Accessibility: every interactive element reachable by keyboard, `aria-live` on the analysis-result region.

**Acceptance:**

- `pnpm build` produces a static bundle deployable behind the FastAPI app (or served on its own Fly.io app — your call, document the choice in `CLAUDE.md`).
- All routes render with no console errors.
- The analyze flow is functionally identical to Phase 1 from a user's perspective.
- Lighthouse score ≥ 90 on performance and accessibility.

### 6.2 Custom PyTorch position-embedding model

**Goal:** learn a 256-dimensional embedding where chess positions with similar strategic themes (isolated queen's pawn, opposite-side castling attack, minority attack, etc.) cluster together.

**Requirements:**

- Architecture: start with the simplest thing that could work. A CNN over the 8×8×N-piece-plane tensor (N = 12 piece types + side-to-move + castling + en-passant planes). One or two conv blocks, a projection head, L2-normalized output.
- Training objective: contrastive (InfoNCE / NT-Xent). Positive pairs = positions from the same game within ±3 plies and with similar evaluation. Negative pairs = positions from different games sampled from the batch.
- Training data: 1M positions drawn from Lichess open database (master + 2000+ ELO subset is fine for Phase 2). Sample positions from games, not PGN text chunks.
- Augmentations: horizontal board mirror (a8–h1 reflection) when legal, and (carefully) color-swap. Document augmentation choices; some destroy strategic meaning and should not be used.
- Training loop in `ml/train_embeddings.py`: deterministic seeds, W&B logging optional, checkpoint every N steps, resume-from-checkpoint support.
- Inference: a single `embed_position(fen: str) -> np.ndarray[256]` function in `backend/app/services/embeddings.py`, CPU-friendly, latency budget 20 ms per position on a modest Fly.io machine.

**Acceptance:**

- Custom model beats the Phase 1 sentence-transformer baseline on the held-out annotated set (§6.5) by at least 5 percentage points on top-5 retrieval precision. If it doesn't, something is wrong — debug before shipping.
- Model checkpoint and a short `MODEL_CARD.md` describing training data, objective, and known limitations are committed (checkpoint via LFS or external storage, not in-repo).

### 6.3 Airflow ingestion pipeline

**Goal:** reproducibly ingest one month of Lichess open data, parse to positions, embed, and upsert into pgvector.

**Requirements:**

- Single DAG: `lichess_ingest` in `pipeline/dags/lichess_ingest.py`.
- Tasks: `fetch_pgn_archive` → `parse_to_positions` → `filter_by_rating` → `embed_positions` → `upsert_pgvector`.
- Idempotent: re-running the DAG on the same month must not double-insert positions. Use a natural key (e.g. hash of FEN + move-number + game-id).
- Failure handling: each task retries 3× with exponential backoff. Failed runs leave a clear log trail.
- Configurable: target month, rating floor, sample rate all come from DAG params, not hardcoded.
- Local dev path: a `make ingest-sample` target that runs the pipeline on 1,000 games for smoke testing without spinning up Airflow.

**Acceptance:**

- Ingesting one month (≈ 10M positions, subsampled to 100K for Phase 2) completes successfully end-to-end on a Fly.io worker.
- After ingestion, a `SELECT count(*)` on the positions table matches expectation within 1%.
- The pgvector IVFFlat (or HNSW) index is built and `EXPLAIN ANALYZE` on a retrieval query uses the index.

### 6.4 pgvector migration

**Goal:** move from whatever Phase 1 uses for retrieval storage to Postgres + pgvector as the single source of truth.

**Requirements:**

- Alembic migrations under `infra/migrations/`.
- Tables:
  - `games` (id, pgn, source, rating_white, rating_black, event_date)
  - `positions` (id, game_id, ply, fen, san_move, eval_cp, eval_mate, embedding vector(256))
  - `themes` (id, name, description) — seeded with ~20 canonical strategic themes
  - `position_themes` (position_id, theme_id, source) — human-labeled for the eval set, model-labeled otherwise
- Index: `CREATE INDEX ON positions USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);`
- Query pattern documented in `backend/app/services/retrieval.py`: given a query embedding, return top-K with game context.

**Acceptance:**

- Migration runs cleanly on a fresh database.
- Query latency for top-10 retrieval at 100K positions is under 50 ms p95 on Fly.io managed Postgres.
- Rollback migration exists and works.

### 6.5 Retrieval evaluation harness

**Goal:** a standing evaluation that reports real numbers every time retrieval logic or the embedding model changes. Without this, Phase 2 is storytelling, not engineering.

**Requirements:**

- Held-out annotated set: 200–500 positions hand-labeled with 1–3 strategic themes each, stored in `ml/eval/annotated_positions.json`. Seed it yourself; 200 is enough for Phase 2. This is the single most important artifact in the project — take it seriously.
- Harness in `ml/eval/retrieval_harness.py`:
  - For each annotated position, generate the query embedding, retrieve top-K from pgvector, measure whether any retrieved position shares a theme with the query.
  - Report: top-1 precision, top-5 precision, top-10 precision, mean retrieval latency, p95 retrieval latency, error rate.
  - Output: a single JSON file (`eval_results_<timestamp>.json`) + a one-page HTML report with the numbers and a comparison-to-previous-run delta.
- CI hook: every PR that touches `backend/app/services/retrieval.py`, `backend/app/services/embeddings.py`, or `ml/` runs the harness and posts the numbers as a PR comment.

**Acceptance:**

- Running `python ml/eval/retrieval_harness.py` on main produces a result in under 60 seconds.
- The baseline number from Phase 1 embeddings is recorded as a checked-in file, so future runs can compare against it.

### 6.6 Weakness classifier

**Goal:** a very simple classifier that, given a sequence of positions from one user's game, predicts the user's weakest theme (e.g. "endgame technique," "opposite-side castling attacks").

**Requirements:**

- Logistic regression (scikit-learn) on hand-crafted features: engine-eval drop statistics, piece-activity deltas, king-safety proxies, time-per-move if available, plus the mean/max distance in embedding space between user positions and strong-player positions for each theme.
- Training set: synthetic for now — use Stockfish-vs-Stockfish games with varying skill levels as the label proxy. Acknowledged limitation.
- Integrated into `backend/app/services/classifier.py` with a `predict_weakness(positions: list[Position]) -> list[ThemePrediction]` function.
- Output is used to *focus* the generated explanation ("your biggest pattern of mistakes this game is X"), not to replace it.

**Acceptance:**

- End-to-end: a full game analysis response now includes a `"weakness": {...}` field.
- Model card + train script committed. Even though the training data is synthetic, document that clearly — do not oversell.

### 6.7 Admin metrics page

**Goal:** a `/admin/metrics` page that shows the live health of the retrieval system. This is a portfolio asset — it's what you'll screen-share in the interview.

**Requirements:**

- Backend endpoint `GET /admin/metrics` returns the latest eval-harness results plus rolling 24h production stats (request count, p50/p95 latency, error rate, embedding-model version).
- Frontend page `/admin/metrics` renders:
  - A "current vs baseline" comparison card for top-K precision
  - A time-series chart of p95 retrieval latency over the last 7 days
  - A version string showing which embedding model is live
- Authentication: simple shared-secret header (env-var-based) is fine for Phase 2. Real auth is Phase 3.

**Acceptance:**

- Page loads in under 2 seconds.
- Every metric shown has a tooltip explaining what it means. A recruiter looking at this should understand what they're seeing.

---

## 7. Phase 2 done definition

Phase 2 is "done" when all of the following are true:

- [ ] Live site at chesscoach.nuezmiami.com is served by the new React+TS frontend.
- [ ] Custom PyTorch embeddings are in production and beat the sentence-transformer baseline on the annotated set.
- [ ] Airflow DAG has run end-to-end on at least one month of Lichess data, and the positions table is populated.
- [ ] `/admin/metrics` loads with real numbers, gated behind a shared-secret header.
- [ ] Retrieval eval harness runs in CI and posts numbers on PRs.
- [ ] A `PHASE2.md` writeup exists in the repo summarizing what was built, what the numbers are, and what's genuinely surprising about the results.
- [ ] README has a 30-second demo GIF, an architecture diagram, and links to the writeup.
- [ ] The old Phase 1 frontend is removed (not just orphaned).

---

## 8. Shared API contract (frontend/backend)

Keep these types identical on both sides.

```typescript
// frontend/src/types/api.ts

export interface AnalysisRequest {
  pgn: string;
  playerColor: "white" | "black";
  question?: string;
}

export interface EvalDrop {
  ply: number;
  san: string;
  evalBefore: number;  // centipawns, + = white advantage
  evalAfter: number;
  severity: "minor" | "major" | "blunder";
}

export interface RetrievedGame {
  gameId: string;
  sourceUrl?: string;
  excerpt: string;   // short PGN snippet
  similarity: number; // cosine, 0..1
  themes: string[];
}

export interface WeaknessPrediction {
  theme: string;
  confidence: number; // 0..1
  rationale: string;
}

export interface AnalysisResponse {
  analysis: string;                // the three grounded paragraphs
  evalDrops: EvalDrop[];
  sources: RetrievedGame[];
  weakness: WeaknessPrediction | null;
  modelVersion: string;
  latencyMs: number;
}

export interface MetricsSnapshot {
  evalResults: {
    topKPrecision: Record<number, number>; // {1: 0.42, 5: 0.71, 10: 0.84}
    meanLatencyMs: number;
    p95LatencyMs: number;
    runAt: string; // ISO datetime
  };
  productionStats: {
    requestCount24h: number;
    p50LatencyMs: number;
    p95LatencyMs: number;
    errorRate24h: number;
  };
  modelVersion: string;
  baselineDelta: Record<number, number>; // top-K change vs baseline
}
```

Backend Pydantic schemas in `backend/app/schemas/` must produce JSON that parses cleanly into these types. A single snapshot test in CI verifies the contract.

---

## 9. Non-negotiables

- **Ship incrementally.** Each component in §6 is a standalone PR. Do not build the whole thing on a feature branch for three weeks and merge at the end.
- **Do not fabricate numbers.** Every claim in the README, the writeup, or future resume bullets must be reproducible from a committed script. If the eval harness says top-5 precision is 0.61, the writeup says 0.61.
- **Do not break the live site.** Users are hitting chesscoach.nuezmiami.com today. Feature-flag risky changes, deploy behind a staging URL first.
- **No secrets in the repo.** `.env.example` yes, `.env` no. Verify with `git-secrets` or similar before every push.
- **Document what you skipped.** If you cut a corner (synthetic training data for the classifier, small annotated set, IVFFlat instead of HNSW), write it down in `PHASE2.md`. Every interviewer will ask "what would you do differently" — the honest answer is the one that impresses.

---

## 10. Out of scope (Phase 3 and later — do not build yet)

- Fine-tuned distilBERT weakness classifier
- XGBoost puzzle ranker trained on Lichess implicit feedback
- User accounts, saved games, history
- Multi-game analysis (season / tournament mode)
- Mobile app
- Realtime streaming analysis
- Fair-play / cheating detection

Each of these has a clear home in Phase 3 or Phase 4. If a Phase 2 decision would prematurely close off one of these, flag it in the PR description and propose an alternative.

---

## 11. Getting started (first commands to run)

```bash
# Verify existing state
git status
git log --oneline -20
ls -la

# Inspect Phase 1
cat backend/requirements.txt 2>/dev/null || cat backend/pyproject.toml 2>/dev/null
find . -name "main.py" -not -path "*/node_modules/*" -not -path "*/.venv/*"

# Read the current frontend
ls frontend/ 2>/dev/null || ls static/ 2>/dev/null || ls public/ 2>/dev/null

# Then: create CLAUDE.md from this document's conventions, and propose a PR plan
```

Ask before restructuring. Propose a component order in writing before opening the first PR.
