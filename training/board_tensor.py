"""FEN -> (12, 8, 8) float tensor encoding.

Channels 0..5 are white {P, N, B, R, Q, K}; channels 6..11 are black {p, n, b,
r, q, k}. Side-to-move, castling rights, and en-passant square are appended as
an 8-dim scalar feature vector the encoder can concatenate after patch
embedding — keeping them out of the 12-channel grid keeps the spatial input
purely piece-occupancy.
"""
from __future__ import annotations

import chess
import torch

_PIECE_TO_CHANNEL: dict[int, int] = {
    (chess.WHITE, chess.PAWN): 0,
    (chess.WHITE, chess.KNIGHT): 1,
    (chess.WHITE, chess.BISHOP): 2,
    (chess.WHITE, chess.ROOK): 3,
    (chess.WHITE, chess.QUEEN): 4,
    (chess.WHITE, chess.KING): 5,
    (chess.BLACK, chess.PAWN): 6,
    (chess.BLACK, chess.KNIGHT): 7,
    (chess.BLACK, chess.BISHOP): 8,
    (chess.BLACK, chess.ROOK): 9,
    (chess.BLACK, chess.QUEEN): 10,
    (chess.BLACK, chess.KING): 11,
}


def fen_to_tensor(fen: str) -> torch.Tensor:
    """Encode a FEN into a (12, 8, 8) float tensor of piece occupancy."""
    board = chess.Board(fen)
    t = torch.zeros(12, 8, 8, dtype=torch.float32)
    for square, piece in board.piece_map().items():
        ch = _PIECE_TO_CHANNEL[(piece.color, piece.piece_type)]
        rank = chess.square_rank(square)
        file = chess.square_file(square)
        t[ch, rank, file] = 1.0
    return t


def fen_to_scalars(fen: str) -> torch.Tensor:
    """8-dim scalar features: stm (1), castling (4), ep-file one-hot bucket (3)."""
    board = chess.Board(fen)
    feats = torch.zeros(8, dtype=torch.float32)
    feats[0] = 1.0 if board.turn == chess.WHITE else 0.0
    feats[1] = 1.0 if board.has_kingside_castling_rights(chess.WHITE) else 0.0
    feats[2] = 1.0 if board.has_queenside_castling_rights(chess.WHITE) else 0.0
    feats[3] = 1.0 if board.has_kingside_castling_rights(chess.BLACK) else 0.0
    feats[4] = 1.0 if board.has_queenside_castling_rights(chess.BLACK) else 0.0
    # coarse ep bucket: none / queenside-half / kingside-half
    if board.ep_square is None:
        feats[5] = 1.0
    elif chess.square_file(board.ep_square) < 4:
        feats[6] = 1.0
    else:
        feats[7] = 1.0
    return feats


def batch_fens(fens: list[str]) -> tuple[torch.Tensor, torch.Tensor]:
    """Stack a list of FENs into (B, 12, 8, 8) and (B, 8) tensors."""
    grids = torch.stack([fen_to_tensor(f) for f in fens])
    scalars = torch.stack([fen_to_scalars(f) for f in fens])
    return grids, scalars
