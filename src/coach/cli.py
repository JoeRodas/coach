from __future__ import annotations

from pathlib import Path

import chess
import click

from coach.agent import AgentContext, run
from coach.config import INDEX_PATH, load_settings
from coach.retrieval import Retriever


@click.group()
def main() -> None:
    """Coach — conversational chess coach CLI."""


@main.command()
@click.argument("pgn_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--side", type=click.Choice(["white", "black"]), default="white")
@click.option(
    "--question",
    default="Where did I go wrong in this game? Give me three paragraphs.",
    help="Question to ask Coach about the game.",
)
def analyze(pgn_path: Path, side: str, question: str) -> None:
    """Analyze a single PGN and print Coach's response."""
    settings = load_settings()
    if not INDEX_PATH.exists():
        raise click.ClickException(
            f"No retrieval index at {INDEX_PATH}. Run scripts/build_index.py first."
        )
    retriever = Retriever(settings.embedding_model, INDEX_PATH)
    ctx = AgentContext(
        pgn_path=str(pgn_path),
        user_side=chess.WHITE if side == "white" else chess.BLACK,
        settings=settings,
        retriever=retriever,
    )
    user_msg = f"{question}\n\nI played as {side}. The PGN is loaded at {pgn_path}."
    click.echo(run(user_msg, ctx))


if __name__ == "__main__":
    main()
