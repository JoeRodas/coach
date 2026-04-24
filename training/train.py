"""Phase 2 encoder training loop — InfoNCE contrastive over adjacent plies.

Minimal single-process trainer. No distributed, no mixed precision, no
gradient accumulation: a small CPU-targeted model trained on ≤1 M positions
doesn't need any of that. Add them only when a real bottleneck shows up.

Usage:
    python -m training.train --shards data/training --epochs 5 --batch-size 128
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import torch
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.utils.data import DataLoader

from .dataset import PositionPairDataset
from .encoder import EncoderConfig, PositionEncoder
from .loss import info_nce_loss

CHECKPOINT_DIR = Path("data/checkpoints")


def train(
    shards: Path,
    epochs: int,
    batch_size: int,
    lr: float,
    temperature: float,
    num_workers: int,
    log_every: int,
    checkpoint_dir: Path,
) -> dict:
    ds = PositionPairDataset(shards)
    print(f"dataset: {ds.stats()}", flush=True)
    loader = DataLoader(
        ds, batch_size=batch_size, shuffle=True,
        num_workers=num_workers, drop_last=True,
    )
    steps_per_epoch = len(loader)
    if steps_per_epoch == 0:
        raise RuntimeError(
            f"Not enough pairs ({len(ds)}) for batch_size={batch_size}. "
            f"Lower --batch-size or feed more shards."
        )

    device = "cpu"  # CPU-inference-friendly target; train on CPU too for now.
    model = PositionEncoder(EncoderConfig()).to(device)
    print(f"encoder params: {model.param_count():,}", flush=True)

    optimizer = AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    scheduler = CosineAnnealingLR(optimizer, T_max=epochs * steps_per_epoch)

    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    ckpt = checkpoint_dir / "encoder.pt"

    history = []
    step = 0
    t0 = time.time()
    for epoch in range(epochs):
        model.train()
        loss_sum = 0.0
        for batch_idx, (ga, sa, gb, sb) in enumerate(loader):
            ga, sa, gb, sb = ga.to(device), sa.to(device), gb.to(device), sb.to(device)
            za = model(ga, sa)
            zb = model(gb, sb)
            loss = info_nce_loss(za, zb, temperature=temperature)

            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            scheduler.step()

            loss_sum += loss.item()
            step += 1
            if step % log_every == 0:
                lr_now = scheduler.get_last_lr()[0]
                print(f"  epoch {epoch} step {step:>5}/{epochs * steps_per_epoch}  "
                      f"loss={loss.item():.4f}  lr={lr_now:.2e}  "
                      f"elapsed={time.time() - t0:.0f}s", flush=True)

        avg = loss_sum / steps_per_epoch
        history.append({"epoch": epoch, "avg_loss": round(avg, 4)})
        print(f"epoch {epoch} done: avg_loss={avg:.4f}", flush=True)

        # Checkpoint after every epoch so a kill mid-run doesn't lose everything.
        torch.save({
            "state_dict": model.state_dict(),
            "config": model.cfg.__dict__,
            "history": history,
        }, ckpt)
        print(f"  checkpoint -> {ckpt} (epoch {epoch})", flush=True)

    print(f"saved -> {ckpt}", flush=True)
    return {"history": history, "checkpoint": str(ckpt)}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--shards", type=Path, default=Path("data/training"))
    p.add_argument("--epochs", type=int, default=5)
    p.add_argument("--batch-size", type=int, default=128)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--temperature", type=float, default=0.1)
    p.add_argument("--num-workers", type=int, default=0)
    p.add_argument("--log-every", type=int, default=50)
    p.add_argument("--checkpoint-dir", type=Path, default=CHECKPOINT_DIR)
    args = p.parse_args()

    result = train(
        shards=args.shards,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        temperature=args.temperature,
        num_workers=args.num_workers,
        log_every=args.log_every,
        checkpoint_dir=args.checkpoint_dir,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
