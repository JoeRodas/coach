"""InfoNCE contrastive loss for position embeddings.

SimCLR-style symmetric loss: given L2-normalized embeddings of two views
(anchor, positive) with in-batch negatives, minimize
    -log( exp(sim(a, p) / τ) / sum_j exp(sim(a, z_j) / τ) )
summed over both directions (a->p and p->a) and averaged.
"""
from __future__ import annotations

import torch
import torch.nn.functional as F


def info_nce_loss(z1: torch.Tensor, z2: torch.Tensor, temperature: float = 0.1) -> torch.Tensor:
    """Symmetric InfoNCE over L2-normalized embeddings.

    z1, z2: (B, d) each; row i of z1 and row i of z2 form a positive pair.
    All other rows serve as in-batch negatives.
    """
    if z1.shape != z2.shape or z1.dim() != 2:
        raise ValueError(f"z1/z2 must be matching (B, d); got {z1.shape} vs {z2.shape}")
    b = z1.shape[0]
    logits_12 = (z1 @ z2.T) / temperature
    logits_21 = logits_12.T
    targets = torch.arange(b, device=z1.device)
    return 0.5 * (F.cross_entropy(logits_12, targets) + F.cross_entropy(logits_21, targets))
