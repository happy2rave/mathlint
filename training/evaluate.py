"""How often the recognizer reads a whole line exactly right.

    uv run python evaluate.py runs/base/best.pt
    uv run python evaluate.py runs/base/best.pt --limit 200 --greedy

Each held-out set (``data/eval/<kind>``) and the real photos
(``realset/labels.tsv``, when there are any) are read one image at a time,
unpadded, as the browser reads them: beam search, then the first reading the
notebook can read. A line counts only if every token is right. The misreadings
go to ``errors-<set>.tsv`` beside the checkpoint.
"""

if __name__ == "__main__":
    import argparse
    import csv
    from pathlib import Path

    import numpy as np
    import torch
    from PIL import Image

    from mathrec import beam, vocab
    from mathrec.dataset import KINDS, load_eval
    from mathrec.image import prepare
    from mathrec.model import Config, Recognizer
    from mathrec.tensors import to_tensor
    from mathrec.validity import reads

    REALSET = Path(__file__).parent / "realset"

    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--limit", type=int, default=0, help="images per set (0: all)")
    parser.add_argument("--width", type=int, default=4, help="beam width")
    parser.add_argument("--greedy", action="store_true", help="greedy only: quick")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if args.checkpoint.suffix == ".bin":  # what the browser runs: int8, exported
        import export

        model = export.load(args.checkpoint).to(device).eval()
        state = {"step": "exported"}
    else:
        state = torch.load(args.checkpoint, map_location=device)
        settings = state["config"]
        settings["channels"], settings["blocks"] = (
            tuple(settings["channels"]),
            tuple(settings["blocks"]),
        )
        model = Recognizer(Config(**settings)).to(device).eval()
        model.load_state_dict(state["model"])

    sets = {kind: load_eval(kind) for kind in KINDS}
    if (REALSET / "labels.tsv").exists():
        with open(REALSET / "labels.tsv", encoding="utf-8", newline="") as handle:
            rows = list(csv.reader(handle, delimiter="\t"))
        sets["real"] = [
            (np.asarray(prepare(Image.open(REALSET / name))), latex) for name, latex in rows
        ]

    print(f"step {state['step']}, beam width {args.width}{' (greedy)' if args.greedy else ''}")
    for name, examples in sets.items():
        if args.limit:
            examples = examples[: args.limit]
        right, errors = 0, []
        for image, latex in examples:
            expected = vocab.join(vocab.tokenize(latex))
            if args.greedy:
                (ids,) = beam.greedy(model, to_tensor([image]).to(device), None)
                got = vocab.decode(ids)
            else:
                reading = beam.best(beam.search(model, image, args.width), valid=reads)
                got = reading.latex if reading else ""
            right += got == expected
            if got != expected:
                errors.append((expected, got))
        rate = right / max(1, len(examples))
        print(f"{name:>18}: {rate:6.1%} of {len(examples)}")
        with open(
            args.checkpoint.parent / f"errors-{name}.tsv", "w", encoding="utf-8", newline=""
        ) as handle:
            csv.writer(handle, delimiter="\t", lineterminator="\n").writerows(errors)
