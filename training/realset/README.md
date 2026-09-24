# Real photos

The recognizer is measured here on photos nobody generated: printed pages and
handwritten notebooks, taken by different people with different phones. It is
never trained on them.

Each photo is one line of math, cropped roughly the way the camera's outline
crops it (some paper around the line is fine). `labels.tsv` lists each photo
with what it says, in the notebook's LaTeX, one tab between them:

```text
page-12-line-3.jpg	\frac{x+1}{2}=3
anna-notebook-1.jpg	2x^{2}-5x+3=0
```

The LaTeX is the recognizer's own spelling (see `mathrec/vocab.py`): scripts
in braces (`x^{2}`), `\le` rather than `\leq`, and so on. `evaluate.py` reads
every photo through the same preparation the browser uses and reports the share
read exactly:

```bash
uv run python evaluate.py runs/base/best.pt
```

Photos added here must be yours to share, or shared with permission; they are
kept in the repository.
