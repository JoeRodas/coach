"""Build the Phase 1 retrieval index from data/games/*.pgn.

Usage: python scripts/build_index.py
"""
from __future__ import annotations

from coach.config import GAMES_DIR, INDEX_PATH, load_settings
from coach.retrieval import build_index, save_index


def main() -> None:
    settings = load_settings()
    print(f"Building index from {GAMES_DIR} using {settings.embedding_model}")
    positions, embeddings = build_index(GAMES_DIR, settings.embedding_model)
    save_index(INDEX_PATH, positions, embeddings)
    print(f"Wrote {len(positions)} positions to {INDEX_PATH}")


if __name__ == "__main__":
    main()
