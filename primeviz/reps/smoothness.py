"""NEW (iteration 3) -- the smoothness landscape.

Every representation before this one is a function of two things: the set's
density, and how it spreads over residue classes to small moduli. That is
exactly the data a sieve has, and it is why none of them can separate the primes
from a set of matched sieve data that happens to contain semiprimes.

This one looks at the other end of the factorisation. Colour each integer by

    r(n) = log(largest prime factor of n) / log n

which is 1 exactly when n is prime, near 0 when n is built from small factors,
and in between otherwise. Rendering r over the number line turns the integers
from a binary set into a continuum, and the primes stop being "the marked
points" and become the r = 1 edge of a landscape.

**This is circular and must not be read as a result.** Computing r requires
factoring n, so the instrument is told the answer before it draws anything: of
course it separates the primes, they are its own boundary case. It earns its
place as an instrument for *understanding* -- for seeing what the difference
between the primes and a rough set actually consists of, and where in the
landscape the sieve barrier sits -- and never as evidence. Any statistic it
reports separates trivially and is reported only to make that separation legible.
"""
from __future__ import annotations

import numpy as np

from ..registry import Representation
from ..theme import INK_MUTED, SEQ_CMAP, SET_COLORS, SURFACE, recessive
from matplotlib.colors import LinearSegmentedColormap

NB_N, NB_R = 320, 200


def _ratio(ctx) -> np.ndarray:
    """log(largest prime factor) / log n, for every n in 2..N."""
    if "lpf_ratio" not in ctx.cache:
        lpf = np.zeros(ctx.N + 1, dtype=np.int32)
        # increasing p, so the last write to each n is its largest prime factor
        for p in np.flatnonzero(ctx.prime_mask):
            lpf[p :: p] = p
        n = np.arange(ctx.N + 1, dtype=np.float64)
        with np.errstate(divide="ignore", invalid="ignore"):
            r = np.log(np.maximum(lpf, 1)) / np.log(np.maximum(n, 2))
        r[:2] = np.nan
        ctx.cache["lpf_ratio"] = r.astype(np.float32)
    return ctx.cache["lpf_ratio"]


def smooth_render(iset, sf, ctx):
    r = _ratio(ctx)
    v = iset.values
    axes = sf.subplots(2, 1, gridspec_kw={"height_ratios": [1.3, 1]})

    # the landscape: all integers in grey, this set's members over the top
    ax = axes[0]
    nn = ctx.integers
    rng = [[2, ctx.N], [0, 1]]
    Hall, _, _ = np.histogram2d(nn, r[2 : ctx.N + 1], bins=[NB_N, NB_R], range=rng)
    ax.imshow(np.log1p(Hall.T), origin="lower", aspect="auto",
              extent=[2, ctx.N, 0, 1],
              cmap=LinearSegmentedColormap.from_list("g", [SURFACE, "#5a5a52"]),
              interpolation="nearest")
    Hset, _, _ = np.histogram2d(v, r[v], bins=[NB_N, NB_R], range=rng)
    masked = np.ma.masked_where(Hset.T == 0, np.log1p(Hset.T))
    ax.imshow(masked, origin="lower", aspect="auto", extent=[2, ctx.N, 0, 1],
              cmap=LinearSegmentedColormap.from_list(
                  "s", [SURFACE, SET_COLORS[iset.key]]),
              interpolation="nearest")
    ax.set_xlabel("n")
    ax.set_ylabel("log(largest prime factor) / log n")
    ax.set_title("the set inside the smoothness landscape", pad=6)
    recessive(ax)
    ax.grid(False)

    # where the set sits in r
    ax = axes[1]
    rv = r[v]
    rv = rv[np.isfinite(rv)]
    ax.hist(rv, bins=np.linspace(0, 1, 101), color=SET_COLORS[iset.key])
    ax.axvline(1.0, color=INK_MUTED, linestyle="--", linewidth=1.2)
    ax.annotate("r = 1 is prime", (1.0, ax.get_ylim()[1] * 0.7), color=INK_MUTED,
                fontsize=8, ha="right", xytext=(-4, 0), textcoords="offset points")
    ax.set_yscale("log")
    ax.set_xlabel("r(n)")
    ax.set_ylabel("count (log)")
    ax.set_title(f"distribution of r   ·   mean {rv.mean():.3f}", pad=6)
    recessive(ax)


def smooth_stats(iset, ctx):
    r = _ratio(ctx)[iset.values]
    r = r[np.isfinite(r)]
    return {
        "mean_log_lpf_ratio": float(r.mean()),
        "frac_prime": float((r >= 0.999).mean()),
        "frac_r_below_half": float((r < 0.5).mean()),
        "min_r": float(np.percentile(r, 1)),
    }


Representation(
    key="smoothness_landscape",
    title="Smoothness landscape — log(largest prime factor)/log n",
    question="what does the difference between these sets actually consist of?",
    render=smooth_render,
    stats=smooth_stats,
    headline="mean_log_lpf_ratio",
    iteration=3,
    panel_size=(5.2, 5.0),
    notes=(
        "Circular by construction — see below — so read it as a diagram, not a "
        "test. The grey background is every integer; the coloured overlay is the "
        "set. The primes are a single line along the top because r = 1 *defines* "
        "prime. A rough ≤ b set is a band whose floor is log b / log n, sagging to "
        "the right as log n grows: everything below that floor has been sieved "
        "away. The Cramér null fills the whole landscape because it is drawn "
        "without regard to factorisation. The gap between the primes' line and the "
        "rough band is the set of semiprimes and higher almost-primes that no "
        "sieve-data statistic in this harness can see."
    ),
    mechanism=(
        "It separates the primes perfectly and this proves nothing: r(n) is "
        "computed *from* the factorisation of n, so the instrument is handed the "
        "answer before it draws. Its value is diagnostic — it makes visible the "
        "region where the parity barrier lives, namely the band between r = 1 and "
        "the rough floor, which is exactly the almost-primes that share all their "
        "small-residue statistics with the primes."
    ),
)
