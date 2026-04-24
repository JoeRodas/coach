"""Re-embed the Phase 1 index with the Phase 2 encoder.

Reads FENs from data/index.npz, runs them through the trained encoder, and
writes a parallel index at data/index_encoder.npz with the same position
metadata but encoder-derived embeddings. Leaves the original index intact so
the Phase 1 vs Phase 2 retrieval benchmarks stay head-to-head comparable.

Usage:
    python -m scripts.build_encoder_index
    python -m scripts.build_encoder_index --checkpoint data/checkpoints/encoder.pt
"""
from __future__ import annotations

import argparse
from pathlib import Path

from training.retriever import build_encoder_index


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-index", type=Path, default=Path("data/index.npz"))
    p.add_argument("--checkpoint", type=Path, default=Path("data/checkpoints/encoder.pt"))
    p.add_argument("--out", type=Path, default=Path("data/index_encoder.npz"))
    args = p.parse_args()

    positions, embeddings = build_encoder_index(
        source_index=args.source_index,
        checkpoint_path=args.checkpoint,
        out_path=args.out,
    )
    print(f"re-embedded {len(positions)} positions -> {args.out}  "
          f"({embeddings.shape[1]}-dim)")


if __name__ == "__main__":
    main()
