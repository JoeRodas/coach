"""Parquet-backed dataset of positive pairs for contrastive training.

A "pair" is two positions we want the encoder to map close together. Phase 2
ships a single positive strategy: **adjacent retained plies from the same
game**. The ingest pipeline keeps every Nth ply, so "adjacent" here means
consecutive rows in a game's ply-sorted list — typically 4–8 plies apart in
real time, which captures local positional continuity without the trivial
"same move, one half-move later" shortcut.

Eval-matched cross-game pairs are a planned second positive strategy; it will
slot into PositivePairIndex.build() alongside the adjacency pass.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pyarrow.parquet as pq
import torch
from torch.utils.data import Dataset

from .board_tensor import fen_to_scalars, fen_to_tensor


@dataclass
class Row:
    fen: str
    score_cp: int
    game_id: str
    ply: int


def _load_shards(shard_dir: Path) -> list[Row]:
    rows: list[Row] = []
    for p in sorted(shard_dir.glob("*.parquet")):
        d = pq.read_table(p, columns=["fen", "score_cp", "game_id", "ply"]).to_pydict()
        for i in range(len(d["fen"])):
            rows.append(Row(
                fen=d["fen"][i],
                score_cp=int(d["score_cp"][i]),
                game_id=d["game_id"][i],
                ply=int(d["ply"][i]),
            ))
    return rows


def _adjacent_pairs(rows: list[Row]) -> list[tuple[int, int]]:
    """Indices of adjacent-ply pairs within each game."""
    by_game: dict[str, list[int]] = {}
    for i, r in enumerate(rows):
        by_game.setdefault(r.game_id, []).append(i)
    pairs: list[tuple[int, int]] = []
    for idxs in by_game.values():
        idxs_sorted = sorted(idxs, key=lambda i: rows[i].ply)
        for a, b in zip(idxs_sorted, idxs_sorted[1:]):
            pairs.append((a, b))
    return pairs


class PositionPairDataset(Dataset):
    """Map-style dataset of (anchor, positive) position-tensor pairs."""

    def __init__(self, shard_dir: Path) -> None:
        self.rows = _load_shards(shard_dir)
        if not self.rows:
            raise RuntimeError(f"No rows found in {shard_dir}")
        self.pairs = _adjacent_pairs(self.rows)
        if not self.pairs:
            raise RuntimeError(
                f"No positive pairs formed from {len(self.rows)} rows. "
                f"Each game needs ≥2 retained plies."
            )

    def __len__(self) -> int:
        return len(self.pairs)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        a, b = self.pairs[idx]
        fa, fb = self.rows[a].fen, self.rows[b].fen
        return (fen_to_tensor(fa), fen_to_scalars(fa),
                fen_to_tensor(fb), fen_to_scalars(fb))

    def stats(self) -> dict:
        games = {r.game_id for r in self.rows}
        return {
            "rows": len(self.rows),
            "games": len(games),
            "pairs": len(self.pairs),
            "pairs_per_game": round(len(self.pairs) / max(1, len(games)), 2),
        }
