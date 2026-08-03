#!/usr/bin/env python3
"""Calibration runs that sit outside the main sweep.

Two jobs, both of which exist because a statistic that looks calibrated on one
control can be badly wrong on another:

  rough      compare the thinned rough null against the *unthinned* one. The
             thinning rule is a suspect in its own right, and separating it
             from the sieve structure needs both.

  deflation  confirm that the large-L sag in the fluctuation curve is the
             estimator and not the sets, using a matched-density Poisson
             control rather than a flat one. A flat control is what hid the
             first bug in this statistic, so it cannot be the thing that
             clears the second.

  python3 calibrate.py            # all three
  python3 calibrate.py deflation  # one of {deflation, rough, sweep}
"""
from __future__ import annotations

import sys

import numpy as np

from primeviz.context import Context
from primeviz.numbers import (
    IntegerSet,
    _log_weights,
    _scale_to_target,
    build_sets,
    make_rough,
)
from primeviz.reps.fluctuation import _cums, _scales, _z_at
from primeviz.reps.modgrid import modgrid_stats
from primeviz.reps.paircorr import pair_stats
from primeviz.reps.spirals import ulam_stats
from primeviz.reps.gaps import gaps_stats
from primeviz.reps.crt_lattice import crt_stats
from primeviz.reps.fluctuation import fluct_stats
from primeviz.reps.polar import polar_stats
from primeviz.reps.spirals import sacks_stats

N = 50_000


def _wrap(name, mask, n):
    return IntegerSet(name, name, "null", n, mask)


def flat_control(ctx, p=0.5, seed=1):
    """Constant density on the candidate pool -- no 1/ln n trend at all."""
    rng = np.random.default_rng(seed)
    return _wrap("flat", ctx.admissible & (rng.random(ctx.N + 1) < p), ctx.N)


def matched_poisson(ctx, target, seed=2):
    """Bernoulli with p proportional to 1/ln n on the candidate pool.

    Same density *profile* as the primes, and independent draws -- so any
    deflation it shows is the estimator, not a property of the primes.
    """
    rng = np.random.default_rng(seed)
    w = _log_weights(ctx.N).copy()
    w[~ctx.admissible] = 0.0
    p = _scale_to_target(w, target)
    return _wrap("poisson", (rng.random(ctx.N + 1) < p) & ctx.admissible, ctx.N)


def fluct_curve(iset, ctx):
    c, cc = _cums(iset, ctx)
    return [float((_z_at(c, cc, ctx.N, L)[1][_z_at(c, cc, ctx.N, L)[2]] ** 2).mean())
            for L in _scales(ctx.N)]


def run_deflation(ctx, sets, n_draw=12):
    print("\n=== large-L deflation: is it the estimator or the sets? ===")
    print("A flat control cannot settle this -- a flat control is what hid the")
    print("first bug in this statistic. The matched-density Poisson control has")
    print("the primes' density profile and independent draws. One draw is not")
    print("enough either: at the largest L only ~27 overlapping windows exist, so")
    print("the statistic itself is noisy. Hence an ensemble.\n")
    Ls = _scales(ctx.N)
    ens = np.array([
        fluct_curve(matched_poisson(ctx, sets["primes"].count, seed=100 + i), ctx)
        for i in range(n_draw)
    ])
    mu, sd = ens.mean(0), ens.std(0, ddof=1)

    print(f"{'L':>30s} " + " ".join(f"{L:>7d}" for L in Ls))
    print(f"{'matched-Poisson mean':>30s} " + " ".join(f"{v:7.2f}" for v in mu))
    print(f"{'matched-Poisson sd':>30s} " + " ".join(f"{v:7.2f}" for v in sd))
    for name, s in (
        ("flat control", flat_control(ctx)),
        ("sieved null (1 draw)", sets["sieved"]),
        ("primes", sets["primes"]),
    ):
        cur = np.array(fluct_curve(s, ctx))
        print(f"{name:>30s} " + " ".join(f"{v:7.2f}" for v in cur))
        if name == "primes":
            z = (cur - mu) / np.where(sd > 0, sd, np.nan)
            print(f"{'primes z vs ensemble':>30s} " + " ".join(f"{v:7.1f}" for v in z))

    trend = mu[-1] - mu[0]
    noisy = sd[-1] / max(mu[-1], 1e-9)
    print(f"\n  matched-Poisson trend across range: {mu[0]:.2f} -> {mu[-1]:.2f} "
          f"(change {trend:+.2f})")
    print(f"  its spread at the largest L: sd/mean = {noisy:.2f}")
    if abs(trend) < 0.25:
        print("  -> NOT CONFIRMED. The control does not sag, so the earlier claim of a")
        print("     systematic large-L deflation was wrong. What is real is that the")
        print("     statistic gets noisy at large L, where few independent windows fit;")
        print("     a single sieved-null draw sagging was that noise, not an estimator")
        print("     bias. Only the ensemble z is interpretable out there.")
    else:
        print("  -> CONFIRMED: the matched-density control reproduces the sag.")


def run_bound_sweep(ctx, sets):
    """Does the rough set converge on the primes as the sieve bound rises?

    This is the honest way to handle the density confound. A rough set at
    bound 47 is ~35% denser than the primes and cannot be thinned to match
    without a thinning rule that wrecks it. But the bound itself is a dial:
    raise it and both the density and the statistics should slide toward the
    primes -- and at bound ~sqrt(N) the rough set simply *is* the primes,
    because a composite with no factor below sqrt(N) does not fit under N.
    """
    print("\n=== sieve-bound sweep (all unthinned, no thinning rule involved) ===")
    print("As the bound rises the rough set converges on the primes by construction:")
    print(f"past sqrt(N) = {int(ctx.N**0.5)} the only survivors are primes. Watch whether")
    print("the statistics slide with it.\n")
    rows = []
    for b in (7, 13, 23, 47, 97, 199):
        s = make_rough(ctx.N, None, 0, bound=b, thin=False)
        rows.append((f"rough<={b}", s))
    rows.append(("primes", sets["primes"]))
    cols = [
        ("mod_grid", modgrid_stats, "reduced_dispersion"),
        ("fluct_sL", fluct_stats, "fluct_dispersion_small_L"),
        ("ulam_diag", ulam_stats, "diag_dispersion"),
        ("crt_indep", crt_stats, "crt_independence"),
        ("gap_lag1", gaps_stats, "gap_lag1_corr"),
        ("polar_710", polar_stats, "ang_dispersion_710"),
        ("sacks", sacks_stats, "local_ang_dispersion"),
        ("deep_ratio", pair_stats, "deep_sieve_ratio"),
    ]
    print(f"{'set':12s} {'count':>7s} {'density':>8s} "
          + " ".join(f"{c[0]:>10s}" for c in cols))
    for name, s in rows:
        vals = " ".join(f"{fn(s, ctx).get(k, float('nan')):10.3f}" for _, fn, k in cols)
        print(f"{name:12s} {s.count:7,d} {s.density:8.4f} {vals}")
    print("\n  rough<=7 is degenerate: that set IS the candidate pool, so the (1-rho)")
    print("  correction divides by zero. The row is left in to show why it is unusable.")


def run_rough(ctx, sets):
    print("\n=== thinned vs unthinned rough null ===")
    print("The thinned set matches the primes' density but its thinning rule")
    print("imposes near-regular spacing. The unthinned set has the sieve")
    print("structure with nothing imposed on its counts.\n")
    thinned = sets["rough"]
    unthinned = make_rough(ctx.N, None, sets["primes"].count, thin=False)
    print(f"  counts: primes={sets['primes'].count:,}  thinned={thinned.count:,}  "
          f"unthinned={unthinned.count:,}\n")

    checks = [
        ("modular_grid.reduced_dispersion", modgrid_stats, "reduced_dispersion"),
        ("count_fluctuation.small_L", fluct_stats, "fluct_dispersion_small_L"),
        ("crt_lattice.crt_independence", crt_stats, "crt_independence"),
        ("prime_gaps.gap_lag1_corr", gaps_stats, "gap_lag1_corr"),
        ("ulam.diag_dispersion", ulam_stats, "diag_dispersion"),
        ("ulam.diag_over_row", ulam_stats, "diag_over_row"),
        ("pair.deep_sieve_ratio", pair_stats, "deep_sieve_ratio"),
        ("pair.pair_corr_dispersion", pair_stats, "pair_corr_dispersion"),
    ]
    cache: dict = {}

    def val(fn, key, s):
        ck = (fn.__name__, s.key, id(s))
        if ck not in cache:
            cache[ck] = fn(s, ctx)
        return cache[ck].get(key, float("nan"))

    print(f"{'statistic':34s} {'primes':>9s} {'sieved':>9s} {'thinned':>9s} {'unthinned':>10s}")
    for label, fn, key in checks:
        row = [val(fn, key, s) for s in
               (sets["primes"], sets["sieved"], thinned, unthinned)]
        print(f"{label:34s} " + " ".join(f"{v:9.3f}" for v in row[:3]) + f" {row[3]:10.3f}")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    ctx = Context(N=N)
    sets = build_sets(N, 0)
    if which in ("both", "deflation"):
        run_deflation(ctx, sets)
    if which in ("both", "rough"):
        run_rough(ctx, sets)
    if which in ("both", "sweep"):
        run_bound_sweep(ctx, sets)
