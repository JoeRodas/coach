// Shared API types. Mirror REQUIREMENTS.md §8 verbatim.
// Backend Pydantic schemas in backend/app/schemas/ must produce JSON that
// parses cleanly into these. A snapshot test in CI (deferred until CI
// exists) will enforce the contract.

export interface AnalysisRequest {
  pgn: string;
  playerColor: "white" | "black";
  question?: string;
}

export interface EvalDrop {
  ply: number;
  san: string;
  evalBefore: number; // centipawns, + = white advantage
  evalAfter: number;
  severity: "minor" | "major" | "blunder";
}

export interface RetrievedGame {
  gameId: string;
  sourceUrl?: string;
  excerpt: string; // short PGN snippet
  similarity: number; // cosine, 0..1
  themes: string[];
}

export interface WeaknessPrediction {
  theme: string;
  confidence: number; // 0..1
  rationale: string;
}

export interface AnalysisResponse {
  analysis: string; // the three grounded paragraphs
  evalDrops: EvalDrop[];
  sources: RetrievedGame[];
  weakness: WeaknessPrediction | null;
  modelVersion: string;
  latencyMs: number;
}

export interface MetricsSnapshot {
  evalResults: {
    topKPrecision: Record<number, number>; // {1: 0.42, 5: 0.71, 10: 0.84}
    meanLatencyMs: number;
    p95LatencyMs: number;
    runAt: string; // ISO datetime
  };
  productionStats: {
    requestCount24h: number;
    p50LatencyMs: number;
    p95LatencyMs: number;
    errorRate24h: number;
  };
  modelVersion: string;
  baselineDelta: Record<number, number>; // top-K change vs baseline
}
