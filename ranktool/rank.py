"""The rank engine: bracket the rank from both sides and certify when they meet.

    lower bound  <=  rank E(Q)  <=  upper bound

  * the lower bound is proved by exhibiting rational points,
  * the upper bound is proved by local obstructions (descent),
  * neither uses any property of Ш.

If the two coincide the rank is a theorem, and finiteness/triviality of the
relevant part of Ш is a *corollary* of the computation rather than an input to
it.  If they do not coincide the tool says so, and says exactly how large the
residual ambiguity is.  It never fills the gap with an assumption.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction as F
from math import gcd

from .arith import sqrt_exact
from .curve import Curve, DescentModel, Point, two_torsion_models
from .descent import DescentResult, two_isogeny_descent
from .height import HeightEngine, Interval


@dataclass
class Certificate:
    curve: Curve
    rank_lower: int | None = None
    rank_upper: int | None = None
    method: str = ""
    model: DescentModel | None = None
    descent: DescentResult | None = None
    points: list = field(default_factory=list)          # on the input curve
    independent_pair: tuple | None = None
    independent_count: int = 0
    regulator: Interval | None = None
    height_constant: float | None = None
    notes: list = field(default_factory=list)
    all_runs: list = field(default_factory=list)
    torsion_hint: str = ""

    @property
    def certified(self) -> bool:
        return (
            self.rank_lower is not None
            and self.rank_upper is not None
            and self.rank_lower == self.rank_upper
        )

    @property
    def rank(self) -> int | None:
        return self.rank_lower if self.certified else None


# ------------------------------------------------------------ helpers ------


def direct_point_search(E: Curve, bound: int = 200) -> list[Point]:
    """Naive search for rational points on the integral short model.

    X = m/k^2, Y = n/k^3 with gcd(m,k)=1, so n^2 = m^3 + A m k^4 + B k^6.
    Every hit is an honest point; this only ever raises the lower bound.
    """
    A, B = E.short_model()
    out = []
    for k in range(1, int(bound ** 0.5) + 2):
        k2 = k * k
        k4 = k2 * k2
        k6 = k4 * k2
        for m in range(-bound, bound + 1):
            if gcd(m, k) != 1:
                continue
            val = m * m * m + A * m * k4 + B * k6
            n = sqrt_exact(val)
            if n is not None:
                out.append(Point(F(m, k2), F(n, k * k * k)))
    return out


def _infinite_order(E: Curve, P: Point) -> bool:
    """Mazur: a rational torsion point has order at most 12."""
    return E.order_of(P, bound=16) is None


def analyse(E: Curve, search_bounds=(60, 250, 900), verbose: bool = False) -> Certificate:
    cert = Certificate(curve=E)

    convs = two_torsion_models(E)
    if not convs:
        cert.method = "no rational 2-torsion: only a lower bound is available"
        pts = [p for p in direct_point_search(E, 120) if _infinite_order(E, p)]
        cert.points = pts[:20]
        cert.rank_lower = 0
        if pts:
            cert.rank_lower = 1
            he = HeightEngine(E)
            cert.height_constant = he.c
            sp = [E.to_short(p) for p in pts]
            k, idx, det = he.max_independent(sp, cap=4)
            cert.independent_count = k
            if k >= 1:
                cert.rank_lower = k
            if k >= 2:
                cert.independent_pair = tuple(pts[i] for i in idx)
                cert.regulator = det
        cert.notes.append(
            "This engine certifies upper bounds by descent via a rational "
            "2-isogeny, which needs a rational point of order 2.  This curve "
            "has none, so no upper bound is proved here."
        )
        return cert

    # Every rational 2-torsion point gives a different 2-isogeny and hence an
    # independent bound on the *same* rank (rank is an isogeny invariant).
    # Taking the best of them is free and can only sharpen the bracket.
    runs = []
    for model, to_model, from_model in convs:
        d = two_isogeny_descent(model, search_bounds)
        runs.append((model, to_model, from_model, d))
    cert.all_runs = runs
    model, to_model, from_model, d = min(runs, key=lambda t: t[3].rank_upper)
    cert.model = model
    cert.descent = d
    cert.method = (
        "descent via the rational 2-isogeny E -> E/<(0,0)>"
        + (f"  (best of {len(runs)} available 2-isogenies)" if len(runs) > 1 else "")
    )
    cert.rank_upper = d.rank_upper
    cert.rank_lower = max(0, max(r[3].rank_lower for r in runs))

    # Collect rational points of infinite order on the input curve, from every
    # run -- a point proved by any model is a point on the curve.
    raw: list[Point] = []
    for mdl, _tm, fm, dd in runs:
        for P in dd.side.points.values():
            raw.append(fm(P))
        for P in dd.side_prime.points.values():
            raw.append(fm(mdl.phi_hat(P)))
    seen = set()
    pts = []
    for P in raw:
        if P.inf:
            continue
        key = (P.x, P.y)
        if key in seen:
            continue
        seen.add(key)
        if not E.is_on(P):
            continue
        if _infinite_order(E, P):
            pts.append(P)
    cert.points = pts

    # Second, logically independent proof of the lower bound: the height
    # pairing.  This uses no descent theory at all, so agreement between the
    # two is a genuine cross-check rather than a restatement.
    if len(pts) >= 2:
        he = HeightEngine(E)
        cert.height_constant = he.c
        sp = [E.to_short(P) for P in pts]
        k, idx, det = he.max_independent(sp, cap=4)
        if k >= 2:
            cert.independent_pair = tuple(pts[i] for i in idx)
            cert.regulator = det
            cert.rank_lower = max(cert.rank_lower, k)
        cert.independent_count = k
        # Cross-check: descent says rank <= U, heights say rank >= k.
        # k > U would mean one of the two engines is wrong.
        if cert.rank_upper is not None and k > cert.rank_upper:
            raise AssertionError(
                f"contradiction: {k} provably independent points but descent "
                f"bounds the rank by {cert.rank_upper}"
            )

    if not d.local_certain:
        cert.notes.append(
            "A local solubility test hit its search budget; the Selmer group "
            "was over-estimated on the safe side, so the upper bound is still "
            "valid (possibly not sharp)."
        )
    return cert


# ------------------------------------------------------------- reporting ----


def format_certificate(c: Certificate) -> str:
    E = c.curve
    L = []
    add = L.append
    add("=" * 72)
    add("ALGEBRAIC RANK CERTIFICATE")
    add("=" * 72)
    add(f"curve         : {E.equation()}")
    add(f"discriminant  : {E.disc}")
    add(f"j-invariant   : {E.j}")
    add(f"method        : {c.method}")
    add("")

    if c.descent is not None:
        d = c.descent
        m = c.model
        add(f"descent model : y^2 = x(x^2 + {m.a}x + {m.b})            [E ]")
        Ep = m.isogenous()
        add(f"2-isogenous   : y^2 = x(x^2 + {Ep.a}x + {Ep.b})            [E']")
        add("")
        for tag, s in (("E ", d.side), ("E'", d.side_prime)):
            add(f"  {tag}: candidate classes d | b, squarefree : {len(s.candidates)}")
            add(f"      Selmer group  S = {s.selmer}")
            add(f"        dim_F2 S    = {s.dim_selmer}")
            add(f"      realised by rational points = {s.realised}")
            add(f"        dim_F2      = {s.dim_realised}")
            if s.obstructions:
                obs = ", ".join(f"{k}:{v}" for k, v in sorted(s.obstructions.items()))
                add(f"      killed locally at          : {obs}")
            add("")
        add("  counting identity:  2^rank = |Im a| * |Im a'| / 4")
        add(f"    upper: rank <= dim S + dim S' - 2 = "
            f"{d.side.dim_selmer} + {d.side_prime.dim_selmer} - 2 = {d.rank_upper}")
        add(f"    lower: rank >= dim G + dim G' - 2 = "
            f"{d.side.dim_realised} + {d.side_prime.dim_realised} - 2 = {d.rank_lower}")
        add("")

    if c.points:
        add("rational points of infinite order found (on the input model):")
        for P in c.points[:8]:
            add(f"    {P}")
        add("")

    if c.independent_pair is not None:
        add(f"independence certificate ({len(c.independent_pair)} points, height pairing):")
        for i, P in enumerate(c.independent_pair):
            add(f"    P{i + 1} = {P}")
        add(f"    |h(2X) - 4h(X)| <= c with c = {c.height_constant:.6f}  (derived)")
        add(f"    det Gram in {c.regulator}  ->  strictly positive")
        add(f"    => these {len(c.independent_pair)} points are independent in "
            f"E(Q) (x) Q, so rank >= {len(c.independent_pair)}.")
        add("")

    add("-" * 72)
    if c.certified:
        add(f"RESULT: rank E(Q) = {c.rank}   [PROVED]")
        add("")
        add("The upper bound is a finite local computation; the lower bound is")
        add("witnessed by explicit rational points.  They agree, so the rank is")
        add("determined outright.  No hypothesis on Ш, and no hypothesis on")
        add("L-functions, was used at any point.")
        if c.descent is not None:
            d = c.descent
            add("")
            add("Corollary obtained (not assumed):")
            add(f"    dim_F2 Ш(E/Q)[phi]      = {d.sha_phi_dim}")
            add(f"    dim_F2 Ш(E'/Q)[phi-hat] = {d.sha_phihat_dim}")
    else:
        add(f"RESULT: {c.rank_lower} <= rank E(Q) <= {c.rank_upper}   [NOT DECIDED]")
        if c.descent is not None:
            gap = c.rank_upper - c.rank_lower
            add("")
            add(f"The bracket is {gap} wide.  That width is exactly")
            add("    dim Ш(E/Q)[phi] + dim Ш(E'/Q)[phi-hat]")
            add("not yet accounted for by rational points.  Either the point")
            add("search must go further, or a second descent is needed.  The")
            add("tool refuses to guess which.")
    for n in c.notes:
        add(f"note: {n}")
    add("=" * 72)
    return "\n".join(L)
