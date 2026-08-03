# Predictions for the `rough` null

Written and committed **before** the null was implemented or run. Baselines are
the N = 50,000 iteration-2 numbers (primes = 5,133 members).

The new null: integers coprime to every prime ≤ 47, deterministically thinned to
match the primes' density profile. It is a single null serving both open
questions — the sieve-bound test and the deterministic/smooth-density control
for hyper-evenness.

## A hazard I have to name in advance

"Deterministic" is not a statistical property, and the *thinning rule* can
decide the answer on its own. Thinning by a running-count target locks the
member count to the target curve within ±1, which makes the set far more evenly
spread than the primes **by construction** — a control that overshoots and
cannot distinguish "primes are unremarkable" from "my thinning rule is very
regular." Thinning by a hash of n has the opposite failure: it behaves exactly
like Bernoulli sampling and would read ≈1.0 no matter what.

So the thinned set is the primary as instructed, and I will *also* record the
**unthinned** rough set on the same statistics. That is one extra column of
numbers, not a second experiment, and without it I cannot tell overshoot from
result. Density is matched to the smooth ∑1/ln n curve, **not** to π(x) —
locking onto π(x) would make counts agree with the primes by construction and
make the whole control circular.

Expected rough-candidate density ∏_{p≤47}(1−1/p) ≈ 0.146, so ≈7,300 candidates
before thinning to 5,133.

## P1 — pair_spectrum: **dies**. Confidence: high.

`deep_sieve_ratio` is 1.059 for primes, 0.999 for the sieved null. The rough set
avoids exactly the primes 11…47 that drive it.

- rough `deep_sieve_ratio` ∈ **[1.03, 1.09]**
- rough `pair_corr_dispersion` ∈ **[1.25, 1.65]** (primes 1.455)
- verdict drops from SURVIVES to DEEP-COPRIMALITY or ARTIFACT

If it does **not** die, my stated mechanism from last round was wrong.

## P2 — ulam_spiral: **I predict it largely dies. This contradicts your prediction.**

Recorded as an explicit disagreement so the run adjudicates rather than either
of us reinterpreting afterwards.

- **Your** prediction: diagonals mostly survive — prime-rich quadratics, not
  small-residue avoidance. Implies rough stays near the sieved null's 1.165 and
  the primes' 1.547 keeps its z ≥ 3.
- **My** prediction: rough diag_dispersion ∈ **[1.35, 1.55]**, closing most of
  the 1.165 → 1.547 gap, so the verdict weakens or dies. Confidence: moderate
  (~60%). Reasoning: a quadratic progression's density of integers coprime to p
  depends on whether its discriminant is a quadratic residue mod p, so the
  count of admissible values varies from diagonal to diagonal for every p up to
  47 — and the rough set feels that as much as the primes do.
- If rough lands below 1.30, you were right and there is quadratic enrichment
  beyond divisibility.

Your caveat is noted and I will apply it: if the diagonals vanish *and* the
rough null also flattens things it should not, suspect the null construction
first. The check is whether rough behaves sanely on the ARTIFACT reps
(polar, sacks) — it should leave them artifacts.

## P3 — hyper-evenness: **mostly dies**, with the overshoot caveat live.

| statistic | primes | sieved | predicted rough (thinned) | predicted rough (unthinned) |
|---|---|---|---|---|
| `modular_grid.reduced_dispersion` | 0.181 | 0.864 | **[0.05, 0.35]** | **[0.15, 0.45]** |
| `count_fluctuation.small_L` | 0.578 | ~0.95 | **[0.00, 0.15]** | **[0.30, 0.75]** |
| `crt_lattice.crt_independence` | 0.708 | 1.014 | **[0.55, 0.85]** | **[0.55, 0.90]** |
| `prime_gaps.gap_lag1_corr` | −0.072 | −0.017 | **[−0.09, −0.04]** | **[−0.09, −0.04]** |

Interpretation fixed in advance:

- If the **unthinned** rough set lands near the primes, the hyper-evenness is a
  generic consequence of sieve structure plus smooth density, and primality
  adds nothing. That is the outcome I expect.
- If the **thinned** set reads ≈0 while the unthinned set reads ≈1, the thinning
  rule ate the experiment and the thinned column must not be used to argue
  anything about the primes.
- If the unthinned rough set stays near the sieved null (~0.9) while the primes
  sit at 0.18, determinism plus smooth density is *not* sufficient and the
  effect is more interesting than I have been giving it credit for.

## P4 — large-L deflation control

Per your correction: a flat control is not sufficient, since a flat control is
what hid the first bug. A **matched-density Poisson** control (Bernoulli with
p ∝ 1/ln n on the same candidate pool) should reproduce the deflation.

- flat control: stays **1.0–1.3** across all scales, no trend
- matched-density Poisson control: declines from **~0.95–1.0** at the smallest
  scales to **0.45–0.65** at the largest, i.e. within ±0.10 of the sieved
  null's measured 0.98 → 0.53 at every scale

Identical deflation confirms the estimator. If the Poisson control does *not*
deflate, the diagnosis is wrong and the decline is a property of the sets.

## P5 — the reps that should not move

`polar_radian` and `sacks_spiral` stay ARTIFACT/COPRIMALITY. `factor_embed`
stays SURVIVES but with a much smaller gap: the rough set's exponent vectors on
the basis 2…71 are zero unless 53, 59, 61, 67 or 71 divides n, so predicted
rough `frac_at_origin` ≈ **0.92** against the primes' 0.996.

## Correction I am carrying into the writeup

The four "converging lines of evidence" for hyper-evenness — modular sweep, CRT
lattice, fluctuation map, gap correlation — are **not** independent. They are
four views of the same two facts: the members avoid small residues, and their
density is smooth. Agreement between them is close to guaranteed and is not
corroboration. The writeup will say so, and this run tests all four against the
same null precisely because they are one claim, not four.

---

# Round 3 predictions: N = 10⁷, primes vs rough ≤ 199

Written and committed **before** the N = 10⁷ code or the new representation was
written. Feasibility was benchmarked first (see below); no comparison was run.

## Setup facts (measured, not predicted)

- π(10⁷) = 664,579; rough ≤199 = 1,044,289 (density 0.1044)
- √N ≈ 3,163, so a bound of 199 sits well below it and the difference set is
  ~380,000 integers — overwhelmingly semiprimes p·q with 199 < p ≤ q, plus a
  thin tail of 3-almost-primes
- this is the gap that did not exist at N = 50,000, where rough ≤199 was six
  elements from the primes

## The prediction: nothing separates

Across all eleven existing representations, primes vs rough ≤199 unthinned:

- **every headline statistic agrees within |z| < 3**, where z is in units of the
  sieved ensemble's spread
- the difference set is dominated by semiprimes with two large factors, and that
  set has smooth density and the same small-residue structure, so no statistic
  built on residues + density can see it
- specifically: `mod_grid.reduced_dispersion`, `fluct_small_L`,
  `ulam.diag_dispersion`, `crt_independence`, `gap_lag1_corr`,
  `polar_710`, `sacks_local`, `deep_sieve_ratio` all match to within a few
  percent, closer than the bound-47 rows did at N = 50,000
- density is *not* matched (0.1044 vs 0.0665, a 57% gap), which is a larger
  confound than at N = 50,000 and will move some statistics on its own. Where a
  statistic moves, the bound sweep at N = 10⁷ is what decides whether it is
  density or something else

**If something does separate, it is to be treated as a bug until it survives
replication** — a different seed, a different N, and a bound sweep showing it is
not monotone in the sieve bound. Prior experience in this project: five apparent
findings so far, five artefacts.

## The one representation that could legitimately separate

`smoothness_landscape` colours every integer by log(largest prime factor)/log n.
This is the only encoding here that touches large factors, so it is the only one
not confined to sieve data — and it will separate the primes trivially and
completely, because a prime is exactly the ratio-1 case.

That is not a discovery and must not be reported as one. **It is circular**: the
ratio requires factoring n, so the instrument already knows the answer it
returns. It is an instrument for understanding — for seeing what the difference
set actually looks like, and where the primes sit in the Dickman landscape — not
for prediction. Predicted: primes are a degenerate spike at ratio 1.0; rough ≤b
sets appear as bands with a floor rising as log b / log n; the Cramér null spans
the full smoothness distribution.
