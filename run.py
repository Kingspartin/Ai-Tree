#!/usr/bin/env python3
"""Blind visual search for structure in the primes.

  python3 run.py                       # iteration 1, N = 50,000
  python3 run.py --quick               # fast smoke test, N = 20,000
  python3 run.py --umap                # add UMAP alongside PCA (slow)
  python3 run.py --iteration 2         # adds any representations tagged iteration 2
  python3 run.py --only modular_grid   # re-render one representation
  python3 run.py --list                # what is registered
"""
from __future__ import annotations

import argparse

from primeviz.context import Context
from primeviz.registry import selected
from primeviz.runner import run_iteration


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-N", type=int, default=50_000)
    ap.add_argument("--iteration", type=int, default=1)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--reps", type=int, default=12, help="null replicates per model")
    ap.add_argument("--umap-max", type=int, default=20_000)
    ap.add_argument("--umap", action="store_true", help="opt in; ~1 min per set")
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--out", default="out")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    if a.list:
        for r in selected(iteration_max=99):
            print(f"  [iter {r.iteration}] {r.key:22s} {r.title}")
        return

    if a.quick:
        a.N, a.reps, a.umap = min(a.N, 20_000), 6, False

    ctx = Context(
        N=a.N,
        seed=a.seed,
        n_rep=a.reps,
        umap_max=a.umap_max,
        use_umap=a.umap,
        out_dir=a.out,
    )
    run_iteration(ctx, a.iteration, only=a.only)


if __name__ == "__main__":
    main()
