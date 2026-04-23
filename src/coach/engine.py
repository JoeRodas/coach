from __future__ import annotations

from dataclasses import dataclass

import chess
import chess.engine
import chess.pgn


@dataclass
class MoveEval:
    ply: int
    move_san: str
    fen_before: str
    fen_after: str
    score_cp: int
    delta_cp: int


@dataclass
class CriticalMoment:
    ply: int
    move_san: str
    fen_before: str
    best_move_san: str
    score_cp_before: int
    score_cp_after: int
    delta_cp: int


def _score_to_cp(score: chess.engine.PovScore, turn: chess.Color) -> int:
    pov = score.pov(turn)
    return pov.score(mate_score=10000) or 0


def analyze_pgn(pgn_path: str, stockfish_path: str, depth: int) -> list[MoveEval]:
    """Walk every ply of a PGN and record Stockfish evals before/after each move.

    Eval is always from the moving side's POV, so `delta_cp` is negative when
    the side to move worsened their position (i.e. blundered).
    """
    with open(pgn_path) as f:
        game = chess.pgn.read_game(f)
    if game is None:
        raise ValueError(f"No game found in {pgn_path}")

    evals: list[MoveEval] = []
    board = game.board()
    with chess.engine.SimpleEngine.popen_uci(stockfish_path) as engine:
        info_before = engine.analyse(board, chess.engine.Limit(depth=depth))
        score_before = _score_to_cp(info_before["score"], board.turn)
        for ply, move in enumerate(game.mainline_moves()):
            fen_before = board.fen()
            san = board.san(move)
            board.push(move)
            info_after = engine.analyse(board, chess.engine.Limit(depth=depth))
            score_after_opp = _score_to_cp(info_after["score"], board.turn)
            score_after = -score_after_opp  # flip back to mover's POV
            evals.append(
                MoveEval(
                    ply=ply,
                    move_san=san,
                    fen_before=fen_before,
                    fen_after=board.fen(),
                    score_cp=score_after,
                    delta_cp=score_after - score_before,
                )
            )
            score_before = -score_after  # now it's opponent's turn, their POV
    return evals


def critical_moments(
    evals: list[MoveEval],
    stockfish_path: str,
    depth: int,
    side: chess.Color | None = None,
    top_k: int = 3,
    min_drop_cp: int = 100,
) -> list[CriticalMoment]:
    """Return the top_k biggest eval drops, optionally filtered to one side.

    `side` selects moves made by WHITE or BLACK; None keeps both. A drop is a
    negative `delta_cp` from the mover's POV (they got worse after their move).
    """
    candidates = [e for e in evals if e.delta_cp <= -min_drop_cp]
    if side is not None:
        candidates = [e for e in candidates if (e.ply % 2 == 0) == (side == chess.WHITE)]
    candidates.sort(key=lambda e: e.delta_cp)
    picks = candidates[:top_k]

    moments: list[CriticalMoment] = []
    with chess.engine.SimpleEngine.popen_uci(stockfish_path) as engine:
        for e in picks:
            board = chess.Board(e.fen_before)
            info = engine.analyse(board, chess.engine.Limit(depth=depth))
            best_line = info.get("pv") or []
            best_san = board.san(best_line[0]) if best_line else "?"
            moments.append(
                CriticalMoment(
                    ply=e.ply,
                    move_san=e.move_san,
                    fen_before=e.fen_before,
                    best_move_san=best_san,
                    score_cp_before=e.score_cp - e.delta_cp,
                    score_cp_after=e.score_cp,
                    delta_cp=e.delta_cp,
                )
            )
    return moments
