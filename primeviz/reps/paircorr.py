"""NEW -- all-pairs difference spectrum.

The gap representation only ever looks at neighbours: it sees the step from one
member to the next and nothing further. This looks at every pair. For each
distance d, count how many n have both n and n+d in the set, and divide by how
many *candidate* integers form such a pair.

Dividing by the candidate count is what makes it worth plotting. Among integers
coprime to 210 the pairs at distance d are already wildly uneven -- d divisible
by 6 has far more of them than d ≡ 1 -- and that unevenness is the entire
content of the raw difference histogram. Normalising it away leaves the question
that is actually open: given how many chances a distance gets, is it taken more
often than chance?

The second panel repeats the calculation in bands of n, so a distance that is
favoured only in part of the range cannot hide inside the average.
"""
from __future__ import annotations

import numpy as np

from ..registry import Representation
from ..stats import dispersion
from ..theme import DIV_CMAP, INK_MUTED, SET_COLORS, recessive

DMAX = 240
N_BANDS = 6


def _pair_counts(mask: np.ndarray, dmax: int) -> np.ndarray:
    """counts[d-1] = #{n : n and n+d both in mask}."""
    m = mask.astype(np.float32)
    return np.array([float(m[:-d] @ m[d:]) for d in range(1, dmax + 1)])


def _member_mask(iset, ctx):
    m = np.zeros(ctx.N + 1, dtype=bool)
    m[iset.values] = True
    return m


def _ratio(obs, cand):
    tot = obs.sum()
    exp = cand * (tot / max(cand.sum(), 1))
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(exp > 0, obs / exp, np.nan)


def pair_render(iset, sf, ctx):
    mm, am = _member_mask(iset, ctx), ctx.admissible
    obs, cand = _pair_counts(mm, DMAX), _pair_counts(am, DMAX)
    d = np.arange(1, DMAX + 1)
    C = _ratio(obs, cand)

    # only distances a pair of candidates can actually span: both are coprime to
    # 210 hence odd, so every odd d is empty by construction and would otherwise
    # break the line into invisible one-point segments
    use = cand > 0
    du = d[use]

    axes = sf.subplots(2, 1, gridspec_kw={"height_ratios": [1, 1.15]})
    ax = axes[0]
    ax.plot(du, C[use], color=SET_COLORS[iset.key], linewidth=1.2)
    ax.axhline(1.0, color=INK_MUTED, linestyle="--", linewidth=1.2)
    ax.annotate("chance = 1", (du[0], 1.0), color=INK_MUTED, fontsize=8,
                xytext=(2, 5), textcoords="offset points")
    ax.set_xlabel("difference d  (odd d impossible, omitted)")
    ax.set_ylabel("obs / chance")
    ax.set_ylim(0.4, 1.6)
    ax.set_title("pairs at distance d, per candidate pair", pad=6)
    recessive(ax)

    edges = np.linspace(2, ctx.N, N_BANDS + 1).astype(int)
    img = np.full((N_BANDS, int(use.sum())), np.nan)
    for b in range(N_BANDS):
        lo, hi = edges[b], edges[b + 1]
        band = np.zeros_like(mm)
        band[lo:hi] = True
        img[b] = _ratio(_pair_counts(mm & band, DMAX), _pair_counts(am & band, DMAX))[use]
    ax = axes[1]
    im = ax.imshow(img, aspect="auto", origin="lower", cmap=DIV_CMAP,
                   vmin=0.6, vmax=1.4, interpolation="nearest",
                   extent=[du[0], du[-1], -0.5, N_BANDS - 0.5])
    ax.set_yticks(range(N_BANDS))
    ax.set_yticklabels([f"{edges[b]//1000}k" for b in range(N_BANDS)])
    ax.set_ylabel("band start")
    ax.set_xlabel("difference d")
    ax.set_title("same ratio, split by position", pad=6)
    sf.colorbar(im, ax=ax, fraction=0.04, pad=0.02, ticks=[0.6, 1.0, 1.4])


DEEP_PRIMES = (11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47)


def _deep_mask(dmax=DMAX):
    """Distances sharing a factor with a prime the sieved null does not know."""
    d = np.arange(1, dmax + 1)
    m = np.zeros(dmax, dtype=bool)
    for p in DEEP_PRIMES:
        m |= d % p == 0
    return m


def pair_stats(iset, ctx):
    mm, am = _member_mask(iset, ctx), ctx.admissible
    obs, cand = _pair_counts(mm, DMAX), _pair_counts(am, DMAX)
    C = _ratio(obs, cand)
    fin = np.isfinite(C)
    deep = _deep_mask()
    a, b = C[fin & deep], C[fin & ~deep]
    return {
        "pair_corr_dispersion": dispersion(obs, cand),
        "pair_corr_spread": float(C[fin].std()),
        # the diagnostic: how much richer are distances divisible by a prime
        # between 11 and 47 -- exactly the primes the sieved null cannot see
        "deep_sieve_ratio": float(a.mean() / b.mean()) if b.size else float("nan"),
        "pair_corr_max": float(C[fin].max()),
        "pair_corr_min": float(C[fin].min()),
    }


Representation(
    key="pair_spectrum",
    title="All-pairs difference spectrum",
    question="is any distance between members taken more often than its number of chances?",
    render=pair_render,
    stats=pair_stats,
    headline="pair_corr_dispersion",
    iteration=2,
    panel_size=(5.2, 5.0),
    notes=(
        "Both panels are already normalised by candidate pairs, so a flat grey line "
        "at 1 is the honest null result and the spikes of a raw difference histogram "
        "have deliberately been divided out. Only even distances appear: two members "
        "coprime to 210 are both odd, so an odd separation is impossible and those "
        "columns are empty by construction, not by absence of structure. Read the "
        "lower panel for vertical stripes that hold across every band — a distance "
        "favoured throughout the range is a much stronger claim than one favoured on "
        "average. The Cramér column sits far below 1 for a mechanical reason rather "
        "than an interesting one: that null lives on all integers while the "
        "normalisation counts candidate pairs among the integers coprime to 210."
    ),
    mechanism=(
        "Not memory, and not new: this is the sieved null's 7 showing. When d shares "
        "a factor p with one of 11…47, the pair (n, n+d) occupies a single residue "
        "class mod p instead of two, so it has one fewer way to be composite and "
        "both ends are likelier to be prime. `deep_sieve_ratio` isolates it — the "
        "primes read ≈1.06, the sieved null ≈1.00, because that null only avoids "
        "factors up to 7 and so has no opinion about 11 through 47. It is the same "
        "mechanism suspected behind the surviving Ulam diagonals, here measured "
        "directly instead of hypothesised. A null sieved at 47 or higher should "
        "erase this verdict; that is the test worth running next."
    ),
)
