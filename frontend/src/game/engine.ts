// Thin wrapper around chess.js. Centralizes the chess-rules surface so the
// rest of the app talks in terms of high-level concepts (status, moves, FEN)
// instead of poking at the chess.js instance directly.
//
// The wrapper exists for two reasons: (1) the chess.js API surface is large
// and we use ~10% of it; (2) it makes mocking trivial in tests of higher-level
// hooks like useGame.

import { Chess } from "chess.js";

export type GameStatus =
  | "in-progress"
  | "checkmate"
  | "stalemate"
  | "draw_threefold"
  | "draw_50"
  | "draw_insufficient";

export type Side = "w" | "b";

export interface MoveAttempt {
  from: string; // e.g. "e2"
  to: string; // e.g. "e4"
  promotion?: "q" | "r" | "b" | "n";
}

export interface AppliedMove {
  san: string;
  fen: string;
  status: GameStatus;
  sideToMove: Side;
  inCheck: boolean;
}

const STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

function statusOf(c: Chess): GameStatus {
  if (c.isCheckmate()) return "checkmate";
  if (c.isStalemate()) return "stalemate";
  if (c.isThreefoldRepetition()) return "draw_threefold";
  if (c.isInsufficientMaterial()) return "draw_insufficient";
  // chess.js exposes isDraw() which covers 50-move + the above; we check
  // 50-move explicitly so the end-game reason is meaningful.
  if (c.isDraw()) return "draw_50";
  return "in-progress";
}

export class GameEngine {
  private c: Chess;

  constructor(fen: string = STARTING_FEN) {
    this.c = new Chess(fen);
  }

  /** Reconstruct an engine (with full move history) from a PGN string. */
  static fromPgn(pgn: string): GameEngine {
    const e = new GameEngine();
    try {
      e.c.loadPgn(pgn);
    } catch {
      // Malformed PGN — fall back to starting position rather than throwing.
      e.c = new Chess(STARTING_FEN);
    }
    return e;
  }

  /** Play a SAN move on the canonical board; preserves history. */
  playSan(san: string): AppliedMove | null {
    try {
      const result = this.c.move(san);
      if (!result) return null;
      return {
        san: result.san,
        fen: this.c.fen(),
        status: statusOf(this.c),
        sideToMove: this.c.turn(),
        inCheck: this.c.inCheck(),
      };
    } catch {
      return null;
    }
  }

  fen(): string {
    return this.c.fen();
  }

  pgn(): string {
    return this.c.pgn();
  }

  history(): string[] {
    return this.c.history();
  }

  sideToMove(): Side {
    return this.c.turn();
  }

  status(): GameStatus {
    return statusOf(this.c);
  }

  inCheck(): boolean {
    return this.c.inCheck();
  }

  isOver(): boolean {
    return this.status() !== "in-progress";
  }

  legalMovesFrom(square: string): string[] {
    return this.c.moves({ square: square as never, verbose: true }).map((m) => m.to as string);
  }

  /** Try a move. Returns null if illegal (caller stays on prior position). */
  tryMove(m: MoveAttempt): AppliedMove | null {
    try {
      const result = this.c.move({
        from: m.from,
        to: m.to,
        promotion: m.promotion ?? "q",
      });
      if (!result) return null;
      return {
        san: result.san,
        fen: this.c.fen(),
        status: statusOf(this.c),
        sideToMove: this.c.turn(),
        inCheck: this.c.inCheck(),
      };
    } catch {
      return null;
    }
  }

  /** Random legal move — used by the mock AI in PR-5. Returns null if no moves. */
  randomMove(): AppliedMove | null {
    const moves = this.c.moves({ verbose: true });
    if (moves.length === 0) return null;
    const pick = moves[Math.floor(Math.random() * moves.length)];
    if (!pick) return null;
    return this.tryMove({ from: pick.from, to: pick.to, promotion: pick.promotion as never });
  }
}

export const STARTING_POSITION_FEN = STARTING_FEN;
