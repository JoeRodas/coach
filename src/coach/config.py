import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
GAMES_DIR = DATA_DIR / "games"
INDEX_PATH = DATA_DIR / "index.npz"


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str
    stockfish_path: str
    stockfish_depth: int
    claude_model: str
    embedding_model: str


def load_settings() -> Settings:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return Settings(
        anthropic_api_key=api_key,
        stockfish_path=os.environ.get("STOCKFISH_PATH", "/opt/homebrew/bin/stockfish"),
        stockfish_depth=int(os.environ.get("STOCKFISH_DEPTH", "15")),
        claude_model=os.environ.get("CLAUDE_MODEL", "claude-opus-4-7"),
        embedding_model=os.environ.get(
            "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        ),
    )
