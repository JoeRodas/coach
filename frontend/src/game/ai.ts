// Mock AI used in PR-5 — picks a random legal move after a small delay so
// the user sees their move land, then a thinking pause, then the AI's
// reply. Real Stockfish backend lands in PR-6 (POST /api/engine/move per
// REQUIREMENTS §D.7).
//
// The signature below is the contract PR-6 must conform to; only the
// implementation swaps.

import { type AppliedMove, GameEngine } from "./engine";

export interface AiMoveRequest {
  fen: string;
  skillLevel: number; // 1..20
}

export interface AiMoveResponse {
  move: AppliedMove;
  ponderMs: number;
}

export interface AiClient {
  move(req: AiMoveRequest): Promise<AiMoveResponse>;
}

const MOCK_PONDER_MS = 600;

export const mockAi: AiClient = {
  async move({ fen }) {
    const start = Date.now();
    await new Promise((resolve) => setTimeout(resolve, MOCK_PONDER_MS));
    const local = new GameEngine(fen);
    const m = local.randomMove();
    if (!m) throw new Error("Mock AI: no legal moves from position");
    return { move: m, ponderMs: Date.now() - start };
  },
};
