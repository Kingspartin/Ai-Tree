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

What is true is that quadratic progressions really are enriched — the mechanism
is that a progression's density of integers coprime to p depends on whether its
discriminant is a quadratic residue mod p. That mechanism just does not need
primality, only sieving.

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
