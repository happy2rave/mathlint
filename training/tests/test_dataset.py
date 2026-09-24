"""Photographed samples, the browser's preparation, and the dataset."""

import random

import numpy as np
import pytest
from PIL import Image

from mathrec import dataset, formulas, photo, render_printed, symbols, vocab
from mathrec.download import DOWNLOADS
from mathrec.image import HEIGHT, MAX_WIDTH, prepare
from mathrec.tensors import collate

needs_handwriting = pytest.mark.skipif(
    not (symbols.CACHE / "detexify.pkl").exists() and not (DOWNLOADS / "detexify.sql").exists(),
    reason="the handwriting datasets are not downloaded",
)


def _dark(pixels):
    return (np.asarray(pixels) < 128).sum()


def test_prepare_evens_out_a_shadow_and_crops_to_the_ink():
    page = np.full((200, 600), 230, dtype=np.float32)
    page *= np.clip(1 - (np.arange(600) - 270) / 60, 0.55, 1)  # a soft shadow over half
    for left in range(100, 500, 40):
        page[80:120, left : left + 20] = 40  # letters in the light and in the shadow
    ready = np.asarray(prepare(Image.fromarray(page.astype(np.uint8))))
    assert ready.shape[0] == HEIGHT
    middle = ready[HEIGHT // 2]
    assert middle.min() < 60  # ink
    assert (middle[: len(middle) // 2] < 128).sum() > 0 and (
        middle[len(middle) // 2 :] < 128
    ).sum() > 0
    between = ready[HEIGHT // 2, ready.shape[1] // 2 - 30 : ready.shape[1] // 2 + 30]
    assert between.max() > 230  # the paper between letters is white on both sides
    assert ready[2].min() > 200 and ready[-3].min() > 200  # paper above and below it


def test_prepare_ignores_ruled_lines_when_cropping():
    page = np.full((300, 600), 240, dtype=np.uint8)
    page[::30, :] = 150  # ruled lines all the way across
    page[140:160, 250:350] = 20  # a short word
    ready = np.asarray(prepare(Image.fromarray(page)))
    # the crop is the word, not the whole ruled page: wide, not a tall slab
    assert ready.shape[1] > 2 * ready.shape[0]


def test_a_photographed_formula_keeps_all_its_ink():
    rng = random.Random(3)
    for latex in formulas.corpus(12, seed=6):
        canvas, size = render_printed.draw_formula(latex, rng)
        clean = prepare(canvas)
        shot = prepare(photo.photograph(canvas, size, rng))
        assert shot.height == HEIGHT and shot.width <= MAX_WIDTH
        # about the same shape once cropped: nothing cut off, nothing big added
        assert 0.6 < shot.width / clean.width < 1.6
        assert _dark(shot) > 0.3 * _dark(clean)


def test_a_batch_pads_images_with_paper_and_tokens_with_pad():
    images = [np.full((HEIGHT, 40), 255, np.uint8), np.zeros((HEIGHT, 70), np.uint8)]
    batch_images, batch_tokens, widths = collate([(images[0], [1, 5, 2]), (images[1], [1, 2])])
    assert widths.tolist() == [40, 70]
    assert batch_images.shape == (2, 1, HEIGHT, 80)
    assert batch_images[0].max() == 0 and batch_images[1, 0, :, :70].min() == 1
    assert batch_images[1, 0, :, 70:].max() == 0
    assert batch_tokens.tolist() == [[1, 5, 2], [1, 2, vocab.PAD]]


@needs_handwriting
def test_the_eval_sets_are_the_same_every_time(tmp_path):
    for kind in dataset.KINDS:
        first = dataset.make_eval(kind, 3, root=tmp_path / "a")
        second = dataset.make_eval(kind, 3, root=tmp_path / "b")
        for name in ["00000.png", "00001.png", "00002.png", "labels.tsv"]:
            assert (first / name).read_bytes() == (second / name).read_bytes()
    loaded = dataset.load_eval("handwritten", root=tmp_path / "a")
    assert len(loaded) == 3 and loaded[0][0].shape[0] == HEIGHT


@needs_handwriting
def test_batches_hold_images_of_about_the_same_width_with_their_tokens():
    groups = dataset.batches(seed=1, size=4, pool=3)
    assert len(groups) == 3
    everything = sorted(image.shape[1] for group in groups for image, _ in group)
    for group in groups:
        widths = sorted(image.shape[1] for image, _ in group)
        # each batch is a run of neighbours in the sorted widths
        start = everything.index(widths[0])
        assert widths == everything[start : start + len(widths)]
        for image, ids in group:
            assert image.dtype == np.uint8 and image.shape[0] == HEIGHT
            assert ids[0] == vocab.START and ids[-1] == vocab.END
            assert len(ids) <= dataset.MAX_TOKENS
