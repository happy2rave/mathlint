# v0.12 "Camera and handwriting" — design

Date: 2026-09-24
Status: shipped in v0.12.0

## Goal

Photograph a problem on paper — printed or handwritten — or write it on the
screen with a finger or stylus, and it lands in the notebook as editable math.
Recognition runs on the device and works offline. The whole feature adds about
5 MB, downloaded the first time it is used. This comes before the app-store
release (v1.0), which moves to after it on the roadmap.

## Decisions

- Both inputs: the camera (and a photo from the gallery) and a handwriting pad.
- One recognizer for both: a compact image-to-LaTeX model. The pad draws its
  strokes into an image and uses the same model.
- About 5 MB in total, loaded on first use, then kept for offline use.
- Training data is only what may be used commercially: formulas we generate,
  typeset in open fonts, and handwritten from symbol collections under ODbL and
  CC BY. No MathWriting, CROHME or HME100K (noncommercial or research-only).

## 1. What the student sees

- **Entry points.** A camera button and a pen button in the notebook bar of
  Solve and Check, beside Examples; a pen tab on the phone keypad.
- **Camera.** The app fades away and the live rear camera fills the screen.
  Only a faint outline of the notebook stays — its ruled lines and red margin —
  as the guide to line the working up with; the capture button and a small
  close button are the only solid things. "Choose a photo" opens the gallery (and
  is the only way in on a desktop without a camera).
- **Capture.** The frame freezes; the part inside the notebook outline is what
  is read, so there is no crop step. "Adjust" offers a crop box when the math
  spilled outside it.
- **The writing animation.** While the model reads, the photo dims; then the
  notebook fades back in and the recognized math is written onto its lines,
  left to right and line by line, with a soft trace following the pen. It is a
  mask sweeping across the rendered lines, so it costs almost nothing, and it
  covers most of the wait. With reduced motion the math simply appears.
- **Pad.** A ruled writing area in the notebook's style, one line tall, with
  undo, clear and Recognize; it also recognizes by itself after a short pause.
- **Result.** Recognized math becomes editable notebook lines; it is never
  solved without the student seeing it first. Symbols the model was unsure of
  are named under the notebook ("check: the 5 on line 2") so they are easy to
  look at.
- **First use.** The recognizer downloads once with a progress bar (about
  4 MB), then works offline. Offline before it was ever downloaded, the button
  says so instead of failing.
- **Privacy.** Photos and strokes never leave the device and are not stored;
  History keeps the recognized text, as it does for typed problems.

## 2. The model and how it learns

- **Architecture.** A small convolutional encoder reads a grayscale image 96 px
  tall (width up to 768 px, padded); a small Transformer decoder writes LaTeX
  token by token with 2-D positional encodings over the encoder's features.
  Target: about 3.5 M parameters, stored as int8 (per-channel scales): about
  3.5 MB. The encoder uses depthwise-separable convolutions to keep a phone's
  CPU time low.
- **Vocabulary.** About 150 tokens: the LaTeX subset the notebook's editor
  already reads — digits, Latin and a few Greek letters, operators and
  relations, `\frac`, `^`, `_`, `\sqrt`, `\int`, `\lim`, `\left( \right)`,
  `\begin{pmatrix}`, functions like `\sin` and `\ln`, and `{`, `}`.
- **Decoding.** Beam search (width 4). A candidate that mathlint's own LaTeX
  reader cannot read is dropped in favour of the next one, so nonsense rarely
  reaches the notebook. Each token keeps its probability; a symbol under 0.6 is
  "unsure".
- **Training data, all generated:**
  1. *Formulas*: sampled from mathlint's problem generators, examples, practice
     bank and a grammar of the math it solves, so the model sees the math
     students type here.
  2. *Layout*: one layout engine places every symbol of a formula in a box —
     fractions, powers, subscripts, roots, integrals, limits, matrices.
  3. *Printed*: each box filled with a glyph from open math fonts (Latin Modern
     Math, STIX Two, Libertinus Math, Noto Sans Math and two text fonts), at
     random sizes.
  4. *Handwritten*: each box filled with a real handwritten sample of that
     symbol — Detexify's strokes and HASYv2's drawings (both ODbL), 29
     handwriting fonts (OFL, Apache 2.0), and simple shapes drawn as strokes for
     what the datasets lack — with random pen width, slant, jitter and spacing.
     EMNIST and MNIST are not used: NIST's terms do not clearly allow it.
  5. *Photographed*: printed and handwritten samples on plain, ruled and squared
     paper, with shadows, perspective, blur, JPEG noise and uneven light. The
     pad's images are clean strokes; the camera's are these. Every training
     image then goes through the browser's own preparation, mirrored in Python.
- **Training** is PyTorch on a local GPU, in its own project (`training/`, with
  its own dependencies so the package's lock file is untouched). Generated data
  and checkpoints stay out of git; only the exported model ships with the site.

## 3. Running it in the browser

- **No ML runtime.** A small JavaScript inference library
  (`web/recognizer/`, about 50 KB) runs exactly the layers the model uses:
  convolution (standard, depthwise, pointwise) with batch norm folded in,
  activation, pooling, linear, layer norm, multi-head attention, softmax and the
  embedding. Weights are int8 and dequantized once when loaded. WebGPU can come
  later if phones need it; the first version is plain JavaScript in a Web
  Worker, so the page never freezes while it reads.
- **Model file.** `recognizer.bin`: a JSON header (layers, shapes, scales,
  vocabulary) followed by the int8 weights, written by `training/export.py`.
- **Preprocessing** in JavaScript: grayscale, contrast normalisation, the crop
  inside the notebook outline, a slight blur and resize to 96 px tall. No
  OpenCV (8 MB).
- **Loading and offline.** The model and the recognizer's code are not in the
  service worker's install-time cache; they are fetched the first time the
  camera or the pad opens, then stored in the same versioned cache, so they
  work offline and a new build replaces them.
- **Parity.** A test runs the exported model in Node on fixed inputs and
  compares the output with PyTorch's (saved as a fixture).
- **Budgets.** Model at most 4 MB; recognizer code at most 60 KB gzipped; a
  line read in under 3 s on a mid-range phone (measured in the browser, shown
  in About with the start-up time).

## 4. Measuring accuracy

- `training/evaluate.py` reports the share of expressions read exactly (the
  expression recognition rate) on held-out generated sets — printed, handwritten
  and photographed separately — and on a real test set.
- **Real test set.** `training/realset/`: photos of real problems (printed
  pages and handwritten notebooks, different people and phones) with their
  LaTeX. It starts small and grows; it is never trained on.
- **Bars for the release:** at least 90% printed and 75% handwritten on the
  generated sets; on real photos at least 85% printed and 60% neat handwriting.
  When the real set is too small to trust, the release notes say so.

## 5. Where it fits in the app

- `web/camera.js` (capture, notebook outline, adjust), `web/pad.js` (strokes,
  rendering, undo), `web/recognizer/` (worker, inference, decoding),
  `web/writing.js` (the writing animation). `app.js` only opens them and puts
  the result into a notebook.
- Every word in the four languages; screen readers hear the recognized math in
  words, as they do for typed math.

## Out of scope

Word problems, several problems in one photo, geometry diagrams, and a server
of any kind.
