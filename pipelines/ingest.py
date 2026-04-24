"""Phase 2 training-data ingestion pipeline.

Downloads a month of Lichess Elite Database games (2400+ rated), filters by
ELO, subsamples plies, Stockfish-labels every Nth ply, and writes Parquet
shards under data/training/.

Usage:
    python -m pipelines.ingest --month 2026-02 --max-games 5000 --depth 8

Each stage is a plain function so it wraps cleanly into Airflow PythonOperators
later. The module is runnable standalone now; the DAG wrapper comes when the
first end-to-end run proves out.

Output schema (Parquet):
    fen            string   — FEN of the position after the move at `ply`
    score_cp       int32    — Stockfish eval in centipawns, mover's POV
    game_id        string   — {site}#{white}#{black}
    ply            int32    — 0-based index of the move that produced `fen`
    white_elo      int32
    black_elo      int32
    side_to_move   string   — 'w' or 'b'
"""
from __future__ import annotations

import argparse
import io
import os
import queue
import ssl
import sys
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import certifi
import chess
import chess.engine
import chess.pgn
import pyarrow as pa
import pyarrow.parquet as pq

from coach.config import DATA_DIR, load_settings

TRAINING_DIR = DATA_DIR / "training"
RAW_DIR = DATA_DIR / "raw"
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

ELITE_URL_TEMPLATE = "https://database.nikonoel.fr/lichess_elite_{month}.zip"


@dataclass
class PositionRecord:
    fen: str
    score_cp: int
    game_id: str
    ply: int
    white_elo: int
    black_elo: int
    side_to_move: str


def download_dump(month: str, dest_dir: Path) -> Path:
    """Download the Lichess Elite ZIP for `month` (YYYY-MM). Skip if cached."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = dest_dir / f"lichess_elite_{month}.zip"
    if out.exists() and out.stat().st_size > 0:
        print(f"  cached: {out} ({out.stat().st_size / 1e6:.1f} MB)")
        return out
    url = ELITE_URL_TEMPLATE.format(month=month)
    print(f"  downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "coach-phase2/1.0"})
    with urllib.request.urlopen(req, timeout=300, context=SSL_CONTEXT) as resp:
        ctype = (resp.headers.get("Content-Type") or "").lower()
        if "zip" not in ctype and "octet-stream" not in ctype:
            # nikonoel's WordPress redirects unknown months to the homepage with
            # HTTP 200 + text/html. Fail fast before we download a 56 KB web page.
            raise RuntimeError(
                f"Unexpected content-type {ctype!r} for {url} — month likely "
                f"not published yet. Check https://database.nikonoel.fr/ for "
                f"the latest available month."
            )
        total = int(resp.headers.get("Content-Length", 0))
        with open(out, "wb") as f:
            read = 0
            chunk = 1 << 20
            while True:
                buf = resp.read(chunk)
                if not buf:
                    break
                f.write(buf)
                read += len(buf)
                if total:
                    pct = 100 * read / total
                    print(f"\r    {read / 1e6:.1f} / {total / 1e6:.1f} MB "
                          f"({pct:.0f}%)", end="", file=sys.stderr)
            print("", file=sys.stderr)
    return out


def iter_elite_games(
    zip_path: Path, min_elo: int = 2200, max_games: int | None = None
) -> Iterator[chess.pgn.Game]:
    """Stream-parse PGNs from a Lichess Elite ZIP, filter by both-sides ELO."""
    yielded = 0
    with zipfile.ZipFile(zip_path) as z:
        pgn_names = [n for n in z.namelist() if n.endswith(".pgn")]
        if not pgn_names:
            raise RuntimeError(f"No .pgn files found in {zip_path}")
        for name in pgn_names:
            with z.open(name) as raw:
                text = io.TextIOWrapper(raw, encoding="utf-8", errors="replace")
                while True:
                    game = chess.pgn.read_game(text)
                    if game is None:
                        break
                    try:
                        w = int(game.headers.get("WhiteElo", "0") or 0)
                        b = int(game.headers.get("BlackElo", "0") or 0)
                    except ValueError:
                        continue
                    if w < min_elo or b < min_elo:
                        continue
                    yield game
                    yielded += 1
                    if max_games is not None and yielded >= max_games:
                        return


def label_game(
    game: chess.pgn.Game,
    engine: chess.engine.SimpleEngine,
    depth: int,
    every_nth_ply: int = 4,
    skip_opening_plies: int = 10,
) -> Iterator[PositionRecord]:
    """Walk a game and yield labeled positions for plies we keep."""
    headers = game.headers
    game_id = "#".join([
        headers.get("Site", "").rsplit("/", 1)[-1] or "?",
        headers.get("White", "?"),
        headers.get("Black", "?"),
    ])
    try:
        w_elo = int(headers.get("WhiteElo", "0") or 0)
        b_elo = int(headers.get("BlackElo", "0") or 0)
    except ValueError:
        w_elo = b_elo = 0

    board = game.board()
    for ply, move in enumerate(game.mainline_moves()):
        board.push(move)
        if ply < skip_opening_plies:
            continue
        if ply % every_nth_ply != 0:
            continue
        info = engine.analyse(board, chess.engine.Limit(depth=depth))
        pov = info["score"].pov(board.turn)
        score_cp = pov.score(mate_score=10000) or 0
        yield PositionRecord(
            fen=board.fen(),
            score_cp=score_cp,
            game_id=game_id,
            ply=ply,
            white_elo=w_elo,
            black_elo=b_elo,
            side_to_move="w" if board.turn == chess.WHITE else "b",
        )


def write_shard(records: list[PositionRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.table({
        "fen": [r.fen for r in records],
        "score_cp": pa.array([r.score_cp for r in records], type=pa.int32()),
        "game_id": [r.game_id for r in records],
        "ply": pa.array([r.ply for r in records], type=pa.int32()),
        "white_elo": pa.array([r.white_elo for r in records], type=pa.int32()),
        "black_elo": pa.array([r.black_elo for r in records], type=pa.int32()),
        "side_to_move": [r.side_to_move for r in records],
    })
    pq.write_table(table, path, compression="zstd")


def _game_to_task(game: chess.pgn.Game) -> dict:
    """Strip a chess.pgn.Game down to a picklable dict for a worker process."""
    headers = game.headers
    game_id = "#".join([
        headers.get("Site", "").rsplit("/", 1)[-1] or "?",
        headers.get("White", "?"),
        headers.get("Black", "?"),
    ])
    try:
        w_elo = int(headers.get("WhiteElo", "0") or 0)
        b_elo = int(headers.get("BlackElo", "0") or 0)
    except ValueError:
        w_elo = b_elo = 0
    return {
        "game_id": game_id,
        "white_elo": w_elo,
        "black_elo": b_elo,
        "uci_moves": [m.uci() for m in game.mainline_moves()],
    }


def _label_task(
    task: dict,
    depth: int,
    every_nth_ply: int,
    skip_opening_plies: int,
    engines: "queue.Queue[chess.engine.SimpleEngine]",
) -> list[PositionRecord]:
    """Pull an engine from the pool, label the game, return it to the pool.

    The pool is owned by the main thread (see `run`); workers only borrow.
    This avoids thread-local engine lifetimes, which caused ThreadPoolExecutor
    shutdown to hang waiting on subprocess-holding threads.
    """
    engine = engines.get()
    try:
        return _label_with_engine(
            engine, task, depth, every_nth_ply, skip_opening_plies,
        )
    finally:
        engines.put(engine)


def _label_with_engine(
    engine: chess.engine.SimpleEngine,
    task: dict,
    depth: int,
    every_nth_ply: int,
    skip_opening_plies: int,
) -> list[PositionRecord]:
    board = chess.Board()
    out: list[PositionRecord] = []
    for ply, uci in enumerate(task["uci_moves"]):
        board.push(chess.Move.from_uci(uci))
        if ply < skip_opening_plies or ply % every_nth_ply != 0:
            continue
        info = engine.analyse(board, chess.engine.Limit(depth=depth))
        pov = info["score"].pov(board.turn)
        score_cp = pov.score(mate_score=10000) or 0
        out.append(PositionRecord(
            fen=board.fen(),
            score_cp=score_cp,
            game_id=task["game_id"],
            ply=ply,
            white_elo=task["white_elo"],
            black_elo=task["black_elo"],
            side_to_move="w" if board.turn == chess.WHITE else "b",
        ))
    return out


def _flush_shard(
    buffer: list[PositionRecord],
    month: str,
    shard_idx: int,
) -> None:
    out = TRAINING_DIR / f"{month}-shard-{shard_idx:04d}.parquet"
    write_shard(buffer, out)
    print(f"    shard {shard_idx}: {len(buffer)} rows -> {out.name}")


def run(
    month: str,
    max_games: int,
    depth: int,
    min_elo: int,
    every_nth_ply: int,
    skip_opening_plies: int,
    shard_size: int,
    workers: int,
) -> None:
    settings = load_settings()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)

    zip_path = download_dump(month, RAW_DIR)

    if workers <= 0:
        workers = max(1, (os.cpu_count() or 2) - 1)
    print(f"  labeling up to {max_games} games at depth {depth} with {workers} worker(s)")

    buffer: list[PositionRecord] = []
    shard_idx = 0
    total_positions = 0
    games_done = 0

    if workers == 1:
        with chess.engine.SimpleEngine.popen_uci(settings.stockfish_path) as engine:
            for game in iter_elite_games(zip_path, min_elo=min_elo, max_games=max_games):
                for rec in label_game(
                    game, engine, depth=depth,
                    every_nth_ply=every_nth_ply,
                    skip_opening_plies=skip_opening_plies,
                ):
                    buffer.append(rec)
                    if len(buffer) >= shard_size:
                        _flush_shard(buffer, month, shard_idx)
                        total_positions += len(buffer)
                        buffer = []
                        shard_idx += 1
                games_done += 1
                if games_done % 100 == 0:
                    print(f"  progress: {games_done} games, "
                          f"{total_positions + len(buffer)} positions")
    else:
        engine_pool: queue.Queue[chess.engine.SimpleEngine] = queue.Queue()
        for _ in range(workers):
            engine_pool.put(chess.engine.SimpleEngine.popen_uci(settings.stockfish_path))
        try:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = [
                    pool.submit(
                        _label_task,
                        _game_to_task(game),
                        depth, every_nth_ply, skip_opening_plies,
                        engine_pool,
                    )
                    for game in iter_elite_games(
                        zip_path, min_elo=min_elo, max_games=max_games,
                    )
                ]
                for fut in as_completed(futures):
                    for rec in fut.result():
                        buffer.append(rec)
                        if len(buffer) >= shard_size:
                            _flush_shard(buffer, month, shard_idx)
                            total_positions += len(buffer)
                            buffer = []
                            shard_idx += 1
                    games_done += 1
                    if games_done % 100 == 0:
                        print(f"  progress: {games_done} games, "
                              f"{total_positions + len(buffer)} positions",
                              flush=True)
        finally:
            # main thread owns engine lifetime — quit every one before returning
            while not engine_pool.empty():
                try: engine_pool.get_nowait().quit()
                except Exception: pass

    if buffer:
        _flush_shard(buffer, month, shard_idx)
        total_positions += len(buffer)

    print(f"\nDone. {games_done} games, {total_positions} labeled positions under {TRAINING_DIR}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--month", required=True, help="Lichess Elite month, YYYY-MM")
    p.add_argument("--max-games", type=int, default=5000)
    p.add_argument("--depth", type=int, default=8, help="Stockfish depth")
    p.add_argument("--min-elo", type=int, default=2200)
    p.add_argument("--every-nth-ply", type=int, default=4)
    p.add_argument("--skip-opening-plies", type=int, default=10)
    p.add_argument("--shard-size", type=int, default=10000)
    p.add_argument("--workers", type=int, default=0,
                   help="parallel Stockfish workers (0 = cpu_count - 1, 1 = serial)")
    args = p.parse_args()
    run(
        month=args.month,
        max_games=args.max_games,
        depth=args.depth,
        min_elo=args.min_elo,
        every_nth_ply=args.every_nth_ply,
        skip_opening_plies=args.skip_opening_plies,
        workers=args.workers,
        shard_size=args.shard_size,
    )


if __name__ == "__main__":
    main()
