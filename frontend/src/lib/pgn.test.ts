import { describe, expect, it } from "vitest";
import { SAMPLE_PGN } from "../data/sampleGame";
import { validatePgn } from "./pgn";

describe("validatePgn", () => {
  it("rejects empty input", () => {
    const r = validatePgn("");
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.reason).toMatch(/paste a game/i);
  });

  it("rejects whitespace-only", () => {
    expect(validatePgn("   \n\t  ").ok).toBe(false);
  });

  it("rejects input with no move-number/SAN pair", () => {
    const r = validatePgn("This is just plain text with no chess notation.");
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.reason).toMatch(/moves/i);
  });

  it("accepts a move-list-only PGN (no headers)", () => {
    expect(validatePgn("1. e4 e5 2. Nf3 Nc6 3. Bb5 a6").ok).toBe(true);
  });

  it("accepts the bundled sample game", () => {
    expect(validatePgn(SAMPLE_PGN).ok).toBe(true);
  });
});
