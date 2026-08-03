"""NEW (iteration 1) -- centred modular walk.

A histogram of residues throws away order. This keeps it: walk through the
members in increasing order and, for each one, take a unit step in the plane at
angle 2π(n mod k)/k. The path accumulates the tiny per-member imbalances that a
histogram averages into invisibility, and turns a slow drift in *where* the
members sit mod k into a visible straight line.

Two corrections, both necessary or the plot only ever rediscovers divisibility:

  * members with gcd(n, k) > 1 are dropped, so the walk lives on the classes the
    set can actually occupy;
  * the mean step over the reduced classes is subtracted, so a set that is
    perfectly even across those classes has expectation zero.

After both, a perfectly equidistributed set gives a random walk: end-to-end
distance grows like √(steps), and drift = |displacement|/√steps is O(1) with no
trend. A drift that grows with the number of steps means the set favours some
reduced classes over others, persistently.
"""
from __future__ import annotations

import numpy as np

from ..registry import Representation
from ..theme import INK_MUTED, SET_COLORS, recessive

MODULI = (8, 9, 11, 13, 16, 25, 29)
SHOW = (8, 11, 13, 25)


def _steps(iset, k):
    v = iset.values
    v = v[np.gcd(v, k) == 1]
    j = np.arange(k)
    red = j[np.gcd(j, k) == 1]
    mu = np.exp(2j * np.pi * red / k).mean()
    return np.exp(2j * np.pi * (v % k) / k) - mu


def _scale(iset, ctx, k, s):
    """Radius an equidistributed set of this size would typically reach.

    Taking a fraction rho of the available integers leaves little room to
    fluctuate, so the displacement is smaller by sqrt(1-rho) than a free random
    walk. Without that factor every set occupying half the candidates looks
    'more ordered' than random by the same amount.
    """
    a = np.flatnonzero(ctx.admissible)
    n_cand = float((np.gcd(a, k) == 1).sum())
    rho = min(s.size / n_cand, 0.999) if n_cand else 0.0
    return float(np.sqrt(s.size * (1.0 - rho)))


def _drift(iset, ctx, k):
    """|displacement| in units of that radius: 1.0 = an ordinary random walk."""
    s = _steps(iset, k)
    if s.size < 10:
        return float("nan")
    return float(abs(s.sum()) / _scale(iset, ctx, k, s))


def walk_render(iset, sf, ctx):
    axes = sf.subplots(2, 2).ravel()
    for ax, k in zip(axes, SHOW):
        s = _steps(iset, k)
        w = np.cumsum(s)
        step = max(len(w) // 4000, 1)
        wt = w[::step]
        ax.plot(wt.real, wt.imag, color=SET_COLORS[iset.key], linewidth=1.0,
                alpha=0.95)
        # the circle an ordinary random walk would typically reach: drift = 1
        r = _scale(iset, ctx, k, s)
        t = np.linspace(0, 2 * np.pi, 200)
        ax.plot(r * np.cos(t), r * np.sin(t), color=INK_MUTED, linewidth=1.0,
                linestyle="--", alpha=0.8, zorder=1)
        ax.scatter([0], [0], s=14, c=INK_MUTED, zorder=3)
        ax.scatter([w[-1].real], [w[-1].imag], s=22,
                   c=SET_COLORS[iset.key], zorder=3)
        ax.set_title(f"k={k}   drift {abs(w[-1]) / r:.2f}", pad=4, fontsize=9)
        ax.set_aspect("equal")
        lim = max(np.abs(w).max(), r) * 1.12
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)
        recessive(ax)
        ax.tick_params(labelsize=7)


def walk_stats(iset, ctx):
    out, drifts = {}, []
    for k in MODULI:
        d = _drift(iset, ctx, k)
        if not np.isfinite(d):
            continue
        drifts.append(d)
        out[f"drift_k{k}"] = d
    out["walk_drift_mean"] = float(np.mean(drifts)) if drifts else float("nan")
    out["walk_drift_max"] = float(np.max(drifts)) if drifts else float("nan")
    return out


Representation(
    key="modular_walk",
    title="Centred modular walk",
    question="do the members drift persistently toward some reduced classes as n grows?",
    render=walk_render,
    stats=walk_stats,
    headline="walk_drift_mean",
    iteration=1,
    panel_size=(4.6, 4.6),
    notes=(
        "The dashed circle is the distance an ordinary random walk of that many "
        "steps would typically reach, so it is the drift = 1 contour and every "
        "panel is readable on its own terms despite the differing axis scales. A "
        "path that fills its circle and ends near the rim is equidistribution; one "
        "that sets off in a straight line past it is a persistent bias; one that "
        "stays huddled well inside — which is what the primes do — is a set spread "
        "*more* evenly than chance."
    ),
    mechanism=(
        "A drift *above* 1 would be a bias among the classes coprime to k — the set "
        "preferring some reduced residues by an amount that does not wash out as n "
        "grows. A drift well *below* 1, which is what the primes give, is the "
        "opposite: the walk keeps returning to the origin because the residues are "
        "spread more evenly than chance would spread them. It is the same "
        "hyper-evenness the modular sweep measures, seen as a path instead of a "
        "histogram."
    ),
)
