# Iteration 2

`N = 50,000`  ·  seed `0`  ·  12 null replicates per model ·  10s

| set | count | density |
|---|---|---|
| primes <= 50,000 | 5,133 | 0.10266 |
| null: Cramer 1/ln n | 5,188 | 0.10376 |
| null: sieved mod 210 | 5,231 | 0.10462 |

Verdicts are on the headline statistic, z measured against an ensemble of independent null draws. `SURVIVES` = separates from both nulls. `COPRIMALITY` = separates from Cramér only, i.e. it is small-factor avoidance. `ARTIFACT` = both nulls reproduce it.

| verdict | representation | headline | real | z vs Cramér | z vs sieved |
|---|---|---|---|---|---|
| **SURVIVES** | `count_fluctuation` | fluct_dispersion_small_L | 0.578 | -7.272 | -5.546 |
| **SURVIVES** | `crt_lattice` | crt_independence | 0.708 | -13.323 | -6.772 |
| **SURVIVES** | `factor_embed` | frac_at_origin | 0.996 | 196.872 | 92.580 |
| **SURVIVES** | `modular_grid` | reduced_dispersion | 0.181 | -14.765 | -6.440 |
| **SURVIVES** | `pair_spectrum` | pair_corr_dispersion | 1.455 | -32.755 | 15.134 |
| **SURVIVES** | `prime_gaps` | gap_lag1_corr | -0.072 | -6.770 | -3.398 |
| **SURVIVES** | `ulam_spiral` | diag_dispersion | 1.547 | -7.442 | 5.396 |
| **COPRIMALITY** | `factor_shift` | mean_basis_exponent_shift | 3.858 | 65.797 | 0.354 |
| **COPRIMALITY** | `sacks_spiral` | local_ang_dispersion | 0.990 | -8.485 | 0.032 |
| **ARTIFACT** | `modular_walk` | walk_drift_mean | 0.416 | -2.494 | -2.912 |
| **ARTIFACT** | `polar_radian` | ang_dispersion_710 | 1.037 | -0.620 | 0.967 |

## Multiscale count-fluctuation map  ·  SURVIVES

*at any scale, does the set clump or resist clumping along the number line?*

![count_fluctuation](count_fluctuation.png)

**Critique.** SURVIVES - fluct_dispersion_small_L=0.578 (Cramer z=-7.272, sieved z=-5.546). Neither matched-density randomness nor small-factor avoidance reproduces this. Needs a mechanism. The real value is BELOW the nulls' - more even/less clumped than random.

**Reading the picture.** The map is a scale-space view: one row per window length, colour is how many standard deviations the count in that window sat from its local expectation. Grey everywhere means fluctuation exactly as large as chance predicts. Red and blue patches that persist upward through the rows are genuine excursions — a run of the number line that is rich or poor at several scales at once. The curve below collapses each row to a single number, and the dashed line is what a randomly sprinkled set gives. Two calibration facts, both measured against a flat random set drawn on the same candidate pool. (1) That control reads 1.00–1.05 at the smallest scales and never trends, but every set with a *varying* density sags at large L — the sieved null falls from 0.98 to 0.53 across the range — because the measurement window is a sixth of the window estimating its own expectation. The downward slope is therefore an artefact of the estimator, not a finding; only the gap between the curves is real. (2) The Cramér column runs ~1.6× high because that null lives on all integers while the candidate pool is the integers coprime to 210, so its binomial variance is mismatched. Read the sieved column: it shares both the support and the density profile of the primes. The headline uses the smallest third of scales, where the control sits at 1.0 and the sieved null at 0.95.

**Why it happens.** Values below 1 mean the count in a window is pinned closer to its expectation than independent sampling would allow — the same hyper-evenness the modular sweep found, but with no reference to residues at all, so it cannot be a divisibility effect in disguise.

| statistic | real | Cramér mean±sd | z | sieved mean±sd | z |
|---|---|---|---|---|---|
| `fluct_dispersion` | 0.416 | 1.565±0.249 | -4.617 | 0.944±0.137 | -3.853 |
| `fluct_dispersion_small_L` | 0.578 | 1.604±0.141 | -7.272 | 0.940±0.065 | -5.546 |
| `fluct_dispersion_large_L` | 0.264 | 1.522±0.492 | -2.556 | 0.948±0.222 | -3.076 |
| `fluct_slope` | -0.418 | -0.055±0.145 | -2.494 | -0.013±0.101 | -4.017 |

## CRT lattice — joint residues (n mod p, n mod q)  ·  SURVIVES

*does knowing n mod p tell you anything about n mod q?*

![crt_lattice](crt_lattice.png)

**Critique.** SURVIVES - crt_independence=0.708 (Cramer z=-13.323, sieved z=-6.772). Neither matched-density randomness nor small-factor avoidance reproduces this. Needs a mechanism. The real value is BELOW the nulls' - more even/less clumped than random.

**Reading the picture.** Grey means the cell holds exactly what independence predicts. A value of χ²/dof near 1 means the two residues carry no information about each other; the picture being visibly speckled at this sample size is expected — roughly 10 members per cell — and is noise, not texture. Compare the reduced statistic with `crt_independence_unreduced` to see how much a naive version of this test would have been driven by the empty row and column alone.

**Why it happens.** Any dependence would mean the members are not spread across residue classes mod pq the way they are spread mod p and mod q separately.

| statistic | real | Cramér mean±sd | z | sieved mean±sd | z |
|---|---|---|---|---|---|
| `crt_independence` | 0.708 | 1.616±0.068 | -13.323 | 1.020±0.046 | -6.772 |
| `crt_independence_max` | 0.832 | 1.768±0.085 | -11.050 | 1.136±0.057 | -5.328 |
| `crt_independence_unreduced` | 0.426 | 0.895±0.029 | -16.040 | 0.562±0.024 | -5.683 |
| `crt_indep_11_13` | 0.555 | 1.590±0.178 | -5.828 | 0.967±0.154 | -2.681 |
| `crt_indep_13_17` | 0.642 | 1.626±0.194 | -5.071 | 1.014±0.134 | -2.774 |

## Factorisation embedding of n (PCA)  ·  SURVIVES

*where does the set sit in the space of small-prime exponent vectors?*

![factor_embed](factor_embed.png)

**Critique.** SURVIVES - frac_at_origin=0.996 (Cramer z=196.872, sieved z=92.580). Neither matched-density randomness nor small-factor avoidance reproduces this. Needs a mechanism. The real value is ABOVE the nulls' - more clumped than random.

**Reading the picture.** Read the axes before the pattern: the coordinates are 'how many times does 2, 3, 5 ... divide n'. Almost every prime is at the origin because none of them do — the primes panel is one coloured dot. Note the disagreement between eye and statistic here, in the direction people usually assume is impossible: the *picture* cannot tell the primes from the sieved null (both collapse to the origin, since PC1 and PC2 are essentially the exponents of 2 and 3, which both sets have set to zero), while the *statistic* separates them at z = 122. Neither is wrong; they are answering different questions, and the statistic's question happens to be a tautology.

**Why it happens.** Tautological, and worth stating plainly so it is not mistaken for a finding: the embedding's coordinates are divisibility by the primes up to 71, and a prime above 71 is divisible by none of them, so it maps to the zero vector by definition. `frac_at_origin` ≈ 1 for the primes is a restatement of what a prime is. It separates from the sieved null only because that null is sieved at 7, not at 71 -- a deeper null (integers with no factor below 71) would erase this entirely.

| statistic | real | Cramér mean±sd | z | sieved mean±sd | z |
|---|---|---|---|---|---|
| `frac_at_origin` | 0.996 | 0.127±0.00442 | 196.872 | 0.551±0.00481 | 92.580 |
| `mean_basis_exponent` | 0.0039 | 2.509±0.019 | -129.161 | 0.595±0.00562 | -105.159 |
| `mean_v2` | 0.000195 | 0.997±0.013 | -76.219 | 0.000195±1.93e-06 | -0.140 |

## Modular grid sweep, k = 2..60  ·  SURVIVES

*beyond avoiding small factors, is the set unevenly spread across residue classes?*

![modular_grid](modular_grid.png)

**Critique.** SURVIVES - reduced_dispersion=0.181 (Cramer z=-14.765, sieved z=-6.440). Neither matched-density randomness nor small-factor avoidance reproduces this. Needs a mechanism. The real value is BELOW the nulls' - more even/less clumped than random.

**Reading the picture.** In the sweep, black = a residue class the set never occupies, grey = exactly the expected share, red = enriched. The banded triangle is the divisibility pattern. The headline statistic throws that pattern away: it looks only at classes coprime to k, counts candidates from the integers coprime to 210, and applies the binomial (1−ρ) correction — so 1.0 means 'no better spread than a random choice of that many candidates', and anything well below 1 means the set is *more* even than random.

**Why it happens.** Two separate things live in this picture. The dark columns are trivial: a class j mod k with gcd(j,k) = d > 1 contains only multiples of d, so it holds no primes past d itself. The headline number is not that — it is the spread across the classes that are allowed, and for the primes it comes out far *below* random. The primes' counts in the reduced classes mod k sit within a few units of dead level where a random set of the same size would scatter by ±√count. The reason is that the primes are one fixed set, not a sample: their counting error in each progression is a single slowly-growing quantity of order √N, shared out over the φ(k) classes, instead of independent per-class sampling noise of order √(count) each. At N=10⁵ that is roughly a threefold smaller deviation, i.e. an order of magnitude in χ².

| statistic | real | Cramér mean±sd | z | sieved mean±sd | z |
|---|---|---|---|---|---|
| `reduced_dispersion` | 0.181 | 1.128±0.064 | -14.765 | 0.905±0.112 | -6.440 |
| `max_reduced_dispersion` | 0.361 | 2.526±0.297 | -7.284 | 2.177±0.843 | -2.153 |
| `reduced_dispersion_allint_pool` | 0.098 | 0.788±0.050 | -13.910 | 0.499±0.060 | -6.656 |
| `all_class_dispersion` | 243.655 | 0.815±0.061 | 4e+03 | 237.084±2.382 | 2.758 |
| `reduced_dispersion_k12` | 0.175 | 0.761±0.456 | -1.285 | 0.983±0.828 | -0.976 |
| `reduced_dispersion_k30` | 0.153 | 0.935±0.509 | -1.536 | 0.991±0.337 | -2.489 |
| `reduced_dispersion_k47` | 0.252 | 1.639±0.284 | -4.890 | 0.922±0.156 | -4.296 |

## All-pairs difference spectrum  ·  SURVIVES

*is any distance between members taken more often than its number of chances?*

![pair_spectrum](pair_spectrum.png)

**Critique.** SURVIVES - pair_corr_dispersion=1.455 (Cramer z=-32.755, sieved z=15.134). Neither matched-density randomness nor small-factor avoidance reproduces this. Needs a mechanism. The real value is ABOVE the nulls' - more clumped than random.

**Reading the picture.** Both panels are already normalised by candidate pairs, so a flat grey line at 1 is the honest null result and the spikes of a raw difference histogram have deliberately been divided out. Only even distances appear: two members coprime to 210 are both odd, so an odd separation is impossible and those columns are empty by construction, not by absence of structure. Read the lower panel for vertical stripes that hold across every band — a distance favoured throughout the range is a much stronger claim than one favoured on average. The Cramér column sits far below 1 for a mechanical reason rather than an interesting one: that null lives on all integers while the normalisation counts candidate pairs among the integers coprime to 210.

**Why it happens.** Not memory, and not new: this is the sieved null's 7 showing. When d shares a factor p with one of 11…47, the pair (n, n+d) occupies a single residue class mod p instead of two, so it has one fewer way to be composite and both ends are likelier to be prime. `deep_sieve_ratio` isolates it — the primes read ≈1.06, the sieved null ≈1.00, because that null only avoids factors up to 7 and so has no opinion about 11 through 47. It is the same mechanism suspected behind the surviving Ulam diagonals, here measured directly instead of hypothesised. A null sieved at 47 or higher should erase this verdict; that is the test worth running next.

| statistic | real | Cramér mean±sd | z | sieved mean±sd | z |
|---|---|---|---|---|---|
| `pair_corr_dispersion` | 1.455 | 69.259±2.070 | -32.755 | 0.444±0.067 | 15.134 |
| `pair_corr_spread` | 0.038 | 0.176±0.00213 | -64.879 | 0.022±0.00182 | 8.560 |
| `deep_sieve_ratio` | 1.059 | 1.143±0.00708 | -11.835 | 1.000±0.0037 | 16.034 |
| `pair_corr_max` | 1.097 | 0.802±0.012 | 24.393 | 1.058±0.011 | 3.780 |
| `pair_corr_min` | 0.948 | 0.232±0.00871 | 82.231 | 0.942±0.00791 | 0.826 |

## Gap series, gap histogram, gap-pair map  ·  SURVIVES

*is the spacing sequence anything other than a memoryless point process?*

![prime_gaps](prime_gaps.png)

**Critique.** SURVIVES - gap_lag1_corr=-0.072 (Cramer z=-6.770, sieved z=-3.398). Neither matched-density randomness nor small-factor avoidance reproduces this. Needs a mechanism. The real value is BELOW the nulls' - more even/less clumped than random.

**Reading the picture.** The third panel divides the observed (gₖ, gₖ₊₁) table by what it would be if consecutive gaps were independent, so grey is 'no memory' and any coloured cell is a gap pair that happens more or less often than chance. The histogram's spikes at multiples of 6 are the thing to be suspicious of.

**Why it happens.** Consecutive members that are all odd force every gap even, and members avoiding 3 as well push gaps toward multiples of 6 -- both are consequences of small-factor avoidance, and a null with the same avoidance shows the same spikes. Any lag-1 correlation beyond that would be genuine memory.

| statistic | real | Cramér mean±sd | z | sieved mean±sd | z |
|---|---|---|---|---|---|
| `gap_var_ratio` | 0.588 | 0.927±0.037 | -9.257 | 0.635±0.017 | -2.807 |
| `gap_lag1_corr` | -0.072 | 0.015±0.013 | -6.770 | -0.019±0.016 | -3.398 |
| `frac_gap_div6` | 0.404 | 0.123±0.00663 | 42.469 | 0.402±0.00522 | 0.464 |
| `frac_gap_even` | 1.000 | 0.471±0.00865 | 61.125 | 1.000±1.93e-06 | 0.140 |
| `max_gap_over_mean` | 7.391 | 9.350±1.436 | -1.364 | 7.278±0.977 | 0.116 |

## Ulam square spiral  ·  SURVIVES

*do the set's members line up on the spiral's diagonals?*

![ulam_spiral](ulam_spiral.png)

**Critique.** SURVIVES - diag_dispersion=1.547 (Cramer z=-7.442, sieved z=5.396). Neither matched-density randomness nor small-factor avoidance reproduces this. Needs a mechanism. The real value is ABOVE the nulls' - more clumped than random.

**Reading the picture.** Diagonals of the square spiral are values of quadratics 4k²+bk+c; rows and columns are not, and act as an internal control — `diag_over_row` is the ratio. The headline counts candidates from the integers coprime to 210 and applies the (1−ρ) correction, so the diagonals that are empty *because they are all even* no longer contribute; `diag_dispersion_allint` is the naive version that lets them count, and the gap between the two is how much of the famous diagonal effect is just parity.

**Why it happens.** Along any diagonal of this spiral n advances by 4k+const, so n mod 2 — and for half of them n mod 3 — is fixed. Every diagonal whose fixed residue shares a factor with 2 or 3 is empty of primes and the rest absorb the density, which is the whole of the naive statistic. Once candidates are restricted to integers coprime to 210 that mechanism is spent, and what is left is the same hyper-evenness seen in the modular sweep rather than a preference for particular quadratics.

| statistic | real | Cramér mean±sd | z | sieved mean±sd | z |
|---|---|---|---|---|---|
| `diag_dispersion_allint` | 14.687 | 0.925±0.035 | 397.163 | 14.422±0.188 | 1.409 |
| `diag_dispersion` | 1.547 | 3.515±0.264 | -7.442 | 1.127±0.078 | 5.396 |
| `anti_dispersion_allint` | 13.341 | 0.925±0.057 | 216.181 | 13.022±0.137 | 2.318 |
| `anti_dispersion` | 1.517 | 1.834±0.167 | -1.901 | 1.092±0.084 | 5.043 |
| `row_dispersion_allint` | 1.943 | 1.044±0.088 | 10.175 | 1.924±0.112 | 0.168 |
| `row_dispersion` | 1.087 | 5.048±0.514 | -7.705 | 1.229±0.127 | -1.119 |
| `col_dispersion_allint` | 1.783 | 1.002±0.104 | 7.531 | 2.077±0.140 | -2.097 |
| `col_dispersion` | 1.058 | 5.380±0.394 | -10.981 | 1.261±0.148 | -1.369 |
| `diag_over_row` | 1.424 | 0.702±0.086 | 8.417 | 0.922±0.081 | 6.226 |

## Factorisation embedding of n−1 (PCA + UMAP)  ·  COPRIMALITY

*is the multiplicative shape of p−1 unusual for an integer of that size?*

![factor_shift](factor_shift.png)

**Critique.** COPRIMALITY - mean_basis_exponent_shift=3.858 (Cramer z=65.797, sieved z=0.354). Beats random integers but not integers that merely avoid factors 2,3,5,7. This is the definition of a prime showing through, not distributional structure. The real value is ABOVE the nulls' - more clumped than random.

**Reading the picture.** Both projections are log-scaled density hexbins, not scatter, because 10⁴ points overplot. PCA is dominated by the 2-adic valuation of n−1. Treat the UMAP clusters as furniture, not findings: the exponent vectors are short integer vectors with many exact duplicates, so UMAP separates them into islands of identical points, and it draws the same islands on all three panels. Cluster count and shape here are a function of n_neighbors and of the discreteness of the coordinates, not of which integers went in.

**Why it happens.** Every prime past 2 is odd, so p−1 is always even, and the density of the basis exponents shifts up accordingly. That is parity, not depth: a null whose members are already odd shows the same thing.

| statistic | real | Cramér mean±sd | z | sieved mean±sd | z |
|---|---|---|---|---|---|
| `mean_v2_of_shift` | 1.991 | 0.998±0.016 | 63.452 | 1.994±0.022 | -0.157 |
| `mean_basis_exponent_shift` | 3.858 | 2.506±0.021 | 65.797 | 3.847±0.031 | 0.354 |
| `frac_shift_div6` | 0.498 | 0.166±0.00513 | 64.778 | 0.501±0.00606 | -0.471 |
| `v2_shape_dispersion` | 576.502 | 1.945±0.918 | 625.844 | 576.385±6.783 | 0.017 |

## Sacks square-root spiral  ·  COPRIMALITY

*does the set concentrate on particular √n phase angles (i.e. quadratics)?*

![sacks_spiral](sacks_spiral.png)

**Critique.** COPRIMALITY - local_ang_dispersion=0.990 (Cramer z=-8.485, sieved z=0.032). Beats random integers but not integers that merely avoid factors 2,3,5,7. This is the definition of a prime showing through, not distributional structure. The real value is BELOW the nulls' - more even/less clumped than random.

**Reading the picture.** Angle is 2π·frac(√n), so a quadratic n = k²+bk+c sits at a *nearly* fixed angle — it drifts by O(1/k), which is why the global binning is nearly blind and the headline uses thin radial annuli instead. Candidates are the integers coprime to 210, so a ray that exists only because its progression is all-even does not count.

**Why it happens.** frac(√n) is almost constant along k²+bk+c, so each quadratic progression is roughly one angular bin. Progressions that are identically even, or identically divisible by 3, hold no primes and the rest absorb the density — that is what the eye reads as rays, and the sieved null draws the same ones.

| statistic | real | Cramér mean±sd | z | sieved mean±sd | z |
|---|---|---|---|---|---|
| `ang_dispersion_allint_360` | 1.180 | 0.899±0.064 | 4.419 | 0.921±0.053 | 4.920 |
| `ang_dispersion_360` | 1.278 | 2.089±0.086 | -9.405 | 0.978±0.052 | 5.731 |
| `ang_dispersion_allint_720` | 1.062 | 0.880±0.038 | 4.809 | 0.880±0.033 | 5.473 |
| `ang_dispersion_720` | 1.234 | 2.184±0.081 | -11.791 | 0.999±0.048 | 4.951 |
| `local_ang_dispersion` | 0.990 | 2.189±0.141 | -8.485 | 0.988±0.059 | 0.032 |

## Centred modular walk  ·  ARTIFACT

*do the members drift persistently toward some reduced classes as n grows?*

![modular_walk](modular_walk.png)

**Critique.** ARTIFACT - walk_drift_mean=0.416 (Cramer z=-2.494, sieved z=-2.912). Both nulls reproduce it; whatever you can see is the encoding drawing itself, not the primes.

**Reading the picture.** The dashed circle is the distance an ordinary random walk of that many steps would typically reach, so it is the drift = 1 contour and every panel is readable on its own terms despite the differing axis scales. A path that fills its circle and ends near the rim is equidistribution; one that sets off in a straight line past it is a persistent bias; one that stays huddled well inside — which is what the primes do — is a set spread *more* evenly than chance.

| statistic | real | Cramér mean±sd | z | sieved mean±sd | z |
|---|---|---|---|---|---|
| `drift_k8` | 0.671 | 0.740±0.324 | -0.211 | 0.781±0.471 | -0.233 |
| `drift_k9` | 0.429 | 0.920±0.655 | -0.751 | 0.872±0.354 | -1.254 |
| `drift_k11` | 0.452 | 1.386±0.697 | -1.339 | 0.709±0.366 | -0.700 |
| `drift_k13` | 0.400 | 1.122±0.840 | -0.860 | 0.835±0.510 | -0.851 |
| `drift_k16` | 0.149 | 0.891±0.367 | -2.020 | 1.021±0.613 | -1.421 |
| `drift_k25` | 0.390 | 1.088±0.796 | -0.877 | 0.974±0.503 | -1.163 |
| `drift_k29` | 0.419 | 0.969±0.512 | -1.076 | 0.833±0.327 | -1.266 |
| `walk_drift_mean` | 0.416 | 1.017±0.241 | -2.494 | 0.861±0.153 | -2.912 |
| `walk_drift_max` | 0.671 | 1.989±0.533 | -2.474 | 1.555±0.380 | -2.325 |

## Polar plot, r=n and θ=n radians  ·  ARTIFACT

*are the visible spiral arms a property of the primes or of 2π?*

![polar_radian](polar_radian.png)

**Critique.** ARTIFACT - ang_dispersion_710=1.037 (Cramer z=-0.620, sieved z=0.967). Both nulls reproduce it; whatever you can see is the encoding drawing itself, not the primes.

**Reading the picture.** Arm counts 6, 44 and 710 are the denominators you get when you approximate 2π by a fraction; 100 is a non-resonant control. Dispersion is measured against the number of candidate integers per angular bin, so a set that is simply 'some integers' scores ~1 no matter how striking the picture looks. The `_allint` variants use all integers as candidates: at 710 bins they read ≈21 for the primes and ≈21 for the sieved null alike, a twentyfold 'signal' that is entirely the even bins being empty. Instructive as a demonstration of how easily a statistic can be manufactured out of nothing.

| statistic | real | Cramér mean±sd | z | sieved mean±sd | z |
|---|---|---|---|---|---|
| `ang_dispersion_allint_6` | 0.491 | 0.927±0.748 | -0.583 | 0.553±0.320 | -0.196 |
| `ang_dispersion_6` | 0.843 | 1.679±1.154 | -0.725 | 0.868±0.506 | -0.050 |
| `ang_dispersion_allint_44` | 1.624 | 0.849±0.183 | 4.242 | 1.218±0.172 | 2.358 |
| `ang_dispersion_44` | 1.144 | 2.488±0.401 | -3.349 | 0.969±0.206 | 0.851 |
| `ang_dispersion_allint_100` | 2.132 | 0.862±0.139 | 9.164 | 2.352±0.193 | -1.134 |
| `ang_dispersion_100` | 1.011 | 4.993±0.538 | -7.401 | 1.003±0.157 | 0.050 |
| `ang_dispersion_allint_710` | 11.406 | 0.891±0.057 | 183.641 | 11.357±0.133 | 0.368 |
| `ang_dispersion_710` | 1.037 | 1.083±0.073 | -0.620 | 0.964±0.076 | 0.967 |
