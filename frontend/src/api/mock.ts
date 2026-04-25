// Mock API used in dev and on the staging Pages deploy until the real
// backend lands. Same shape as `api` from ./client so callers swap with
// zero changes. Returns a deterministic AnalysisResponse keyed off the
// PGN's hash so re-runs feel stable, after a small delay so loading
// states are exercisable.

import type {
  AnalysisRequest,
  AnalysisResponse,
  EvalDrop,
  MetricsSnapshot,
  RetrievedGame,
} from "../types/api";

function hashString(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = (h * 31 + s.charCodeAt(i)) | 0;
  }
  return Math.abs(h);
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

const FAKE_DROPS: EvalDrop[] = [
  { ply: 12, san: "Nbd7", evalBefore: 30, evalAfter: -180, severity: "major" },
  { ply: 14, san: "Qe6", evalBefore: -200, evalAfter: -650, severity: "major" },
  { ply: 16, san: "Nxb8", evalBefore: -700, evalAfter: -32000, severity: "blunder" },
];

const FAKE_SOURCES: RetrievedGame[] = [
  {
    gameId: "morphy-vs-anderssen-1858",
    sourceUrl: "https://www.chessgames.com/perl/chessgame?gid=1242886",
    excerpt: "1.e4 e5 2.Nf3 d6 3.d4 Bg4 — same Philidor with early ...Bg4 pin",
    similarity: 0.91,
    themes: ["development tempo", "open lines vs uncastled king"],
  },
  {
    gameId: "kasparov-vs-topalov-1999",
    sourceUrl: "https://www.chessgames.com/perl/chessgame?gid=1011478",
    excerpt: "Sacrifice on b5 to expose the king and infiltrate down the d-file",
    similarity: 0.78,
    themes: ["king-hunt", "rook lift"],
  },
];

export const mockApi = {
  async analyze(body: AnalysisRequest): Promise<AnalysisResponse> {
    await delay(700);
    const seed = hashString(body.pgn + body.playerColor);
    // Stable rotation of the analysis per PGN so the page doesn't feel random
    const colorWord = body.playerColor === "white" ? "White" : "Black";
    const opener = body.question
      ? `On your question — "${body.question}" — the short answer is below.`
      : `Here's where the game turned for ${colorWord}.`;
    return {
      analysis: [
        opener,
        `${colorWord}'s development was already a tempo behind by move 7. The pin on f3 was solved cleanly with Qxf3, leaving the d-file as White's highway. The decisive moment came when the rook arrived on d1 with no defender to challenge it — by then ${colorWord}'s pieces were tactically frozen.`,
        "Master games in this structure (see the cited sources) consistently show that giving up the bishop on f3 needs to be met with rapid kingside development, not headers like ...c6 and ...b5 that open the king further. The pattern to remember: when an opponent castles long against an undeveloped position, every tempo you spend on the queenside is a tempo they spend on your king.",
      ].join("\n\n"),
      evalDrops: FAKE_DROPS,
      sources: FAKE_SOURCES.slice(0, (seed % 2) + 1),
      weakness: {
        theme: "open-file king safety",
        confidence: 0.62,
        rationale:
          "Three of three major errors in this game involved leaving central files open while the king sat on the back rank.",
      },
      modelVersion: "mock-0.1.0",
      latencyMs: 700,
    };
  },

  async metrics(_adminSecret: string): Promise<MetricsSnapshot> {
    await delay(200);
    return {
      evalResults: {
        topKPrecision: { 1: 0.42, 5: 0.71, 10: 0.84 },
        meanLatencyMs: 38,
        p95LatencyMs: 71,
        runAt: new Date().toISOString(),
      },
      productionStats: {
        requestCount24h: 0,
        p50LatencyMs: 0,
        p95LatencyMs: 0,
        errorRate24h: 0,
      },
      modelVersion: "mock-0.1.0",
      baselineDelta: { 1: 0, 5: 0, 10: 0 },
    };
  },
};
