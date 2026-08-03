"""Elliptic curves over Q: exact models, exact point arithmetic, exact
isomorphisms.  Nothing here is numerical.

Two models matter for the rank engine:

  * the general Weierstrass model the user supplies,
        y^2 + a1 x y + a3 y = x^3 + a2 x^2 + a4 x + a6
  * the *descent model*
        y^2 = x (x^2 + a x + b)                        (a, b integers)
    which exists over Q exactly when E has a rational point of order 2.

The isomorphism between them is explicit and defined over Q, so the
Mordell-Weil rank is literally the same number on both sides.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction as F
from math import gcd

from .arith import factorize, prime_divisors

Q = F


class Singular(ValueError):
    pass


# ------------------------------------------------------------------ points ---


@dataclass(frozen=True)
class Point:
    """A rational point.  ``inf`` marks the point at infinity."""

    x: F = F(0)
    y: F = F(0)
    inf: bool = False

    def __repr__(self) -> str:  # pragma: no cover - display only
        if self.inf:
            return "O"
        return f"({self.x}, {self.y})"


O = Point(inf=True)


# ------------------------------------------------------------------ curves ---


class Curve:
    """y^2 + a1 x y + a3 y = x^3 + a2 x^2 + a4 x + a6 over Q."""

    def __init__(self, a1=0, a2=0, a3=0, a4=0, a6=0):
        self.a1, self.a2, self.a3, self.a4, self.a6 = (F(t) for t in (a1, a2, a3, a4, a6))
        self.b2 = self.a1 * self.a1 + 4 * self.a2
        self.b4 = 2 * self.a4 + self.a1 * self.a3
        self.b6 = self.a3 * self.a3 + 4 * self.a6
        self.b8 = (
            self.a1 * self.a1 * self.a6
            + 4 * self.a2 * self.a6
            - self.a1 * self.a3 * self.a4
            + self.a2 * self.a3 * self.a3
            - self.a4 * self.a4
        )
        self.c4 = self.b2 * self.b2 - 24 * self.b4
        self.c6 = -(self.b2 ** 3) + 36 * self.b2 * self.b4 - 216 * self.b6
        self.disc = (
            -self.b2 * self.b2 * self.b8
            - 8 * self.b4 ** 3
            - 27 * self.b6 * self.b6
            + 9 * self.b2 * self.b4 * self.b6
        )
        if self.disc == 0:
            raise Singular("discriminant is zero: not an elliptic curve")
        self.j = self.c4 ** 3 / self.disc

    # -- basic ------------------------------------------------------------

    def __repr__(self) -> str:  # pragma: no cover - display only
        return f"Curve[{self.a1},{self.a2},{self.a3},{self.a4},{self.a6}]"

    def equation(self) -> str:
        lhs = "y^2"
        if self.a1:
            lhs += f" + {self.a1}*x*y"
        if self.a3:
            lhs += f" + {self.a3}*y"
        rhs = "x^3"
        for c, s in ((self.a2, "x^2"), (self.a4, "x"), (self.a6, "")):
            if c:
                rhs += f" + {c}{'*' + s if s else ''}"
        return f"{lhs} = {rhs}"

    def is_on(self, P: Point) -> bool:
        if P.inf:
            return True
        x, y = P.x, P.y
        return (
            y * y + self.a1 * x * y + self.a3 * y
            == x ** 3 + self.a2 * x * x + self.a4 * x + self.a6
        )

    # -- group law --------------------------------------------------------

    def neg(self, P: Point) -> Point:
        if P.inf:
            return P
        return Point(P.x, -P.y - self.a1 * P.x - self.a3)

    def add(self, P: Point, Qp: Point) -> Point:
        if P.inf:
            return Qp
        if Qp.inf:
            return P
        x1, y1, x2, y2 = P.x, P.y, Qp.x, Qp.y
        if x1 == x2 and (y1 + y2 + self.a1 * x2 + self.a3) == 0:
            return O
        if P == Qp:
            num = 3 * x1 * x1 + 2 * self.a2 * x1 + self.a4 - self.a1 * y1
            den = 2 * y1 + self.a1 * x1 + self.a3
            if den == 0:
                return O
            lam = num / den
        else:
            lam = (y2 - y1) / (x2 - x1)
        nu = y1 - lam * x1
        x3 = lam * lam + self.a1 * lam - self.a2 - x1 - x2
        y3 = -(lam + self.a1) * x3 - nu - self.a3
        return Point(x3, y3)

    def sub(self, P: Point, Qp: Point) -> Point:
        return self.add(P, self.neg(Qp))

    def dbl(self, P: Point) -> Point:
        return self.add(P, P)

    def mul(self, n: int, P: Point) -> Point:
        if n < 0:
            return self.mul(-n, self.neg(P))
        R, Qc = O, P
        while n:
            if n & 1:
                R = self.add(R, Qc)
            Qc = self.dbl(Qc)
            n >>= 1
        return R

    def order_of(self, P: Point, bound: int = 24) -> int | None:
        """Exact order of P if it is at most `bound`, else None (=> infinite
        order, by Mazur's theorem, once bound >= 12)."""
        R = P
        for k in range(1, bound + 1):
            if R.inf:
                return k
            R = self.add(R, P)
        return None

    # -- models -----------------------------------------------------------

    def transform(self, u, r, s, t) -> "Curve":
        """The isomorphic curve under (x,y) -> (u^2 x + r, u^3 y + s u^2 x + t).

        Same curve, different equation.  Any honest rank engine must return the
        same answer on both, which makes this the sharpest end-to-end test of
        the model-reduction code.
        """
        u, r, s, t = F(u), F(r), F(s), F(t)
        if u == 0:
            raise ValueError("u must be nonzero")
        a1 = (self.a1 + 2 * s) / u
        a2 = (self.a2 - s * self.a1 + 3 * r - s * s) / u ** 2
        a3 = (self.a3 + r * self.a1 + 2 * t) / u ** 3
        a4 = (
            self.a4 - s * self.a3 + 2 * r * self.a2
            - (t + r * s) * self.a1 + 3 * r * r - 2 * s * t
        ) / u ** 4
        a6 = (
            self.a6 + r * self.a4 + r * r * self.a2 + r ** 3
            - t * self.a3 - t * t - r * t * self.a1
        ) / u ** 6
        return Curve(a1, a2, a3, a4, a6)

    def two_torsion_x(self) -> list[F]:
        """Rational x-coordinates of the points of order 2.

        These are the rational roots of 4x^3 + b2 x^2 + 2 b4 x + b6.
        """
        c = [self.b6, 2 * self.b4, self.b2, F(4)]  # ascending
        return _rational_roots(c)

    def short_model(self) -> tuple[int, int]:
        """Integral short model Y^2 = X^3 + A X + B, via (x,y) -> (36x+3b2, 216y)
        composed with clearing denominators.  Returns (A, B)."""
        A = -27 * self.c4
        B = -54 * self.c6
        # clear denominators by (A,B) -> (u^4 A, u^6 B)
        dens = [A.denominator, B.denominator]
        u = 1
        for p in set(prime_divisors(dens[0]) + prime_divisors(dens[1])):
            eA = _pval(A, p)
            eB = _pval(B, p)
            k = 0
            while 4 * k + eA < 0 or 6 * k + eB < 0:
                k += 1
            u *= p ** k
        A *= u ** 4
        B *= u ** 6
        assert A.denominator == 1 and B.denominator == 1
        return int(A), int(B)

    def to_short(self, P: Point) -> Point:
        """Image of P on the integral short model (same rank, same heights)."""
        A0 = -27 * self.c4
        B0 = -54 * self.c6
        dens = [A0.denominator, B0.denominator]
        u = 1
        for p in set(prime_divisors(dens[0]) + prime_divisors(dens[1])):
            eA, eB = _pval(A0, p), _pval(B0, p)
            k = 0
            while 4 * k + eA < 0 or 6 * k + eB < 0:
                k += 1
            u *= p ** k
        if P.inf:
            return O
        X = 36 * P.x + 3 * self.b2
        Y = 216 * P.y + 108 * (self.a1 * P.x + self.a3)
        return Point(X * u * u, Y * u ** 3)


def _pval(q: F, p: int) -> int:
    n, d = q.numerator, q.denominator
    if n == 0:
        return 1 << 30
    v = 0
    while n % p == 0:
        n //= p
        v += 1
    while d % p == 0:
        d //= p
        v -= 1
    return v


def _rational_roots(c: list[F]) -> list[F]:
    """All rational roots of a polynomial with rational coefficients
    (ascending coefficient list), by the rational root theorem."""
    while len(c) > 1 and c[-1] == 0:
        c = c[:-1]
    if len(c) <= 1:
        return []
    # clear denominators -> integer coefficients
    L = 1
    for t in c:
        L = L * t.denominator // gcd(L, t.denominator)
    ic = [int(t * L) for t in c]
    g = 0
    for t in ic:
        g = gcd(g, abs(t))
    ic = [t // g for t in ic]
    a0, an = ic[0], ic[-1]
    roots: list[F] = []
    if a0 == 0:
        roots.append(F(0))
        while ic[0] == 0:
            ic = ic[1:]
        a0 = ic[0]
    ps = _divisors(abs(a0))
    qs = _divisors(abs(an))
    seen = set(roots)
    for p in ps:
        for q in qs:
            for s in (1, -1):
                r = F(s * p, q)
                if r in seen:
                    continue
                acc = F(0)
                for t in reversed(ic):
                    acc = acc * r + t
                if acc == 0:
                    seen.add(r)
                    roots.append(r)
    return sorted(roots)


def _divisors(n: int) -> list[int]:
    if n == 0:
        return [1]
    f = factorize(n)
    out = [1]
    for p, e in f.items():
        out = [d * p ** k for d in out for k in range(e + 1)]
    return sorted(out)


# --------------------------------------------------- the descent model ------


class DescentModel:
    """y^2 = x (x^2 + a x + b), with integers a, b, plus the isomorphism back
    to the curve it came from."""

    def __init__(self, a: int, b: int):
        if b == 0 or a * a - 4 * b == 0:
            raise Singular("y^2 = x(x^2+ax+b) is singular")
        self.a, self.b = int(a), int(b)
        self.curve = Curve(0, a, 0, b, 0)

    def __repr__(self) -> str:  # pragma: no cover
        return f"y^2 = x(x^2 + {self.a}x + {self.b})"

    @property
    def disc(self):
        return self.curve.disc

    def isogenous(self) -> "DescentModel":
        """The 2-isogenous curve E' = E/<(0,0)>."""
        return DescentModel(-2 * self.a, self.a * self.a - 4 * self.b)

    def phi(self, P: Point) -> Point:
        """The 2-isogeny E -> E' with kernel {O, (0,0)}."""
        if P.inf or P.x == 0:
            return O
        x, y = P.x, P.y
        return Point(y * y / (x * x), y * (x * x - self.b) / (x * x))

    def phi_hat(self, P: Point) -> Point:
        """The dual isogeny E' -> E (same formula on E', then divide by 4)."""
        if P.inf or P.x == 0:
            return O
        Ep = self.isogenous()
        x, y = P.x, P.y
        X = y * y / (x * x)
        Y = y * (x * x - Ep.b) / (x * x)
        return Point(X / 4, Y / 8)


def to_descent_model(E: Curve, which: int = 0):
    """If E has a rational point of order 2, return (model, to_model, from_model).

    The maps are mutually inverse Q-isomorphisms on rational points, so they
    transport the full Mordell-Weil group -- in particular the rank -- exactly.

    ``which`` selects the 2-torsion point to move to the origin.  A curve with
    full rational 2-torsion has three of them, giving three genuinely different
    descents (three different isogenies) and therefore three independent upper
    bounds on the same rank.  See ``two_torsion_models``.
    """
    xs = E.two_torsion_x()
    if not xs or which >= len(xs):
        return None
    x0 = xs[which]

    # Step 1: y^2 + a1xy + a3y = ...  ->  Y^2 = X^3 + b2 X^2 + 8 b4 X + 16 b6
    #         with X = 4x, Y = 8y + 4a1 x + 4a3
    # Step 2: translate X by X0 = 4*x0 so the 2-torsion point sits at 0
    X0 = 4 * x0
    A2 = E.b2 + 3 * X0
    A4 = 3 * X0 * X0 + 2 * E.b2 * X0 + 8 * E.b4

    # Step 3: scale (X,Y) -> (u^2 X, u^3 Y) to make (a,b) integral & minimal
    u = F(1)
    dens = {p for p in prime_divisors(A2.denominator)} | {
        p for p in prime_divisors(A4.denominator)
    }
    for p in dens:
        e2, e4 = _pval(A2, p), _pval(A4, p)
        k = 0
        while 2 * k + e2 < 0 or 4 * k + e4 < 0:
            k += 1
        u *= p ** k
    a = A2 * u * u
    b = A4 * u ** 4
    assert a.denominator == 1 and b.denominator == 1
    a, b = int(a), int(b)
    # Minimise: (a,b) -> (a/p^2, b/p^4) is the substitution (X,Y) -> (X/p^2, Y/p^3),
    # i.e. u -> u/p.  The scaling factor must be updated in step, or the
    # isomorphism stops being an isomorphism.
    for p in prime_divisors(gcd(a, b) if a else abs(b)):
        while a % (p * p) == 0 and b % (p ** 4) == 0:
            a //= p * p
            b //= p ** 4
            u /= p
    model = DescentModel(a, b)

    def to_model(P: Point) -> Point:
        if P.inf:
            return O
        X = 4 * P.x
        Y = 8 * P.y + 4 * E.a1 * P.x + 4 * E.a3
        return Point((X - X0) * u * u, Y * u ** 3)

    def from_model(P: Point) -> Point:
        if P.inf:
            return O
        X = P.x / (u * u) + X0
        Y = P.y / (u ** 3)
        x = X / 4
        y = (Y - 4 * E.a1 * x - 4 * E.a3) / 8
        return Point(x, y)

    return model, to_model, from_model


def two_torsion_models(E: Curve):
    """Every descent model of E, one per rational point of order 2."""
    out = []
    for i in range(len(E.two_torsion_x())):
        conv = to_descent_model(E, i)
        if conv is not None:
            out.append(conv)
    return out
