"""Local solubility of the genus-one curves

        C :  w^2 = c4 u^4 + c3 u^3 v + c2 u^2 v^2 + c1 u v^3 + c0 v^4

over R and over Q_p.

Logic
-----
A rational point on C would be a point over every completion of Q.  So
"C has no point over some Q_p" is a *proof* that C has no rational point.
That is the only way a descent can ever rule anything out, and it is
completely unconditional: it is a finite computation, not an assumption.

Deciding C(Q_p) != {} is a finite computation because Q_p-solubility only
depends on (u:v) mod a bounded power of p.  We do the tree search over
P^1(Z_p) explicitly.

Soundness discipline
--------------------
The search returns (soluble, certain).  Every ``True`` with ``certain=True``
is backed by an explicit p-adic point; every ``False`` with ``certain=True``
is backed by an exhausted search tree.  If the budget is exhausted we return
``(True, False)`` -- i.e. we fall back to the answer that can only *enlarge*
the Selmer group and therefore only *weaken* the upper bound on the rank.
An uncertain local answer can never make the tool claim a rank it has not
proved.
"""

from __future__ import annotations

from .arith import (
    is_square_in_qp,
    poly_content,
    poly_deriv,
    poly_eval,
    poly_shift_scale,
    poly_strip,
    prime_divisors,
    valuation,
)

MAX_DEPTH = 40
MAX_NODES = 400_000


class _Budget:
    __slots__ = ("nodes", "certain")

    def __init__(self):
        self.nodes = 0
        self.certain = True


def _has_simple_root(f, p) -> bool:
    """Hensel: if v_p(f(r)) > 2 v_p(f'(r)) for some r, then f has a simple root
    alpha in Z_p.  Near a simple root f(alpha + h) = h * (unit), so v_p(f(t))
    runs through every large integer and the unit part runs through every
    residue class -- hence p^e f(t) is a square for a suitable t, whatever e is.
    """
    df = poly_deriv(f)
    if not df or all(c == 0 for c in df):
        return False
    for r in range(p):
        fr = poly_eval(f, r)
        if fr == 0:
            return True
        dfr = poly_eval(df, r)
        if dfr == 0:
            continue
        if valuation(fr, p) > 2 * valuation(dfr, p):
            return True
    return False


def _solv(f, e: int, p: int, depth: int, bud: _Budget) -> bool:
    """Is there t in Z_p with p^e * f(t) a square in Q_p (0 allowed)?

    ``f`` has integer coefficients and content prime to p; ``e`` is 0 or 1.
    """
    bud.nodes += 1
    if bud.nodes > MAX_NODES or depth > MAX_DEPTH:
        bud.certain = False
        return True  # conservative: only ever weakens the final upper bound

    f = poly_strip(f)
    if all(c == 0 for c in f):
        return True

    # (1) direct hits: t = r is an honest p-adic (indeed integral) point.
    span = 8 if p == 2 else p
    for r in range(span):
        val = poly_eval(f, r)
        if is_square_in_qp((p ** e) * val, p):
            return True

    # (2) a simple p-adic root of f always yields a point (see docstring).
    if _has_simple_root(f, p):
        return True

    # (3) recurse only into residue classes that are still undecided.
    #     If p does not divide f(r) then f is a unit on the whole class
    #     t = r + p Z_p, and step (1) already decided that class:
    #       * p odd : f(t) = f(r) mod p, so the square class is constant;
    #       * p = 2 : f(t) = f(r) mod 8 on each class mod 8, all of which
    #                 were tested in step (1).
    for r in range(p):
        if poly_eval(f, r) % p != 0:
            continue
        g = poly_shift_scale(f, r, p)
        g = poly_strip(g)
        if all(c == 0 for c in g):
            return True
        m = valuation(poly_content(g), p)
        g = tuple(c // p ** m for c in g)
        if _solv(g, (e + m) % 2, p, depth + 1, bud):
            return True
    return False


def qp_soluble(quartic, p: int) -> tuple[bool, bool]:
    """Does w^2 = Q(u,v) have a Q_p-point?  quartic = [c4, c3, c2, c1, c0]."""
    c4, c3, c2, c1, c0 = quartic
    bud = _Budget()
    # chart v = 1, t = u in Z_p
    f = poly_strip((c0, c1, c2, c3, c4))
    m = valuation(poly_content(f), p) if any(f) else 0
    f0 = tuple(c // p ** m for c in f) if any(f) else f
    if _solv(f0, m % 2, p, 0, bud):
        return True, bud.certain
    # chart u = 1, v = p*s with s in Z_p  (the rest of P^1(Z_p))
    g = poly_strip((c4, c3, c2, c1, c0))
    g = poly_shift_scale(g, 0, p)  # v -> p s
    g = poly_strip(g)
    if not any(g):
        return True, bud.certain
    m = valuation(poly_content(g), p)
    g = tuple(c // p ** m for c in g)
    if _solv(g, m % 2, p, 0, bud):
        return True, bud.certain
    return False, bud.certain


def r_soluble_biquadratic(d: int, a: int, e: int) -> bool:
    """Real solubility of w^2 = d u^4 + a u^2 v^2 + e v^4.

    Put s = (u/v)^2 >= 0 and ask whether f(s) = d s^2 + a s + e is >= 0
    somewhere on s >= 0 (s = infinity corresponds to v = 0).
    """
    if d > 0 or e > 0:
        return True
    if d == 0:
        return a > 0 or e >= 0
    # d < 0 and e <= 0: the maximum of f on s >= 0 is at s* = -a/(2d) = a/(2|d|),
    # which is >= 0 only when a >= 0, and there f(s*) = e - a^2/(4d).
    if a <= 0:
        return e >= 0
    return a * a - 4 * d * e >= 0  # <=> e - a^2/(4d) >= 0 for d < 0


def bad_primes_biquadratic(d: int, a: int, e: int) -> list[int]:
    """Primes at which w^2 = d u^4 + a u^2 v^2 + e v^4 may fail to be smooth.

    The discriminant of the binary quartic d u^4 + a u^2v^2 + e v^4 is
    16 * d * e * (a^2 - 4de)^2.  At every other prime p the reduction is a
    smooth genus-one curve over F_p, which has an F_p-point by Hasse-Weil
    (#C(F_p) >= p + 1 - 2 sqrt(p) > 0 for p >= 3), and that point lifts by
    Hensel.  So only these primes can obstruct.
    """
    n = 2 * d * e * (a * a - 4 * d * e)
    return sorted(set(prime_divisors(n)) | {2})


def everywhere_locally_soluble(d: int, a: int, e: int) -> tuple[bool, bool, dict]:
    """Full local test for C_d : w^2 = d u^4 + a u^2 v^2 + e v^4.

    Returns (soluble_everywhere, certain, witness) where ``witness`` records the
    place that obstructs, if any.
    """
    if not r_soluble_biquadratic(d, a, e):
        return False, True, {"obstruction": "R"}
    certain = True
    for p in bad_primes_biquadratic(d, a, e):
        ok, cert = qp_soluble([d, 0, a, 0, e], p)
        certain = certain and cert
        if not ok:
            return False, True, {"obstruction": f"Q_{p}"}
    return True, certain, {"obstruction": None}
