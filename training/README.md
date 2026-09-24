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
fonts or assembled from handwritten symbols under ODbL and CC BY licenses, then
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
| `mathrec/image.py` | The shape of every input: grayscale, cropped to the ink, 96 px tall |
