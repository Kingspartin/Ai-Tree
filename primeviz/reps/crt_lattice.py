"""NEW (iteration 1) -- CRT lattice: joint residues on two coprime moduli.

Everything so far that looks at residues looks at one modulus at a time, which
can only ever see marginal biases. The Chinese-remainder view plots the pair
(n mod p, n mod q) as a point in a p×q lattice, so it can see something the
marginals cannot: whether knowing n mod p tells you anything about n mod q.

The test is deliberately *not* uniformity. The row j=0 is empty for the primes
and not for the nulls, and that is just "p is the only prime divisible by p"
again. So the table is cut down to the reduced classes on both axes and
compared against the product of its own marginals -- an independence test,
immune to any marginal bias either set happens to have.

Moduli are all > 7, i.e. outside what the sieved null knows about, so a
marginal-based statistic here would have produced a false positive. This is the
representation stress-testing the null, not the other way round.
"""
from __future__ import annotations

import numpy as np

from ..registry import Representation
from ..theme import DIV_CMAP, recessive

PAIRS = ((11, 13), (13, 17), (17, 19), (23, 29), (29, 31))
SHOW = PAIRS[:3]


def _table(iset, p, q, reduced=True):
    v = iset.values
    if reduced:
        v = v[(v % p != 0) & (v % q != 0)]
        a, b = v % p - 1, v % q - 1
        H = np.zeros((p - 1, q - 1))
    else:
        a, b = v % p, v % q
        H = np.zeros((p, q))
    np.add.at(H, (a, b), 1.0)
    return H


def _independence(H, n_candidates: float | None = None):
    """chi-square per dof against the product of the table's own marginals.

    With `n_candidates`, apply the same binomial (1-rho) correction used
    elsewhere: the set occupies a large fraction of the candidate integers, so
    its cell counts are less variable than Poisson and an uncorrected chi-square
    lands near (1-rho) even under perfect independence.
    """
    tot = H.sum()
    if tot < 10 or H.size < 4:
        return float("nan")
    exp = np.outer(H.sum(1), H.sum(0)) / tot
    good = exp > 0
    dof = (H.shape[0] - 1) * (H.shape[1] - 1)
    d = float((((H[good] - exp[good]) ** 2) / exp[good]).sum() / dof)
    if n_candidates:
        rho = tot / float(n_candidates)
        if rho >= 1.0:
            return float("nan")
        d /= 1.0 - rho
    return d


def _n_candidates(ctx, p, q):
    a = np.flatnonzero(ctx.admissible)
    return float(((a % p != 0) & (a % q != 0)).sum())


def crt_render(iset, sf, ctx):
    axes = sf.subplots(1, 3)
    for ax, (p, q) in zip(axes, SHOW):
        H = _table(iset, p, q)
        exp = np.outer(H.sum(1), H.sum(0)) / max(H.sum(), 1)
        with np.errstate(divide="ignore", invalid="ignore"):
            R = np.where(exp > 0, H / exp, np.nan)
        im = ax.imshow(R.T, origin="lower", cmap=DIV_CMAP, vmin=0.4, vmax=1.6,
                       interpolation="nearest", aspect="equal",
                       extent=[0.5, p - 0.5, 0.5, q - 0.5])
        ax.set_title(f"({p}, {q})", pad=6)
        ax.set_xlabel(
            f"n mod {p}   ·   χ²/dof {_independence(H, _n_candidates(ctx, p, q)):.2f}"
        )
        ax.set_ylabel(f"n mod {q}")
        recessive(ax)
        ax.grid(False)
    sf.colorbar(im, ax=axes, fraction=0.025, pad=0.02, ticks=[0.5, 1.0, 1.5]).set_label(
        "obs / independent", color="#c3c2b7", fontsize=8
    )


def crt_stats(iset, ctx):
    red = [
        _independence(_table(iset, p, q), _n_candidates(ctx, p, q)) for p, q in PAIRS
    ]
    full = [_independence(_table(iset, p, q, reduced=False)) for p, q in PAIRS]
    out = {
        "crt_independence": float(np.nanmean(red)),
        "crt_independence_max": float(np.nanmax(red)),
        "crt_independence_unreduced": float(np.nanmean(full)),
    }
    for (p, q), r in zip(PAIRS[:2], red):
        out[f"crt_indep_{p}_{q}"] = float(r)
    return out


Representation(
    key="crt_lattice",
    title="CRT lattice — joint residues (n mod p, n mod q)",
    question="does knowing n mod p tell you anything about n mod q?",
    render=crt_render,
    stats=crt_stats,
    headline="crt_independence",
    iteration=1,
    panel_size=(5.4, 3.2),
    notes=(
        "Grey means the cell holds exactly what independence predicts. A value of "
        "χ²/dof near 1 means the two residues carry no information about each "
        "other; the picture being visibly speckled at this sample size is expected "
        "— roughly 10 members per cell — and is noise, not texture. Compare the "
        "reduced statistic with `crt_independence_unreduced` to see how much a "
        "naive version of this test would have been driven by the empty row and "
        "column alone."
    ),
    mechanism=(
        "Any dependence would mean the members are not spread across residue "
        "classes mod pq the way they are spread mod p and mod q separately."
    ),
)
