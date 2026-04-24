"""Position encoder: small transformer over an 8x8 board-patch sequence.

Architecture (Phase 2):
- Input: (B, 12, 8, 8) piece-occupancy grid + (B, 8) scalar features.
- Patch embedding: treat each of the 64 squares as a 12-dim token, linear
  project to d_model.
- Add learned positional embedding (64 tokens).
- Prepend a learned CLS token, and a scalar-feature token from the 8-dim
  scalars projected to d_model.
- 4 transformer encoder layers (d_model=128, 4 heads, FF=256, GELU).
- Read the CLS token, project with a 2-layer MLP head to d_out for the
  contrastive loss.

Size budget: ~500k params. CPU-inference-friendly.
"""
from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.nn as nn


@dataclass
class EncoderConfig:
    d_model: int = 128
    n_heads: int = 4
    n_layers: int = 4
    d_ff: int = 256
    d_out: int = 128  # projection dim used for retrieval + contrastive loss
    dropout: float = 0.1


class PositionEncoder(nn.Module):
    def __init__(self, cfg: EncoderConfig | None = None) -> None:
        super().__init__()
        self.cfg = cfg or EncoderConfig()

        self.patch_proj = nn.Linear(12, self.cfg.d_model)
        self.scalar_proj = nn.Linear(8, self.cfg.d_model)

        # 64 square tokens + 1 CLS + 1 scalar-feature token = 66 positions
        self.pos_emb = nn.Parameter(torch.zeros(1, 66, self.cfg.d_model))
        self.cls_token = nn.Parameter(torch.zeros(1, 1, self.cfg.d_model))
        nn.init.trunc_normal_(self.pos_emb, std=0.02)
        nn.init.trunc_normal_(self.cls_token, std=0.02)

        layer = nn.TransformerEncoderLayer(
            d_model=self.cfg.d_model,
            nhead=self.cfg.n_heads,
            dim_feedforward=self.cfg.d_ff,
            dropout=self.cfg.dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(layer, num_layers=self.cfg.n_layers)

        self.head = nn.Sequential(
            nn.Linear(self.cfg.d_model, self.cfg.d_model),
            nn.GELU(),
            nn.Linear(self.cfg.d_model, self.cfg.d_out),
        )

    def forward(self, grid: torch.Tensor, scalars: torch.Tensor) -> torch.Tensor:
        # grid:    (B, 12, 8, 8) -> (B, 64, 12) -> (B, 64, d_model)
        b = grid.shape[0]
        patches = grid.view(b, 12, 64).transpose(1, 2)
        patch_tok = self.patch_proj(patches)
        scalar_tok = self.scalar_proj(scalars).unsqueeze(1)
        cls_tok = self.cls_token.expand(b, -1, -1)
        x = torch.cat([cls_tok, scalar_tok, patch_tok], dim=1) + self.pos_emb
        x = self.encoder(x)
        cls_out = x[:, 0]
        z = self.head(cls_out)
        z = nn.functional.normalize(z, dim=-1)
        return z

    def param_count(self) -> int:
        return sum(p.numel() for p in self.parameters())
