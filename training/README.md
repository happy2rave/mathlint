# Training mathlint's recognizer

This project trains the model that turns a photo of math, or math written on
the screen, into the LaTeX the notebook reads. It is separate from the mathlint
package: it has its own dependencies (PyTorch with CUDA) and its own lock file,
and nothing here ships except the exported model.

```bash
cd training
uv sync                    # PyTorch for CUDA 12.8, NumPy, Pillow, and mathlint itself
uv run pytest              # the data generators and the model
```

Everything the model learns from is generated here and may be used
commercially: formulas sampled from the math mathlint solves, typeset in open
fonts or assembled from handwritten symbols under the ODbL and open font licenses, then
"photographed" on paper. Downloads, generated data and checkpoints go to
`training/data/` and `training/runs/`, which git ignores.

## The pieces

| Module | What it does |
| --- | --- |
| `mathrec/vocab.py` | The LaTeX the recognizer may write, one spelling per picture |
| `mathrec/formulas.py` | Formulas to learn from, weighted like what students bring |
| `mathrec/layout.py` | Where every symbol goes: fractions, scripts, roots, brackets, matrices |
| `mathrec/fonts.py` | The open fonts printed formulas are typeset in, pinned by hash |
| `mathrec/render_printed.py` | A formula as a textbook prints it |
| `mathrec/symbols.py` | Handwritten samples of every symbol: Detexify strokes, HASYv2 drawings, handwriting fonts |
| `mathrec/render_hand.py` | A formula as one writer writes it, from those samples |
| `mathrec/image.py` | The shape of every input, and `prepare`: the browser's own preparation of a photo, mirrored |
| `mathrec/photo.py` | A formula photographed: paper, ruled or squared, light, shadow, tilt, blur, JPEG |
| `mathrec/dataset.py` | The endless training stream, and the fixed held-out sets in `data/eval/` |

## Handwriting

The first `symbols.bank()` downloads Detexify's dump (1 GB, from the Internet
Archive) and HASYv2 (Zenodo), checks both against pinned SHA-256 hashes, and
keeps at most 800 samples of each symbol in `data/symbols/` (about 25 seconds,
once). Neither dataset has = ( ) , ; . ! ' or, in HASYv2's case, a lowercase t;
those come from the 29 handwriting fonts and from simple shapes drawn here as
strokes.

A handwritten image is one writer: one pen width, one ink, one slant, and one
sample for each symbol, so every x in a line looks alike, as it does on paper.

## Held-out sets

```bash
uv run python -m mathrec.dataset 1000   # 1000 images of each kind in data/eval/
```

The sets come from fixed seeds, so every machine makes the same images. They
are never trained on.
