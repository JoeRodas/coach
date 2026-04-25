import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { type PersistedLiveGame, clearLive, loadLive, saveLive } from "./persist";

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  localStorage.clear();
});

describe("persist (live game)", () => {
  it("loadLive returns null when nothing is stored", () => {
    expect(loadLive()).toBeNull();
  });

  it("saveLive then loadLive round-trips", () => {
    const g: PersistedLiveGame = {
      pgn: "1. e4 e5",
      userColor: "w",
      aiSkill: 12,
      startedAt: "2026-04-24T20:00:00.000Z",
    };
    saveLive(g);
    expect(loadLive()).toEqual(g);
  });

  it("clearLive removes the stored game", () => {
    saveLive({
      pgn: "1. e4",
      userColor: "b",
      aiSkill: 5,
      startedAt: "2026-04-24T20:00:00.000Z",
    });
    clearLive();
    expect(loadLive()).toBeNull();
  });

  it("loadLive returns null for malformed JSON", () => {
    localStorage.setItem("coach.game.live", "not json");
    expect(loadLive()).toBeNull();
  });

  it("loadLive returns null for valid JSON missing required fields", () => {
    localStorage.setItem("coach.game.live", JSON.stringify({ pgn: "1. e4" }));
    expect(loadLive()).toBeNull();
  });

  it("loadLive returns null for invalid userColor", () => {
    localStorage.setItem(
      "coach.game.live",
      JSON.stringify({
        pgn: "1. e4",
        userColor: "white", // should be "w"
        aiSkill: 10,
        startedAt: "2026-04-24T20:00:00.000Z",
      }),
    );
    expect(loadLive()).toBeNull();
  });
});
