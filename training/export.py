"""Write the trained recognizer as ``recognizer.bin`` for the browser.

    uv run python export.py runs/base/best.pt            # web/recognizer/recognizer.bin
    uv run python export.py --fixtures                   # web/tests/fixtures/ (tests)

The file is ``MLREC001``, the header's length (4 bytes, little-endian), a JSON
header (the model's settings, the vocabulary, and where each tensor is), then
the tensors. Batch norm is folded into the convolution before it. Every matrix
and convolution is int8 with one scale per output row or channel, a quarter of
the size of float32; biases and norms stay float32.

``load`` reads such a file back into a PyTorch model, so the tests compare the
browser with exactly the numbers it has.
"""

from __future__ import annotations

import base64
import json
import struct
from pathlib import Path

import numpy as np
import torch

from mathrec import vocab
from mathrec.image import HEIGHT
from mathrec.model import STRIDE, Config, ConvNorm, Recognizer

ROOT = Path(__file__).resolve().parent.parent
MAGIC = b"MLREC001"
QUANTIZE_FROM = 1024  # tensors with fewer numbers stay float32


def folded(model: Recognizer) -> dict[str, np.ndarray]:
    """Every tensor the browser needs, with batch norm folded into its convolution."""
    model = model.eval()
    out: dict[str, np.ndarray] = {}
    folded_norms = set()
    for name, module in model.named_modules():
        if isinstance(module, ConvNorm):
            conv, norm = module[0], module[1]
            factor = norm.weight / torch.sqrt(norm.running_var + norm.eps)
            out[f"{name}.weight"] = (conv.weight * factor[:, None, None, None]).detach().numpy()
            out[f"{name}.bias"] = (norm.bias - norm.running_mean * factor).detach().numpy()
            folded_norms.update({f"{name}.0.", f"{name}.1."})
    for name, tensor in model.state_dict().items():
        if any(name.startswith(prefix) for prefix in folded_norms):
            continue
        out[name] = tensor.detach().numpy()
    return {name: array.astype(np.float32) for name, array in out.items()}


def save(model: Recognizer, path: Path) -> int:
    tensors = folded(model)
    entries, chunks, offset = {}, [], 0

    def put(data: bytes) -> int:
        nonlocal offset
        start = offset
        chunks.append(data + b"\0" * (-len(data) % 4))
        offset += len(chunks[-1])
        return start

    for name, array in tensors.items():
        entry = {"shape": list(array.shape)}
        if array.size >= QUANTIZE_FROM and array.ndim >= 2:
            rows = array.reshape(array.shape[0], -1)
            scale = np.abs(rows).max(axis=1) / 127
            scale[scale == 0] = 1.0
            quantized = np.clip(np.rint(rows / scale[:, None]), -127, 127).astype(np.int8)
            entry.update(dtype="int8", offset=put(quantized.tobytes()))
            entry["scales"] = put(scale.astype("<f4").tobytes())
        else:
            entry.update(dtype="float32", offset=put(array.astype("<f4").tobytes()))
        entries[name] = entry
    header = {
        "format": 1,
        "config": model.settings(),
        "height": HEIGHT,
        "stride": STRIDE,
        "tokens": vocab.TOKENS,
        "special": {"pad": vocab.PAD, "start": vocab.START, "end": vocab.END},
        "tensors": entries,
    }
    text = json.dumps(header, separators=(",", ":")).encode("utf-8")
    text += b" " * (-(len(MAGIC) + 4 + len(text)) % 4)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(MAGIC + struct.pack("<I", len(text)) + text)
        for chunk in chunks:
            handle.write(chunk)
    return path.stat().st_size


def load(path: Path) -> Recognizer:
    """A PyTorch model holding exactly the numbers in ``path`` (dequantized)."""
    raw = path.read_bytes()
    assert raw[:8] == MAGIC
    (length,) = struct.unpack("<I", raw[8:12])
    header = json.loads(raw[12 : 12 + length])
    data = raw[12 + length :]
    settings = header["config"]
    settings["channels"], settings["blocks"] = (
        tuple(settings["channels"]),
        tuple(settings["blocks"]),
    )
    model = Recognizer(Config(**settings)).eval()
    state = model.state_dict()
    for name, entry in header["tensors"].items():
        shape = entry["shape"]
        count = int(np.prod(shape))
        if entry["dtype"] == "int8":
            quantized = np.frombuffer(data, np.int8, count, entry["offset"]).astype(np.float32)
            scales = np.frombuffer(data, "<f4", shape[0], entry["scales"])
            array = (quantized.reshape(shape[0], -1) * scales[:, None]).reshape(shape)
        else:
            array = np.frombuffer(data, "<f4", count, entry["offset"]).reshape(shape)
        tensor = torch.from_numpy(array.copy())
        prefix = name.rsplit(".", 1)[0]
        if f"{prefix}.0.weight" in state and f"{prefix}.1.running_var" in state:
            # a folded convolution: the norm after it does nothing but add the bias
            if name.endswith(".weight"):
                state[f"{prefix}.0.weight"] = tensor
            else:
                norm = dict(model.named_modules())[f"{prefix}.1"]
                state[f"{prefix}.1.bias"] = tensor
                state[f"{prefix}.1.weight"] = torch.ones_like(tensor)
                state[f"{prefix}.1.running_mean"] = torch.zeros_like(tensor)
                state[f"{prefix}.1.running_var"] = torch.full_like(tensor, 1 - norm.eps)
        else:
            state[name] = tensor
    model.load_state_dict(state)
    return model


def _checkpoint(path: Path) -> Recognizer:
    state = torch.load(path, map_location="cpu")
    settings = state["config"]
    settings["channels"], settings["blocks"] = (
        tuple(settings["channels"]),
        tuple(settings["blocks"]),
    )
    model = Recognizer(Config(**settings))
    model.load_state_dict(state["model"])
    return model.eval()


def _pixels(image: np.ndarray) -> dict:
    return {
        "width": int(image.shape[1]),
        "height": int(image.shape[0]),
        "pixels": base64.b64encode(image.astype(np.uint8).tobytes()).decode("ascii"),
    }


@torch.no_grad()
def fixtures(folder: Path, model_path: Path | None) -> None:
    """The tests' fixtures: a tiny random model with PyTorch's outputs, and, when
    the real model exists, a few held-out images with Python's readings."""
    from mathrec import beam
    from mathrec.tensors import to_tensor
    from tests.test_model import TINY

    folder.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(0)
    tiny = Recognizer(TINY).eval()
    for module in tiny.modules():  # batch norm as after training
        if isinstance(module, torch.nn.BatchNorm2d):
            module.running_mean.uniform_(-0.5, 0.5)
            module.running_var.uniform_(0.5, 2.0)
            module.weight.data.uniform_(0.5, 1.5)
            module.bias.data.uniform_(-0.5, 0.5)
    save(tiny, folder / "tiny.bin")
    tiny = load(folder / "tiny.bin")
    image = np.random.default_rng(3).integers(0, 256, (HEIGHT, 72)).astype(np.uint8)
    memory, _ = tiny.encode(to_tensor([image]))
    tokens = [vocab.START, 5, 9, 12, 40]
    logits = tiny.decode(memory, torch.tensor([tokens]))
    expected = {
        "image": _pixels(image),
        "memory": memory[0].flatten().tolist(),
        "memoryShape": list(memory[0].shape),
        "tokens": tokens,
        "logits": logits[0].flatten().tolist(),
    }
    (folder / "tiny.json").write_text(json.dumps(expected), encoding="utf-8")

    if model_path is None:
        return
    model = load(model_path)
    from mathrec.dataset import KINDS, load_eval

    readings = []
    for kind in KINDS:
        for image, latex in load_eval(kind)[:2]:
            best = beam.search(model, image, width=4)
            readings.append(
                {
                    "kind": kind,
                    "truth": vocab.join(vocab.tokenize(latex)),
                    "python": best[0].latex if best else "",
                    "image": _pixels(image),
                }
            )
    (folder / "readings.json").write_text(json.dumps(readings), encoding="utf-8")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint", type=Path, nargs="?")
    parser.add_argument("--out", type=Path, default=ROOT / "web" / "recognizer" / "recognizer.bin")
    parser.add_argument("--fixtures", action="store_true", help="write web/tests/fixtures/")
    args = parser.parse_args()
    if args.checkpoint:
        size = save(_checkpoint(args.checkpoint), args.out)
        print(f"{args.out}: {size / 1e6:.2f} MB")
    if args.fixtures:
        fixtures(ROOT / "web" / "tests" / "fixtures", args.out if args.out.exists() else None)
        print("fixtures written")
