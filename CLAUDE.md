# CLAUDE.md — working instructions for this repo

This file is the durable, in-repo source of truth for Claude Code sessions.
Read it end-to-end before doing anything. It tells you (a) what the project
is, (b) what already exists, (c) what's been decided, (d) what's blocked,
(e) what's been learned the hard way.

If you're tempted to do something that contradicts this file, **stop and
ask the user first**. If you're tempted to expand or update this file
yourself, also stop and ask first — the user maintains it.

---

## 1. Project at a glance

**Coach** is a **chess platform where you play against an AI opponent**, with
a grounded post-game analysis as the differentiator. After each game, Coach
delivers a three-paragraph review citing similar positions from a master-game
corpus. Live at <https://chesscoach.nuezmiami.com>.

> The original positioning ("paste-a-PGN analysis tool") was the Phase 1 +
> Phase 2 design through 2026-04-24. On 2026-04-24 the owner pivoted to the
> chess-platform framing ("Amendment D" in REQUIREMENTS.md). The analysis
> surface is preserved — it's now the post-game review, reachable from the
> end-of-game modal.

**Phase 1** (Minimum Lovable Coach — analysis only) shipped — see
`WRITEUP_PHASE1.md` and the `9975358` commit. Stack: FastAPI + Stockfish +
sentence-transformer retrieval + Anthropic Claude generation + vanilla
static HTML frontend.

**Phase 2 D** is the active scope. The authoritative spec is `REQUIREMENTS.md`,
which has an Amendment D section at the bottom that supersedes the original
where they conflict. Read both. Six goals, in priority order:

1. **Chess client** (§D.4 / §6.0) — the new top. Play vs AI, time controls,
   game lifecycle, history.
2. **React + TS frontend** (§6.1) — already in flight; PR-1 + PR-2 merged.
3. **Custom PyTorch embeddings** (§6.2) — supports analysis quality.
4. **Airflow ingestion + pgvector** (§6.3, §6.4) — supports analysis quality.
5. **Eval harness + LR weakness classifier** (§6.5, §6.6) — supports
   analysis quality.
6. **`/admin/metrics` page** (§6.7) — operations.

Out of scope for Phase 2 D: multiplayer (PvP), opening explorer, puzzles,
lessons, tournaments, ratings, sound, board themes, PGN export, mobile app,
realtime streaming, BERT fine-tuning, XGBoost ranker. See REQUIREMENTS.md
§10 + §D.8 for the full list.

---

## 2. Current state of the repo (verify, don't trust)

```
coach/
├── CLAUDE.md           ← this file
├── REQUIREMENTS.md     ← client spec (authoritative)
├── PROJECT_COACH.md    ← original Phase 1 spec
├── PHASE2_PLAN.md      ← scratch plan + benchmark-correction notes
├── README.md           ← public-facing + HF Spaces frontmatter
├── WRITEUP_PHASE1.md
├── Dockerfile          ← HF Spaces image
├── fly.toml            ← retained for reference, app destroyed
├── deploy/
│   └── cloudflare-worker.js
├── src/coach/          ← Phase 1 FastAPI app (agent, retrieval, web, …)
├── pipelines/ingest.py ← Lichess Elite → Stockfish-labeled Parquet
├── training/           ← encoder.py, dataset.py, train.py, loss.py, …
├── evals/              ← retrieval.py, queries.jsonl, results/
├── scripts/            ← build_index.py, build_encoder_index.py, build_clean_index.py
├── tests/
└── data/               ← gitignored: index.npz, training/*.parquet, raw/*.zip, checkpoints/*.pt
```

Layout **does not yet match REQUIREMENTS.md §5** (target is `backend/app/`,
`ml/`, `pipeline/dags/`, `frontend/`, `infra/`). Migration is incremental,
component by component, **not big-bang**. Coach is live; do not break it.

### What's actually deployed right now

- **App (Phase 1 prod)**: Hugging Face Space `NuezMiami/coach`, Docker SDK,
  free CPU tier, 16 GB RAM. Native URL `https://nuezmiami-coach.hf.space`.
- **Domain (Phase 1 prod)**: Cloudflare Worker `steep-cell-2bea`
  reverse-proxies `chesscoach.nuezmiami.com/*` → HF Space. Code at
  `deploy/cloudflare-worker.js`.
- **Phase 2 SPA staging**: Cloudflare Pages project `coach-frontend`,
  auto-deploys on every push to `main`. Build cmd
  `pnpm install --frozen-lockfile && pnpm build`, build output
  `frontend/dist`, root dir `frontend`, `NODE_VERSION=22.14.0`. Live at
  <https://coach-frontend.pages.dev> and (pending DNS) at
  `chesscoach-v2.nuezmiami.com`. The §7 cutover swaps the Worker route
  from HF Space → Pages once PR-3 ships.
- **Secrets**: `ANTHROPIC_API_KEY` is set as an HF Space secret in the
  Space settings, not in any repo file.
- **Why not Fly.io** (which the spec assumes): user has no credit card on
  file. Fly trial expired 2026-04-23; we migrated to HF Spaces + Cloudflare
  Workers as the only zero-cost combo. `fly.toml` and Fly-specific bits
  stay in the repo for reference but are unused.

### What's already built toward Phase 2 (anchored in commit `44960c4`)

- `pipelines/ingest.py` — Lichess Elite PGN download, ply subsample,
  Stockfish-label, write Parquet shards.
- `training/` — InfoNCE position encoder (12×8×8 grid + 8 scalar features,
  4-layer transformer, **128-dim out, ~574k params**), trainer with
  per-epoch checkpoints, dataset (adjacent-ply pairs only — see decision §4),
  encoder retriever for cosine search.
- `evals/retrieval.py` — Recall@k / MRR harness, three modes:
  `phase1_sentence_transformer` (leaky baseline),
  `phase1_sentence_transformer_clean` (the fair baseline), `phase2_encoder`.
- 80-query eval set in `evals/queries.jsonl` (auto-generated by ECO).
- Latest encoder checkpoint: `data/checkpoints/encoder.pt`, 10 epochs,
  final loss 0.49, **128-dim** — to be replaced by 256-dim per §4.

Untracked, not-yet-used here: nothing — anchor commit captured everything
that's substantive. Local `data/` artifacts (parquet shards, lichess raw
zip, npz indexes, .pt checkpoints) are gitignored.

---

## 3. Stack (per REQUIREMENTS.md §4 + adjustments for hosting reality)

| Layer | Choice | Notes |
|---|---|---|
| Backend | FastAPI (Python 3.11+) | Existing. |
| Frontend | React 18 + TypeScript + Vite + Tailwind + react-query | New, §6.1. |
| Database | **Neon** Postgres 17.8 + pgvector 0.8.0 | Spec said Fly managed Postgres; we use Neon (free tier, no card). pgvector 0.8.0 supports HNSW, so we use HNSW not IVFFlat. |
| ML framework | PyTorch 2.x | Existing. |
| Pipeline | Apache Airflow | Existing `pipelines/ingest.py` becomes a DAG, §6.3. |
| Engine | Stockfish | Existing — also serves the chess client's AI opponent (§D.4.3). |
| LLM | Anthropic Claude API | Existing. `claude-opus-4-7` per `coach.config`. |
| Hosting (web) | HF Spaces + Cloudflare Worker | Not Fly.io — see §2. |
| Package mgmt | Python: stay on the project's existing setup; JS: pnpm | |
| Tests | pytest, vitest | |
| Lint/format | ruff (Python), biome (TS) | |
| Chess rules engine (frontend) | `chess.js` ^1.0 | Added per Amendment §D.3. Pure JS, ~30 KB. |
| Chess board UI | `react-chessboard` ^4.x | Added per Amendment §D.3. Drag-and-drop board, ~80 KB. |

Add no new dependencies without a one-line justification in the PR.

---

## 4. Locked decisions (do not re-litigate)

These are user-confirmed. If a future session questions them, point at this
section and ask before changing course.

- **Embedding dim: 256.** Retrain. The 128-dim checkpoint stays as a
  comparison point in the writeup ("we tried 128 first, scaled to 256
  for reasons X").
- **Positive-pair definition: same game ±3 plies AND similar engine eval.**
  Current `training/dataset.py` only does adjacency; needs the eval-similarity
  filter added.
- **Training data scale: 1M positions** from Lichess open data (master /
  2000+ ELO subset is fine for Phase 2). Existing 94k-pair shard set is
  a stepping stone.
- **Acceptance threshold:** the **clean (scrubbed) Phase 1 baseline** is
  THE baseline the encoder must beat by 5pp on top-5 precision. Both
  numbers (leaky and clean) get documented in `PHASE2.md` so the leak
  finding is visible, not hidden.
- **Component order:** per Amendment §D.2. **Chess client (§6.0)** is the
  new top priority, then the rest of §6.1 frontend (PR-3 metrics page),
  then embeddings (§6.2), then pipeline (§6.3) + pgvector (§6.4), then
  eval harness + classifier (§6.5, §6.6), then admin metrics (§6.7).
  Original Phase 2 frontend-first reasoning ("validate every subsequent
  backend change in the new UI") still holds for the §6.2-§6.7 supporting
  work.
- **Chess client framing (Amendment §D):** AI opponent only (no PvP);
  Stockfish via backend `POST /api/engine/move` (not browser WASM);
  localStorage persistence (cross-device requires accounts → Phase 2 D
  follow-up); `react-chessboard` + `chess.js`. PR rollout per §D.10.
- **Postgres host: Neon.** Free tier, supports pgvector, no credit card.
  `DATABASE_URL` lives in `.env`, with an `.env.example` template
  committed.
- **Theme annotation: hybrid.** User personally defines the ~20-theme
  vocabulary (names + one-sentence descriptions) and hand-labels a 40–50
  position seed set. Then Claude proposes labels for positions 51–200
  using the seed as few-shot examples; user reviews and corrects every
  one. Methodology documented in `MODEL_CARD.md`. Build the tooling
  first; **do not propose labels yourself before the seed exists**.

### Workflow conventions (per spec §7, §9)

- One PR per component in §6. Each PR meets its acceptance criteria
  before merging. No three-week feature branches.
- No fabricated numbers. Every metric in writeup/README/resume must be
  reproducible from a committed script.
- Do not break the live site. Risky changes go behind a feature flag or
  a staging URL.
- No secrets in the repo. `.env.example` only.

---

## 5. Open blockers / deps to resolve

- ~~Neon project not yet created.~~ **Done 2026-04-24.** Project
  `chesscoach`, branch `production`, db `neondb`, pooled endpoint
  `ep-fancy-heart-an5mvv2b-pooler.c-6.us-east-1.aws.neon.tech`. pgvector
  0.8.0 confirmed working (round-trip cosine-distance query returned 0.0).
  `DATABASE_URL` is in local `.env` (gitignored).
- **Theme vocabulary + seed labels not yet authored.** User to deliver
  ~20 themes and ~40–50 hand-labeled positions. Until that lands,
  retrieval eval can't switch to the spec's themes-based metric.
- **No GitHub remote / CI yet.** Spec assumes PRs and a CI hook that
  posts eval-harness numbers as PR comments. Local repo currently
  tracks `origin/main` (Phase 1 commit only); the anchor commit is
  one ahead and unpushed. Decide whether to push and wire CI before
  PR-driven workflow begins.
- **`MODEL_CARD.md` doesn't exist yet.** Required by §6.2 and the theme
  annotation methodology. Created when the encoder retrain lands.

---

## 6. Findings (durable engineering notes — append, do not edit prior entries)

### 2026-04-24 — Phase 1 retrieval baseline was inflated by an ECO/opening-name leak

**What:** Phase 1 retrieval works by embedding a short text descriptor of
each position with a generic sentence-transformer. The descriptor template
in `src/coach/retrieval.py::format_context` was

```
{white} vs {black} | {ECO} {opening_name} | move N {color} to move | FEN ...
```

The retrieval benchmark's automatic relevance rule is *same ECO*. So both
the indexed docs and the queries contained the ground-truth ECO code as a
literal string token. The sentence-transformer was partly **string-matching
the answer**, not understanding the position.

**How caught:** When the freshly trained Phase 2 encoder scored Recall@20
= 0.287 against the original Phase 1 baseline of 0.688, the gap was
suspicious — sentence-transformers shouldn't dominate a contrastive
position encoder at understanding board structure. Read both retrievers'
input strings, spotted the ECO in the indexed text.

**Fix (commit `44960c4`):**

- `scripts/build_clean_index.py` re-embeds the index with the
  `"{eco} {opening}"` segment stripped → `data/index_clean.npz`.
- `evals/retrieval.py --system phase1_sentence_transformer_clean` scrubs
  the same segment from queries and uses a `game_id → ECO` lookup from
  the original (un-scrubbed) index for relevance scoring (since the
  cleaned contexts no longer contain ECO).

**Numbers** (same 80 queries, same 8,847-position index, k=20):

| system | recall@20 | recall@10 | mrr@20 |
|---|---|---|---|
| Phase 1 leaky | 0.688 | 0.613 | 0.477 |
| Phase 1 clean | **0.050** | 0.013 | 0.004 |
| Phase 2 encoder (2 / 5 epochs, 128-dim) | 0.287 | 0.188 | 0.128 |
| random baseline | 0.222 | — | — |

**Implications:**

- Off-the-shelf sentence-transformers operating on FEN-as-text are at or
  below random on this task. They never understood position structure;
  they string-matched ECO codes.
- The encoder is genuinely doing useful retrieval (~6× the clean Phase 1
  on Recall@20, ~30× on MRR), even partially trained.
- For Phase 2, the **clean baseline is THE baseline** for the §6.2
  acceptance criterion. The leaky number is documented in `PHASE2.md`
  to make the leak finding visible, not hidden.
- Reusable lesson: when constructing benchmark queries from indexed-doc
  templates, sanity-check that the relevance signal isn't *literally
  present in the embedding input*. Anonymizing player names (which the
  query generator already did) was insufficient — ECO was the leak.

### 2026-04-24 (later) — Encoder loss vs retrieval: a 5× training run only buys ~13% retrieval gain

**What:** Re-ran the InfoNCE encoder for the full 10 epochs originally
planned, then re-scored against the same 80-query benchmark. Loss curve
flattened cleanly — from 1.65 (epoch 0) to 0.49 (epoch 9), most of the
descent done by epoch 4. Retrieval numbers, same index, same queries:

| stage | loss | recall@20 | recall@10 | mrr@20 |
|---|---|---|---|---|
| Phase 1 clean (no encoder) | — | 0.050 | 0.013 | 0.004 |
| Phase 2 encoder, 2 epochs | 2.60 | 0.287 | 0.188 | 0.128 |
| Phase 2 encoder, 10 epochs | 0.49 | **0.325** | **0.237** | **0.134** |
| random | — | 0.222 | — | — |

**The interesting bit:** training loss dropped **81%** (2.60 → 0.49) but
retrieval Recall@20 only improved **13% relative** (0.287 → 0.325).
Recall@10 saw the largest gain (+26%); MRR@20 barely moved (+5%). That
gap is the encoder hitting the ceiling of what its current training
signal can teach.

**Probable cause:** the only positive-pair signal we feed it is "two
adjacent retained plies from the same game." That's enough for the model
to learn coarse positional similarity — pieces in roughly the same
places, similar pawn structures — but it never sees a signal that
distinguishes "same opening idea" from "same midgame structure." The
benchmark's relevance rule is *same ECO* (i.e. same opening), so the
encoder is being graded on a dimension its training data doesn't isolate.

**Implication for §6.2:** the spec's required positive-pair definition
(*"same game within ±3 plies AND similar evaluation"*) is exactly the
right next move — it adds a tactical/strategic-state filter that should
push the encoder toward what the benchmark is actually measuring. Plus
the spec's 256-dim output (we trained at 128) gives more capacity. If
both of those changes don't push Recall@20 substantially past 0.325,
then we have an encoder-architecture problem, not a training problem.

**Saved artifacts:**
- `evals/results/phase2-2ep-2026-04-24.json` — the early-stop run
- `evals/results/phase2-10ep-2026-04-24.json` — the planned-length run

### 2026-04-24 (later) — Product pivot to chess platform (Amendment D)

**What:** the owner pivoted Coach's positioning from "analysis tool" to
"chess platform with grounded analysis as a feature." See REQUIREMENTS.md
§D for the full amendment text. The original positioning is preserved
above the amendment in the spec for history.

**Why:** owner's call. Both products are coherent; the chess-platform
framing ships a more obvious user motion ("play chess") and turns the
retrieval-grounded analysis into a differentiator the user *experiences
in context* rather than a standalone tool the user has to seek out.

**What stays:**
- All Phase 1 backend infra (FastAPI, Stockfish, Anthropic, Phase 1
  retrieval).
- The Cloudflare Pages staging + HF Space prod story.
- The Neon Postgres + pgvector decision (will eventually back game
  history once accounts are in scope).
- All four Phase 2 ML goals (§6.2 embeddings, §6.3 Airflow, §6.5 eval
  harness, §6.6 classifier). They support the analysis feature inside
  the new product.
- PR-1 (frontend scaffold) and PR-2 (analyze flow) — both merged, both
  remain useful. The analyze surface gets renamed `/analyze` → `/review`
  and becomes reachable from end-of-game.

**What changes:**
- Top of priority order is now §6.0 chess client.
- New tooling: `chess.js` + `react-chessboard` (frontend); new backend
  endpoint `POST /api/engine/move` wrapping the existing Stockfish.
- Significant additions to "out of scope" — multiplayer, ratings,
  themes, sound, PGN export all explicitly deferred.
- Original §10's "user accounts, mobile app" softened: accounts may
  re-enter Phase 2 D scope if cross-device game history is wanted.

**Cost acknowledged:** chess-platform MVP is 3–5 weeks of focused work,
not days. Polished version another 2–4 weeks.

**PR rollout per §D.10:** PR-4 (this spec amendment) → PR-5 (chess
client scaffold with mock AI) → PR-6 (real Stockfish backend integration)
→ PR-7 (time controls + lifecycle) → PR-8 (history page) → PR-9 (polish).
Existing PR-3 (metrics page mock) carries forward at lower priority.

---

## 7. Status snapshot (updated as work progresses)

- [x] Anchor commit of all in-flight Phase 2 work — `44960c4`.
- [x] CLAUDE.md (this file) created.
- [x] Neon project created, `DATABASE_URL` in `.env`, pgvector 0.8.0 verified.
- [x] PR-4 — Amendment D pivot recorded in REQUIREMENTS.md + CLAUDE.md. *(this PR)*
- [ ] §6.0 / §D.4 chess client (the new top priority).
  - [ ] PR-5 scaffold: `chess.js`, `react-chessboard`, `/play` route, mock AI.
  - [ ] PR-6 backend `POST /api/engine/move` wrapping Stockfish; SPA flips from mock to real.
  - [ ] PR-7 time controls + game lifecycle (resign, draw offer, end-of-game modal, "Review with Coach" link).
  - [ ] PR-8 `/history` page; localStorage persistence.
  - [ ] PR-9 polish (mobile, captured-pieces strip, last-move highlight, legal-move dots, promotion picker).
- [~] §6.1 frontend rebuild (React + TS + Vite + Tailwind).
  - [x] PR-1 scaffold merged (`8518781`). Cloudflare Pages project `coach-frontend` live at <https://coach-frontend.pages.dev> (verified rendering 2026-04-24). Custom domain `chesscoach-v2.nuezmiami.com` pending DNS/SSL provisioning. Note: an earlier Worker named `coach` was created by mistake during dashboard navigation; if it still exists, delete it (housekeeping, no functional impact).
  - [x] PR-2 analyze flow with Phase 1 parity merged (`14cf8b1`).
  - [ ] PR-3 metrics page (renders mock until §6.7 backend exists). Lower priority post-pivot.
  - [ ] Rename `/analyze` → `/review` (small follow-up, can fold into PR-7's end-of-game integration).
- [ ] §6.2 encoder retrained at 256-dim with eval-similarity positives.
- [ ] §6.3 Airflow DAG for Lichess ingestion.
- [ ] §6.4 Postgres + pgvector schema and migration.
- [ ] §6.5 Themes-based eval harness, hand-labeled set.
- [ ] §6.6 LR weakness classifier.
- [ ] §6.7 `/admin/metrics` page.
