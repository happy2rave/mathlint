"""The browser's copy of the model reads like the model itself."""

import torch

import export
from mathrec.model import Recognizer
from tests.test_model import TINY


def test_the_exported_model_gives_nearly_the_same_logits(tmp_path):
    torch.manual_seed(0)
    model = Recognizer(TINY).eval()
    for module in model.modules():
        if isinstance(module, torch.nn.BatchNorm2d):
            module.running_mean.uniform_(-0.5, 0.5)
            module.running_var.uniform_(0.5, 2.0)
    export.save(model, tmp_path / "model.bin")
    copy = export.load(tmp_path / "model.bin")
    images = torch.rand(2, 1, 96, 128)
    tokens = torch.tensor([[1, 5, 9, 12], [1, 7, 7, 2]])
    with torch.no_grad():
        original, exported = model(images, tokens), copy(images, tokens)
    # int8 weights: close, and the same token wins nearly everywhere
    assert (original - exported).abs().max() < 0.05 * original.abs().max()
    assert (original.argmax(-1) == exported.argmax(-1)).float().mean() > 0.9


def test_matrices_are_int8_and_small_tensors_float(tmp_path):
    size = export.save(Recognizer().eval(), tmp_path / "model.bin")
    assert size < 4_000_000  # the download budget
