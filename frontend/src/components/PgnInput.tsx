// Form for the analyze flow: PGN textarea, color picker, optional question,
// "Try a sample game", and an Analyze button. Validation runs on submit and
// surfaces inline; the parent handles the actual mutation.

import { useState } from "react";
import { SAMPLE_PGN, SAMPLE_PLAYER_COLOR } from "../data/sampleGame";
import { validatePgn } from "../lib/pgn";
import type { AnalysisRequest } from "../types/api";

interface Props {
  onSubmit: (req: AnalysisRequest) => void;
  isSubmitting: boolean;
}

export default function PgnInput({ onSubmit, isSubmitting }: Props) {
  const [pgn, setPgn] = useState("");
  const [playerColor, setPlayerColor] = useState<"white" | "black">("white");
  const [question, setQuestion] = useState("");
  const [error, setError] = useState<string | null>(null);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const v = validatePgn(pgn);
    if (!v.ok) {
      setError(v.reason);
      return;
    }
    setError(null);
    onSubmit({
      pgn: pgn.trim(),
      playerColor,
      question: question.trim() || undefined,
    });
  }

  function loadSample() {
    setPgn(SAMPLE_PGN);
    setPlayerColor(SAMPLE_PLAYER_COLOR);
    setQuestion("");
    setError(null);
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-4 rounded-lg border border-slate-200 bg-white p-6"
    >
      <div>
        <div className="flex items-baseline justify-between">
          <label htmlFor="pgn" className="block text-sm font-medium text-slate-700">
            PGN
          </label>
          <button
            type="button"
            onClick={loadSample}
            className="text-sm text-indigo-700 hover:text-indigo-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
          >
            Try a sample game
          </button>
        </div>
        <textarea
          id="pgn"
          name="pgn"
          rows={10}
          value={pgn}
          onChange={(e) => setPgn(e.target.value)}
          placeholder="[Event &quot;…&quot;]&#10;1. e4 e5 2. Nf3 …"
          aria-invalid={error !== null}
          aria-describedby={error ? "pgn-error" : undefined}
          className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 font-mono text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
        {error ? (
          <p id="pgn-error" className="mt-1 text-sm text-red-700">
            {error}
          </p>
        ) : null}
      </div>

      <fieldset>
        <legend className="text-sm font-medium text-slate-700">You played</legend>
        <div className="mt-1 flex gap-4">
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="radio"
              name="playerColor"
              value="white"
              checked={playerColor === "white"}
              onChange={() => setPlayerColor("white")}
              className="h-4 w-4 text-indigo-600 focus:ring-indigo-500"
            />
            White
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="radio"
              name="playerColor"
              value="black"
              checked={playerColor === "black"}
              onChange={() => setPlayerColor("black")}
              className="h-4 w-4 text-indigo-600 focus:ring-indigo-500"
            />
            Black
          </label>
        </div>
      </fieldset>

      <div>
        <label htmlFor="question" className="block text-sm font-medium text-slate-700">
          Question <span className="text-slate-400">(optional)</span>
        </label>
        <input
          id="question"
          name="question"
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. Where did I go wrong?"
          className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
      </div>

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={isSubmitting}
          className="inline-flex items-center rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 disabled:cursor-not-allowed disabled:bg-indigo-400"
        >
          {isSubmitting ? "Analyzing…" : "Analyze"}
        </button>
      </div>
    </form>
  );
}
