"""NEW -- multiscale count-fluctuation map.

Iteration 1 kept finding the same thing in residue space: the primes are spread
*more* evenly than a random set of matched density. This asks the same question
in position space, where residues play no part at all.

Slide a window of length L along the integers, count how many members fall in
it, and compare with how many the local density says should. Standardise, and
you get one number per (position, scale). Stack the scales and you have an
image: horizontal is where you are on the number line, vertical is how wide a
window you looked through, colour is how far off the count was.

The local density is estimated from a window twenty times wider, so the smooth
1/ln n thinning is divided out and only genuine fluctuation is left. A set
sprinkled at random with constant density gives standardised deviations of
variance 1 at every scale; below 1 is a set that resists clumping.

Calibration was not free, and both problems it turned up looked like findings:

  * with the density window uncapped it saturates at N, stops being local, and
    the 1/ln n trend leaks straight back in -- inflating every density-varying
    set tenfold at the largest scales while leaving a flat control at 1.0;
  * windows whose density window overran either end of the range carry a
    miscentred estimate, which showed up as a red stripe at low n.

With both fixed a flat control reads 1.00-1.05 at the smallest scales.

A third claim -- that a residual *systematic* deflation remained at large L --
was made here and is now retracted. It rested on one draw of the sieved null
sagging from 0.98 to 0.53. An ensemble of twelve matched-density Poisson draws
does not sag at all (0.94 -> 0.82, well inside its own spread), so there is no
estimator bias to correct. What is true is narrower: at the largest L only ~27
heavily overlapping windows fit, the statistic's own spread there is sd/mean
~ 0.26, and a single draw wanders. The curve is still informative -- the primes
sit 3 to 6 sd below the matched-density ensemble at *every* scale, not just the
small ones -- but only the ensemble z is worth reading at large L.
"""
from __future__ import annotations

import numpy as np

from ..registry import Representation
from ..theme import DIV_CMAP, INK_MUTED, SET_COLORS, recessive

N_SCALES = 13
GRID_W = 340


SMOOTH_RATIO = 20  # local density window, as a multiple of the measurement window


def _scales(N):
    """Measurement scales.

    The ceiling is not cosmetic. The local density is estimated from a window
    SMOOTH_RATIO times wider, and that wider window cannot exceed N; once it
    saturates, the estimate stops being local and the smooth 1/ln n thinning
    leaks into the statistic as if it were fluctuation. It inflates every
    density-varying set by an order of magnitude at L = N/8 while leaving a
    flat control at 1.0 -- i.e. it looks exactly like a real effect. So L is
    capped at N/SMOOTH_RATIO and the usable scale range grows with N.
    """
    return np.unique(
        np.geomspace(max(N // 400, 120), max(N // SMOOTH_RATIO, 400), N_SCALES).astype(int)
    )


def _cums(iset, ctx):
    m = np.zeros(ctx.N + 1, dtype=np.int64)
    m[iset.values] = 1
    return np.cumsum(m), np.cumsum(ctx.admissible.astype(np.int64))


def _z_at(c, cc, N, L):
    """Standardised count deviation for every window of length L."""
    step = max(L // 2, 1)
    starts = np.arange(0, max(N - L, 1), step)
    obs = (c[starts + L] - c[starts]).astype(float)
    cand = (cc[starts + L] - cc[starts]).astype(float)

    # local density from a much wider window, so the 1/ln n trend is removed
    S = int(min(max(SMOOTH_RATIO * L, 4000), N // 3))
    ctr = starts + L // 2
    hi = np.clip(ctr + S // 2, S, N)
    lo = hi - S
    rho = (c[hi] - c[lo]) / np.maximum(cc[hi] - cc[lo], 1)

    exp = cand * rho
    var = np.maximum(exp * (1.0 - rho), 1e-9)
    # drop windows whose density window ran into either end of the range: there
    # the local estimate is not centred and the edge shows up as a red stripe
    ok = (exp > 0) & (ctr >= S // 2) & (ctr <= N - S // 2)
    z = np.zeros_like(obs)
    z[ok] = (obs[ok] - exp[ok]) / np.sqrt(var[ok])
    return ctr, z, ok


def fluct_render(iset, sf, ctx):
    c, cc = _cums(iset, ctx)
    Ls = _scales(ctx.N)
    img = np.full((len(Ls), GRID_W), np.nan)
    grid = np.linspace(0, ctx.N, GRID_W)
    curve = []
    for i, L in enumerate(Ls):
        ctr, z, ok = _z_at(c, cc, ctx.N, L)
        img[i] = np.interp(grid, ctr[ok], z[ok], left=np.nan, right=np.nan)
        curve.append(float((z[ok] ** 2).mean()))

    axes = sf.subplots(2, 1, gridspec_kw={"height_ratios": [1.35, 1]})
    ax = axes[0]
    im = ax.imshow(img, aspect="auto", origin="lower", cmap=DIV_CMAP,
                   vmin=-3, vmax=3, interpolation="nearest",
                   extent=[0, ctx.N, -0.5, len(Ls) - 0.5])
    ax.set_yticks(range(0, len(Ls), 3))
    ax.set_yticklabels([f"{Ls[i]:,}" for i in range(0, len(Ls), 3)])
    ax.set_ylabel("window length L")
    ax.set_xlabel("n")
    ax.set_title("standardised count deviation", pad=6)
    sf.colorbar(im, ax=ax, fraction=0.04, pad=0.02, ticks=[-3, 0, 3])

    ax = axes[1]
    ax.plot(Ls, curve, color=SET_COLORS[iset.key], marker="o", markersize=4)
    ax.axhline(1.0, color=INK_MUTED, linestyle="--", linewidth=1.2)
    ax.annotate("random = 1", (Ls[0], 1.0), color=INK_MUTED, fontsize=8,
                xytext=(2, 4), textcoords="offset points")
    ax.set_xscale("log")
    ax.set_ylim(0, 3.2)  # fixed across all three panels so they can be compared
    ax.set_xticks([200, 500, 1000, 2000])
    ax.set_xticklabels(["200", "500", "1k", "2k"])
    ax.minorticks_off()
    ax.set_xlabel("window length L")
    ax.set_ylabel("variance of deviation")
    ax.set_title("fluctuation vs scale", pad=6)
    recessive(ax)


def fluct_stats(iset, ctx):
    c, cc = _cums(iset, ctx)
    Ls = _scales(ctx.N)
    vals = []
    for L in Ls:
        _, z, ok = _z_at(c, cc, ctx.N, L)
        vals.append(float((z[ok] ** 2).mean()))
    vals = np.array(vals)
    return {
        "fluct_dispersion": float(vals.mean()),
        "fluct_dispersion_small_L": float(vals[: len(vals) // 3].mean()),
        "fluct_dispersion_large_L": float(vals[-len(vals) // 3 :].mean()),
        "fluct_slope": float(
            np.polyfit(np.log(Ls.astype(float)), np.log(np.maximum(vals, 1e-6)), 1)[0]
        ),
    }


Representation(
    key="count_fluctuation",
    title="Multiscale count-fluctuation map",
    question="at any scale, does the set clump or resist clumping along the number line?",
    render=fluct_render,
    stats=fluct_stats,
    headline="fluct_dispersion_small_L",
    iteration=2,
    panel_size=(5.2, 5.0),
    notes=(
        "The map is a scale-space view: one row per window length, colour is how "
        "many standard deviations the count in that window sat from its local "
        "expectation. Grey everywhere means fluctuation exactly as large as chance "
        "predicts. Red and blue patches that persist upward through the rows are "
        "genuine excursions — a run of the number line that is rich or poor at "
        "several scales at once. The curve below collapses each row to a single "
        "number, and the dashed line is what a randomly sprinkled set gives. "
        "Two calibration facts. (1) A single curve's downward slope at large L is "
        "mostly noise, not signal and not estimator bias: only ~27 overlapping "
        "windows fit at the widest scale and the statistic's own spread there is "
        "sd/mean ≈ 0.26. A twelve-draw matched-density Poisson ensemble does not "
        "trend (0.94 → 0.82). Read the gap between curves, not the slope of one — "
        "the primes sit 3–6 sd below that ensemble at every scale. (2) The Cramér "
        "column runs ~1.6× high because that null lives on all integers while the "
        "candidate pool is the integers coprime to 210, so its binomial variance is "
        "mismatched. Read the sieved column: it shares both the support and the "
        "density profile of the primes. The headline uses the smallest third of "
        "scales, where the control sits at 1.0 and the sieved null at 0.95."
    ),
    mechanism=(
        "Values below 1 mean the count in a window is pinned closer to its "
        "expectation than independent sampling would allow — the same hyper-evenness "
        "the modular sweep found, but with no reference to residues at all, so it "
        "cannot be a divisibility effect in disguise."
    ),
)
