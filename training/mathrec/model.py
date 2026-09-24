"""The recognizer: a small convolutional encoder and a Transformer decoder.

Built only from layers the browser's hand-written inference runs — convolution
(standard, depthwise, pointwise) with batch norm folded in at export, ReLU,
linear, layer norm, multi-head attention and an embedding — so what trains here
is exactly what runs there. Positions are sinusoidal, computed rather than
stored, so a line of any width and any length costs no extra weights.

The encoder turns a 96-pixel-tall image into a grid 6 tall and a sixteenth as
wide, one 256-number vector per cell, and one Transformer layer lets every cell
see the whole line. The decoder writes the LaTeX one token at a time, looking
back at the tokens so far and across at the grid.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import torch
import torch.nn.functional as F
from torch import nn

from . import vocab

STRIDE = 16  # the encoder's grid is this many pixels to a cell, both ways


@dataclass
class Config:
    width: int = 256  # d_model
    heads: int = 8
    encoder_layers: int = 1
    encoder_ffn: int = 512
    decoder_layers: int = 3
    decoder_ffn: int = 768
    channels: tuple[int, ...] = (32, 64, 128, 256)  # stem, then the three stages
    blocks: tuple[int, ...] = (2, 3, 4)  # separable blocks in each stage
    vocab_size: int = len(vocab.TOKENS)


class ConvNorm(nn.Sequential):
    def __init__(self, cin: int, cout: int, kernel: int, stride: int = 1, groups: int = 1):
        conv = nn.Conv2d(cin, cout, kernel, stride, kernel // 2, groups=groups, bias=False)
        super().__init__(conv, nn.BatchNorm2d(cout))


class Separable(nn.Module):
    """A depthwise 3×3 then a pointwise 1×1, with a shortcut when the shape allows."""

    def __init__(self, cin: int, cout: int, stride: int = 1):
        super().__init__()
        self.depthwise = ConvNorm(cin, cin, 3, stride, groups=cin)
        self.pointwise = ConvNorm(cin, cout, 1)
        self.shortcut = stride == 1 and cin == cout

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.pointwise(F.relu(self.depthwise(x)))
        return F.relu(out + x if self.shortcut else out)


class Attention(nn.Module):
    def __init__(self, width: int, heads: int):
        super().__init__()
        self.heads = heads
        self.query = nn.Linear(width, width)
        self.key = nn.Linear(width, width)
        self.value = nn.Linear(width, width)
        self.out = nn.Linear(width, width)

    def _split(self, x: torch.Tensor) -> torch.Tensor:
        batch, length, width = x.shape
        return x.view(batch, length, self.heads, width // self.heads).transpose(1, 2)

    def forward(self, x, context, mask=None, causal=False) -> torch.Tensor:
        q, k, v = (
            self._split(self.query(x)),
            self._split(self.key(context)),
            self._split(self.value(context)),
        )
        out = F.scaled_dot_product_attention(q, k, v, attn_mask=mask, is_causal=causal)
        return self.out(out.transpose(1, 2).reshape(x.shape))


class FeedForward(nn.Sequential):
    def __init__(self, width: int, hidden: int):
        super().__init__(nn.Linear(width, hidden), nn.ReLU(), nn.Linear(hidden, width))


class EncoderLayer(nn.Module):
    def __init__(self, config: Config):
        super().__init__()
        self.norm1 = nn.LayerNorm(config.width)
        self.attention = Attention(config.width, config.heads)
        self.norm2 = nn.LayerNorm(config.width)
        self.ffn = FeedForward(config.width, config.encoder_ffn)

    def forward(self, x, mask):
        y = self.norm1(x)
        x = x + self.attention(y, y, mask)
        return x + self.ffn(self.norm2(x))


class DecoderLayer(nn.Module):
    def __init__(self, config: Config):
        super().__init__()
        self.norm1 = nn.LayerNorm(config.width)
        self.self_attention = Attention(config.width, config.heads)
        self.norm2 = nn.LayerNorm(config.width)
        self.cross_attention = Attention(config.width, config.heads)
        self.norm3 = nn.LayerNorm(config.width)
        self.ffn = FeedForward(config.width, config.decoder_ffn)

    def forward(self, x, memory, memory_mask):
        y = self.norm1(x)
        x = x + self.self_attention(y, y, causal=True)
        x = x + self.cross_attention(self.norm2(x), memory, memory_mask)
        return x + self.ffn(self.norm3(x))


def sinusoid(positions: torch.Tensor, width: int) -> torch.Tensor:
    """The Transformer's sine and cosine position code, ``width`` numbers per position."""
    frequencies = torch.exp(
        torch.arange(0, width, 2, device=positions.device, dtype=torch.float32)
        * (-math.log(10000.0) / width)
    )
    angles = positions.float()[:, None] * frequencies[None, :]
    return torch.stack([angles.sin(), angles.cos()], dim=-1).flatten(1)


def grid_positions(rows: int, columns: int, width: int, device) -> torch.Tensor:
    """Half the numbers code the row, half the column; (rows × columns, width)."""
    y = sinusoid(torch.arange(rows, device=device), width // 2)
    x = sinusoid(torch.arange(columns, device=device), width // 2)
    return torch.cat(
        [y[:, None, :].expand(rows, columns, -1), x[None, :, :].expand(rows, columns, -1)], dim=-1
    ).reshape(rows * columns, width)


class Recognizer(nn.Module):
    def __init__(self, config: Config | None = None):
        super().__init__()
        self.config = config = config or Config()
        channels = config.channels
        layers: list[nn.Module] = [ConvNorm(1, channels[0], 3, stride=2), nn.ReLU()]
        for stage, count in enumerate(config.blocks):
            cin, cout = channels[stage], channels[stage + 1]
            layers.append(Separable(cin, cout, stride=2))
            layers += [Separable(cout, cout) for _ in range(count - 1)]
        self.cnn = nn.Sequential(*layers)
        self.project = nn.Linear(channels[-1], config.width)
        self.encoder = nn.ModuleList(EncoderLayer(config) for _ in range(config.encoder_layers))
        self.encoder_norm = nn.LayerNorm(config.width)
        self.embed = nn.Embedding(config.vocab_size, config.width)
        self.decoder = nn.ModuleList(DecoderLayer(config) for _ in range(config.decoder_layers))
        self.decoder_norm = nn.LayerNorm(config.width)
        self.classify = nn.Linear(config.width, config.vocab_size)

    def encode(
        self, images: torch.Tensor, widths: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor | None]:
        """Images (batch, 1, 96, W), ink 1 and paper 0 → memory (batch, cells, width).

        ``widths`` (in pixels) marks the paper padded on the right of narrower
        images, which the decoder then never looks at.
        """
        grid = self.cnn(images)
        batch, _, rows, columns = grid.shape
        memory = self.project(grid.flatten(2).transpose(1, 2))
        memory = memory + grid_positions(rows, columns, self.config.width, images.device)
        mask = None
        if widths is not None:
            used = (widths + STRIDE - 1) // STRIDE
            column = torch.arange(columns, device=images.device)
            keep = column[None, None, :] < used[:, None, None]  # (batch, 1, columns)
            mask = keep.expand(batch, rows, columns).reshape(batch, 1, 1, -1)
        for layer in self.encoder:
            memory = layer(memory, mask)
        return self.encoder_norm(memory), mask

    def decode(self, memory: torch.Tensor, tokens: torch.Tensor, mask=None) -> torch.Tensor:
        """Tokens so far (batch, length) → logits for the next token at every position."""
        length = tokens.shape[1]
        positions = sinusoid(torch.arange(length, device=tokens.device), self.config.width)
        x = self.embed(tokens) * math.sqrt(self.config.width) + positions
        for layer in self.decoder:
            x = layer(x, memory, mask)
        return self.classify(self.decoder_norm(x))

    def forward(self, images, tokens, widths=None) -> torch.Tensor:
        memory, mask = self.encode(images, widths)
        return self.decode(memory, tokens, mask)

    def settings(self) -> dict:
        return asdict(self.config)


def parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters())
