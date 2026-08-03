# Results: the rough null

Scored against `PREDICTIONS.md`, which was committed before the null was
implemented. N = 50,000, primes = 5,133.

## The headline

**Nothing survives.** Every statistic that had been reading as prime structure
is a smooth function of one dial — how deeply the set has been sieved — and the
primes sit at the end of that dial rather than off it.

The sieve-bound sweep (`calibrate.py sweep`, all unthinned, no thinning rule
anywhere in it):

| set | count | density | mod_grid | fluct_sL | ulam_diag | crt_indep | gap_lag1 | polar_710 | sacks | deep_ratio |
|---|---|---|---|---|---|---|---|---|---|---|
| rough ≤13 | 9,597 | 0.192 | 0.019 | 0.201 | 2.704 | 0.525 | −0.209 | 0.165 | 1.028 | 1.036 |
| rough ≤23 | 8,194 | 0.164 | 0.041 | 0.308 | 2.038 | 0.483 | −0.159 | 0.261 | 0.995 | 1.056 |
| rough ≤47 | 6,928 | 0.139 | 0.070 | 0.406 | 1.649 | 0.547 | −0.124 | 0.410 | 0.995 | 1.064 |
| rough ≤97 | 5,870 | 0.117 | 0.117 | 0.526 | 1.381 | 0.624 | −0.091 | 1.126 | 0.977 | 1.060 |
| rough ≤199 | 5,139 | 0.1028 | 0.175 | 0.579 | 1.530 | 0.707 | −0.072 | 1.041 | 0.985 | 1.059 |
| **primes** | **5,133** | **0.1027** | **0.181** | **0.578** | **1.547** | **0.708** | **−0.072** | **1.037** | **0.990** | **1.059** |

Every column is monotone in the bound and lands on the primes' value. Not one
statistic in this harness distinguishes the primes from a set defined purely by
"has no small prime factor."

**The caveat that keeps this honest.** At N = 50,000 the rough ≤199 set differs
from the primes by *six elements* — a composite with no factor below 199 needs
both factors above 199, and 199² = 39,601, so barely any fit under 50,000. That
row is very nearly circular and is not evidence by itself. The evidence is the
**trend** across bounds 13 → 199, which shows these statistics tracking sieve
depth continuously, with the primes as its limit. Testing "sieving versus
primality" at a bound near √N is impossible in principle, because there the two
sets coincide.

## Scorecard

| # | prediction | outcome |
|---|---|---|
| P1 | `deep_sieve_ratio` for rough ∈ [1.03, 1.09] | **hit** — 1.064 |
| P1 | `pair_corr_dispersion` for rough ∈ [1.25, 1.65] | **miss** — 2.574 |
| P1 | pair_spectrum verdict dies | **miss at bound 47**, dies at matched density |
| P2 | *my* call: rough diag ∈ [1.35, 1.55], Ulam largely dies | **direction hit**, range miss (1.649) |
| P2 | *your* call: Ulam diagonals mostly survive | **disconfirmed** |
| P3 | thinned `fluct_small_L` ∈ [0.00, 0.15] | **hit** — 0.107 |
| P3 | unthinned `fluct_small_L` ∈ [0.30, 0.75] | **hit** — 0.406 |
| P3 | thinned `mod_grid` ∈ [0.05, 0.35] | **miss** — 2.866 |
| P3 | unthinned `mod_grid` ∈ [0.15, 0.45] | **miss** — 0.070 |
| P3 | unthinned `crt_indep` ∈ [0.55, 0.90] | **miss** — 0.547 |
| P3 | `gap_lag1` ∈ [−0.09, −0.04] | **miss** — −0.124 |
| P3 | interpretation: unthinned near primes ⇒ generic sieve structure | **confirmed** |
| P4 | matched-density Poisson reproduces the large-L sag | **miss — diagnosis was wrong** |
| P5 | polar/sacks stay artifacts | **hit** at matched density |
| P5 | rough `frac_at_origin` ≈ 0.92 | **hit** — 0.906 |

Roughly half the numeric ranges missed, and they missed in a consistent
direction: I repeatedly underestimated how much more even the rough sets are.
The directional and mechanistic calls held.

## The wall has a name: the parity problem

Verified before writing it down, not taken from memory. The **parity problem**
in sieve theory was identified and named by **Atle Selberg in 1949**. The
statement: sieve methods cannot distinguish integers with an odd number of prime
factors from those with an even number. If a set consists entirely of numbers
with an odd number of prime factors, or entirely of numbers with an even number,
sieve theory on its own yields no non-trivial lower bound on its size, and upper
bounds are off by a factor of at least 2. Since a prime is the case "exactly one
prime factor" — odd — sieves cannot isolate primes from almost-primes. This is
why sieve results bottom out at "prime or semiprime": Chen's theorem
(stated 1966, published 1973) gets every sufficiently large even number as a
prime plus a prime-or-semiprime, and no further. From around 1996 Friedlander
and Iwaniec developed parity-sensitive sieves that inject extra input to get
past it.

**What this harness did, stated exactly.** Every statistic in it is a function
of two things: the set's density, and how the set distributes across residue
classes to small moduli. That is precisely the data a sieve has access to. The
`rough ≤ b` null is built to match the primes on exactly that data while
containing semiprimes — it *is* the parity problem's counterexample construction,
arrived at here by looking for a fair control rather than by reading it off.
The sweep then shows what the barrier predicts: no statistic separates them.

**Where the analogy stops.** The parity problem is a theorem about what can be
*proved* from sieve axioms, i.e. from bounds on |A_d|. Nothing here proves
anything. What happened is weaker and empirical: eleven encodings, all of them
functions of sieve data, all failed to separate primes from a sieve-matched set
— which is consistent with the barrier and explained by it, but is not a
derivation of it. The honest claim is that the search walked into a known wall
from the outside and can now see its shape.

That is the actual result of this project. Every apparent finding in iterations
1 and 2 was a rediscovery of "these integers have no small factors", and the
reason no encoding got further is that no encoding was ever looking at anything
else.

## P2: the disagreement, resolved

You predicted the Ulam diagonals would mostly survive, on the grounds that they
come from prime-rich quadratics rather than small-residue avoidance. They did
not. A set with no primality in it at all reproduces them: `diag_dispersion` is
1.649 at bound 47 and 1.530 at bound 199 against the primes' 1.547, and
`diag_over_row` — which divides out any overall evenness — is 2.058 for rough
≤47 against 1.424 for the primes, i.e. the rough set has a *stronger* diagonal
preference than the primes do.

Your caveat was to suspect the null construction if they vanished. Three checks,
all passed: the unthinned sets have no thinning rule to blame; the sweep is
monotone rather than jumping; and the calibration reps stay put at matched
density (polar 1.041 vs 1.037, sacks 0.985 vs 0.990). The construction is sound.

**Settled, and recorded without softening: the Ulam diagonals are a sieve
effect.** The mechanism is the quadratic-residue one — a quadratic progression's
density of integers coprime to p depends on whether the progression's
discriminant is a quadratic residue mod p, so progressions split into
richer and poorer families for every p, and the enrichment compounds over all p
up to the sieve bound. Quadratic enrichment requires sieving and not primality.
"Prime-rich quadratics" is a misnomer: they are *rough-rich* quadratics, and the
primes inherit the effect by being rough, not by being prime.

## Hyper-evenness: retired as a finding

`fluct_small_L` is 0.579 for rough ≤199 against 0.578 for the primes; the
modular sweep is 0.175 against 0.181. The 3-to-6 sd gap below the
matched-density Poisson ensemble is entirely reproduced by a sieve-defined set.
It is a sieve effect, not a prime effect, and it is withdrawn as a result.

The mechanism is not mysterious once stated: a set that avoids every prime up to
b is confined to the ∏(1−1/p) fraction of residues mod the primorial of b that
survive, and within that constraint its counts in any window or class are pinned
by the wheel structure rather than free to fluctuate. Deeper sieve, tighter
pinning — which is exactly the monotone column in the sweep. The primes are the
b → √N end of that, and nothing more.

## P4: my diagnosis was wrong, and your control caught it

I had claimed a systematic large-L deflation in the fluctuation statistic and
attributed it to the density estimator. **Retracted.** A twelve-draw
matched-density Poisson ensemble does not sag: 0.94 → 0.82 across the scale
range, well inside its own spread. The claim rested on a single sieved-null draw
falling 0.98 → 0.53, and at the widest scale only ~27 heavily overlapping
windows fit, where the statistic's own sd/mean is 0.26. That was noise in one
draw, read as a bias.

The correction matters in both directions: with a proper ensemble the primes sit
**3 to 6 sd below** the matched-density control at *every* scale, not just the
small ones. The effect is broader than I had claimed, and my reason for
restricting the headline to small L was wrong even though the restriction was
harmless.

You were right that a flat control could not settle this. A flat control has no
density trend and so cannot reproduce a trend-related artefact — it would have
agreed with me by staying flat.

## The thinning rule ate the first version of this control

Pre-registered as a hazard, and it happened. Thinning the rough set by a greedy
running-count match imposes near-regular spacing, and it corrupted the control
in *both* directions at once — `mod_grid` 2.866 (primes 0.181; far less even)
while `gap_lag1` went to −0.219 and `fluct_small_L` to 0.107 (far more regular).
The default rough null is therefore unthinned, and the density mismatch it
carries is handled by the bound sweep instead.

There is no fix available here, only a trade: every deterministic
density-matching rule either locks the counts (and manufactures evenness) or
hashes them (and behaves like Bernoulli, proving nothing). "Deterministic" was
never the operative property. Sieve structure is.

## Correction carried into the writeup

The modular sweep, CRT lattice, fluctuation map and gap correlation were
described as four converging lines of evidence. They are not independent, and
that framing is withdrawn. They are four views of the same two facts — the
members avoid small residues, and their density is smooth — so their agreement
was close to guaranteed and never corroborative. This run tested them against
one null precisely because they are one claim; and as one claim, it is now
accounted for.

---

# Round 3: N = 10⁷, primes vs rough ≤ 199

12 representations, 9m22s, peak RSS well under the 15 GB available. N = 10⁷ was
feasible; the engineering it needed is listed at the end.

## The prediction was wrong as written, and right underneath

I pre-registered "nothing separates" across all eleven representations. **Six of
twelve read SURVIVES at bound 199.** As a literal prediction that is a miss.

The pre-registered decider was the bound sweep, and it is unambiguous:

| set | count | density | mod_grid | fluct_sL | ulam_diag | crt | gap_lag1 | polar710 | sacks | pair_disp |
|---|---|---|---|---|---|---|---|---|---|---|
| rough ≤199 | 1,044,289 | 0.1044 | 0.012 | 0.086 | 11.871 | 0.108 | −0.084 | 0.813 | 1.180 | 285.5 |
| rough ≤401 | 926,575 | 0.0927 | 0.023 | 0.132 | 9.639 | 0.165 | −0.071 | 0.848 | 1.259 | 224.9 |
| rough ≤801 | 813,194 | 0.0813 | 0.034 | 0.258 | 7.846 | 0.235 | −0.058 | 0.866 | 1.113 | 173.6 |
| rough ≤1601 | 712,778 | 0.0713 | 0.055 | 0.291 | 6.583 | 0.300 | −0.047 | 0.903 | 0.936 | 133.3 |
| rough ≤3163 | 664,579 | 0.0665 | 0.082 | 0.318 | 6.566 | 0.319 | −0.038 | 0.958 | 0.871 | 116.4 |
| **primes** | **664,579** | **0.0665** | **0.082** | **0.318** | **6.566** | **0.319** | **−0.038** | **0.958** | **0.871** | **116.4** |

Every column is monotone in the bound. At bound 3163 = ⌊√N⌋ the rough set *is*
the primes — identical count, every statistic identical to the last digit — for
the structural reason that a composite with no factor below √N does not fit
under N. **The conclusion is unchanged and now holds at 200× the range: nothing
separates the primes from a sieve-defined set except sieve depth.**

## Why the bound-199 separations appeared: χ²/dof is not scale-free

This is a fifth calibration bug in the same family and it is worth stating
plainly. Most statistics here are χ² per degree of freedom. Under pure noise
that lands at 1 regardless of sample size — which is why it looked safe. But
when there is a *systematic* relative deviation δ between bins, it goes as

    χ²/dof ≈ 1 + δ² · E

where E is the expected count per bin. So a set with more members reads a larger
dispersion for *identical* relative structure. The rough ≤199 set has 1.57× the
primes' members, and that alone inflates it.

Checked directly. Subsampling rough ≤199 down to the primes' exact count:

| statistic | rough ≤199 full | subsampled to prime count | primes |
|---|---|---|---|
| `ulam.diag_dispersion` | 11.871 | 6.354 | 6.566 |
| `modular_grid.reduced_dispersion` | 0.012 | 0.409 | 0.082 |

The Ulam separation is entirely the count: matched on count, an 81% gap becomes
3%. The modular-grid row is a warning about the control rather than a result —
random subsampling *injects* the Poisson noise that an evenness statistic is
measuring, so it drives a hyper-even set from 0.012 up to 0.409 and is not a
valid matched-count control for that family. The bound sweep is, and it agrees.

**Consequence for the harness: dispersion statistics are only comparable between
sets of matched count.** The Cramér and sieved nulls always were (both matched
to π(N)); the rough null is not, and every rough z at a bound well below √N must
be read through the sweep rather than on its own.

## The smoothness landscape

Circular by construction, as pre-registered, and it earns its place anyway: it
makes the barrier visible. At N = 10⁷ the rough ≤199 panel resolves into exactly
three strata, and their positions are derivable rather than observed:

- **r = 1**: the primes.
- **a band at r ∈ [0.50, 0.67]**: the semiprimes. If n = p·q with both factors
  above 199, the larger satisfies q ≥ √n, giving r ≥ ½; and p > 199 forces
  q < n/199, giving r < 1 − log 199/log n = 0.671 at n = 10⁷. The band's floor
  and ceiling are those two lines.
- **a thin bar near r ≈ ⅓**: 3-almost-primes, which need n > 199³ ≈ 7.9 × 10⁶ and
  so exist only in the last fifth of the range.

The gap between r = 0.671 and r = 1 is the whole result of this project drawn as
a picture. Everything in that band shares its density and all of its
small-residue statistics with the primes, and no encoding in this harness — none
of which look above the sieve bound — can tell the two apart.

## Scorecard, round 3

| prediction | outcome |
|---|---|
| nothing separates across all 11 reps at bound 199 | **miss** — 6 of 12 read SURVIVES |
| where a statistic moves, the bound sweep decides | **held** — monotone, converging exactly |
| the difference set is dominated by large-factor semiprimes with smooth density | **hit** — visible as the r ∈ [0.5, 0.67] band |
| a separation should be treated as a bug until replicated | **applied** — all six traced to count scaling |
| smoothness landscape separates trivially and proves nothing | **hit** — mean r = 1.000 by definition |

Running total across three rounds: eleven apparent findings, eleven artefacts.

## Engineering N = 10⁷ needed

- the square-spiral coordinates had to be vectorised; the previous Python list
  of 10⁷ step tuples would have needed several GB (verified identical to the old
  implementation at three sizes)
- residue histograms of all integers cached on the context — recomputing them
  per evaluation cost 8.7 s × ~26 evaluations per representation
- Sacks and polar renders rasterised to 2D histograms above 200k points
- the exponent-vector PCA fitted on a 400k subsample instead of all 10⁷
