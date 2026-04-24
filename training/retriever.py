"""Phase 2 retriever: cosine search over encoder-derived embeddings.

Same `search(query_fen, k) -> list[SearchHit]` API surface as Phase 1's
`coach.retrieval.Retriever`, so `coach.agent` can swap one for the other
without touching the tool-calling loop. The only public difference is the
query signature — Phase 1 embeds a text context, Phase 2 embeds a FEN
directly via the trained board-tensor encoder.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch

from coach.retrieval import IndexedPosition, SearchHit, load_index

from .board_tensor import batch_fens
from .encoder import EncoderConfig, PositionEncoder


def load_encoder(checkpoint_path: Path) -> PositionEncoder:
    ckpt = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    model = PositionEncoder(EncoderConfig(**ckpt["config"]))
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    return model


@torch.no_grad()
def embed_fens(
    model: PositionEncoder, fens: list[str], batch_size: int = 128
) -> np.ndarray:
    out: list[np.ndarray] = []
    for i in range(0, len(fens), batch_size):
        chunk = fens[i : i + batch_size]
        grid, scalars = batch_fens(chunk)
        z = model(grid, scalars).cpu().numpy().astype(np.float32)
        out.append(z)
    return np.concatenate(out, axis=0) if out else np.zeros((0, model.cfg.d_out), np.float32)


class EncoderRetriever:
    """FEN -> cosine search against an encoder-embedded index."""

    def __init__(self, checkpoint_path: Path, index_path: Path) -> None:
        self.model = load_encoder(checkpoint_path)
        self.positions, self.embeddings = load_index(index_path)

    def search(self, query_fen: str, k: int = 20) -> list[SearchHit]:
        q = embed_fens(self.model, [query_fen])
        scores = (self.embeddings @ q.T).ravel()
        idx = np.argsort(-scores)[:k]
        return [
            SearchHit(position=self.positions[i], score=float(scores[i]))
            for i in idx
        ]


def build_encoder_index(
    source_index: Path, checkpoint_path: Path, out_path: Path
) -> tuple[list[IndexedPosition], np.ndarray]:
    """Re-embed a Phase 1 index's FENs with the trained encoder."""
    positions, _ = load_index(source_index)
    model = load_encoder(checkpoint_path)
    embeddings = embed_fens(model, [p.fen for p in positions])
    # L2-normalized by the encoder's final step; persist for cosine search.
    np.savez(
        out_path,
        embeddings=embeddings,
        game_id=np.array([p.game_id for p in positions]),
        ply=np.array([p.ply for p in positions]),
        fen=np.array([p.fen for p in positions]),
        context=np.array([p.context for p in positions]),
    )
    return positions, embeddings
