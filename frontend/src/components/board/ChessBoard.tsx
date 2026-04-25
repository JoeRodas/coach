// Thin wrapper around react-chessboard. Centralizes the props translation
// so the rest of the app can render a board with a high-level API.
//
// The library handles drag-and-drop, square highlighting, and piece
// rendering. We supply the FEN, the orientation, and a callback that
// receives a {sourceSquare, targetSquare, piece} for every drop attempt
// — returning false rejects the drop visually.

import { Chessboard } from "react-chessboard";

interface Props {
  fen: string;
  orientation: "white" | "black";
  onMove: (from: string, to: string, promotion?: "q" | "r" | "b" | "n") => boolean;
  /** Disable interaction (e.g. while AI is thinking, or game is over). */
  locked?: boolean;
}

export default function ChessBoard({ fen, orientation, onMove, locked }: Props) {
  return (
    <Chessboard
      position={fen}
      boardOrientation={orientation}
      arePiecesDraggable={!locked}
      onPieceDrop={(from, to, piece) => {
        // Auto-promote to queen unless we surface a picker. PR-9 polish
        // adds the picker UI; for now queen is the right default for
        // "play vs AI" since 99% of promotions are queens anyway.
        const isPawnPromotion =
          (piece?.toLowerCase() === "wp" && to[1] === "8") ||
          (piece?.toLowerCase() === "bp" && to[1] === "1");
        return onMove(from, to, isPawnPromotion ? "q" : undefined);
      }}
      customBoardStyle={{
        borderRadius: "0.5rem",
        boxShadow: "0 4px 12px rgba(0, 0, 0, 0.08)",
      }}
    />
  );
}
