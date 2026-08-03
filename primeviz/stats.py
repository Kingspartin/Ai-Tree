"""Null comparison: turning "I think I see something" into a number.

Every representation reports scalars. Each scalar is recomputed over an
ensemble of independent null draws, giving a mean and spread, and the real
value is scored as z = (real - mean) / sd.

Verdict on the headline statistic:

  ARTIFACT      |z| < 3 against both nulls. The picture looks the same on
                random integers of the same density; it is showing you the
                encoding, not the primes.
  COPRIMALITY   separates from Cramer but not from the sieved null. Real, but
                it is "primes have no small factors" -- true by definition,
                not a discovery.
  SURVIVES      separates from both. Worth explaining.
  INCONCLUSIVE  degenerate spread, or a statistic that could not be computed.

z = 3 is the bar, not a p-value ritual: with ~12 replicates the tail is not
resolved, so treat 3 as "look again", and 6+ as "the nulls do not do this".
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class NullScore:
    model: str
    mean: float
    sd: float
    z: float
    frac_ge: float  # fraction of null draws >= real


@dataclass
class StatResult:
    name: str
    real: float
    nulls: dict[str, NullScore] = field(default_factory=dict)

    @property
    def z_cramer(self) -> float:
        return self.nulls.get("cramer", NullScore("", 0, 0, float("nan"), 0)).z

    @property
    def z_sieved(self) -> float:
        return self.nulls.get("sieved", NullScore("", 0, 0, float("nan"), 0)).z


Z_BAR = 3.0


def verdict(res: StatResult) -> str:
    zc, zs = res.z_cramer, res.z_sieved
    if not np.isfinite(res.real) or (not np.isfinite(zc) and not np.isfinite(zs)):
        return "INCONCLUSIVE"
    if np.isfinite(zs) and abs(zs) >= Z_BAR:
        return "SURVIVES"
    if np.isfinite(zc) and abs(zc) >= Z_BAR:
        return "COPRIMALITY"
    return "ARTIFACT"


def score(real_vals: dict, null_vals: dict[str, list[dict]]) -> dict[str, StatResult]:
    """real_vals: {stat: value}; null_vals: {model: [ {stat: value}, ... ]}."""
    out: dict[str, StatResult] = {}
    for name, rv in real_vals.items():
        res = StatResult(name=name, real=float(rv))
        for model, draws in null_vals.items():
            arr = np.array(
                [d[name] for d in draws if name in d and np.isfinite(d[name])],
                dtype=float,
            )
            if arr.size < 2:
                res.nulls[model] = NullScore(model, np.nan, np.nan, np.nan, np.nan)
                continue
            mu, sd = float(arr.mean()), float(arr.std(ddof=1))
            z = (res.real - mu) / sd if sd > 0 else (
                0.0 if np.isclose(res.real, mu) else np.inf * np.sign(res.real - mu)
            )
            res.nulls[model] = NullScore(
                model, mu, sd, float(z), float((arr >= res.real).mean())
            )
        out[name] = res
    return out


# --- statistic primitives -----------------------------------------------------


def dispersion(
    obs: np.ndarray, cells: np.ndarray, total: int | None = None, correct: bool = False
) -> float:
    """Chi-square per degree of freedom of `obs` counts across bins that hold
    `cells` candidate integers each.

    Expected counts are the *conditional* ones (the set's own density spread
    over the bins), so this asks "is the set clumped relative to how many
    integers each bin could have held", not "is the set the right size".

    `correct=True` divides by (1 - rho), rho being the fraction of candidate
    integers the set actually occupies. Without it the scale is misleading:
    picking a fraction rho of the candidates in each bin is binomial, not
    Poisson, so its variance is exp*(1-rho) and chi-square/dof lands at (1-rho)
    rather than 1. With rho ~ 0.5 -- which is where the primes sit among the
    integers coprime to 210 -- that is a factor-of-two error in exactly the
    statistic the verdicts hang on. Use it whenever `cells` really is the
    candidate pool the set was drawn from; a corrected value of ~1 means
    "indistinguishable from choosing that many candidates at random".
    """
    obs = np.asarray(obs, dtype=float)
    cells = np.asarray(cells, dtype=float)
    keep = cells > 0
    obs, cells = obs[keep], cells[keep]
    if obs.size < 2 or cells.sum() == 0:
        return float("nan")
    total = float(obs.sum() if total is None else total)
    exp = cells * (total / cells.sum())
    good = exp > 0
    d = float((((obs[good] - exp[good]) ** 2) / exp[good]).sum() / good.sum())
    if correct:
        rho = total / float(cells.sum())
        if rho >= 1.0:
            return float("nan")
        d /= 1.0 - rho
    return d


def counts_by(index: np.ndarray, nbins: int, weights=None) -> np.ndarray:
    return np.bincount(index, weights=weights, minlength=nbins)[:nbins].astype(float)
