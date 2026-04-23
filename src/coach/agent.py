from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import chess
from anthropic import Anthropic

from coach.config import Settings
from coach.engine import CriticalMoment, analyze_pgn, critical_moments
from coach.retrieval import Retriever, format_context

TOOLS: list[dict[str, Any]] = [
    {
        "name": "identify_critical_moments",
        "description": (
            "Run Stockfish over the user's PGN and return the top-k moves where "
            "the eval dropped the most for the requested side. Use this first."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "side": {"type": "string", "enum": ["white", "black"]},
                "top_k": {"type": "integer", "default": 3},
            },
            "required": ["side"],
        },
    },
    {
        "name": "retrieve_similar_positions",
        "description": (
            "Given a FEN, return up to k master-game positions that are similar "
            "by embedding. Use this after identifying a critical moment to ground "
            "the explanation in known master play."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "fen": {"type": "string"},
                "k": {"type": "integer", "default": 5},
            },
            "required": ["fen"],
        },
    },
]

SYSTEM_PROMPT = """You are Coach, a chess coach for club players.

Your job: given a PGN the user just played, explain where they went wrong, why,
and what to study. Always ground your answer in (a) Stockfish analysis from
`identify_critical_moments` and (b) master-game positions from
`retrieve_similar_positions`. Do not invent moves or claims. If a tool returns
no critical moments, say so honestly.

Respond in three short paragraphs:
1. What happened — cite ply and SAN of the biggest drop.
2. Why it was wrong — reference the retrieved master position(s) by game_id.
3. What to study next — one concrete recommendation.
"""


@dataclass
class AgentContext:
    pgn_path: str
    user_side: chess.Color
    settings: Settings
    retriever: Retriever


def _run_tool(name: str, args: dict[str, Any], ctx: AgentContext) -> str:
    if name == "identify_critical_moments":
        side = chess.WHITE if args["side"] == "white" else chess.BLACK
        top_k = args.get("top_k", 3)
        evals = analyze_pgn(ctx.pgn_path, ctx.settings.stockfish_path, ctx.settings.stockfish_depth)
        moments = critical_moments(
            evals, ctx.settings.stockfish_path, ctx.settings.stockfish_depth,
            side=side, top_k=top_k,
        )
        return json.dumps([_moment_to_dict(m) for m in moments])

    if name == "retrieve_similar_positions":
        board = chess.Board(args["fen"])
        context = format_context(white="?", black="?", eco="", opening="", board=board)
        hits = ctx.retriever.search(context, k=args.get("k", 5))
        return json.dumps([
            {"game_id": h.position.game_id, "ply": h.position.ply,
             "fen": h.position.fen, "score": h.score}
            for h in hits
        ])

    return json.dumps({"error": f"unknown tool {name}"})


def _moment_to_dict(m: CriticalMoment) -> dict[str, Any]:
    return {
        "ply": m.ply,
        "move_san": m.move_san,
        "fen_before": m.fen_before,
        "best_move_san": m.best_move_san,
        "score_cp_before": m.score_cp_before,
        "score_cp_after": m.score_cp_after,
        "delta_cp": m.delta_cp,
    }


def run(user_message: str, ctx: AgentContext, max_turns: int = 6) -> str:
    client = Anthropic(api_key=ctx.settings.anthropic_api_key)
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]

    for _ in range(max_turns):
        resp = client.messages.create(
            model=ctx.settings.claude_model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason != "tool_use":
            return "".join(
                block.text for block in resp.content if getattr(block, "type", "") == "text"
            )

        tool_results = []
        for block in resp.content:
            if getattr(block, "type", "") != "tool_use":
                continue
            result = _run_tool(block.name, block.input, ctx)
            tool_results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": result}
            )
        messages.append({"role": "user", "content": tool_results})

    raise RuntimeError("agent exceeded max_turns without a final answer")
