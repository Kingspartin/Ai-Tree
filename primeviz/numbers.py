"""Integer sets: the real primes and the null controls they are tested against.

Two nulls, deliberately:

  cramer  Each n >= 2 is kept independently with probability proportional to
          1/ln n (Cramer's model), rescaled so the expected count matches
          pi(N). It has the right *density* and nothing else -- in particular
          half its members are even. Any representation keyed on divisibility
          will beat this null trivially.

  sieved  Same 1/ln n weighting, but restricted to residues coprime to the
          primorial 2*3*5*7 = 210 and renormalised to the same expected count.
          This null already knows "primes avoid small factors", so structure
          that survives *it* is not just coprimality showing up in a costume.

A representation that separates from `cramer` but not from `sieved` has found
small-prime divisibility, which is a property of the definition of a prime, not
a discovery about their distribution.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np


def sieve_mask(N: int) -> np.ndarray:
    """Boolean mask of length N+1, True at primes."""
    m = np.ones(N + 1, dtype=bool)
    m[:2] = False
    for p in range(2, int(N**0.5) + 1):
        if m[p]:
            m[p * p :: p] = False
    return m


@lru_cache(maxsize=8)
def primes_upto(n: int) -> tuple:
    return tuple(np.flatnonzero(sieve_mask(n)).tolist())


@dataclass
class IntegerSet:
    """A subset of [2, N] plus the metadata needed to render and score it."""

    key: str
    label: str
    kind: str  # "real" | "null"
    N: int
    mask: np.ndarray
    seed: int | None = None
    _values: np.ndarray | None = field(default=None, repr=False, compare=False)

    @property
    def values(self) -> np.ndarray:
        if self._values is None:
            self._values = np.flatnonzero(self.mask).astype(np.int64)
        return self._values

    @property
    def count(self) -> int:
        return int(self.mask.sum())

    @property
    def density(self) -> float:
        return self.count / (self.N - 1)


def _scale_to_target(weights: np.ndarray, target: int) -> np.ndarray:
    """Scale weights so that sum(min(s*w, 1)) == target, then clip to [0, 1].

    Bisection rather than a plain multiply, because clipping at 1 destroys the
    expectation for small n where 1/ln n is already large.
    """
    lo, hi = 0.0, 1.0
    while np.minimum(weights * hi, 1.0).sum() < target:
        hi *= 2.0
        if hi > 1e9:
            break
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if np.minimum(weights * mid, 1.0).sum() < target:
            lo = mid
        else:
            hi = mid
    return np.minimum(weights * hi, 1.0)


def _log_weights(N: int) -> np.ndarray:
    n = np.arange(N + 1, dtype=float)
    w = np.zeros(N + 1)
    w[2:] = 1.0 / np.log(n[2:])
    return w


def make_primes(N: int) -> IntegerSet:
    return IntegerSet("primes", f"primes <= {N:,}", "real", N, sieve_mask(N))


def make_cramer(N: int, rng: np.random.Generator, target: int) -> IntegerSet:
    p = _scale_to_target(_log_weights(N), target)
    mask = rng.random(N + 1) < p
    mask[:2] = False
    return IntegerSet("cramer", "null: Cramer 1/ln n", "null", N, mask)


def make_sieved(
    N: int, rng: np.random.Generator, target: int, primorial_bound: int = 7
) -> IntegerSet:
    """Cramer weighting restricted to residues coprime to the primorial."""
    small = [p for p in primes_upto(primorial_bound)]
    w = _log_weights(N)
    for p in small:
        w[::p] = 0.0
    p_keep = _scale_to_target(w, target - len(small))
    mask = rng.random(N + 1) < p_keep
    mask[:2] = False
    for p in small:  # keep the small primes themselves so the low end is comparable
        if p <= N:
            mask[p] = True
    return IntegerSet(
        "sieved", f"null: sieved mod {int(np.prod(small))}", "null", N, mask
    )


ROUGH_BOUND = 47


def rough_candidates(N: int, bound: int | None = None) -> np.ndarray:
    bound = ROUGH_BOUND if bound is None else bound
    """Mask of integers with no prime factor <= bound (plus those primes)."""
    m = np.ones(N + 1, dtype=bool)
    m[:2] = False
    for p in primes_upto(bound):
        m[::p] = False
        if p <= N:
            m[p] = True  # keep the small primes so the low end stays comparable
    return m


def make_rough(
    N: int,
    rng: np.random.Generator | None,
    target: int,
    bound: int | None = None,
    thin: bool = True,
) -> IntegerSet:
    """Integers with no prime factor <= 47, thinned to the primes' density.

    Deterministic: no random numbers are drawn. It knows about divisibility by
    every prime up to 47, which is what makes it the test for whether a
    surviving pattern is really just a deeper version of coprimality.

    The thinning target is the smooth curve sum 1/ln n, deliberately **not**
    pi(x). Locking the running count onto pi(x) would make counts agree with
    the primes by construction and turn every count-based comparison circular.

    The thinning is nonetheless a greedy running-count match, which pins the
    member count to that smooth curve within +-1 and therefore makes the set
    more evenly spread than the primes *by construction*. That is a real hazard
    for any evenness statistic, which is why `thin=False` exists and is reported
    alongside: the unthinned set has the same sieve structure with nothing
    imposed on its counts.
    """
    bound = ROUGH_BOUND if bound is None else bound
    cand = rough_candidates(N, bound)
    idx = np.flatnonzero(cand)
    if not thin:
        m = np.zeros(N + 1, dtype=bool)
        m[idx] = True
        return IntegerSet(
            "rough", f"det: no factor <= {bound} (unthinned)", "null", N, m
        )

    w = _log_weights(N)
    cum = np.cumsum(w)
    cum *= target / cum[-1]  # smooth target count up to each n

    # greedy: keep a candidate whenever the smooth target has moved past the
    # number kept so far
    keep = np.zeros(idx.size, dtype=bool)
    kept = 0
    tgt = cum[idx]
    for i in range(idx.size):
        if tgt[i] > kept:
            keep[i] = True
            kept += 1
    m = np.zeros(N + 1, dtype=bool)
    m[idx[keep]] = True
    return IntegerSet("rough", f"det: no factor <= {bound}", "null", N, m)


def make_rough_unthinned(N, rng, target, bound: int | None = None):
    """The default rough null: sieve structure, no thinning rule.

    Thinning was tried first, to match the primes' density exactly, and it
    corrupted the control: a greedy running-count match imposes near-regular
    spacing, which drove `modular_grid.reduced_dispersion` to 2.87 (primes
    0.18), `gap_lag1_corr` to -0.22 (primes -0.07) and the polar dispersion to
    0.62 -- distortions in both directions that have nothing to do with the
    sieve. The unthinned set is ~35% denser than the primes instead, which is a
    real confound but a legible one: see the sieve-bound sweep in calibrate.py,
    where raising the bound slides density and every statistic smoothly onto
    the primes' values.
    """
    return make_rough(N, rng, target, bound=bound, thin=False)


NULL_FACTORIES = {
    "cramer": make_cramer,
    "sieved": make_sieved,
    "rough": make_rough_unthinned,
}

# a deterministic null has no ensemble -- one draw is the only draw
DETERMINISTIC_NULLS = {"rough"}


def build_sets(N: int, seed: int) -> dict[str, IntegerSet]:
    """The three display sets: one real, two nulls, all with matched counts."""
    real = make_primes(N)
    rng = np.random.default_rng(seed)
    out = {"primes": real}
    for key, fn in NULL_FACTORIES.items():
        s = fn(N, rng, real.count)
        s.seed = seed
        out[key] = s
    return out


def null_replicates(
    N: int, target: int, model: str, n_rep: int, seed: int
) -> list[IntegerSet]:
    """An ensemble of independent draws from one null model, for z-scores."""
    fn = NULL_FACTORIES[model]
    out = []
    for i in range(n_rep):
        rng = np.random.default_rng((seed + 1) * 100003 + i)
        s = fn(N, rng, target)
        s.seed = i
        out.append(s)
    return out


# --- multiplicative structure -------------------------------------------------


@lru_cache(maxsize=4)
def _basis(n_primes: int) -> tuple:
    p, cand = [], 2
    while len(p) < n_primes:
        if all(cand % q for q in p):
            p.append(cand)
        cand += 1
    return tuple(p)


def exponent_vectors(m: np.ndarray, n_primes: int = 20) -> np.ndarray:
    """Exponent of each of the first `n_primes` primes in each entry of m.

    The smooth part only: anything left over after dividing out the basis is
    discarded, which is the whole point -- two integers are close here when
    their small-prime structure agrees.
    """
    basis = _basis(n_primes)
    m = np.asarray(m, dtype=np.int64)
    out = np.zeros((m.size, n_primes), dtype=np.int16)
    for j, p in enumerate(basis):
        t = m.copy()
        e = np.zeros(m.size, dtype=np.int16)
        while True:
            div = (t % p == 0) & (t > 0)
            if not div.any():
                break
            e[div] += 1
            t[div] //= p
        out[:, j] = e
    return out
