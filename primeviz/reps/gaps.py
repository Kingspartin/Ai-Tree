"""The set as a point process: consecutive differences.

Everything here is derived from the sorted members alone -- no layout, no
projection -- which makes it the hardest representation to fool. If a picture
elsewhere is really about spacing, it should show up here too.
"""
from __future__ import annotations

import numpy as np

from ..registry import Representation
from ..theme import DIV_CMAP, SEQ_CMAP, SET_COLORS, INK_MUTED, recessive

MAXG = 60


def _gaps(iset):
    v = iset.values
    return np.diff(v).astype(float), v[:-1]


def gaps_render(iset, sf, ctx):
    g, at = _gaps(iset)
    mg = g.mean()
    axes = sf.subplots(1, 3, gridspec_kw={"width_ratios": [1.15, 1, 1.15]})

    ax = axes[0]
    ax.scatter(at, g, s=0.6, c=SET_COLORS[iset.key], alpha=0.35, linewidths=0)
    w = max(len(g) // 120, 1)
    trim = len(g) - len(g) % w
    ax.plot(at[:trim].reshape(-1, w).mean(1), g[:trim].reshape(-1, w).max(1),
            color=INK_MUTED, linewidth=1.4, label="running max")
    ax.set_title("gap vs position", pad=6)
    ax.set_xlabel("n")
    ax.set_ylabel("gap")
    ax.legend(loc="upper left")
    recessive(ax)

    ax = axes[1]
    edges = np.arange(0.5, MAXG + 1.5)
    ax.hist(g, bins=edges, color=SET_COLORS[iset.key], alpha=0.9)
    ax.axvline(mg, color=INK_MUTED, linewidth=1.4, linestyle="--")
    ax.annotate(f"mean {mg:.2f}", (mg, ax.get_ylim()[1] * 0.92),
                color=INK_MUTED, fontsize=8, xytext=(4, 0),
                textcoords="offset points")
    ax.set_title("gap histogram", pad=6)
    ax.set_xlabel("gap")
    ax.set_ylabel("count")
    ax.set_xlim(0, MAXG)
    recessive(ax)

    ax = axes[2]
    lim = min(MAXG, int(np.percentile(g, 99.9)) + 2)
    H, _, _ = np.histogram2d(g[:-1], g[1:], bins=[np.arange(0.5, lim + 1.5)] * 2)
    exp = np.outer(H.sum(1), H.sum(0)) / max(H.sum(), 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        R = np.where(exp > 8, H / exp, np.nan)
    im = ax.imshow(R.T, origin="lower", cmap=DIV_CMAP, vmin=0.4, vmax=1.6, aspect="auto",
                   extent=[0.5, lim + 0.5, 0.5, lim + 0.5], interpolation="nearest")
    ax.set_title("gap pair, obs / independent", pad=6)
    ax.set_xlabel("gₖ")
    ax.set_ylabel("gₖ₊₁")
    sf.colorbar(im, ax=ax, fraction=0.045, pad=0.03)
    recessive(ax)


def gaps_stats(iset, ctx):
    g, _ = _gaps(iset)
    mg = g.mean()
    a, b = g[:-1], g[1:]
    corr = float(np.corrcoef(a, b)[0, 1]) if g.size > 3 else np.nan
    return {
        "gap_var_ratio": float(g.var() / mg**2),
        "gap_lag1_corr": corr,
        "frac_gap_div6": float((g % 6 == 0).mean()),
        "frac_gap_even": float((g % 2 == 0).mean()),
        "max_gap_over_mean": float(g.max() / mg),
    }


Representation(
    key="prime_gaps",
    title="Gap series, gap histogram, gap-pair map",
    question="is the spacing sequence anything other than a memoryless point process?",
    render=gaps_render,
    stats=gaps_stats,
    headline="gap_lag1_corr",
    iteration=1,
    panel_size=(5.6, 3.8),
    notes=(
        "The third panel divides the observed (gₖ, gₖ₊₁) table by what it would be "
        "if consecutive gaps were independent, so grey is 'no memory' and any "
        "coloured cell is a gap pair that happens more or less often than chance. "
        "The histogram's spikes at multiples of 6 are the thing to be suspicious of."
    ),
    mechanism=(
        "Consecutive members that are all odd force every gap even, and members "
        "avoiding 3 as well push gaps toward multiples of 6 -- both are consequences "
        "of small-factor avoidance, and a null with the same avoidance shows the "
        "same spikes. Any lag-1 correlation beyond that would be genuine memory."
    ),
)
