"""Polar plot with r = n and θ = n radians.

Included as a calibration target. The radian angle makes consecutive integers
step by 1 rad, so points fall on spokes wherever a rational p/q approximates
2π well. Those spokes have nothing to do with which integers are plotted -- any
subset of the integers, prime or random, draws them. If the harness does not
call this an artifact, the harness is broken.
"""
from __future__ import annotations

import numpy as np

from ..registry import Representation
from ..stats import dispersion
from ..theme import SET_COLORS, bare

TWO_PI = 2.0 * np.pi
ARMS = (6, 44, 100, 710)  # 6, 44, 710 are rational approximations to 2π; 100 is a control


def polar_render(iset, sf, ctx):
    v = iset.values
    th = (v % TWO_PI).astype(float)
    axes = sf.subplots(1, 2, gridspec_kw={"width_ratios": [1, 1]})
    for ax, cap in zip(axes, (ctx.N, min(ctx.N, 4000))):
        sel = v <= cap
        r = v[sel].astype(float)
        t = th[sel]
        ax.scatter(
            r * np.cos(t), r * np.sin(t), s=0.9, c=SET_COLORS[iset.key],
            linewidths=0, alpha=0.8,
        )
        ax.set_aspect("equal")
        ax.set_title(f"r=n, θ=n rad, n ≤ {cap:,}", pad=6)
        bare(ax)


def _bin(v, nb):
    return np.minimum(((v % TWO_PI) / TWO_PI * nb).astype(int), nb - 1)


def polar_stats(iset, ctx):
    n_all = ctx.integers
    adm = np.flatnonzero(ctx.admissible)
    out = {}
    for nb in ARMS:
        cells = np.bincount(_bin(n_all, nb), minlength=nb).astype(float)
        cells_adm = np.bincount(_bin(adm, nb), minlength=nb).astype(float)
        obs = np.bincount(_bin(iset.values, nb), minlength=nb).astype(float)
        out[f"ang_dispersion_allint_{nb}"] = dispersion(obs, cells)
        out[f"ang_dispersion_{nb}"] = dispersion(obs, cells_adm, correct=True)
    return out


Representation(
    key="polar_radian",
    title="Polar plot, r=n and θ=n radians",
    question="are the visible spiral arms a property of the primes or of 2π?",
    render=polar_render,
    stats=polar_stats,
    headline="ang_dispersion_710",
    iteration=1,
    panel_size=(4.6, 3.6),
    notes=(
        "Arm counts 6, 44 and 710 are the denominators you get when you approximate "
        "2π by a fraction; 100 is a non-resonant control. Dispersion is measured "
        "against the number of candidate integers per angular bin, so a set that is "
        "simply 'some integers' scores ~1 no matter how striking the picture looks. "
        "The `_allint` variants use all integers as candidates: at 710 bins they read "
        "≈21 for the primes and ≈21 for the sieved null alike, a twentyfold 'signal' "
        "that is entirely the even bins being empty. Instructive as a demonstration "
        "of how easily a statistic can be manufactured out of nothing."
    ),
    mechanism=(
        "The spokes themselves are nothing about the primes: with 2π ≈ 44/7 ≈ "
        "710/113, integers one apart land at angles that nearly repeat after 44 or "
        "710 steps, so *any* set of integers is drawn onto them. The picture is of "
        "the continued-fraction expansion of 2π, and the statistic agrees — at 6, 44 "
        "and 100 bins the primes match the sieved null within z≈1. "
        "The one bin count that does separate, 710, separates for a reason that is "
        "still not about distribution: 710 = 2·5·71, and because 113/710 ≈ 1/2π the "
        "bin index is essentially n mod 710, so ten of the 710 bins are the classes "
        "divisible by 71. The primes vacate those ten bins; the sieved null, which "
        "only knows about factors up to 7, does not. That accounts for an excess of "
        "about 0.3 in χ²/dof, which is the whole of the observed gap. It is a "
        "measurement of the null's sieve bound, not of the primes."
    ),
)
