from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import chess.pgn
import numpy as np
from sentence_transformers import SentenceTransformer


@dataclass
class IndexedPosition:
    game_id: str
    ply: int
    fen: str
    context: str  # short textual rendering used for embedding


@dataclass
class SearchHit:
    position: IndexedPosition
    score: float


def format_context(
    white: str, black: str, eco: str, opening: str, board: chess.Board
) -> str:
    """Render a short descriptor used as the embedding input.

    Phase 1 uses off-the-shelf sentence-transformers, so we embed a text
    description. Both the index and query sides must call this with the same
    template so the embeddings land in the same space. Phase 2 replaces this
    with a learned position encoder.
    """
    return (
        f"{white} vs {black} | {eco} {opening} | move {board.fullmove_number} "
        f"{'white' if board.turn == chess.WHITE else 'black'} to move | "
        f"FEN {board.fen()}"
    )


def position_context(game: chess.pgn.Game, board: chess.Board) -> str:
    headers = game.headers
    return format_context(
        white=headers.get("White", "?"),
        black=headers.get("Black", "?"),
        eco=headers.get("ECO", ""),
        opening=headers.get("Opening", ""),
        board=board,
    )


def build_index(games_dir: Path, model_name: str) -> tuple[list[IndexedPosition], np.ndarray]:
    model = SentenceTransformer(model_name)
    positions: list[IndexedPosition] = []
    for pgn_path in sorted(games_dir.glob("*.pgn")):
        with open(pgn_path) as f:
            while True:
                game = chess.pgn.read_game(f)
                if game is None:
                    break
                board = game.board()
                game_id = pgn_path.stem + "#" + (game.headers.get("Site", "") or "")
                for ply, move in enumerate(game.mainline_moves()):
                    board.push(move)
                    if ply % 4 != 0:  # subsample every 4th ply to keep index small
                        continue
                    positions.append(
                        IndexedPosition(
                            game_id=game_id,
                            ply=ply,
                            fen=board.fen(),
                            context=position_context(game, board),
                        )
                    )
    if not positions:
        raise RuntimeError(f"No positions extracted from {games_dir}")

    embeddings = model.encode(
        [p.context for p in positions],
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    return positions, np.asarray(embeddings, dtype=np.float32)


def save_index(path: Path, positions: list[IndexedPosition], embeddings: np.ndarray) -> None:
    np.savez(
        path,
        embeddings=embeddings,
        game_id=np.array([p.game_id for p in positions]),
        ply=np.array([p.ply for p in positions]),
        fen=np.array([p.fen for p in positions]),
        context=np.array([p.context for p in positions]),
    )


def load_index(path: Path) -> tuple[list[IndexedPosition], np.ndarray]:
    data = np.load(path, allow_pickle=False)
    positions = [
        IndexedPosition(
            game_id=str(gid), ply=int(ply), fen=str(fen), context=str(ctx)
        )
        for gid, ply, fen, ctx in zip(
            data["game_id"], data["ply"], data["fen"], data["context"], strict=True
        )
    ]
    return positions, data["embeddings"]


class Retriever:
    def __init__(self, model_name: str, index_path: Path) -> None:
        self.model = SentenceTransformer(model_name)
        self.positions, self.embeddings = load_index(index_path)

    def search(self, query_context: str, k: int = 20) -> list[SearchHit]:
        q = self.model.encode([query_context], normalize_embeddings=True)
        scores = (self.embeddings @ q.T).ravel()
        idx = np.argsort(-scores)[:k]
        return [SearchHit(position=self.positions[i], score=float(scores[i])) for i in idx]
