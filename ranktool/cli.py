"""Command line interface.

    python -m ranktool --short A B          y^2 = x^3 + A x + B
    python -m ranktool --model a b          y^2 = x(x^2 + a x + b)
    python -m ranktool --weierstrass a1 a2 a3 a4 a6
    python -m ranktool --congruent N        y^2 = x^3 - N^2 x
"""

from __future__ import annotations

import argparse
import sys

from .curve import Curve, Singular
from .rank import analyse, format_certificate


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ranktool",
        description="Unconditional algebraic rank of an elliptic curve over Q.",
        epilog="The rank is only reported when it is proved from both sides.",
    )
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--short", nargs=2, type=int, metavar=("A", "B"),
                   help="y^2 = x^3 + A x + B")
    g.add_argument("--model", nargs=2, type=int, metavar=("a", "b"),
                   help="y^2 = x(x^2 + a x + b)")
    g.add_argument("--weierstrass", nargs=5, type=int,
                   metavar=("a1", "a2", "a3", "a4", "a6"),
                   help="y^2 + a1 xy + a3 y = x^3 + a2 x^2 + a4 x + a6")
    g.add_argument("--congruent", type=int, metavar="N",
                   help="the congruent-number curve y^2 = x^3 - N^2 x")
    p.add_argument("--search", type=int, default=900,
                   help="final point-search bound (default 900)")
    p.add_argument("--quiet", action="store_true",
                   help="print just the verdict line")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.short:
        E = Curve(0, 0, 0, args.short[0], args.short[1])
    elif args.model:
        a, b = args.model
        E = Curve(0, a, 0, b, 0)
    elif args.weierstrass:
        E = Curve(*args.weierstrass)
    else:
        n = args.congruent
        E = Curve(0, 0, 0, -n * n, 0)

    bounds = tuple(sorted({60, 250, args.search}))
    cert = analyse(E, search_bounds=bounds)

    if args.quiet:
        if cert.certified:
            print(f"rank = {cert.rank}  [proved]")
        else:
            print(f"{cert.rank_lower} <= rank <= {cert.rank_upper}  [undecided]")
    else:
        print(format_certificate(cert))
    return 0 if cert.certified else 2


if __name__ == "__main__":  # pragma: no cover
    try:
        sys.exit(main())
    except Singular as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(3)
