"""Training batches made by worker processes, as fast as the GPU takes them.

The workers import only the data code, never PyTorch: on Windows every process
that loads PyTorch's CUDA libraries reserves gigabytes, and a dozen of them run
out of memory. The script that starts them must import PyTorch only under
``if __name__ == "__main__"``, because each worker re-imports it.
"""

from __future__ import annotations

import multiprocessing
import os
from collections import deque
from itertools import count

from . import dataset


def _make(task: tuple[int, int, int]):
    seed, size, pool = task
    return dataset.batches(seed, size, pool)


def batches(seed: int, size: int, workers: int, pool: int = 4):
    """Endless batches (lists of (image, ids)), made ``workers`` at a time."""
    # one BLAS thread each: the workers are parallel already, and OpenBLAS would
    # otherwise reserve half a gigabyte in every one for threads it never uses
    for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ.setdefault(name, "1")
    context = multiprocessing.get_context("spawn")
    seeds = count(seed * 1_000_003)
    with context.Pool(workers) as processes:
        waiting = deque(
            processes.apply_async(_make, ((next(seeds), size, pool),)) for _ in range(workers + 2)
        )
        while True:
            groups = waiting.popleft().get()
            waiting.append(processes.apply_async(_make, ((next(seeds), size, pool),)))
            yield from groups
