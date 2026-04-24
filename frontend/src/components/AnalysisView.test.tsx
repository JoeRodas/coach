import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { AnalysisResponse } from "../types/api";
import AnalysisView from "./AnalysisView";

const FIXTURE: AnalysisResponse = {
  analysis: "First paragraph.\n\nSecond paragraph.\n\nThird paragraph.",
  evalDrops: [{ ply: 12, san: "Nbd7", evalBefore: 30, evalAfter: -180, severity: "major" }],
  sources: [
    {
      gameId: "test-game-1",
      excerpt: "Some excerpt",
      similarity: 0.9,
      themes: ["theme-a"],
    },
  ],
  weakness: {
    theme: "open-file king safety",
    confidence: 0.62,
    rationale: "Three of three errors on open files.",
  },
  modelVersion: "test-0.0.0",
  latencyMs: 42,
};

describe("AnalysisView", () => {
  it("renders all three commentary paragraphs", () => {
    render(<AnalysisView data={FIXTURE} />);
    expect(screen.getByText("First paragraph.")).toBeInTheDocument();
    expect(screen.getByText("Second paragraph.")).toBeInTheDocument();
    expect(screen.getByText("Third paragraph.")).toBeInTheDocument();
  });

  it("renders the weakness pattern when present", () => {
    render(<AnalysisView data={FIXTURE} />);
    expect(screen.getByText(/open-file king safety/i)).toBeInTheDocument();
  });

  it("omits the weakness section when null", () => {
    render(<AnalysisView data={{ ...FIXTURE, weakness: null }} />);
    expect(screen.queryByRole("heading", { name: /pattern of mistakes/i })).toBeNull();
  });

  it("renders the eval-drop list", () => {
    render(<AnalysisView data={FIXTURE} />);
    expect(screen.getByText(/Nbd7/)).toBeInTheDocument();
  });

  it("renders the sources accordion", () => {
    render(<AnalysisView data={FIXTURE} />);
    expect(screen.getByText(/test-game-1/)).toBeInTheDocument();
  });

  it("uses aria-live so screen readers announce new analysis", () => {
    const { container } = render(<AnalysisView data={FIXTURE} />);
    const live = container.querySelector('[aria-live="polite"]');
    expect(live).not.toBeNull();
  });
});
