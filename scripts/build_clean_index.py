"""Build a leak-scrubbed Phase 1 index for fair head-to-head with Phase 2.

The original Phase 1 context string includes `"{eco} {opening}"` (e.g.
`"A01 Nimzo-Larsen Attack"`). The retrieval benchmark's relevance rule is
`same ECO`, so the sentence-transformer is partially solving the task by
matching ECO substrings in both the indexed docs and the query — a leak the
Phase 2 board-tensor encoder cannot exploit. This script re-embeds the index
with that segment removed, so a query likewise scrubbed of ECO/opening text
gives a comparison the encoder can actually be measured against.

Usage:
    python -m scripts.build_clean_index
    python -m scripts.build_clean_index --out data/index_clean.npz
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from coach.config import load_settings
from coach.retrieval import IndexedPosition, load_index, save_index


def scrub_eco_segment(context: str) -> str:
    """Drop the second pipe-segment (the `"{eco} {opening}"` slot)."""
    parts = [p.strip() for p in context.split("|")]
    if len(parts) < 4:
        return context
    return " | ".join([parts[0]] + parts[2:])


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-index", type=Path, default=Path("data/index.npz"))
    p.add_argument("--out", type=Path, default=Path("data/index_clean.npz"))
    args = p.parse_args()

    settings = load_settings()
    positions, _ = load_index(args.source_index)

    cleaned = [
        IndexedPosition(
            game_id=p.game_id, ply=p.ply, fen=p.fen,
            context=scrub_eco_segment(p.context),
        )
        for p in positions
    ]

    model = SentenceTransformer(settings.embedding_model)
    embeddings = model.encode(
        [p.context for p in cleaned],
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    save_index(args.out, cleaned, np.asarray(embeddings, dtype=np.float32))
    print(f"re-embedded {len(cleaned)} positions (ECO segment scrubbed) -> {args.out}")


if __name__ == "__main__":
    main()
