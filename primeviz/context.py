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
        # Vectorised: run lengths are 1,1,2,2,3,3,... and directions cycle
        # R,U,L,D. Building this as a Python list costs ~10 GB at N=10^7.
        # segment lengths 1,1,2,2,...,s,s cover s(s+1) steps, and M-1 < (2m+2)(2m+3)
        s_max = 2 * m + 2
        lens = np.repeat(np.arange(1, s_max + 1, dtype=np.int64), 2)
        dirs = np.tile(np.array([0, 1, 2, 3], dtype=np.int8), len(lens) // 4 + 1)
        dirs = dirs[: len(lens)]
        dx = np.repeat(np.array([1, 0, -1, 0], dtype=np.int32)[dirs], lens)[: M - 1]
        dy = np.repeat(np.array([0, 1, 0, -1], dtype=np.int32)[dirs], lens)[: M - 1]
        assert dx.size == M - 1, (dx.size, M - 1)
        x = np.zeros(M, dtype=np.int32)
        y = np.zeros(M, dtype=np.int32)
        np.cumsum(dx, out=x[1:])
        np.cumsum(dy, out=y[1:])
        return x, y, M

    # --- cached candidate-pool quantities -------------------------------------
    # These depend only on the integers, not on the set being scored, and the
    # scorer evaluates every statistic ~25 times per representation. Recomputing
    # the mod-k histograms of all integers costs 8.7 s per evaluation at 10^7.

    @cached_property
    def _mod_cells(self) -> dict:
        return {}

    def mod_counts(self, k: int) -> tuple[np.ndarray, np.ndarray]:
        """(all integers, admissible integers) counted by residue mod k."""
        if k not in self._mod_cells:
            self._mod_cells[k] = (
                np.bincount(self.integers % k, minlength=k).astype(float),
                np.bincount(np.flatnonzero(self.admissible) % k, minlength=k).astype(
                    float
                ),
            )
        return self._mod_cells[k]

    @cached_property
    def admissible_idx(self) -> np.ndarray:
        return np.flatnonzero(self.admissible)

    @cached_property
    def ulam_admissible(self) -> np.ndarray:
        return np.flatnonzero(self.admissible[: self.ulam[2] + 1])

    @cached_property
    def prime_mask(self) -> np.ndarray:
        from .numbers import sieve_mask

        return sieve_mask(self.N)

    @cached_property
    def cache(self) -> dict:
        """Scratch space for representations to memoise set-independent work."""
        return {}

    @cached_property
    def sacks(self) -> tuple[np.ndarray, np.ndarray]:
        r = np.sqrt(np.arange(self.N + 1, dtype=np.float64))
        th = 2.0 * np.pi * r
        return (r * np.cos(th)).astype(np.float32), (r * np.sin(th)).astype(np.float32)

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
