# Coach — Requirements (Phase 2 handoff for Claude Code)

**Product:** Coach, a conversational chess coach.
**Live URL:** https://chesscoach.nuezmiami.com
**Owner:** Joseph Rodas (Nuez IA)
**Status as of this document:** Phase 1 shipped. Phase 2 is the scope of work below.

> **AMENDMENT D — 2026-04-24.** Coach has pivoted from "analysis tool" to
> "chess platform with grounded analysis as a feature." See **§D** at the
> bottom of this document for the new top-priority component (§6.0 chess
> client) and the section-by-section deltas to §1, §3, §6.1, §7, §8, §10.
> The original sections are preserved below for history; affected sections
> carry "[Amended in §D]" pointers. **Where original and amended text
> conflict, §D wins.**

---

## How to use this document

This is a handoff spec for Claude Code. Read it end-to-end before writing any code. Then:

1. Run `ls` at the repo root and read `CLAUDE.md` if one exists. If not, create one that summarizes this document.
2. Read the actual Phase 1 codebase before proposing changes. Do not assume file layout from this doc — verify it.
3. Work phase by phase, component by component, in the order listed in §5. Do not jump ahead.
4. Open a PR per component. Each PR must pass its acceptance criteria in §7 before moving on.
5. When ambiguous, ask rather than guess. Over-scoping Phase 2 into Phase 3 work is the single biggest failure mode for this project.

---

## 1. What Coach is *[Amended in §D — repositioned as a chess platform]*

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

## 3. Phase 2 goals *[Amended in §D — new top priority added (§6.0); existing four reordered as supporting work]*

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

### 6.1 Frontend rebuild (React + TypeScript) *[Amended in §D — analyze flow becomes "Review", reachable from end-of-game; new pages /play and /history added]*

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

## 7. Phase 2 done definition *[Amended in §D — chess client criteria added]*

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

## 8. Shared API contract (frontend/backend) *[Amended in §D — new endpoints for engine moves and game persistence]*

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

## 10. Out of scope (Phase 3 and later — do not build yet) *[Amended in §D — additions for the chess platform pivot]*

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

---

## D. Amendment — Chess platform pivot (2026-04-24)

> Where the original sections above conflict with this amendment, **§D wins.**
> Where they don't conflict, both apply.

### D.0 What changed and why

Coach pivots from "analysis tool" to "chess platform with grounded analysis as a feature." The user's primary action becomes **play a game vs the AI**. The existing analyze surface (PR-1, PR-2 already merged) becomes the post-game review.

**Why:** product call from the owner, made 2026-04-24 after evaluating the original positioning. Both products are coherent; this one ships a more obvious user motion ("play chess") and turns the retrieval-grounded analysis into a differentiator the user *experiences in context* rather than a standalone tool the user has to seek out.

**Cost acknowledged:** chess-platform MVP is 3–5 weeks of focused work, not days. Polished version (animations, sound, mobile, themes) another 2–4 weeks. The Phase 2 backend ML goals (embeddings §6.2, Airflow §6.3, eval harness §6.5, weakness classifier §6.6, admin metrics §6.7) all remain in scope; they're now framed as supporting work for the analysis feature inside the new product.

### D.1 New §1 (replaces original §1's framing)

Coach is a **chess platform where you play against an AI opponent**. After each game, Coach delivers a grounded, three-paragraph analysis of the game you just played, citing similar positions from a master-game corpus.

The differentiator vs. chess.com Play vs Computer / Lichess Stockfish opponent: every analysis insight Coach generates cites specific master games as evidence — not just engine output, not just LLM parametric memory.

The original "paste a PGN to analyze" surface remains (reachable from `/review`), so users can also feed in games played elsewhere.

### D.2 New §3 (replaces original priority order)

Phase 2 D goals, in priority order:

1. **Chess client (§6.0 below)** — the new top. Users can play complete games vs an AI opponent at adjustable strength.
2. **React+TS frontend (§6.1)** — already in flight; PR-1 and PR-2 merged; remaining PR-3 (metrics page) carries forward.
3. **Custom PyTorch embeddings (§6.2)** — supports analysis quality.
4. **Airflow ingestion (§6.3) + pgvector (§6.4)** — supports analysis quality.
5. **Retrieval eval harness + weakness classifier (§6.5, §6.6)** — supports analysis quality.
6. **Admin metrics page (§6.7)** — operations.

### D.3 Tech stack additions (extends original §4)

| Layer | Choice | Why |
|---|---|---|
| Chess rules engine | `chess.js` ^1.0 | De facto standard; pure JS; ~30 KB; battle-tested move validation, draw detection, FEN/PGN. |
| Chess board UI | `react-chessboard` ^4.x | Drag-and-drop chessboard React component, ~80 KB. Saves ~2 days vs writing a custom SVG board. |

### D.4 New §6.0 — Chess client (the new top-priority component)

#### Goal
A first-time visitor can start a game vs an AI opponent at a chosen skill level, play a complete game with drag-and-drop or click-to-move, and receive a Coach grounded review when the game ends — without reading any docs.

#### D.4.1 Board UI
- Drag-and-drop pieces; click-to-select-then-click-to-target as fallback.
- Legal-move dots/highlights when a piece is selected.
- Last-move highlight on both squares (from + to).
- Captured-pieces strip beside the board, sorted by piece value.
- Promotion picker UI when a pawn reaches the last rank.
- Board orientation flips so the user's pieces are always at the bottom.
- Coordinate labels (a–h, 1–8) on board edges.
- Responsive: scales to viewport on mobile (375px wide minimum) without losing interactivity.

#### D.4.2 Game state management
- `chess.js` for rules, move validation, draw detection (50-move, threefold, insufficient material, stalemate).
- State held in React; persisted to localStorage on every move.
- Tracks: full move history (SAN), per-move FEN, side to move, in-check, game status (`in-progress | checkmate | stalemate | draw_50 | draw_threefold | draw_insufficient | resigned | timeout`).

#### D.4.3 AI opponent
- New backend endpoint `POST /api/engine/move`: takes `{fen: string, skillLevel: number}`, returns `{move: string (SAN), fen: string (newFen), evalCp?: number, ponderMs: number}`.
- Implementation: existing Stockfish wrapper in `coach.engine`, exposed via FastAPI route. Skill levels 1–20 map to Stockfish's `Skill Level` UCI option.
- Latency budget: under 2 s p95 per move at skill level 20 on the HF Space free CPU tier. If we exceed, lower default depth.
- AI starts thinking after the user's move is submitted; the SPA shows a "Computer is thinking…" status during the round-trip.

#### D.4.4 Time controls
- Initial time + per-move increment, picked at game start.
- Presets: Bullet (1+0, 2+1), Blitz (3+0, 5+0, 5+3), Rapid (10+0, 15+10), Classical (30+0), Unlimited (no clock).
- Clock counts down only on the side-to-move's clock. Increment added on each completed move.
- Game ends with a "loss on time" status if a clock hits zero.

#### D.4.5 Game lifecycle
- **New game screen**: pick color (white / black / random), AI skill level (slider 1–20 with text descriptors at key points), time control. "Start game" begins play.
- **In-game**: board, both clocks, move list (SAN, two columns), buttons for "Resign" and "Offer draw" (offer is auto-accepted by AI under certain eval conditions, otherwise declined silently).
- **End-of-game**: result modal showing `1-0 / 0-1 / ½-½` with the reason ("checkmate", "resignation", "stalemate", etc.), a "Review with Coach" button (links into PR-2's analyze flow with the just-played PGN preloaded), and a "Play again" button (returns to the new-game screen with the prior settings).

#### D.4.6 Game history
- Local-first: completed games stored in localStorage as `{id, pgn, result, white, black, played_at, time_control, ai_skill}`.
- `/history` page lists completed games (most recent first), each entry clickable into a read-only review.
- Postgres-backed cross-device history is a deliberate Phase 2 D **follow-up** that requires user accounts (originally out of scope per §10; this amendment moves "user accounts" to "may be added inside Phase 2 D if cross-device history is explicitly requested by the owner").

#### D.4.7 Acceptance
- A first-time visitor can start a game, play through to completion, and get a Coach review without reading any docs.
- The board renders correctly on mobile (375px wide) and desktop.
- A completed game persists across browser refreshes via localStorage.
- AI move latency < 2 s p95 at skill level 20 on the HF Space free tier.
- Lighthouse ≥ 90 performance and accessibility on `/play`.

### D.5 New §6.1 reframe (small)

The PR-2 analyze flow stays. The route renames from `/` (analyze) to `/review` (analyze a PGN you paste, OR review a game you just finished). The new `/play` becomes the default landing route. Both flows reuse the same `AnalysisView` once the backend exists.

### D.6 New §7 additions (chess client criteria)

In addition to original §7's done items:

- [ ] `/play` renders a working chess client; user can complete a game vs AI at any skill level (1–20).
- [ ] `/history` lists completed games and lets the user re-open them.
- [ ] End-of-game "Review with Coach" launches the `/review` flow with the PGN pre-loaded.
- [ ] Lighthouse ≥ 90 performance + accessibility on `/play`.
- [ ] AI move latency < 2 s p95 at skill 20 on HF Space free tier.

### D.7 New §8 additions (API contract)

```typescript
// frontend/src/types/api.ts (additions)

export interface EngineMoveRequest {
  fen: string;
  skillLevel: number; // 1..20
}

export interface EngineMoveResponse {
  move: string;       // SAN
  fen: string;        // post-move FEN
  evalCp?: number;    // engine eval after the move, +ve = white advantage
  ponderMs: number;   // server-side think time
}

export type GameResult = "1-0" | "0-1" | "1/2-1/2";
export type GameEndReason =
  | "checkmate"
  | "resignation"
  | "timeout"
  | "stalemate"
  | "draw_50"
  | "draw_threefold"
  | "draw_insufficient";

export interface PersistedGame {
  id: string;          // local UUID
  pgn: string;
  result: GameResult;
  reason: GameEndReason;
  white: "user" | "ai";
  black: "user" | "ai";
  aiSkill: number;
  timeControl: { initialMs: number; incrementMs: number } | null;
  playedAt: string;    // ISO
}
```

Backend endpoint:

```
POST /api/engine/move
Request:  EngineMoveRequest
Response: EngineMoveResponse
Errors:   400 on invalid FEN; 409 if FEN is terminal (game already over)
```

Game persistence is **localStorage only** in Phase 2 D's MVP. No `PersistedGame` API endpoints in this amendment. They'd land if/when cross-device history is added (which would also require user accounts, currently still out per §10 unless explicitly opted into).

### D.8 New §10 additions (out of scope, in addition to original)

- **Multiplayer (human-vs-human) play.** Websockets, matchmaking, anti-cheat. Phase 3.
- **Time controls beyond initial+increment.** No Bronstein, no multi-stage Fischer.
- **Opening explorer / openings book.**
- **Tactical puzzles** (a separate product surface).
- **Lessons / courses.**
- **Tournaments.**
- **Ratings (Elo / Glicko).** Each completed game records its result; no rating-tracking system.
- **Sound effects.** chess.com has them; we ship without for v1.
- **Board themes / piece sets.** One default theme; user theming is Phase 3.
- **Export game as PGN** (nice-to-have, deferred).
- **Game annotation by the user** (annotations come from Coach; user-authored annotations are out).
- **Game sharing via URL** (deferred).

### D.9 Repository layout additions (extends original §5)

```
frontend/src/
├── pages/
│   ├── PlayPage.tsx          ← NEW (§D.4)
│   ├── HistoryPage.tsx       ← NEW (§D.4.6)
│   ├── ReviewPage.tsx        ← was AnalyzePage; renamed; behavior unchanged
│   └── MetricsPage.tsx
├── game/
│   ├── engine.ts             ← chess.js wrapper (rules, draw detection)
│   ├── clock.ts              ← time-control state machine
│   ├── persist.ts            ← localStorage I/O for PersistedGame
│   └── ai.ts                 ← engine.move() client wrapper
├── components/board/
│   ├── ChessBoard.tsx        ← react-chessboard wrapper
│   ├── PromotionPicker.tsx
│   ├── CapturedPieces.tsx
│   └── MoveList.tsx
└── hooks/
    ├── useGame.ts            ← orchestrates engine + clock + AI
    └── useGameHistory.ts
```

### D.10 PR rollout plan

- **PR-4 (this PR)** — Amendment D in REQUIREMENTS.md + CLAUDE.md update. **Spec only, no code.**
- **PR-5** — chess client scaffold: `chess.js`, `react-chessboard`, `/play` route, mock AI (returns random legal move) so UI is verifiable end-to-end without backend changes.
- **PR-6** — backend `POST /api/engine/move` endpoint wrapping the existing Stockfish engine; SPA flips from mock AI to real.
- **PR-7** — time controls + game lifecycle (resign, draw offer, end-of-game modal, "Review with Coach" link).
- **PR-8** — `/history` page; localStorage persistence wired through.
- **PR-9** — polish (mobile responsiveness, captured-pieces strip, last-move highlight, legal-move dots, promotion picker).
- **Existing PR-3** (metrics page mock) — carries forward, lower priority, lands when convenient.

Each PR is independently shippable to the staging Cloudflare Pages deploy and verifiable end-to-end before the next starts.
