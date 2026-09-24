"""Training the recognizer on the GPU (run through ``train.py``).

Checkpoints and a log go to ``runs/<name>/``: ``last.pt`` every check,
``best.pt`` when the held-out sets read best so far. ``--resume`` carries on
from ``last.pt``.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import torch
import torch.nn.functional as F

from . import feed, vocab
from .beam import greedy
from .dataset import KINDS, load_eval
from .model import Config, Recognizer, parameters
from .tensors import collate, to_tensor

RUNS = Path(__file__).parent.parent / "runs"


def learning_rate(step: int, peak: float, warmup: int, total: int) -> float:
    if step < warmup:
        return peak * (step + 1) / warmup
    progress = min(1.0, (step - warmup) / max(1, total - warmup))
    return peak * (0.02 + 0.98 * 0.5 * (1 + math.cos(math.pi * progress)))


def loss_of(model: Recognizer, images, tokens, widths, smoothing: float) -> torch.Tensor:
    logits = model(images, tokens[:, :-1], widths)
    return F.cross_entropy(
        logits.reshape(-1, logits.shape[-1]).float(),
        tokens[:, 1:].reshape(-1),
        ignore_index=vocab.PAD,
        label_smoothing=smoothing,
    )


@torch.no_grad()
def check(model: Recognizer, sets: dict, device, batch: int = 64) -> dict[str, float]:
    """The share of each held-out set read exactly, decoding greedily."""
    model.eval()
    rates = {}
    for kind, examples in sets.items():
        right = 0
        for start in range(0, len(examples), batch):
            chunk = examples[start : start + batch]
            images = to_tensor([image for image, _ in chunk]).to(device)
            widths = torch.tensor([image.shape[1] for image, _ in chunk], device=device)
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device.type == "cuda"):
                readings = greedy(model, images, widths)
            for ids, (_, latex) in zip(readings, chunk, strict=True):
                right += vocab.decode(ids) == vocab.join(vocab.tokenize(latex))
        rates[kind] = right / len(examples)
    model.train()
    return rates


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="base")
    parser.add_argument("--steps", type=int, default=60000)
    parser.add_argument("--batch", type=int, default=64)
    parser.add_argument("--lr", type=float, default=6e-4)
    parser.add_argument("--warmup", type=int, default=2000)
    parser.add_argument("--smoothing", type=float, default=0.1)
    parser.add_argument("--workers", type=int, default=14)
    parser.add_argument("--every", type=int, default=2000, help="steps between checks")
    parser.add_argument("--held-out", type=int, default=300, help="images of each kind checked")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    folder = RUNS / args.name
    folder.mkdir(parents=True, exist_ok=True)
    model = Recognizer(Config()).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=args.lr, betas=(0.9, 0.98), weight_decay=0.01
    )
    step, best = 0, -1.0
    if args.resume:
        state = torch.load(folder / "last.pt", map_location=device)
        model.load_state_dict(state["model"])
        optimizer.load_state_dict(state["optimizer"])
        step, best = state["step"], state["best"]
    print(f"{parameters(model):,} parameters on {device}; starting at step {step}")

    sets = {kind: load_eval(kind)[: args.held_out] for kind in KINDS}
    groups = feed.batches(args.seed * 100_003 + step, args.batch, args.workers)
    started, seen, running = time.time(), 0, 0.0
    model.train()
    for group in groups:
        if step >= args.steps:
            break
        images, tokens, widths = collate(group)
        for group in optimizer.param_groups:
            group["lr"] = learning_rate(step, args.lr, args.warmup, args.steps)
        images = images.to(device, non_blocking=True)
        tokens = tokens.to(device, non_blocking=True)
        widths = widths.to(device, non_blocking=True)
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device.type == "cuda"):
            loss = loss_of(model, images, tokens, widths, args.smoothing)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        step += 1
        seen += images.shape[0]
        running = 0.98 * running + 0.02 * loss.item() if step > 1 else loss.item()
        if step % 100 == 0:
            rate = seen / (time.time() - started)
            print(
                f"step {step} loss {running:.3f} lr {group['lr']:.2e} {rate:.0f} images/s",
                flush=True,
            )
        if step % args.every == 0 or step == args.steps:
            rates = check(model, sets, device)
            mean = sum(rates.values()) / len(rates)
            entry = {"step": step, "loss": running, "rates": rates, "mean": mean}
            print(json.dumps(entry), flush=True)
            with open(folder / "log.jsonl", "a", encoding="utf-8") as log:
                log.write(json.dumps(entry) + "\n")
            state = {
                "model": model.state_dict(),
                "optimizer": optimizer.state_dict(),
                "config": model.settings(),
                "step": step,
                "best": max(best, mean),
            }
            torch.save(state, folder / "last.pt")
            if mean > best:
                best = mean
                torch.save(state, folder / "best.pt")
