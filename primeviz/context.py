"""Per-run configuration and cached geometry shared by all representations."""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property

import numpy as np

from .numbers import exponent_vectors


@dataclass
class Context:
    N: int = 50_000
    seed: int = 0
    n_rep: int = 12
    umap_max: int = 20_000
    use_umap: bool = False
    n_basis: int = 20
    out_dir: str = "out"

    # geometry is expensive-ish and identical for every set, so build it once
    @cached_property
    def ulam(self) -> tuple[np.ndarray, np.ndarray, int]:
        """(x, y, M) for n = 1..M laid on a square spiral.

        M is truncated to the largest complete odd square <= N so that every
        diagonal is fully populated -- otherwise the partial outer ring alone
        creates apparent line-to-line variation.
        """
        m = int((np.sqrt(self.N) - 1) // 2)
        M = (2 * m + 1) ** 2
        dirs = [(1, 0), (0, 1), (-1, 0), (0, -1)]
        steps: list[tuple[int, int]] = []
        seg, i = 1, 0
        while len(steps) < M - 1:
            for _ in range(2):
                steps.extend([dirs[i % 4]] * seg)
                i += 1
            seg += 1
        arr = np.array(steps[: M - 1], dtype=np.int32)
        xy = np.zeros((M, 2), dtype=np.int32)
        xy[1:] = np.cumsum(arr, axis=0)
        return xy[:, 0], xy[:, 1], M

    @cached_property
    def sacks(self) -> tuple[np.ndarray, np.ndarray]:
        n = np.arange(self.N + 1, dtype=float)
        r = np.sqrt(n)
        th = 2.0 * np.pi * r
        return r * np.cos(th), r * np.sin(th)

    @cached_property
    def integers(self) -> np.ndarray:
        return np.arange(2, self.N + 1, dtype=np.int64)

    @cached_property
    def admissible(self) -> np.ndarray:
        """Mask over 0..N of integers coprime to 2*3*5*7.

        The right candidate pool for most counting statistics: primes past 7
        live entirely inside it, so measuring them against *all* integers
        builds small-factor avoidance into the answer before the null ever
        gets a say.
        """
        m = np.ones(self.N + 1, dtype=bool)
        m[:2] = False
        for p in (2, 3, 5, 7):
            m[::p] = False
        return m

    def exps(self, m: np.ndarray) -> np.ndarray:
        return exponent_vectors(m, self.n_basis)

    def subsample(self, arr: np.ndarray, cap: int, seed: int = 7) -> np.ndarray:
        if arr.shape[0] <= cap:
            return arr
        idx = np.random.default_rng(seed).choice(arr.shape[0], cap, replace=False)
        idx.sort()
        return arr[idx]
