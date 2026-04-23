from __future__ import annotations

import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

import chess
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from coach.agent import AgentContext, run
from coach.config import INDEX_PATH, load_settings
from coach.retrieval import Retriever

STATIC_DIR = Path(__file__).parent / "static"

_state: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = load_settings()
    if not INDEX_PATH.exists():
        raise RuntimeError(
            f"Missing retrieval index at {INDEX_PATH}. Run scripts/build_index.py."
        )
    _state["settings"] = settings
    _state["retriever"] = Retriever(settings.embedding_model, INDEX_PATH)
    yield


app = FastAPI(title="Coach", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class AnalyzeRequest(BaseModel):
    pgn: str
    side: str = "white"
    question: str = "Where did I go wrong in this game?"


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest) -> dict[str, str]:
    if req.side not in {"white", "black"}:
        raise HTTPException(422, "side must be 'white' or 'black'")
    if not req.pgn.strip():
        raise HTTPException(422, "pgn is empty")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".pgn", delete=False) as f:
        f.write(req.pgn)
        pgn_path = f.name

    try:
        ctx = AgentContext(
            pgn_path=pgn_path,
            user_side=chess.WHITE if req.side == "white" else chess.BLACK,
            settings=_state["settings"],
            retriever=_state["retriever"],
        )
        user_msg = f"{req.question}\n\nI played as {req.side}."
        answer = run(user_msg, ctx)
    finally:
        Path(pgn_path).unlink(missing_ok=True)

    return {"answer": answer}
