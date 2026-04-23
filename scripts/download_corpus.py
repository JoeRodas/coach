"""Download ~500 master games from Lichess for the Phase 1 retrieval corpus.

Pulls recent rated classical + rapid games by a handful of top GMs from the
public Lichess API and writes one PGN file per player under data/games/.
No API key required for public games. Respects Lichess rate limits.

Usage: python scripts/download_corpus.py [--per-player 100]

Swap to a better source (PGN Mentor, Caissabase, annotated-games sets) in
Phase 2 when retrieval quality starts to matter.
"""
from __future__ import annotations

import argparse
import ssl
import sys
import time
import urllib.error
import urllib.request

import certifi

from coach.config import GAMES_DIR

SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

DEFAULT_PLAYERS = [
    "DrNykterstein",      # Magnus Carlsen
    "Zhigalko_Sergei",    # Sergei Zhigalko, GM
    "nihalsarin2004",     # Nihal Sarin
    "DanielNaroditsky",   # Daniel Naroditsky, GM
    "penguingim1",        # Andrew Tang, GM
]

BASE_URL = "https://lichess.org/api/games/user/{user}"


def fetch_player_pgns(user: str, max_games: int) -> str:
    params = (
        f"?max={max_games}"
        "&rated=true"
        "&perfType=blitz,rapid,classical"
        "&clocks=false"
        "&evals=false"
        "&opening=true"
    )
    url = BASE_URL.format(user=user) + params
    req = urllib.request.Request(url, headers={"Accept": "application/x-chess-pgn"})
    with urllib.request.urlopen(req, timeout=60, context=SSL_CONTEXT) as resp:
        return resp.read().decode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-player", type=int, default=100,
                        help="Games to pull per player (default 100 -> ~500 total)")
    parser.add_argument("--players", nargs="+", default=DEFAULT_PLAYERS)
    args = parser.parse_args()

    GAMES_DIR.mkdir(parents=True, exist_ok=True)
    total = 0
    for i, user in enumerate(args.players):
        out = GAMES_DIR / f"{user}.pgn"
        if out.exists() and out.stat().st_size > 0:
            print(f"  skip {user}: {out} already exists")
            continue
        print(f"  [{i + 1}/{len(args.players)}] fetching {args.per_player} games for {user}")
        try:
            pgn = fetch_player_pgns(user, args.per_player)
        except urllib.error.HTTPError as e:
            print(f"  ! {user}: HTTP {e.code} — skipping", file=sys.stderr)
            continue
        out.write_text(pgn, encoding="utf-8")
        game_count = pgn.count("[Event ")
        total += game_count
        print(f"    wrote {game_count} games to {out}")
        time.sleep(2)  # be polite to the API

    print(f"Done. ~{total} games under {GAMES_DIR}")


if __name__ == "__main__":
    main()
