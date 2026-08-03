"""Integers written into a width-k grid, swept over k.

Row-major layout in width k puts n and n+k in the same column, so a column *is*
a residue class mod k. Stripes in the picture are residue-class biases and
nothing else -- which makes this the cleanest place to separate "primes avoid
small factors" from "primes are unevenly spread among the classes they can
occupy".

Two statistics, and the gap between them is the whole point:
  all_dispersion      over every residue class mod k
  reduced_dispersion  over only the classes coprime to k
"""
from __future__ import annotations

import numpy as np

from ..registry import Representation
from ..stats import dispersion
from ..theme import DIV_CMAP, SET_COLORS, SURFACE, bare, ratio_norm
from matplotlib.colors import ListedColormap

K_MIN, K_MAX = 2, 60
SWEEP_W = 480


def _gcd_reduced(k: int) -> np.ndarray:
    j = np.arange(k)
    return np.gcd(j, k) == 1


def _ratio_row(iset, ctx, k):
    cells, _ = ctx.mod_counts(k)
    obs = np.bincount(iset.values % k, minlength=k).astype(float)
    exp = cells * (obs.sum() / cells.sum())
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(exp > 0, obs / exp, np.nan)


def modgrid_render(iset, sf, ctx):
    axes = sf.subplots(1, 3, gridspec_kw={"width_ratios": [1.25, 1, 1]})

    # (1) sweep: one row per k, cells = observed/expected per residue class
    sweep = np.full((K_MAX - K_MIN + 1, SWEEP_W), np.nan)
    for i, k in enumerate(range(K_MIN, K_MAX + 1)):
        row = _ratio_row(iset, ctx, k)
        sweep[i] = row[np.minimum((np.arange(SWEEP_W) * k) // SWEEP_W, k - 1)]
    ax = axes[0]
    im = ax.imshow(
        sweep, aspect="auto", cmap=DIV_CMAP, norm=ratio_norm(2.0),
        origin="lower", extent=[0, 1, K_MIN - 0.5, K_MAX + 0.5],
        interpolation="nearest",
    )
    ax.set_title("obs / expected per class", pad=6)
    ax.set_xlabel("residue j/k")
    ax.set_ylabel("modulus k")
    ax.set_xticks([0, 0.5, 1])
    sf.colorbar(im, ax=ax, fraction=0.05, pad=0.02, ticks=[0, 1, 2])

    # (2,3) the literal grids
    cmap2 = ListedColormap([SURFACE, SET_COLORS[iset.key]])
    for ax, k, rows in ((axes[1], 30, 320), (axes[2], 210, 320)):
        span = k * rows
        img = np.zeros((rows, k), dtype=np.uint8)
        v = iset.values[iset.values < span]
        img[v // k, v % k] = 1
        ax.imshow(img, cmap=cmap2, interpolation="nearest", aspect="auto")
        ax.set_title(f"width {k}", pad=6)
        ax.set_xlabel(f"n < {span:,}")
        bare(ax)


def modgrid_stats(iset, ctx):
    red_adm, red_all, alld = [], [], []
    per_k = {}
    for k in range(3, K_MAX + 1):
        cells, cells_adm = ctx.mod_counts(k)
        obs = np.bincount(iset.values % k, minlength=k).astype(float)
        alld.append(dispersion(obs, cells))
        m = _gcd_reduced(k)
        if m.sum() >= 2:
            red_all.append(dispersion(obs[m], cells[m]))
            d = dispersion(obs[m], cells_adm[m], correct=True)
            red_adm.append(d)
            per_k[k] = d
    out = {
        "reduced_dispersion": float(np.nanmean(red_adm)),
        "max_reduced_dispersion": float(np.nanmax(red_adm)),
        "reduced_dispersion_allint_pool": float(np.nanmean(red_all)),
        "all_class_dispersion": float(np.nanmean(alld)),
    }
    for k in (12, 30, 47):
        if k in per_k:
            out[f"reduced_dispersion_k{k}"] = float(per_k[k])
    return out


Representation(
    key="modular_grid",
    title="Modular grid sweep, k = 2..60",
    question="beyond avoiding small factors, is the set unevenly spread across residue classes?",
    render=modgrid_render,
    stats=modgrid_stats,
    headline="reduced_dispersion",
    iteration=1,
    panel_size=(5.8, 4.4),
    notes=(
        "In the sweep, black = a residue class the set never occupies, grey = "
        "exactly the expected share, red = enriched. The banded triangle is the "
        "divisibility pattern. The headline statistic throws that pattern away: it "
        "looks only at classes coprime to k, counts candidates from the integers "
        "coprime to 210, and applies the binomial (1−ρ) correction — so 1.0 means "
        "'no better spread than a random choice of that many candidates', and "
        "anything well below 1 means the set is *more* even than random."
    ),
    mechanism=(
        "Two separate things live in this picture. The dark columns are trivial: a "
        "class j mod k with gcd(j,k) = d > 1 contains only multiples of d, so it "
        "holds no primes past d itself. The headline number is not that — it is the "
        "spread across the classes that are allowed, and for the primes it comes out "
        "far *below* random. The primes' counts in the reduced classes mod k sit "
        "within a few units of dead level where a random set of the same size would "
        "scatter by ±√count. The reason is that the primes are one fixed set, not a "
        "sample: their counting error in each progression is a single slowly-growing "
        "quantity of order √N, shared out over the φ(k) classes, instead of "
        "independent per-class sampling noise of order √(count) each. At N=10⁵ that "
        "is roughly a threefold smaller deviation, i.e. an order of magnitude in χ²."
    ),
)
