"""Canonical heights with a *self-derived*, certified error bound.

Why this file exists
--------------------
The descent gives the rank as an exact count of square classes.  This file
gives a second, logically independent proof of the lower bound: it shows two
specific points are independent in E(Q) (x) Q by proving their height-pairing
determinant is nonzero.

Nothing is quoted from the literature.  The O(1) constant relating the naive
and the canonical height is computed at run time from the curve itself.

The derivation
--------------
On Y^2 = X^3 + A X + B write X(P) = m/n in lowest terms.  Duplication gives

    X(2P) = f(m,n) / g(m,n),
    f = m^4 - 2A m^2 n^2 - 8B m n^3 + A^2 n^4,
    g = 4 m^3 n + 4A m n^3 + 4B n^4,

two binary quartics with resultant R != 0 (R = 0 would force Delta = 0).
Solving the Sylvester system exactly produces integral binary cubics with

    p f + q g = R m^7 ,        p~ f + q~ g = R n^7 .                   (I)

Two consequences, both elementary:

  upper:  |f|,|g| <= max(||f||_1, ||g||_1) * M^4,     M = max(|m|,|n|)
  lower:  from (I), |R| M^7 <= K * M^3 * max(|f|,|g|), K = ||p||_1+||q||_1
          (taking whichever of the two identities has M^7 on the right),
          so max(|f|,|g|) >= (|R|/K) M^4.
  gcd  :  (I) also shows gcd(f(m,n), g(m,n)) | R when gcd(m,n) = 1,
          since R m^7 and R n^7 both lie in the ideal (f(m,n), g(m,n)).

Hence with h(P) = log max(|m|,|n|):

    4 h(P) - log K  <=  h(2P)  <=  4 h(P) + log max(||f||_1, ||g||_1) ,

so |h(2P) - 4h(P)| <= c with c := max(log K, log max(||f||_1,||g||_1)),
and telescoping the definition hhat(P) = lim h(2^N P)/4^N gives the *proved*
enclosure

    | hhat(P) - h(2^N P)/4^N |  <=  c / (3 * 4^N).

Everything above is exact integer arithmetic except the final logarithms,
which are taken in padded interval arithmetic.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from math import gcd
from fractions import Fraction as F

from .curve import Curve, Point

_PAD = 1e-9  # absolute padding added to every logarithm, to swallow FP error


@dataclass(frozen=True)
class Interval:
    lo: float
    hi: float

    def __add__(self, o):
        o = _iv(o)
        return Interval(self.lo + o.lo, self.hi + o.hi)

    def __sub__(self, o):
        o = _iv(o)
        return Interval(self.lo - o.hi, self.hi - o.lo)

    def __mul__(self, o):
        o = _iv(o)
        c = [self.lo * o.lo, self.lo * o.hi, self.hi * o.lo, self.hi * o.hi]
        return Interval(min(c), max(c))

    __rmul__ = __mul__

    def __truediv__(self, k: float):
        return Interval(min(self.lo / k, self.hi / k), max(self.lo / k, self.hi / k))

    @property
    def certainly_positive(self) -> bool:
        return self.lo > 0

    def __repr__(self) -> str:  # pragma: no cover - display only
        return f"[{self.lo:.6f}, {self.hi:.6f}]"


def _iv(x):
    return x if isinstance(x, Interval) else Interval(float(x), float(x))


def log_interval(n: int) -> Interval:
    """Rigorous (padded) enclosure of log(n) for a positive integer n."""
    if n <= 0:
        raise ValueError("log of non-positive integer")
    if n == 1:
        return Interval(0.0, 0.0)
    # exact-ish: use bit length to stay accurate for huge integers
    bl = n.bit_length()
    if bl <= 900:
        v = math.log(n)
    else:
        shift = bl - 900
        v = math.log(n >> shift) + shift * math.log(2.0)
    eps = _PAD + 1e-14 * abs(v)
    return Interval(v - eps, v + eps)


# ------------------------------------------------------ Sylvester machinery --


def _solve(M, rhs):
    """Exact Gaussian elimination over Q.  M is a list of rows of Fractions."""
    n = len(M)
    A = [row[:] + [rhs[i]] for i, row in enumerate(M)]
    for col in range(n):
        piv = None
        for r in range(col, n):
            if A[r][col] != 0:
                piv = r
                break
        if piv is None:
            return None
        A[col], A[piv] = A[piv], A[col]
        pv = A[col][col]
        A[col] = [t / pv for t in A[col]]
        for r in range(n):
            if r != col and A[r][col] != 0:
                fct = A[r][col]
                A[r] = [A[r][k] - fct * A[col][k] for k in range(n + 1)]
    return [A[i][n] for i in range(n)]


def _det(M):
    n = len(M)
    A = [row[:] for row in M]
    det = F(1)
    for col in range(n):
        piv = None
        for r in range(col, n):
            if A[r][col] != 0:
                piv = r
                break
        if piv is None:
            return F(0)
        if piv != col:
            A[col], A[piv] = A[piv], A[col]
            det = -det
        det *= A[col][col]
        inv = A[col][col]
        A[col] = [t / inv for t in A[col]]
        for r in range(col + 1, n):
            if A[r][col] != 0:
                fct = A[r][col]
                A[r] = [A[r][k] - fct * A[col][k] for k in range(n)]
    return det


def duplication_forms(A: int, B: int):
    """Coefficients (by descending power of m) of the two binary quartics."""
    f = [1, 0, -2 * A, -8 * B, A * A]
    g = [0, 4, 0, 4 * A, 4 * B]
    return f, g


def height_constant(A: int, B: int) -> tuple[float, dict]:
    """c with |h(2P) - 4h(P)| <= c, derived from the curve, plus a report."""
    f, g = duplication_forms(A, B)
    # Sylvester system: unknowns p_0..p_3, q_0..q_3 (cubic forms)
    M = []
    for k in range(8):
        row = []
        for i in range(4):
            j = k - i
            row.append(F(f[j]) if 0 <= j <= 4 else F(0))
        for i in range(4):
            j = k - i
            row.append(F(g[j]) if 0 <= j <= 4 else F(0))
        M.append(row)
    R = _det(M)
    if R == 0:
        raise ValueError("resultant vanishes: singular curve")

    Ks = []
    for target in (0, 7):
        rhs = [F(1) if k == target else F(0) for k in range(8)]
        z = _solve(M, rhs)
        assert z is not None
        z = [R * t for t in z]  # now integral: adj(M) e_target
        Ks.append(sum(abs(t) for t in z))
    K = max(Ks)

    nf = sum(abs(t) for t in f)
    ng = sum(abs(t) for t in g)
    up = math.log(float(max(nf, ng)))
    lo = math.log(float(K))
    c = max(up, lo) + _PAD
    return c, {
        "resultant": R,
        "K": K,
        "norm_f": nf,
        "norm_g": ng,
        "c_upper": up,
        "c_lower": lo,
        "c": c,
    }


# ------------------------------------------------------- canonical heights --


def naive_height(P: Point) -> Interval:
    """h(P) = log max(|num X|, |den X|); h(O) = 0."""
    if P.inf:
        return Interval(0.0, 0.0)
    x = P.x
    return log_interval(max(abs(x.numerator), x.denominator))


class HeightEngine:
    """Certified canonical heights on the integral short model of a curve."""

    def __init__(self, E: Curve, max_bits: int = 250_000, target_error: float = 5e-3):
        self.A, self.B = E.short_model()
        self.short = Curve(0, 0, 0, self.A, self.B)
        self.c, self.report = height_constant(self.A, self.B)
        self.max_bits = max_bits
        # Choose N so that the certified error c/(3*4^N) meets the target.
        N = 1
        while self.c / (3.0 * 4.0 ** N) > target_error and N < 14:
            N += 1
        self.max_steps = N
        self.target_error = target_error
        self._cache: dict = {}

    def to_short(self, E: Curve, P: Point) -> Point:
        return E.to_short(P)

    def _x_double(self, m: int, n: int):
        """x = m/n (lowest terms, n > 0)  ->  x(2P), in lowest terms.

        This is the duplication map written directly on the x-line, which is
        all a height computation ever needs.  Returns None when 2P = O.
        """
        A, B = self.A, self.B
        m2 = m * m
        n2 = n * n
        num = m2 * m2 - 2 * A * m2 * n2 - 8 * B * m * n2 * n + A * A * n2 * n2
        den = 4 * n * (m2 * m + A * m * n2 + B * n2 * n)
        if den == 0:
            return None
        g = gcd(num, den)
        num //= g
        den //= g
        if den < 0:
            num, den = -num, -den
        return num, den

    def canonical(self, P: Point) -> Interval:
        """Enclosure of hhat(P) that is *proved* to contain the true value.

        hhat(P) = lim h(2^N P)/4^N, and |h(2^N P)/4^N - hhat(P)| <= c/(3*4^N)
        by the telescoping argument in the module docstring.  So the returned
        interval is a theorem about the curve, not a numerical estimate.
        """
        key = (P.inf, P.x, P.y)
        if key in self._cache:
            return self._cache[key]
        if P.inf:
            return Interval(0.0, 0.0)
        m, n = P.x.numerator, P.x.denominator
        N = 0
        while N < self.max_steps:
            nxt = self._x_double(m, n)
            if nxt is None:
                # 2^(N+1) P = O, so P is torsion and hhat(P) = 0 exactly.
                self._cache[key] = Interval(0.0, 0.0)
                return self._cache[key]
            if max(abs(nxt[0]), nxt[1]).bit_length() > self.max_bits:
                break
            m, n = nxt
            N += 1
        h = log_interval(max(abs(m), n))
        err = self.c / (3.0 * 4.0 ** N)
        val = Interval(h.lo / 4.0 ** N - err, h.hi / 4.0 ** N + err)
        self._cache[key] = val
        return val

    def pairing(self, P: Point, Qp: Point) -> Interval:
        """<P,Q> = (hhat(P+Q) - hhat(P) - hhat(Q)) / 2."""
        S = self.short.add(P, Qp)
        return (self.canonical(S) - self.canonical(P) - self.canonical(Qp)) / 2.0

    def gram(self, pts):
        n = len(pts)
        return [[self.pairing(pts[i], pts[j]) if i != j else self.canonical(pts[i])
                 for j in range(n)] for i in range(n)]

    def regulator(self, pts) -> Interval:
        """Enclosure of det Gram(pts) via Laplace expansion (division-free, so
        interval arithmetic stays valid)."""
        return _det_interval(self.gram(pts))

    def regulator_2x2(self, P: Point, Qp: Point) -> Interval:
        return self.regulator([P, Qp])

    def independent(self, pts) -> tuple[bool, Interval]:
        """Certified independence: the height pairing is positive definite on
        E(Q) (x) R with kernel exactly the torsion, so a Gram determinant that
        is *provably* nonzero proves the points are independent in E(Q) (x) Q.
        """
        if len(pts) > 6:
            raise NotImplementedError("regulator expansion limited to 6 points")
        det = self.regulator(pts)
        return det.certainly_positive, det

    def max_independent(self, pts, cap: int = 4):
        """Largest subset of `pts` proved independent.  Returns (size, subset,
        det).  Purely a lower bound on the rank -- it can never overstate."""
        best = (0, [], None)
        n = len(pts)
        from itertools import combinations

        for k in range(1, min(cap, n) + 1):
            found = None
            for combo in combinations(range(n), k):
                sub = [pts[i] for i in combo]
                ok, det = self.independent(sub)
                if ok:
                    found = (k, list(combo), det)
                    break
            if found is None:
                break
            best = found
        return best


def _det_interval(M):
    n = len(M)
    if n == 1:
        return M[0][0]
    if n == 2:
        return M[0][0] * M[1][1] - M[0][1] * M[1][0]
    total = Interval(0.0, 0.0)
    for j in range(n):
        minor = [[M[i][k] for k in range(n) if k != j] for i in range(1, n)]
        term = M[0][j] * _det_interval(minor)
        total = total + (term if j % 2 == 0 else Interval(0.0, 0.0) - term)
    return total
