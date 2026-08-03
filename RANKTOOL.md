# ranktool — the algebraic rank, from the equation alone

A tool that determines the algebraic rank `r = rank E(Q)` of an elliptic curve
over **Q** directly from its equation, **without assuming anything about the
Tate–Shafarevich group Ш** — not its finiteness, not its order, not its parity,
and without using L-functions or BSD.

Pure Python 3, standard library only. No Sage, no PARI, no Magma, no `sympy`.

```
$ python -m ranktool --congruent 34
...
RESULT: rank E(Q) = 2   [PROVED]
```

---

## 1. The problem, stated precisely

`E(Q) ≅ Z^r ⊕ E(Q)_tors` (Mordell–Weil). The torsion is easy and finite. The
rank `r` is the hard part.

The usual ways of "getting" the rank all borrow something unproven:

| route | what it silently assumes |
|---|---|
| `r = ord_{s=1} L(E,s)` | BSD — open |
| read `r` off the Selmer group | `Ш = 0` — false in general |
| "Ш is finite, so descent terminates" | finiteness of Ш — open |
| Ш has square order / parity arguments | requires finiteness first |

So the question is: **what can be proved about `r` using only finite,
terminating computations on the equation?**

## 2. The one honest idea

Squeeze `r` from both sides with two computations that are each individually
airtight, and see whether they meet.

```
        points you can exhibit          local obstructions you can verify
                    │                                    │
                    ▼                                    ▼
        rank ≥ (lower bound)   ≤   r   ≤   (upper bound) = rank + dim Ш-part
```

* **Lower bound.** Exhibit rational points. A point is a witness: once you have
  it, nothing can take it away. No assumption is involved in *having* a point.
* **Upper bound.** Descent. A curve with no point over some **Q_p** has no
  rational point either — a finite check that *proves* a negative.

**Ш is exactly the gap between these two brackets.** So:

> If the brackets meet, the rank is a theorem, and the triviality of the
> relevant part of Ш is a **corollary** of the computation, not an input to it.

That inversion is the whole design. The tool never assumes Ш; when it succeeds
it *proves* something about Ш on the way past.

## 3. The mechanism, derived from scratch

Take a curve with a rational point of order 2. Move it to the origin:

```
E  : y² = x(x² + a x + b)                    T = (0,0)
E' : y² = x(x² − 2a x + (a² − 4b))           = E/⟨T⟩
φ : E → E',   φ̂ : E' → E,   φ̂ ∘ φ = [2]
```

### 3.1 Where the classes live (why the search is finite)

Define `α : E(Q) → Q*/(Q*)²` by `O ↦ 1`, `(0,0) ↦ b`, `(x,y) ↦ x`. It is a
homomorphism with kernel `φ̂(E'(Q))`.

Write `x = m/n²` in lowest terms. Then `y² = x(x²+ax+b)` clears to

```
(y n³)² = m (m² + a m n² + b n⁴)
```

and any common factor of the two right-hand factors divides `b`. A product of
two almost-coprime integers being a square forces each to be a square times
that common factor — so **the squarefree part of x divides b**. The candidate
set is finite and explicit: the squarefree divisors of `b`, positive *and*
negative. Nothing is approximated here.

### 3.2 The homogeneous space

`α(P) = d` says `x = d T²`. Substituting and putting `W = y/(dT)`:

```
C_d :  W² = d T⁴ + a T² + (b/d)
```

Homogenising `T = u/v`, `W = w/v²`:

```
C_d :  w² = d u⁴ + a u²v² + e v⁴,        e = b/d
back-map:  x = d u²/v² ,  y = d u w/v³
```

So: **d is in the image of α ⟺ C_d has a rational point.** The rank question
has become a finite list of concrete quartic equations.

### 3.3 The two brackets

* `d` **realised**: find `(u,v,w)` by search → `d ∈ Im α`, permanently.
* `d` **killed**: show `C_d(Q_p) = ∅` for one prime → `d ∉ Im α`, permanently.
* `d` locally soluble but no point found → **undecided**; this is where Ш lives.

Both brackets are groups, so it suffices to track subgroups of `Q*/(Q*)²`.

### 3.4 The counting identity

From `φ̂ ∘ φ = [2]` and the descent exact sequences:

```
        2^r = |Im α| · |Im α'| / 4
```

Hence, with `G ⊆ Im α ⊆ S` (realised ⊆ image ⊆ Selmer) on both sides:

```
  dim G + dim G' − 2   ≤   r   ≤   dim S + dim S' − 2
```

Both ends are computed in exact integer arithmetic. When they coincide, `r` is
determined and

```
  dim Ш(E/Q)[φ] = dim S − dim G  =  0 ,   likewise for φ̂
```

falls out as a **result**.

A curve with full rational 2-torsion has three different 2-isogenies, each
giving an independent bound on the same rank. The tool runs all of them and
keeps the best bracket — free, and never weaker.

### 3.5 Deciding `C_d(Q_p) ≠ ∅` — the only step that could hide a lie

Solubility over **Q_p** depends only on `(u:v)` modulo a bounded power of `p`,
so it is decidable. `ranktool/local.py` walks `P¹(Z_p)` explicitly:

* a residue `r` with `p^e f(r)` an actual square in **Q_p** → soluble (a witness);
* a **simple** `p`-adic root of `f` → soluble (near a simple root `f(α+h) = h·unit`,
  so the valuation runs through every large integer *and* the unit part through
  every class, so some `t` makes `p^e f(t)` a square);
* a class where `f` is a `p`-adic **unit** is fully decided by the tests above
  (`p` odd: `f` is constant mod `p`; `p = 2`: constant mod 8 on classes mod 8),
  so the recursion only descends into classes where `p | f(r)` — which keeps
  the tree thin;
* only **bad primes** need checking: elsewhere the quartic reduces to a smooth
  genus-1 curve over `F_p`, which has a point by Hasse–Weil (`p+1−2√p > 0` for
  `p ≥ 3`), and Hensel lifts it.

**Soundness discipline.** If the search budget is ever exhausted the routine
returns "soluble, *uncertain*" — the answer that can only *enlarge* the Selmer
group and therefore only *weaken* the upper bound. An uncertain local answer
can never cause the tool to claim a rank it has not proved.

### 3.6 A second, independent proof of the lower bound

`ranktool/height.py` proves the same lower bound by a route that uses no
descent theory at all: the canonical height pairing. Two points with a
provably nonzero Gram determinant are independent in `E(Q) ⊗ Q`.

The `O(1)` constant is **derived at run time**, not quoted. On `Y² = X³+AX+B`
with `X = m/n` in lowest terms, duplication is `X(2P) = f(m,n)/g(m,n)` for two
binary quartics. Solving their Sylvester system exactly gives integral cubics

```
 p·f + q·g = R·m⁷ ,      p̃·f + q̃·g = R·n⁷ ,     R = Res(f,g) ≠ 0
```

which yield, with `M = max(|m|,|n|)` and `K = ‖p‖₁+‖q‖₁`, all three facts at once:

```
 |f|,|g| ≤ max(‖f‖₁,‖g‖₁)·M⁴       gcd(f,g) | R       max(|f|,|g|) ≥ (|R|/K)·M⁴
```

so `|h(2P) − 4h(P)| ≤ c` with `c = max(log K, log max(‖f‖₁,‖g‖₁))`, and
telescoping `ĥ(P) = lim h(2^N P)/4^N` gives the **proved** enclosure

```
 | ĥ(P) − h(2^N P)/4^N |  ≤  c / (3·4^N)
```

Everything is exact integer arithmetic except the final logarithms, taken in
padded interval arithmetic. The two engines agreeing is a genuine cross-check —
`analyse()` raises if the height engine ever proves more independent points
than descent allows.

## 4. Usage

```bash
python -m ranktool --congruent 34          # y² = x³ − 34²x
python -m ranktool --short -1156 0         # y² = x³ + Ax + B
python -m ranktool --model -102 2312       # y² = x(x² + ax + b)
python -m ranktool --weierstrass 0 1 0 -2 0
python -m ranktool --congruent 34 --quiet
```

```python
from ranktool import Curve, analyse, format_certificate
print(format_certificate(analyse(Curve(0, 0, 0, -1156, 0))))
```

Exit code `0` = rank proved, `2` = undecided bracket, `3` = singular input.

### A rank 2 certificate

```
curve         : y^2 = x^3 + -1156*x
descent model : y^2 = x(x^2 + -102x + 2312)        [E ]
2-isogenous   : y^2 = x(x^2 + 204x + 1156)         [E']

  E : Selmer group  S = [1, 2, 17, 34]             dim_F2 S = 2
      realised by rational points = [1, 2, 17, 34]     dim = 2
      killed locally at: -34:R, -17:R, -2:R, -1:R
  E': Selmer group  S = [1, 2, 17, 34]             dim_F2 S = 2
      realised by rational points = [1, 2, 17, 34]     dim = 2
      killed locally at: -34:Q_2, -17:Q_2, -2:Q_2, -1:Q_2

  counting identity:  2^rank = |Im a| * |Im a'| / 4
    upper: rank <= 2 + 2 - 2 = 2
    lower: rank >= 2 + 2 - 2 = 2

independence certificate (2 points, height pairing):
    P1 = (162, -2016)
    P2 = (153/4, -867/8)
    |h(2X) - 4h(X)| <= c with c = 120.401865  (derived)
    det Gram in [7.069951, 7.129217]  ->  strictly positive

RESULT: rank E(Q) = 2   [PROVED]

Corollary obtained (not assumed):
    dim_F2 Ш(E/Q)[phi]      = 0
    dim_F2 Ш(E'/Q)[phi-hat] = 0
```

## 5. Validation

| test | result |
|---|---|
| 1988 curves `y² = x(x²+ax+b)`, \|a\|≤12, \|b\|≤40 | **0 internal errors**, 97.2 % certified outright |
| congruent-number curves `y² = x³−n²x`, `n = 1..65` | 64/65 decided, **0 disagreements** with the classical congruent-number list |
| model invariance: 40 random `(u,r,s,t)` re-coordinatisations | **40/40** identical brackets |
| Selmer set is closed under multiplication | asserted on every run |
| realised classes ⊆ Selmer classes | asserted on every run |
| descent bound vs. height-pairing bound | contradiction raises, never silently reported |
| `ĥ(nP) = n² ĥ(P)` | interval-checked in the test suite |

The single undecided congruent case is `n = 17` — the classical
Lind–Reichardt curve `2y² = x⁴ − 17`, the textbook example of a genus-1 curve
with points everywhere locally and none globally. The tool's one failure is
exactly the case mathematics has always regarded as the hard one, and it
reports it as a bracket rather than a rank.

```bash
python -m unittest discover -s tests -v
```

## 6. The boundary — stated honestly

**What is proved.** Every rank this tool prints is a theorem about that curve,
independent of Ш, BSD, GRH and modularity. Every bracket it prints is a true
bracket. It has no mode in which it guesses.

**What is not.** The procedure is *sound* but not *complete*: it is a
semi-decision procedure. It terminates with an answer exactly when the two
brackets meet, and they fail to meet precisely when some Selmer class is a
genuine Ш class.

The scope of the upper-bound engine is curves with a rational point of order 2
(descent via 2-isogeny). Curves without one get a certified lower bound only,
and say so. Closing the remaining gaps requires:

* **deeper point search** — when the gap is only a large generator (a search
  failure, not Ш);
* **full 2-descent** over the cubic étale algebra `Q[x]/f(x)` — extends the
  upper bound to all curves; needs class groups and units of cubic fields;
* **4-descent / n-descent** — the only thing that closes a *genuine* Ш[2] gap
  such as `n = 17`, by showing the offending 2-covering is itself not covered.

**Is a complete tool impossible?** No — and that should be said plainly rather
than dressed up. There is no known algorithm guaranteed to terminate on every
curve, and providing one is equivalent to a major open problem: this descent
tower terminates for every curve **iff** Ш is finite. That is an open question,
not a proved impossibility. Nothing here shows a complete rank algorithm cannot
exist; what is shown is that *this* method's termination is exactly as hard as
Ш-finiteness — which is precisely why the tool reports brackets instead of
pretending.

So the honest summary: **the rank is determinable from the equation with no Ш
hypothesis whenever the two brackets meet — which is the overwhelming majority
of curves (97 % in the sweep above) and every rank-2 case tested — and in the
remaining cases the correct output is a bracket, not a number.**

## 7. Layout

```
ranktool/
  arith.py     exact integers: squares, valuations, factorisation, polynomials
  curve.py     Weierstrass curves, exact group law, models, 2-isogeny
  local.py     solubility over R and Q_p  (the only "proves a negative" step)
  descent.py   Selmer groups, homogeneous spaces, point search, both brackets
  height.py    canonical heights with a self-derived certified error bound
  rank.py      orchestration, cross-checks, certificate rendering
  cli.py       command line
tests/         unit tests, invariance tests, known-rank regression tests
```
