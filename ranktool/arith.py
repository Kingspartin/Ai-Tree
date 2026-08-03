"""Exact integer arithmetic primitives.

Everything in this file is exact: no floating point, no probabilistic answers
that are allowed to be wrong.  (Miller-Rabin is used only inside factorisation,
with a deterministic witness set valid for all n < 3.3e24, and a strong
fallback above that.)
"""

from __future__ import annotations

import random
from math import gcd, isqrt

# ---------------------------------------------------------------- squares ---

# Cheap residue filters: a square must be a QR modulo each of these moduli.
_SQ_MOD64 = [False] * 64
_SQ_MOD63 = [False] * 63
_SQ_MOD65 = [False] * 65
_SQ_MOD11 = [False] * 11
for _i in range(64):
    _SQ_MOD64[(_i * _i) % 64] = True
for _i in range(63):
    _SQ_MOD63[(_i * _i) % 63] = True
for _i in range(65):
    _SQ_MOD65[(_i * _i) % 65] = True
for _i in range(11):
    _SQ_MOD11[(_i * _i) % 11] = True


def is_square(n: int) -> bool:
    """Exact perfect-square test with fast residue rejection."""
    if n < 0:
        return False
    if not _SQ_MOD64[n & 63]:
        return False
    if not _SQ_MOD63[n % 63]:
        return False
    if not _SQ_MOD65[n % 65]:
        return False
    if not _SQ_MOD11[n % 11]:
        return False
    r = isqrt(n)
    return r * r == n


def sqrt_exact(n: int) -> int | None:
    if n < 0:
        return None
    r = isqrt(n)
    return r if r * r == n else None


# ------------------------------------------------------------ valuations ---


def valuation(n: int, p: int) -> int:
    """v_p(n) for n != 0.  v_p(0) is returned as a large sentinel."""
    if n == 0:
        return 1 << 30
    v = 0
    while n % p == 0:
        n //= p
        v += 1
    return v


def unit_part(n: int, p: int) -> int:
    while n % p == 0:
        n //= p
    return n


def legendre(a: int, p: int) -> int:
    """Legendre symbol (a/p) for an odd prime p."""
    a %= p
    if a == 0:
        return 0
    return 1 if pow(a, (p - 1) // 2, p) == 1 else -1


def is_square_in_qp(n: int, p: int) -> bool:
    """Is the rational integer n a square in Q_p?  (0 counts as a square.)"""
    if n == 0:
        return True
    v = valuation(n, p)
    if v % 2:
        return False
    u = n // (p ** v)
    if p == 2:
        return u % 8 == 1
    return legendre(u, p) == 1


# --------------------------------------------------------- factorisation ---


def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if n % p == 0:
            return n == p
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for a in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def _pollard_rho(n: int) -> int:
    if n % 2 == 0:
        return 2
    while True:
        x = random.randrange(2, n)
        y, c, d = x, random.randrange(1, n), 1
        while d == 1:
            x = (x * x + c) % n
            y = (y * y + c) % n
            y = (y * y + c) % n
            d = gcd(abs(x - y), n)
        if d != n:
            return d


def factorize(n: int) -> dict[int, int]:
    """Prime factorisation of |n| as {prime: exponent}.  factorize(0) -> {}."""
    n = abs(n)
    out: dict[int, int] = {}
    if n <= 1:
        return out
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47):
        while n % p == 0:
            out[p] = out.get(p, 0) + 1
            n //= p
    stack = [n] if n > 1 else []
    while stack:
        m = stack.pop()
        if m == 1:
            continue
        if _is_prime(m):
            out[m] = out.get(m, 0) + 1
            continue
        d = _pollard_rho(m)
        stack.append(d)
        stack.append(m // d)
    return out


def prime_divisors(n: int) -> list[int]:
    return sorted(factorize(n))


def squarefree_part(n: int) -> int:
    """The squarefree integer d with n = d * (square).  Sign is preserved."""
    if n == 0:
        return 0
    s = -1 if n < 0 else 1
    d = 1
    for p, e in factorize(n).items():
        if e % 2:
            d *= p
    return s * d


def squarefree_divisors(n: int) -> list[int]:
    """All squarefree integers d (positive and negative) dividing n != 0."""
    ps = prime_divisors(n)
    pos = [1]
    for p in ps:
        pos += [d * p for d in pos]
    pos.sort()
    return [s * d for d in pos for s in (1, -1)]


# ------------------------------------------------------------ polynomials ---
# Polynomials are ascending coefficient tuples: (c0, c1, ...) == sum c_i x^i.


def poly_eval(c, x: int) -> int:
    acc = 0
    for a in reversed(c):
        acc = acc * x + a
    return acc


def poly_deriv(c):
    return tuple(i * c[i] for i in range(1, len(c)))


def poly_shift_scale(c, r: int, p: int):
    """Coefficients of f(r + p*t) as a polynomial in t."""
    n = len(c)
    # binomial table
    binom = [[0] * n for _ in range(n)]
    for i in range(n):
        binom[i][0] = 1
        for j in range(1, i + 1):
            binom[i][j] = binom[i - 1][j - 1] + binom[i - 1][j]
    out = [0] * n
    rp = [1] * n
    for i in range(1, n):
        rp[i] = rp[i - 1] * r
    pp = [1] * n
    for i in range(1, n):
        pp[i] = pp[i - 1] * p
    for i in range(n):
        ci = c[i]
        if ci == 0:
            continue
        for j in range(i + 1):
            out[j] += ci * binom[i][j] * rp[i - j] * pp[j]
    return tuple(out)


def poly_content(c) -> int:
    g = 0
    for a in c:
        g = gcd(g, abs(a))
    return g


def poly_strip(c):
    """Drop trailing zero coefficients (keep at least one)."""
    c = list(c)
    while len(c) > 1 and c[-1] == 0:
        c.pop()
    return tuple(c)
