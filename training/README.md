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
| `mathrec/model.py` | The recognizer: a separable CNN, one Transformer layer over its grid, a three-layer decoder |
| `mathrec/beam.py` | Greedy decoding, and beam search that keeps each token's probability |
| `mathrec/feed.py` | Worker processes that make the training data (without PyTorch) |
| `train.py`, `evaluate.py`, `export.py` | Train on the GPU; measure; write `web/recognizer/recognizer.bin` and the web tests' fixtures |

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

## Training and results

```bash
uv run python train.py --name base --steps 60000      # about 2.5 hours on an 8 GB laptop GPU
uv run python evaluate.py runs/base/best.pt
uv run python export.py runs/base/best.pt --fixtures  # the model and the tests' fixtures
uv run python evaluate.py ../web/recognizer/recognizer.bin
```

The model has 3.72 million weights and exports to 3.86 MB. It trained on 3.8
million generated images (batches of 64, AdamW, 2,000 warm-up steps, then a
cosine schedule from 6e-4; label smoothing 0.1; bfloat16). The best checkpoint
came at step 56,000. The share of each held-out set (1,000 images) read exactly,
every token right, with beam search (width 4) and mathlint's own check of what
the notebook can read:

| Set | PyTorch | Exported (int8), as the browser runs it |
| --- | --- | --- |
| printed | 99.8% | 99.8% |
| handwritten | 98.5% | 98.4% |
| printed, photographed | 99.2% | 99.0% |
| handwritten, photographed | 96.2% | 95.9% |

Almost every misreading is one symbol in a dense spot: a small exponent (3 read
as 2), a letter (z as x), `<` for `\le`, or a crowded matrix. In node the
exported model reads a line in about 0.4 s on a laptop (widest lines about
0.9 s), preparation and beam search included.

These sets are generated, so they measure the model against the generator.
Real photos (`realset/`) measure it against the world; that set is still to
be collected.

