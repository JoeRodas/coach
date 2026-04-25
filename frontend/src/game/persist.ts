// localStorage I/O for an in-progress game. PR-5 stores only the live
// game; PR-8 will add a separate `coach.history` key for completed games
// per Amendment §D.4.6.
//
// We store the full PGN (which is enough to reconstruct the position via
// chess.js) plus a couple of session settings. Storing FEN alone would
// lose move history, which we want for the post-game review surface.

const KEY_LIVE = "coach.game.live";

export interface PersistedLiveGame {
  pgn: string;
  userColor: "w" | "b";
  aiSkill: number; // 1..20, ignored by mock AI in PR-5
  startedAt: string; // ISO
}

export function loadLive(): PersistedLiveGame | null {
  if (typeof localStorage === "undefined") return null;
  const raw = localStorage.getItem(KEY_LIVE);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    if (
      typeof parsed?.pgn === "string" &&
      (parsed.userColor === "w" || parsed.userColor === "b") &&
      typeof parsed.aiSkill === "number" &&
      typeof parsed.startedAt === "string"
    ) {
      return parsed as PersistedLiveGame;
    }
    return null;
  } catch {
    return null;
  }
}

export function saveLive(g: PersistedLiveGame): void {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(KEY_LIVE, JSON.stringify(g));
}

export function clearLive(): void {
  if (typeof localStorage === "undefined") return;
  localStorage.removeItem(KEY_LIVE);
}
