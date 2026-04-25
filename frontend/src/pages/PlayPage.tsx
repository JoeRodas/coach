// PR-5 chess client scaffold. Renders the board, a move list, status, and
// a "New game" button. Mock AI plays a random legal move 600ms after the
// user moves. Position auto-persists to localStorage.
//
// PR-7 adds: time controls, resign / draw-offer, end-of-game modal with
// "Review with Coach" link, new-game-options screen (color picker, skill
// slider, time-control picker).

import ChessBoard from "../components/board/ChessBoard";
import MoveList from "../components/board/MoveList";
import { useGame } from "../hooks/useGame";

const STATUS_LABEL: Record<string, string> = {
  "in-progress": "in progress",
  checkmate: "checkmate",
  stalemate: "stalemate · draw",
  draw_threefold: "draw by threefold repetition",
  draw_50: "draw by 50-move rule",
  draw_insufficient: "draw by insufficient material",
};

export default function PlayPage() {
  const { state, submitUserMove, newGame } = useGame();

  const orientation = state.userColor === "w" ? "white" : "black";
  const isOver = state.status !== "in-progress";
  const lockBoard = state.isAiThinking || isOver;

  return (
    <section aria-labelledby="play-heading" className="space-y-6">
      <header className="flex items-baseline justify-between">
        <div className="space-y-1">
          <h1 id="play-heading" className="text-2xl font-semibold tracking-tight">
            Play
          </h1>
          <p className="text-slate-600">
            You're {state.userColor === "w" ? "white" : "black"}. The AI is currently a random-move
            mock; real Stockfish lands in PR-6.
          </p>
        </div>
        <button
          type="button"
          onClick={() =>
            newGame({ userColor: state.userColor === "w" ? "b" : "w", aiSkill: state.aiSkill })
          }
          className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
        >
          New game (swap color)
        </button>
      </header>

      <div className="grid gap-6 md:grid-cols-[minmax(0,_1fr)_18rem]">
        <div className="mx-auto w-full max-w-[36rem]">
          <ChessBoard
            fen={state.fen}
            orientation={orientation}
            locked={lockBoard}
            onMove={(from, to, promotion) => {
              const result = submitUserMove({ from, to, promotion });
              return result !== null;
            }}
          />
        </div>

        <aside className="space-y-4">
          <div className="rounded-lg border border-slate-200 bg-white p-4" aria-live="polite">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Status</p>
            <p className="mt-1 text-sm text-slate-800">
              {isOver ? (
                <strong>Game over — {STATUS_LABEL[state.status]}.</strong>
              ) : state.isAiThinking ? (
                "Computer is thinking…"
              ) : state.sideToMove === state.userColor ? (
                <>Your move{state.inCheck ? " (you're in check)" : ""}.</>
              ) : (
                "Waiting for the computer."
              )}
            </p>
            {state.lastAiPonderMs !== null ? (
              <p className="mt-1 text-xs text-slate-500">
                Last AI ponder: {state.lastAiPonderMs} ms
              </p>
            ) : null}
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Moves</p>
            <div className="mt-2 max-h-72 overflow-y-auto">
              <MoveList history={state.history} />
            </div>
          </div>
        </aside>
      </div>
    </section>
  );
}
