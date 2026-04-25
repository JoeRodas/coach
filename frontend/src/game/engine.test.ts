import { describe, expect, it } from "vitest";
import { GameEngine, STARTING_POSITION_FEN } from "./engine";

describe("GameEngine", () => {
  it("starts in the standard chess position", () => {
    const e = new GameEngine();
    expect(e.fen()).toBe(STARTING_POSITION_FEN);
    expect(e.sideToMove()).toBe("w");
    expect(e.status()).toBe("in-progress");
    expect(e.history()).toEqual([]);
  });

  it("plays a legal opening move and updates state", () => {
    const e = new GameEngine();
    const r = e.tryMove({ from: "e2", to: "e4" });
    expect(r).not.toBeNull();
    expect(r?.san).toBe("e4");
    expect(e.sideToMove()).toBe("b");
    expect(e.history()).toEqual(["e4"]);
  });

  it("rejects an illegal move and leaves position unchanged", () => {
    const e = new GameEngine();
    const r = e.tryMove({ from: "e2", to: "e5" });
    expect(r).toBeNull();
    expect(e.sideToMove()).toBe("w");
    expect(e.history()).toEqual([]);
  });

  it("detects checkmate via Scholar's Mate", () => {
    const e = new GameEngine();
    e.tryMove({ from: "e2", to: "e4" });
    e.tryMove({ from: "e7", to: "e5" });
    e.tryMove({ from: "f1", to: "c4" });
    e.tryMove({ from: "b8", to: "c6" });
    e.tryMove({ from: "d1", to: "h5" });
    e.tryMove({ from: "g8", to: "f6" });
    e.tryMove({ from: "h5", to: "f7" });
    expect(e.status()).toBe("checkmate");
    expect(e.isOver()).toBe(true);
  });

  it("playSan lands a move identical to from/to/promotion", () => {
    const a = new GameEngine();
    const b = new GameEngine();
    a.tryMove({ from: "e2", to: "e4" });
    b.playSan("e4");
    expect(a.fen()).toBe(b.fen());
    expect(a.history()).toEqual(b.history());
  });

  it("randomMove returns a valid move from a fresh position", () => {
    const e = new GameEngine();
    const r = e.randomMove();
    expect(r).not.toBeNull();
    expect(e.history().length).toBe(1);
  });

  it("fromPgn reconstructs an engine with full move history", () => {
    const a = new GameEngine();
    a.tryMove({ from: "e2", to: "e4" });
    a.tryMove({ from: "c7", to: "c5" });
    a.tryMove({ from: "g1", to: "f3" });
    const b = GameEngine.fromPgn(a.pgn());
    expect(b.fen()).toBe(a.fen());
    expect(b.history()).toEqual(a.history());
  });

  it("fromPgn falls back to starting position on garbage input", () => {
    const e = GameEngine.fromPgn("not a real pgn");
    expect(e.fen()).toBe(STARTING_POSITION_FEN);
  });

  it("legalMovesFrom lists targets for a piece", () => {
    const e = new GameEngine();
    const targets = e.legalMovesFrom("e2");
    expect(targets.sort()).toEqual(["e3", "e4"]);
  });
});
