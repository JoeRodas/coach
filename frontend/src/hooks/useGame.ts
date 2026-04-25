// Orchestrates the chess engine, AI, and persistence. The PlayPage
// renders state from this hook and calls back into it for user actions.
//
// State machine (PR-5 minimum):
//   idle -> awaiting-user-move -> awaiting-ai-move -> awaiting-user-move ...
//                            \-> game-over (terminal)
//
// PR-7 will add resign / draw-offer / timeout transitions.

import { useCallback, useEffect, useRef, useState } from "react";
import { mockAi } from "../game/ai";
import {
  type AppliedMove,
  GameEngine,
  type GameStatus,
  type MoveAttempt,
  type Side,
} from "../game/engine";
import { clearLive, loadLive, saveLive } from "../game/persist";

export interface NewGameOptions {
  userColor: "w" | "b";
  aiSkill: number;
}

export interface UseGameState {
  fen: string;
  history: string[];
  status: GameStatus;
  sideToMove: Side;
  inCheck: boolean;
  userColor: "w" | "b";
  aiSkill: number;
  isAiThinking: boolean;
  lastAiPonderMs: number | null;
}

const DEFAULT_OPTIONS: NewGameOptions = { userColor: "w", aiSkill: 10 };

export function useGame() {
  // Engine instance lives in a ref so React re-renders don't reset it.
  const engineRef = useRef<GameEngine>(new GameEngine());
  const [version, setVersion] = useState(0);
  const bump = useCallback(() => setVersion((v) => v + 1), []);

  const [opts, setOpts] = useState<NewGameOptions>(DEFAULT_OPTIONS);
  const [isAiThinking, setIsAiThinking] = useState(false);
  const [lastAiPonderMs, setLastAiPonderMs] = useState<number | null>(null);
  const [hydrated, setHydrated] = useState(false);

  // Hydrate from localStorage on first render. If a saved game exists,
  // reconstruct the engine from its PGN so move history is preserved.
  useEffect(() => {
    if (hydrated) return;
    const saved = loadLive();
    if (saved) {
      engineRef.current = GameEngine.fromPgn(saved.pgn);
      setOpts({ userColor: saved.userColor, aiSkill: saved.aiSkill });
    }
    setHydrated(true);
    bump();
  }, [hydrated, bump]);

  // Persist after every engine change. `version` is the manual re-run
  // signal — bumped by bump() whenever the engine ref mutates. Biome's
  // exhaustive-deps rule can't see through the ref, so we silence it.
  // biome-ignore lint/correctness/useExhaustiveDependencies: version is the engine-change trigger
  useEffect(() => {
    if (!hydrated) return;
    const e = engineRef.current;
    if (e.history().length === 0) {
      clearLive();
      return;
    }
    saveLive({
      pgn: e.pgn(),
      userColor: opts.userColor,
      aiSkill: opts.aiSkill,
      startedAt: new Date().toISOString(),
    });
  }, [version, opts.userColor, opts.aiSkill, hydrated]);

  const aiMove = useCallback(async () => {
    const e = engineRef.current;
    if (e.isOver()) return;
    setIsAiThinking(true);
    try {
      const res = await mockAi.move({ fen: e.fen(), skillLevel: opts.aiSkill });
      // Replay the AI's chosen move (SAN) on the canonical engine so
      // history() and pgn() stay in sync. The mock AI computes against
      // its own throwaway engine; we don't trust its FEN as a shortcut.
      const applied = e.playSan(res.move.san);
      if (!applied) {
        // Defensive: if SAN parse fails for any reason, reset engine to the
        // mock's claimed position. PR-6's real Stockfish backend should
        // make this unreachable.
        engineRef.current = new GameEngine(res.move.fen);
      }
      setLastAiPonderMs(res.ponderMs);
      bump();
    } finally {
      setIsAiThinking(false);
    }
  }, [opts.aiSkill, bump]);

  // After a user move, if it's the AI's turn and the game is on, kick off
  // the AI. `version` bumps whenever the engine ref mutates; biome can't
  // see through the ref so we silence the rule.
  // biome-ignore lint/correctness/useExhaustiveDependencies: version is the engine-change trigger
  useEffect(() => {
    if (!hydrated) return;
    const e = engineRef.current;
    if (e.isOver()) return;
    if (e.sideToMove() !== opts.userColor && !isAiThinking) {
      void aiMove();
    }
  }, [version, hydrated, opts.userColor, isAiThinking, aiMove]);

  const submitUserMove = useCallback(
    (m: MoveAttempt): AppliedMove | null => {
      const e = engineRef.current;
      if (e.isOver()) return null;
      if (e.sideToMove() !== opts.userColor) return null;
      const result = e.tryMove(m);
      if (result) bump();
      return result;
    },
    [opts.userColor, bump],
  );

  const newGame = useCallback(
    (next: NewGameOptions) => {
      engineRef.current = new GameEngine();
      setOpts(next);
      setLastAiPonderMs(null);
      setIsAiThinking(false);
      clearLive();
      bump();
    },
    [bump],
  );

  const e = engineRef.current;
  const state: UseGameState = {
    fen: e.fen(),
    history: e.history(),
    status: e.status(),
    sideToMove: e.sideToMove(),
    inCheck: e.inCheck(),
    userColor: opts.userColor,
    aiSkill: opts.aiSkill,
    isAiThinking,
    lastAiPonderMs,
  };

  return { state, submitUserMove, newGame };
}
