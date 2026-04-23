# Coach

Conversational chess coach. You paste a PGN, it tells you where you went
wrong, why, and what to study — grounded in Stockfish analysis and a vector
index of master games. Deployed at
[chesscoach.nuezmiami.com](https://chesscoach.nuezmiami.com).

See `PROJECT_COACH.md` (copied at the repo root from `~/Downloads/`) for the
full spec and the Slack-JD mapping that justifies each component.

## Phase 1 — Minimum Lovable Coach

End-to-end pipeline on one game at a time. No training, no ingestion DAG, no
custom models yet. Just:

- `coach.engine` — Stockfish wrapper for position eval and critical-moment
  detection.
- `coach.retrieval` — sentence-transformer embeddings over ~500 hand-curated
  master PGNs, in-memory cosine index.
- `coach.agent` — Claude tool-calling loop that orchestrates analysis +
  retrieval and hands structured context to the generator.
- `coach.commentary` — grounded 3-paragraph explanation from Claude.
- `coach.cli` — `coach analyze path/to/game.pgn` for local testing.

Phases 2 (custom embeddings + Airflow) and 3 (BERT weakness classifier,
XGBoost ranker, eval harness) are not scaffolded yet — add when Phase 1 ships.

## Quickstart (local)

```bash
brew install stockfish
cp .env.example .env  # fill in ANTHROPIC_API_KEY
pip install -e ".[dev,web]"
python scripts/download_corpus.py  # pulls ~400 master PGNs
python scripts/build_index.py      # embeds into data/index.npz
uvicorn coach.web:app --reload     # http://127.0.0.1:8000
```

## Deploy to chesscoach.nuezmiami.com (Fly.io + Cloudflare)

The apex `nuezmiami.com` is registered at Cloudflare Registrar; Coach lives
on the `chesscoach` subdomain. Fly hosts the app.

```bash
# 1. Fly app + image (one-time)
flyctl auth login
flyctl launch --copy-config --no-deploy   # accept the fly.toml as-is
flyctl secrets set ANTHROPIC_API_KEY="$(grep ANTHROPIC_API_KEY .env | cut -d= -f2)"
flyctl deploy                             # first build is slow (~10 min)

# 2. Custom subdomain — CNAME is enough, no A/AAAA needed
flyctl certs add chesscoach.nuezmiami.com

# 3. In Cloudflare dashboard → nuezmiami.com → DNS → Add record:
#    Type:   CNAME
#    Name:   chesscoach
#    Target: coach-nuezmiami.fly.dev
#    Proxy:  DNS only (grey cloud) — required for Fly to issue TLS
#    TTL:    Auto
#    (After cert issues, you may flip to proxied for Cloudflare CDN.)

flyctl certs check chesscoach.nuezmiami.com  # wait until Verified
```

## Layout

```
src/coach/
  agent.py        # tool-calling orchestrator
  engine.py       # Stockfish wrapper
  retrieval.py    # embedding + cosine search
  commentary.py   # final LLM generation
  web.py          # FastAPI HTTP server
  static/         # HTML chat UI
  cli.py          # CLI entry point
  config.py       # env loading
data/games/       # master PGN corpus (not checked in)
scripts/          # build_index, download_corpus
Dockerfile        # stockfish + python + uvicorn
fly.toml          # Fly.io deployment config
tests/
```
