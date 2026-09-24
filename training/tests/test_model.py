"""The recognizer's shape, its size, and that it can learn at all."""

import random

import numpy as np
import torch

from mathrec import beam, formulas, render_printed, vocab
from mathrec.image import HEIGHT, prepare
from mathrec.model import Config, Recognizer, parameters
from mathrec.tensors import collate

TINY = Config(
    width=64,
    heads=4,
    encoder_ffn=128,
    decoder_layers=2,
    decoder_ffn=128,
    channels=(8, 16, 32, 64),
    blocks=(1, 1, 1),
)


def test_the_model_fits_the_download_budget():
    assert parameters(Recognizer()) <= 4_000_000


def test_logits_for_every_position_and_every_token():
    model = Recognizer(TINY).eval()
    images = torch.zeros(2, 1, HEIGHT, 320)
    tokens = torch.ones(2, 7, dtype=torch.long)
    assert model(images, tokens).shape == (2, 7, len(vocab.TOKENS))


def test_what_else_is_in_a_batch_never_reaches_an_image_reading():
    torch.manual_seed(0)
    model = Recognizer(TINY).eval()
    for module in model.modules():  # batch norm as after training, not the identity
        if isinstance(module, torch.nn.BatchNorm2d):
            module.running_mean.uniform_(-0.5, 0.5)
            module.bias.data.uniform_(-0.5, 0.5)
    rng = np.random.default_rng(0)
    narrow = rng.integers(0, 256, (HEIGHT, 160)).astype(np.uint8)
    tokens = torch.tensor([[vocab.START, 5, 9, 12]]).repeat(2, 1)
    outputs = []
    for seed in (1, 2):
        wide = np.random.default_rng(seed).integers(0, 256, (HEIGHT, 400)).astype(np.uint8)
        images, _, widths = collate([(narrow, [1]), (wide, [1])])
        memory, mask = model.encode(images, widths)
        outputs.append(model.decode(memory, tokens, mask)[0])
    assert torch.allclose(outputs[0], outputs[1], atol=1e-5)


def _printed(count, seed):
    rng = random.Random(seed)
    out = []
    for latex in formulas.corpus(count, seed=seed):
        if len(vocab.tokenize(latex)) <= 10:
            out.append((np.asarray(prepare(render_printed.draw_formula(latex, rng)[0])), latex))
    return out


def test_a_tiny_model_learns_a_handful_of_formulas_by_heart():
    torch.manual_seed(0)
    examples = _printed(40, seed=3)[:8]
    batch = [(image, vocab.encode(vocab.tokenize(latex))) for image, latex in examples]
    images, tokens, widths = collate(batch)
    model = Recognizer(TINY)
    optimizer = torch.optim.Adam(model.parameters(), lr=4e-3)
    for _ in range(200):
        logits = model(images, tokens[:, :-1], widths)
        loss = torch.nn.functional.cross_entropy(
            logits.reshape(-1, logits.shape[-1]), tokens[:, 1:].reshape(-1), ignore_index=vocab.PAD
        )
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    model.eval()
    readings = beam.greedy(model, images, widths)
    right = sum(
        vocab.decode(ids) == vocab.join(vocab.tokenize(latex))
        for ids, (_, latex) in zip(readings, examples, strict=True)
    )
    assert right >= 7

    # beam search agrees, gives every token a probability, and best() filters
    image, latex = examples[0]
    readings = beam.search(model, image, width=4)
    assert readings[0].latex == vocab.join(vocab.tokenize(latex))
    assert len(readings[0].probs) == len(readings[0].ids)
    assert all(0 < p <= 1 for p in readings[0].probs)
    assert readings == sorted(readings, key=lambda r: r.score, reverse=True)
    assert beam.best(readings, valid=lambda text: False) is readings[0]
    if len(readings) > 1:
        second = readings[1].latex
        assert beam.best(readings, valid=lambda text: text == second) is readings[1]
