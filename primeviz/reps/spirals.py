"""Square spiral and square-root spiral.

Both lay the integers on a plane in an order that makes certain quadratic
sub-sequences collinear. That is the entire idea: if a set is enriched on some
quadratic progressions, a layout that straightens those progressions into lines
will show it as lines.
"""
from __future__ import annotations

import numpy as np
from matplotlib.colors import ListedColormap

from ..registry import Representation
from ..stats import dispersion
from ..theme import SET_COLORS, SURFACE, bare

# --- Ulam: square spiral ------------------------------------------------------


def _ulam_index(iset, ctx):
    x, y, M = ctx.ulam
    v = iset.values
    v = v[v <= M]
    return x[v - 1], y[v - 1], M


def ulam_render(iset, sf, ctx):
    x, y, M = ctx.ulam
    m = (int(np.sqrt(M)) - 1) // 2
    img = np.zeros((2 * m + 1, 2 * m + 1), dtype=np.uint8)
    sx, sy, _ = _ulam_index(iset, ctx)
    img[sy + m, sx + m] = 1

    axes = sf.subplots(1, 2, gridspec_kw={"width_ratios": [1.6, 1]})
    ax = axes[0]
    ax.imshow(
        img,
        cmap=ListedColormap([SURFACE, SET_COLORS[iset.key]]),
        interpolation="nearest",
        origin="lower",
    )
    ax.set_title(f"square spiral, n ≤ {M:,}", pad=6)
    bare(ax)

    # zoom on the centre so individual cells are resolvable
    z = 60
    c = m
    ax2 = axes[1]
    ax2.imshow(
        img[c - z : c + z, c - z : c + z],
        cmap=ListedColormap([SURFACE, SET_COLORS[iset.key]]),
        interpolation="nearest",
        origin="lower",
    )
    ax2.set_title(f"centre {2*z}×{2*z}", pad=6)
    bare(ax2)


def ulam_stats(iset, ctx):
    x, y, M = ctx.ulam
    m = (int(np.sqrt(M)) - 1) // 2
    sx, sy, _ = _ulam_index(iset, ctx)
    # candidate pool: integers coprime to 210, which is where the primes live
    na = np.flatnonzero(ctx.admissible[: M + 1])
    ax_, ay_ = x[na - 1], y[na - 1]
    out = {}
    families = {
        "diag": (x + y + 2 * m, ax_ + ay_ + 2 * m, sx + sy + 2 * m, 4 * m + 1),
        "anti": (x - y + 2 * m, ax_ - ay_ + 2 * m, sx - sy + 2 * m, 4 * m + 1),
        "row": (y + m, ay_ + m, sy + m, 2 * m + 1),
        "col": (x + m, ax_ + m, sx + m, 2 * m + 1),
    }
    for name, (all_idx, adm_idx, set_idx, nb) in families.items():
        cells = np.bincount(all_idx, minlength=nb).astype(float)
        cells_adm = np.bincount(adm_idx, minlength=nb).astype(float)
        obs = np.bincount(set_idx, minlength=nb).astype(float)
        out[f"{name}_dispersion_allint"] = dispersion(obs, cells)
        out[f"{name}_dispersion"] = dispersion(obs, cells_adm, correct=True)
    for suffix in ("", "_allint"):
        out[f"diag_dispersion{suffix}"] = 0.5 * (
            out[f"diag_dispersion{suffix}"] + out[f"anti_dispersion{suffix}"]
        )
    out["diag_over_row"] = out["diag_dispersion"] / max(out["row_dispersion"], 1e-9)
    return out


Representation(
    key="ulam_spiral",
    title="Ulam square spiral",
    question="do the set's members line up on the spiral's diagonals?",
    render=ulam_render,
    stats=ulam_stats,
    headline="diag_dispersion",
    iteration=1,
    panel_size=(5.6, 4.2),
    notes=(
        "Diagonals of the square spiral are values of quadratics 4k²+bk+c; rows and "
        "columns are not, and act as an internal control — `diag_over_row` is the "
        "ratio. The headline counts candidates from the integers coprime to 210 and "
        "applies the (1−ρ) correction, so the diagonals that are empty *because they "
        "are all even* no longer contribute; `diag_dispersion_allint` is the naive "
        "version that lets them count, and the gap between the two is how much of "
        "the famous diagonal effect is just parity."
    ),
    mechanism=(
        "Along any diagonal of this spiral n advances by 4k+const, so n mod 2 — and "
        "for half of them n mod 3 — is fixed. Every diagonal whose fixed residue "
        "shares a factor with 2 or 3 is empty of primes and the rest absorb the "
        "density, which is the whole of the naive statistic. Once candidates are "
        "restricted to integers coprime to 210 that mechanism is spent, and what is "
        "left is the same hyper-evenness seen in the modular sweep rather than a "
        "preference for particular quadratics."
    ),
)


# --- Sacks: square-root spiral ------------------------------------------------


def sacks_render(iset, sf, ctx):
    X, Y = ctx.sacks
    v = iset.values
    ax = sf.subplots(1, 1)
    ax.scatter(
        X[v], Y[v], s=1.5, c=SET_COLORS[iset.key], linewidths=0, alpha=0.95
    )
    lim = np.sqrt(ctx.N) * 1.02
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_aspect("equal")
    ax.set_title("r=√n, θ=2π√n", pad=6)
    bare(ax)


def _sacks_bins(N, nb=720):
    n = np.arange(N + 1, dtype=float)
    frac = np.modf(np.sqrt(n))[0]
    return np.minimum((frac * nb).astype(int), nb - 1), nb


def sacks_stats(iset, ctx):
    out = {}
    adm = np.flatnonzero(ctx.admissible)
    for nb in (360, 720):
        idx, nb = _sacks_bins(ctx.N, nb)
        cells = np.bincount(idx[2:], minlength=nb).astype(float)
        cells_adm = np.bincount(idx[adm], minlength=nb).astype(float)
        obs = np.bincount(idx[iset.values], minlength=nb).astype(float)
        out[f"ang_dispersion_allint_{nb}"] = dispersion(obs, cells)
        out[f"ang_dispersion_{nb}"] = dispersion(obs, cells_adm, correct=True)

    # A quadratic family only holds a fixed angle asymptotically -- it drifts by
    # O(1/k) -- so a global angular bin smears it. Measure angle within thin
    # radial annuli instead, where the drift is small, then average.
    nb, n_ann = 90, 8
    idx, _ = _sacks_bins(ctx.N, nb)
    root = np.sqrt(np.arange(ctx.N + 1, dtype=float))
    ann = np.minimum((root / (np.sqrt(ctx.N) / n_ann)).astype(int), n_ann - 1)
    vals = []
    for a in range(1, n_ann):
        sel_adm = adm[ann[adm] == a]
        v = iset.values[ann[iset.values] == a]
        if v.size < 2 * nb:
            continue
        cells = np.bincount(idx[sel_adm], minlength=nb).astype(float)
        obs = np.bincount(idx[v], minlength=nb).astype(float)
        vals.append(dispersion(obs, cells, correct=True))
    out["local_ang_dispersion"] = float(np.nanmean(vals)) if vals else float("nan")
    return out


Representation(
    key="sacks_spiral",
    title="Sacks square-root spiral",
    question="does the set concentrate on particular √n phase angles (i.e. quadratics)?",
    render=sacks_render,
    stats=sacks_stats,
    headline="local_ang_dispersion",
    iteration=1,
    panel_size=(5.0, 5.2),
    notes=(
        "Angle is 2π·frac(√n), so a quadratic n = k²+bk+c sits at a *nearly* fixed "
        "angle — it drifts by O(1/k), which is why the global binning is nearly "
        "blind and the headline uses thin radial annuli instead. Candidates are the "
        "integers coprime to 210, so a ray that exists only because its progression "
        "is all-even does not count."
    ),
    mechanism=(
        "frac(√n) is almost constant along k²+bk+c, so each quadratic progression "
        "is roughly one angular bin. Progressions that are identically even, or "
        "identically divisible by 3, hold no primes and the rest absorb the density "
        "— that is what the eye reads as rays, and the sieved null draws the same "
        "ones."
    ),
)
