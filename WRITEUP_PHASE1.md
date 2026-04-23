# Phase 1 writeup — skeleton

**This is a scaffold, not the final post.** The spec says the writeup's value comes from specificity and honesty in *your* voice. I've filled every concrete fact from the Phase 1 build and flagged the spots that need your first-person narrative with `[FILL IN]`.

Target: 1500 words, your blog or Medium. Title options at the bottom.

---

## Hook (≈150 words)

Open with the thing you actually wanted to know: **"where did I go wrong in this game."** Every club player has asked it. Stockfish can tell you the move was bad; it can't tell you *why* it was bad, what the plan should have been, or which master game teaches the same lesson.

Coach is the thing that does. Paste a PGN, it answers in three paragraphs grounded in engine analysis and retrieval over a master-game corpus.

[FILL IN: one or two sentences on *why you* built it — your Ajedrez.ai context, the Handshake AI eval background, or the Slack ML job target. Anchor the post in a real motivation. Avoid "I've always been passionate about AI" — be specific.]

Phase 1 took **three weekends**. It's deployed at `chesscoach.nuezmiami.com`. Code at `[github.com/you/coach]`.

## What "minimum lovable" looks like (≈250 words)

Phase 1 is deliberately thin. Four components, each the simplest possible:

- **Agent loop** — Claude Opus with two tools: `identify_critical_moments(pgn, side)` and `retrieve_similar_positions(fen)`. The LLM decides when to call what; a grounded 3-paragraph system prompt forces it to cite ply numbers and master-game IDs.
- **Engine** — Stockfish at depth 15, walking every ply, recording the eval delta from the mover's POV. "Critical moment" = any move with ≥100cp drop; top 3 biggest drops surface.
- **Retrieval** — 400 recent games from 4 titled Lichess accounts (Carlsen, Zhigalko, Nihal Sarin, Andrew Tang). Every 4th ply indexed with `all-MiniLM-L6-v2` (off-the-shelf sentence-transformer, 384 dims). 8,847 positions, 12 MB `.npz` file, cosine search in-memory.
- **UI** — FastAPI + 130 lines of vanilla HTML/CSS/JS. Textarea for PGN, dropdown for side, button that waits 1–3 minutes for Stockfish.

[FILL IN: a sentence on why you chose each over the more complex alternative. E.g. why an in-memory npz instead of pgvector, why text-context embeddings instead of training a position encoder. The spec calls these out as Phase 2 upgrades — name them honestly so the reader knows what's coming.]

[FILL IN: one paragraph on what you explicitly *didn't* build. No auth, no persistence, no weakness classifier, no puzzle ranker, no Airflow, no eval harness. Those are Phases 2 and 3 — shipping without them is the point.]

## End-to-end demo (≈300 words)

Sample input: [FILL IN — the Morphy Opera House game is built into the UI as the "Try a sample game" button, or pick one of your own Lichess games].

Coach output (edited for length):

> **1. What happened.** Stockfish flags three rook-endgame slips, all on the White king's journey. The single biggest swing was **move 57. Kf4** (ply 114), which dropped the eval from roughly +0.1 to −2.4 — turning a holdable endgame into a lost one. The engine preferred **Ra2**, activating the rook instead of walking the king forward...
>
> **2. Why it was wrong.** The common theme is king activity preferred over rook activity. In `nihalsarin2004#lichess.org/hrh3qPec` around ply 100–120 (rook + a/b/c-pawns vs. rook + g/h-pawns, near-identical to your ply 100 and 114 positions), the defender keeps the rook behind the passed pawn and uses the h-pawn as a shield...
>
> **3. What to study next.** Drill rook endgames with an outside passed pawn vs. kingside pawn majority — specifically the principle "rook behind the passed pawn, king stays home until the rook is working." A focused week with Mueller & Lamprecht's *Fundamental Chess Endings* (the R+P chapter on Tarrasch's rule and active rooks) plus replaying the Nihal Sarin game above move-by-move from ply 95 onward will directly patch the exact decision you got wrong on move 51 and move 57.

[FILL IN: two sentences of your reaction. Not "wow, amazing." Something like "the retrieval pick was genuinely relevant — the Nihal game had the same pawn structure, which is the only thing sentence-transformers could have keyed on since the surrounding text was almost identical."]

## What was hard (≈350 words)

Three places the naive path didn't work.

**POV flipping in Stockfish evals.** `python-chess` returns evaluations from the side-to-move's perspective. To compute a per-move delta that's always negative-when-blundered, I record the pre-move score from the mover's POV, push the move, read the post-move score from the opponent's POV, negate it, and take the diff. [FILL IN: one sentence on how long this took to debug or the specific bug that made you write it down.]

**Embedding-context drift between index and query.** First version embedded master positions as `"{White} vs {Black} | {ECO} {Opening} | move N X to move | FEN ..."` but queried with `"user game | move N X to move | FEN ..."`. Same FEN, different prose prefix — enough to skew retrieval toward games with similar-sounding players. Fix: single `format_context` helper called from both sides, player names absent on the query side become `"?"` (matching how missing PGN headers get rendered at index time).

**Lichess API rate limits and the 0-byte trap.** First corpus run pulled `rated=true&perfType=classical,rapid` for 5 top GMs. Three of them play almost exclusively bullet on Lichess, so the API returned empty files. Writing a 0-byte `.pgn` fools the "already downloaded" check on retry. Fix: broaden to `blitz,rapid,classical` and skip files only if non-zero size.

[FILL IN: anything that bit you. If the Anthropic tool-calling format confused you, say so. If the sentence-transformers import time or the torch download surprised you, say so. Readers trust honesty.]

## What's next (≈200 words)

Phase 1 deliberately uses off-the-shelf everything. Phase 2 replaces the retrieval substrate:

- **Custom position embeddings.** PyTorch, contrastive learning on 1M positions from Lichess's monthly dump. Positions from the same game or with similar Stockfish evals pull together; unrelated pairs push apart. The goal is beating sentence-transformers on a held-out retrieval benchmark that I'll publish with the model.
- **Airflow ingestion.** Right now `scripts/download_corpus.py` is one-shot. Phase 2 turns it into a DAG that pulls Lichess's monthly PGN dump, shards it, runs Stockfish evals at depth 15, and writes training features to Parquet.
- **Weakness classifier (logistic regression first).** Per Slack's "bootstrap a logistic regression and move on" framing, Phase 2's weakness signal is hand-crafted features — centipawn loss by phase, by piece, by motif tag — fed to a logreg. BERT fine-tuning is Phase 3 once the simpler model has a number to beat.

[FILL IN: one sentence on your timeline. Be honest — if Phase 2 will take 3 weekends, say 3 weekends. Don't promise "next month."]

---

### Title options

- *"I built a conversational chess coach in three weekends — here's how"* (per the spec)
- *"Coach: grounding a chess LLM in Stockfish and master-game retrieval"*
- *"Stockfish knew where I went wrong. Coach can say why."*

### Numbers to double-check before you publish

- [ ] Word count of final draft
- [ ] Exact game count in corpus at publish time (`ls data/games/*.pgn | wc -l` × ~100)
- [ ] Exact indexed position count (from `scripts/build_index.py` output)
- [ ] Deployed URL status 200 at publish time
- [ ] GitHub repo public and pinned on your profile
- [ ] One screenshot of the UI with a real sample output

### Distribution checklist (from PROJECT_COACH.md §Publication plan)

- [ ] Show HN post
- [ ] r/MachineLearning project post (read their rules first)
- [ ] r/chess + r/chessprogramming
- [ ] LinkedIn (personal framing)
- [ ] Twitter/X thread with screenshots
- [ ] Cold email to a Slack ML engineer citing Slackbot as the inspiration
