# Iteration 3

`N = 10,000,000`  ·  seed `0`  ·  12 null replicates per model ·  561s

| set | count | density |
|---|---|---|
| primes <= 10,000,000 | 664,579 | 0.06646 |
| null: Cramer 1/ln n | 665,004 | 0.06650 |
| null: sieved mod 210 | 665,478 | 0.06655 |
| det: no factor <= 199 (unthinned) | 1,044,289 | 0.10443 |

Verdicts are on the headline statistic, z measured against an ensemble of independent null draws. `SURVIVES` = separates from both nulls. `COPRIMALITY` = separates from Cramér only, i.e. it is small-factor avoidance. `ARTIFACT` = both nulls reproduce it.

| verdict | representation | headline | real | z vs Cramér | z vs sieved | z vs rough |
|---|---|---|---|---|---|---|
| **SURVIVES** | `count_fluctuation` | fluct_dispersion_small_L | 0.318 | -13.099 | -9.065 | 3.155 |
| **SURVIVES** | `crt_lattice` | crt_independence | 0.319 | -18.555 | -11.643 | 3.681 |
| **SURVIVES** | `pair_spectrum` | pair_corr_dispersion | 116.435 | -215.450 | 847.063 | -1.24e+03 |
| **SURVIVES** | `prime_gaps` | gap_lag1_corr | -0.038 | -39.550 | -28.144 | 43.811 |
| **SURVIVES** | `sacks_spiral` | local_ang_dispersion | 0.871 | -8.191 | -2.207 | -5.250 |
| **SURVIVES** | `smoothness_landscape` | mean_log_lpf_ratio | 1.000 | 1.82e+03 | 1.3e+03 | 742.908 |
| **SURVIVES** | `ulam_spiral` | diag_dispersion | 6.566 | -100.361 | 217.391 | -222.648 |
| **DEEP-COPRIMALITY** | `factor_embed` | frac_at_origin | 1.000 | 1.93e+03 | 831.510 | -0.021 |
| **DEEP-COPRIMALITY** | `factor_shift` | mean_basis_exponent_shift | 3.883 | 630.425 | 18.245 | -1.310 |
| **DEEP-COPRIMALITY** | `modular_grid` | reduced_dispersion | 0.082 | -10.028 | -5.309 | 0.447 |
| **DEEP-COPRIMALITY** | `modular_walk` | walk_drift_mean | 0.286 | -4.542 | -4.570 | 1.419 |
| **COPRIMALITY** | `polar_radian` | ang_dispersion_710 | 0.958 | -9.574 | -1.175 | 2.339 |

## Multiscale count-fluctuation map  ·  SURVIVES

*at any scale, does the set clump or resist clumping along the number line?*

![count_fluctuation](count_fluctuation.png)

**Critique.** SURVIVES - fluct_dispersion_small_L=0.318 (z: Cramer -13.099, sieved -9.065, rough 3.155). Not reproduced by matched-density randomness, by small-factor avoidance, or by a deterministic set avoiding every prime up to 199. Needs a mechanism. Real is ABOVE the null - more clumped.

**Reading the picture.** The map is a scale-space view: one row per window length, colour is how many standard deviations the count in that window sat from its local expectation. Grey everywhere means fluctuation exactly as large as chance predicts. Red and blue patches that persist upward through the rows are genuine excursions — a run of the number line that is rich or poor at several scales at once. The curve below collapses each row to a single number, and the dashed line is what a randomly sprinkled set gives. Two calibration facts. (1) A single curve's downward slope at large L is mostly noise, not signal and not estimator bias: only ~27 overlapping windows fit at the widest scale and the statistic's own spread there is sd/mean ≈ 0.26. A twelve-draw matched-density Poisson ensemble does not trend (0.94 → 0.82). Read the gap between curves, not the slope of one — the primes sit 3–6 sd below that ensemble at every scale. (2) The Cramér column runs ~1.6× high because that null lives on all integers while the candidate pool is the integers coprime to 210, so its binomial variance is mismatched. Read the sieved column: it shares both the support and the density profile of the primes. The headline uses the smallest third of scales, where the control sits at 1.0 and the sieved null at 0.95.

**Why it happens.** Values below 1 mean the count in a window is pinned closer to its expectation than independent sampling would allow — the same hyper-evenness the modular sweep found, but with no reference to residues at all, so it cannot be a divisibility effect in disguise.

| statistic | real | Cramér | z | sieved | z | rough | z |
|---|---|---|---|---|---|---|---|
| `fluct_dispersion` | 0.616 | 1.529±0.149 | -6.121 | 1.355±0.166 | -4.461 | 0.079 | 3.236 |
| `fluct_dispersion_small_L` | 0.318 | 1.231±0.070 | -13.099 | 0.984±0.074 | -9.065 | 0.086 | 3.155 |
| `fluct_dispersion_large_L` | 1.033 | 1.917±0.275 | -3.212 | 1.860±0.329 | -2.510 | 0.084 | 2.884 |
| `fluct_slope` | 0.545 | 0.208±0.076 | 4.429 | 0.296±0.082 | 3.044 | 0.011 | 6.532 |

## CRT lattice — joint residues (n mod p, n mod q)  ·  SURVIVES

*does knowing n mod p tell you anything about n mod q?*

![crt_lattice](crt_lattice.png)

**Critique.** SURVIVES - crt_independence=0.319 (z: Cramer -18.555, sieved -11.643, rough 3.681). Not reproduced by matched-density randomness, by small-factor avoidance, or by a deterministic set avoiding every prime up to 199. Needs a mechanism. Real is ABOVE the null - more clumped.

**Reading the picture.** Grey means the cell holds exactly what independence predicts. A value of χ²/dof near 1 means the two residues carry no information about each other; the picture being visibly speckled at this sample size is expected — roughly 10 members per cell — and is noise, not texture. Compare the reduced statistic with `crt_independence_unreduced` to see how much a naive version of this test would have been driven by the empty row and column alone.

**Why it happens.** Any dependence would mean the members are not spread across residue classes mod pq the way they are spread mod p and mod q separately.

| statistic | real | Cramér | z | sieved | z | rough | z |
|---|---|---|---|---|---|---|---|
| `crt_independence` | 0.319 | 1.313±0.054 | -18.555 | 0.987±0.057 | -11.643 | 0.108 | 3.681 |
| `crt_independence_max` | 0.404 | 1.514±0.117 | -9.509 | 1.074±0.097 | -6.910 | 0.149 | 2.641 |
| `crt_independence_unreduced` | 0.304 | 0.929±0.027 | -23.544 | 0.699±0.035 | -11.301 | 0.159 | 4.154 |
| `crt_indep_11_13` | 0.250 | 1.304±0.243 | -4.334 | 0.987±0.136 | -5.411 | 0.077 | 1.273 |
| `crt_indep_13_17` | 0.244 | 1.340±0.189 | -5.790 | 0.995±0.119 | -6.325 | 0.087 | 1.317 |

## All-pairs difference spectrum  ·  SURVIVES

*is any distance between members taken more often than its number of chances?*

![pair_spectrum](pair_spectrum.png)

**Critique.** SURVIVES - pair_corr_dispersion=116.435 (z: Cramer -215.450, sieved 847.063, rough -1.24e+03). Not reproduced by matched-density randomness, by small-factor avoidance, or by a deterministic set avoiding every prime up to 199. Needs a mechanism. Real is BELOW the null - more even/less clumped.

**Reading the picture.** Both panels are already normalised by candidate pairs, so a flat grey line at 1 is the honest null result and the spikes of a raw difference histogram have deliberately been divided out. Only even distances appear: two members coprime to 210 are both odd, so an odd separation is impossible and those columns are empty by construction, not by absence of structure. Read the lower panel for vertical stripes that hold across every band — a distance favoured throughout the range is a much stronger claim than one favoured on average. The Cramér column sits far below 1 for a mechanical reason rather than an interesting one: that null lives on all integers while the normalisation counts candidate pairs among the integers coprime to 210.

**Why it happens.** Not memory, and not new: this is the sieved null's 7 showing. When d shares a factor p with one of 11…47, the pair (n, n+d) occupies a single residue class mod p instead of two, so it has one fewer way to be composite and both ends are likelier to be prime. `deep_sieve_ratio` isolates it — the primes read ≈1.06, the sieved null ≈1.00, because that null only avoids factors up to 7 and so has no opinion about 11 through 47. It is the same mechanism suspected behind the surviving Ulam diagonals, here measured directly instead of hypothesised. A null sieved at 47 or higher should erase this verdict; that is the test worth running next.

| statistic | real | Cramér | z | sieved | z | rough | z |
|---|---|---|---|---|---|---|---|
| `pair_corr_dispersion` | 116.435 | 5.73e+03±26.056 | -215.450 | 0.590±0.137 | 847.063 | 285.475 | -1.24e+03 |
| `pair_corr_spread` | 0.036 | 0.174±0.000206 | -669.145 | 0.00275±0.000334 | 100.251 | 0.036 | 0.223 |
| `deep_sieve_ratio` | 1.062 | 1.143±0.00105 | -76.940 | 1.000±0.000382 | 161.411 | 1.062 | -0.724 |
| `pair_corr_max` | 1.083 | 0.738±0.00179 | 192.367 | 1.008±0.00161 | 46.552 | 1.081 | 0.876 |
| `pair_corr_min` | 0.969 | 0.228±0.000785 | 942.882 | 0.993±0.00117 | -20.319 | 0.972 | -2.557 |

## Gap series, gap histogram, gap-pair map  ·  SURVIVES

*is the spacing sequence anything other than a memoryless point process?*

![prime_gaps](prime_gaps.png)

**Critique.** SURVIVES - gap_lag1_corr=-0.038 (z: Cramer -39.550, sieved -28.144, rough 43.811). Not reproduced by matched-density randomness, by small-factor avoidance, or by a deterministic set avoiding every prime up to 199. Needs a mechanism. Real is ABOVE the null - more clumped.

**Reading the picture.** The third panel divides the observed (gₖ, gₖ₊₁) table by what it would be if consecutive gaps were independent, so grey is 'no memory' and any coloured cell is a gap pair that happens more or less often than chance. The histogram's spikes at multiples of 6 are the thing to be suspicious of.

**Why it happens.** Consecutive members that are all odd force every gap even, and members avoiding 3 as well push gaps toward multiples of 6 -- both are consequences of small-factor avoidance, and a null with the same avoidance shows the same spikes. Any lag-1 correlation beyond that would be genuine memory.

| statistic | real | Cramér | z | sieved | z | rough | z |
|---|---|---|---|---|---|---|---|
| `gap_var_ratio` | 0.698 | 0.944±0.00195 | -126.307 | 0.750±0.00163 | -31.812 | 0.552 | 89.169 |
| `gap_lag1_corr` | -0.038 | 0.00528±0.0011 | -39.550 | -0.00866±0.00105 | -28.144 | -0.084 | 43.811 |
| `frac_gap_div6` | 0.430 | 0.139±0.00032 | 910.897 | 0.433±0.000653 | -3.693 | 0.401 | 45.341 |
| `frac_gap_even` | 1.000 | 0.483±0.00068 | 760.599 | 1.000±1.77e-09 | 0.549 | 1.000 | -309.636 |
| `max_gap_over_mean` | 10.235 | 14.423±1.934 | -2.165 | 12.121±0.899 | -2.098 | 10.025 | 0.233 |

## Sacks square-root spiral  ·  SURVIVES

*does the set concentrate on particular √n phase angles (i.e. quadratics)?*

![sacks_spiral](sacks_spiral.png)

**Critique.** SURVIVES - local_ang_dispersion=0.871 (z: Cramer -8.191, sieved -2.207, rough -5.250). Not reproduced by matched-density randomness, by small-factor avoidance, or by a deterministic set avoiding every prime up to 199. Needs a mechanism. Real is BELOW the null - more even/less clumped.

**Reading the picture.** Angle is 2π·frac(√n), so a quadratic n = k²+bk+c sits at a *nearly* fixed angle — it drifts by O(1/k), which is why the global binning is nearly blind and the headline uses thin radial annuli instead. Candidates are the integers coprime to 210, so a ray that exists only because its progression is all-even does not count.

**Why it happens.** frac(√n) is almost constant along k²+bk+c, so each quadratic progression is roughly one angular bin. Progressions that are identically even, or identically divisible by 3, hold no primes and the rest absorb the density — that is what the eye reads as rays, and the sieved null draws the same ones.

| statistic | real | Cramér | z | sieved | z | rough | z |
|---|---|---|---|---|---|---|---|
| `ang_dispersion_allint_360` | 0.913 | 0.897±0.051 | 0.307 | 0.766±0.065 | 2.251 | 0.950 | -0.574 |
| `ang_dispersion_360` | 1.154 | 1.361±0.078 | -2.638 | 0.982±0.077 | 2.227 | 1.965 | -10.484 |
| `ang_dispersion_allint_720` | 0.957 | 0.918±0.045 | 0.873 | 0.786±0.037 | 4.632 | 0.816 | 3.828 |
| `ang_dispersion_720` | 1.199 | 1.411±0.061 | -3.476 | 0.989±0.051 | 4.127 | 1.502 | -5.942 |
| `local_ang_dispersion` | 0.871 | 1.370±0.061 | -8.191 | 1.001±0.059 | -2.207 | 1.180 | -5.250 |

## Smoothness landscape — log(largest prime factor)/log n  ·  SURVIVES

*what does the difference between these sets actually consist of?*

![smoothness_landscape](smoothness_landscape.png)

**Critique.** SURVIVES - mean_log_lpf_ratio=1.000 (z: Cramer 1.82e+03, sieved 1.3e+03, rough 742.908). Not reproduced by matched-density randomness, by small-factor avoidance, or by a deterministic set avoiding every prime up to 199. Needs a mechanism. Real is ABOVE the null - more clumped.

**Reading the picture.** Circular by construction — see below — so read it as a diagram, not a test. The grey background is every integer; the coloured overlay is the set. The primes are a single line along the top because r = 1 *defines* prime. A rough ≤ b set is a band whose floor is log b / log n, sagging to the right as log n grows: everything below that floor has been sieved away. The Cramér null fills the whole landscape because it is drawn without regard to factorisation. The gap between the primes' line and the rough band is the set of semiprimes and higher almost-primes that no sieve-data statistic in this harness can see.

**Why it happens.** It separates the primes perfectly and this proves nothing: r(n) is computed *from* the factorisation of n, so the instrument is handed the answer before it draws. Its value is diagnostic — it makes visible the region where the parity barrier lives, namely the band between r = 1 and the rough floor, which is exactly the almost-primes that share all their small-residue statistics with the primes.

| statistic | real | Cramér | z | sieved | z | rough | z |
|---|---|---|---|---|---|---|---|
| `mean_log_lpf_ratio` | 1.000 | 0.647±0.000194 | 1.82e+03 | 0.730±0.000208 | 1.3e+03 | 0.846 | 742.908 |
| `frac_prime` | 1.000 | 0.067±0.000381 | 2.45e+03 | 0.292±0.00054 | 1.31e+03 | 0.636 | 672.914 |
| `frac_r_below_half` | 0.000 | 0.272±0.000556 | -488.880 | 0.146±0.000275 | -532.078 | 1.92e-06 | -0.00696 |
| `min_r` | 1.000 | 0.266±0.000387 | 1.9e+03 | 0.326±0.000646 | 1.04e+03 | 0.504 | 767.754 |

## Ulam square spiral  ·  SURVIVES

*do the set's members line up on the spiral's diagonals?*

![ulam_spiral](ulam_spiral.png)

**Critique.** SURVIVES - diag_dispersion=6.566 (z: Cramer -100.361, sieved 217.391, rough -222.648). Not reproduced by matched-density randomness, by small-factor avoidance, or by a deterministic set avoiding every prime up to 199. Needs a mechanism. Real is BELOW the null - more even/less clumped.

**Reading the picture.** Diagonals of the square spiral are values of quadratics 4k²+bk+c; rows and columns are not, and act as an internal control — `diag_over_row` is the ratio. The headline counts candidates from the integers coprime to 210 and applies the (1−ρ) correction, so the diagonals that are empty *because they are all even* no longer contribute; `diag_dispersion_allint` is the naive version that lets them count, and the gap between the two is how much of the famous diagonal effect is just parity.

**Why it happens.** Along any diagonal of this spiral n advances by 4k+const, so n mod 2 — and for half of them n mod 3 — is fixed. Every diagonal whose fixed residue shares a factor with 2 or 3 is empty of primes and the rest absorb the density, which is the whole of the naive statistic. Once candidates are restricted to integers coprime to 210 that mechanism is spent, and what is left is the same hyper-evenness seen in the modular sweep rather than a preference for particular quadratics.

| statistic | real | Cramér | z | sieved | z | rough | z |
|---|---|---|---|---|---|---|---|
| `diag_dispersion_allint` | 131.638 | 1.057±0.00849 | 1.54e+04 | 127.451±0.178 | 23.465 | 206.005 | -416.769 |
| `diag_dispersion` | 6.566 | 18.550±0.119 | -100.361 | 1.386±0.024 | 217.391 | 11.871 | -222.648 |
| `anti_dispersion_allint` | 118.742 | 1.058±0.018 | 6.72e+03 | 114.383±0.144 | 30.348 | 186.081 | -468.877 |
| `anti_dispersion` | 6.952 | 6.092±0.090 | 9.573 | 1.384±0.023 | 238.659 | 13.218 | -268.614 |
| `row_dispersion_allint` | 13.677 | 1.329±0.020 | 617.980 | 12.817±0.101 | 8.533 | 19.508 | -57.860 |
| `row_dispersion` | 2.503 | 24.291±0.188 | -116.145 | 1.548±0.044 | 21.609 | 2.817 | -7.111 |
| `col_dispersion_allint` | 13.559 | 1.321±0.046 | 266.176 | 12.937±0.134 | 4.655 | 20.098 | -48.944 |
| `col_dispersion` | 2.465 | 24.318±0.296 | -73.882 | 1.562±0.038 | 23.473 | 2.801 | -8.749 |
| `diag_over_row` | 2.623 | 0.764±0.00921 | 201.813 | 0.896±0.031 | 56.311 | 4.213 | -51.852 |

## Factorisation embedding of n (PCA)  ·  DEEP-COPRIMALITY

*where does the set sit in the space of small-prime exponent vectors?*

![factor_embed](factor_embed.png)

**Critique.** DEEP-COPRIMALITY - frac_at_origin=1.000 (z: Cramer 1.93e+03, sieved 831.510, rough -0.021). Beats avoidance of 2,3,5,7 but not avoidance of every prime up to 199. Still divisibility, just deeper - and the deterministic rough set has no primality in it. Real is ABOVE the null - more clumped.

**Reading the picture.** Read the axes before the pattern: the coordinates are 'how many times does 2, 3, 5 ... divide n'. Almost every prime is at the origin because none of them do — the primes panel is one coloured dot. Note the disagreement between eye and statistic here, in the direction people usually assume is impossible: the *picture* cannot tell the primes from the sieved null (both collapse to the origin, since PC1 and PC2 are essentially the exponents of 2 and 3, which both sets have set to zero), while the *statistic* separates them at z = 122. Neither is wrong; they are answering different questions, and the statistic's question happens to be a tautology.

**Why it happens.** Tautological, and worth stating plainly so it is not mistaken for a finding: the embedding's coordinates are divisibility by the primes up to 71, and a prime above 71 is divisible by none of them, so it maps to the zero vector by definition. `frac_at_origin` ≈ 1 for the primes is a restatement of what a prime is. It separates from the sieved null only because that null is sieved at 7, not at 71 -- a deeper null (integers with no factor below 71) would erase this entirely.

| statistic | real | Cramér | z | sieved | z | rough | z |
|---|---|---|---|---|---|---|---|
| `frac_at_origin` | 1.000 | 0.128±0.000451 | 1.93e+03 | 0.559±0.00053 | 831.510 | 1.000 | -0.021 |
| `mean_basis_exponent` | 3.01e-05 | 2.513±0.00225 | -1.11e+03 | 0.597±0.000871 | -685.483 | 1.92e-05 | 0.013 |
| `mean_v2` | 1.5e-06 | 1.000±0.00138 | -724.099 | 1.51e-06±1.77e-09 | -0.549 | 9.58e-07 | 309.636 |

## Factorisation embedding of n−1 (PCA + UMAP)  ·  DEEP-COPRIMALITY

*is the multiplicative shape of p−1 unusual for an integer of that size?*

![factor_shift](factor_shift.png)

**Critique.** DEEP-COPRIMALITY - mean_basis_exponent_shift=3.883 (z: Cramer 630.425, sieved 18.245, rough -1.310). Beats avoidance of 2,3,5,7 but not avoidance of every prime up to 199. Still divisibility, just deeper - and the deterministic rough set has no primality in it. Real is ABOVE the null - more clumped.

**Reading the picture.** Both projections are log-scaled density hexbins, not scatter, because 10⁴ points overplot. PCA is dominated by the 2-adic valuation of n−1. Treat the UMAP clusters as furniture, not findings: the exponent vectors are short integer vectors with many exact duplicates, so UMAP separates them into islands of identical points, and it draws the same islands on all three panels. Cluster count and shape here are a function of n_neighbors and of the discreteness of the coordinates, not of which integers went in.

**Why it happens.** Every prime past 2 is odd, so p−1 is always even, and the density of the basis exponents shifts up accordingly. That is parity, not depth: a null whose members are already odd shows the same thing.

| statistic | real | Cramér | z | sieved | z | rough | z |
|---|---|---|---|---|---|---|---|
| `mean_v2_of_shift` | 1.999 | 1.000±0.00151 | 662.089 | 1.999±0.00115 | -0.274 | 2.000 | -0.632 |
| `mean_basis_exponent_shift` | 3.883 | 2.513±0.00217 | 630.425 | 3.853±0.00167 | 18.245 | 3.886 | -1.310 |
| `frac_shift_div6` | 0.500 | 0.167±0.000335 | 993.050 | 0.500±0.000449 | -0.069 | 0.500 | -0.357 |
| `v2_shape_dispersion` | 7.47e+04 | 148.079±9.699 | 7.69e+03 | 7.47e+04±82.376 | 0.458 | 1.17e+05 | -518.147 |

## Modular grid sweep, k = 2..60  ·  DEEP-COPRIMALITY

*beyond avoiding small factors, is the set unevenly spread across residue classes?*

![modular_grid](modular_grid.png)

**Critique.** DEEP-COPRIMALITY - reduced_dispersion=0.082 (z: Cramer -10.028, sieved -5.309, rough 0.447). Beats avoidance of 2,3,5,7 but not avoidance of every prime up to 199. Still divisibility, just deeper - and the deterministic rough set has no primality in it. Real is BELOW the null - more even/less clumped.

**Reading the picture.** In the sweep, black = a residue class the set never occupies, grey = exactly the expected share, red = enriched. The banded triangle is the divisibility pattern. The headline statistic throws that pattern away: it looks only at classes coprime to k, counts candidates from the integers coprime to 210, and applies the binomial (1−ρ) correction — so 1.0 means 'no better spread than a random choice of that many candidates', and anything well below 1 means the set is *more* even than random.

**Why it happens.** Two separate things live in this picture. The dark columns are trivial: a class j mod k with gcd(j,k) = d > 1 contains only multiples of d, so it holds no primes past d itself. The headline number is not that — it is the spread across the classes that are allowed, and for the primes it comes out far *below* random. The primes' counts in the reduced classes mod k sit within a few units of dead level where a random set of the same size would scatter by ±√count. The reason is that the primes are one fixed set, not a sample: their counting error in each progression is a single slowly-growing quantity of order √N, shared out over the φ(k) classes, instead of independent per-class sampling noise of order √(count) each. At N=10⁵ that is roughly a threefold smaller deviation, i.e. an order of magnitude in χ².

| statistic | real | Cramér | z | sieved | z | rough | z |
|---|---|---|---|---|---|---|---|
| `reduced_dispersion` | 0.082 | 1.046±0.096 | -10.028 | 0.922±0.158 | -5.309 | 0.012 | 0.447 |
| `max_reduced_dispersion` | 0.177 | 2.292±0.572 | -3.696 | 2.093±0.828 | -2.313 | 0.040 | 0.165 |
| `reduced_dispersion_allint_pool` | 0.058 | 0.845±0.081 | -9.671 | 0.654±0.112 | -5.322 | 0.00629 | 0.460 |
| `all_class_dispersion` | 3.16e+04 | 0.916±0.052 | 6.11e+05 | 3.07e+04±36.047 | 24.625 | 4.96e+04 | -500.477 |
| `reduced_dispersion_k12` | 0.052 | 0.649±0.339 | -1.762 | 0.511±0.336 | -1.365 | 0.00176 | 0.150 |
| `reduced_dispersion_k30` | 0.044 | 0.804±0.459 | -1.657 | 1.092±0.840 | -1.247 | 0.0018 | 0.050 |
| `reduced_dispersion_k47` | 0.121 | 1.426±0.219 | -5.954 | 0.961±0.256 | -3.285 | 0.040 | 0.318 |

## Centred modular walk  ·  DEEP-COPRIMALITY

*do the members drift persistently toward some reduced classes as n grows?*

![modular_walk](modular_walk.png)

**Critique.** DEEP-COPRIMALITY - walk_drift_mean=0.286 (z: Cramer -4.542, sieved -4.570, rough 1.419). Beats avoidance of 2,3,5,7 but not avoidance of every prime up to 199. Still divisibility, just deeper - and the deterministic rough set has no primality in it. Real is BELOW the null - more even/less clumped.

**Reading the picture.** The dashed circle is the distance an ordinary random walk of that many steps would typically reach, so it is the drift = 1 contour and every panel is readable on its own terms despite the differing axis scales. A path that fills its circle and ends near the rim is equidistribution; one that sets off in a straight line past it is a persistent bias; one that stays huddled well inside — which is what the primes do — is a set spread *more* evenly than chance.

**Why it happens.** A drift *above* 1 would be a bias among the classes coprime to k — the set preferring some reduced residues by an amount that does not wash out as n grows. A drift well *below* 1, which is what the primes give, is the opposite: the walk keeps returning to the origin because the residues are spread more evenly than chance would spread them. It is the same hyper-evenness the modular sweep measures, seen as a path instead of a histogram.

| statistic | real | Cramér | z | sieved | z | rough | z |
|---|---|---|---|---|---|---|---|
| `drift_k8` | 0.350 | 0.926±0.437 | -1.318 | 0.898±0.322 | -1.703 | 0.062 | 0.895 |
| `drift_k9` | 0.212 | 0.835±0.581 | -1.072 | 0.886±0.333 | -2.020 | 0.058 | 0.465 |
| `drift_k11` | 0.056 | 1.076±0.692 | -1.473 | 1.191±0.517 | -2.194 | 0.032 | 0.048 |
| `drift_k13` | 0.132 | 1.177±0.539 | -1.936 | 0.732±0.336 | -1.784 | 0.027 | 0.313 |
| `drift_k16` | 0.243 | 0.903±0.474 | -1.391 | 0.759±0.408 | -1.263 | 0.078 | 0.406 |
| `drift_k25` | 0.777 | 1.071±0.817 | -0.360 | 0.985±0.340 | -0.610 | 0.261 | 1.517 |
| `drift_k29` | 0.233 | 1.016±0.609 | -1.288 | 0.849±0.404 | -1.525 | 0.154 | 0.195 |
| `walk_drift_mean` | 0.286 | 1.001±0.157 | -4.542 | 0.900±0.134 | -4.570 | 0.096 | 1.419 |
| `walk_drift_max` | 0.777 | 1.927±0.531 | -2.166 | 1.497±0.174 | -4.143 | 0.261 | 2.969 |

## Polar plot, r=n and θ=n radians  ·  COPRIMALITY

*are the visible spiral arms a property of the primes or of 2π?*

![polar_radian](polar_radian.png)

**Critique.** COPRIMALITY - ang_dispersion_710=0.958 (z: Cramer -9.574, sieved -1.175, rough 2.339). Beats random integers but not integers that merely avoid factors 2,3,5,7. The definition of a prime showing through, not distributional structure. Real is BELOW the null - more even/less clumped.

**Reading the picture.** Arm counts 6, 44 and 710 are the denominators you get when you approximate 2π by a fraction; 100 is a non-resonant control. Dispersion is measured against the number of candidate integers per angular bin, so a set that is simply 'some integers' scores ~1 no matter how striking the picture looks. The `_allint` variants use all integers as candidates: at 710 bins they read ≈21 for the primes and ≈21 for the sieved null alike, a twentyfold 'signal' that is entirely the even bins being empty. Instructive as a demonstration of how easily a statistic can be manufactured out of nothing.

**Why it happens.** The spokes themselves are nothing about the primes: with 2π ≈ 44/7 ≈ 710/113, integers one apart land at angles that nearly repeat after 44 or 710 steps, so *any* set of integers is drawn onto them. The picture is of the continued-fraction expansion of 2π, and the statistic agrees — at 6, 44 and 100 bins the primes match the sieved null within z≈1. The one bin count that does separate, 710, separates for a reason that is still not about distribution: 710 = 2·5·71, and because 113/710 ≈ 1/2π the bin index is essentially n mod 710, so ten of the 710 bins are the classes divisible by 71. The primes vacate those ten bins; the sieved null, which only knows about factors up to 7, does not. That accounts for an excess of about 0.3 in χ²/dof, which is the whole of the observed gap. It is a measurement of the null's sieve bound, not of the primes.

| statistic | real | Cramér | z | sieved | z | rough | z |
|---|---|---|---|---|---|---|---|
| `ang_dispersion_allint_6` | 4.402 | 0.665±0.281 | 13.285 | 0.751±0.459 | 7.949 | 6.618 | -4.827 |
| `ang_dispersion_6` | 6.343 | 0.904±0.397 | 13.714 | 1.015±0.618 | 8.622 | 12.464 | -9.906 |
| `ang_dispersion_allint_44` | 2.766 | 0.884±0.196 | 9.589 | 0.809±0.167 | 11.707 | 3.637 | -5.210 |
| `ang_dispersion_44` | 3.938 | 1.357±0.350 | 7.369 | 1.011±0.245 | 11.940 | 6.628 | -10.972 |
| `ang_dispersion_allint_100` | 1.663 | 0.896±0.151 | 5.081 | 0.870±0.099 | 7.986 | 1.953 | -2.923 |
| `ang_dispersion_100` | 2.156 | 1.429±0.185 | 3.929 | 1.023±0.112 | 10.096 | 3.291 | -10.114 |
| `ang_dispersion_allint_710` | 0.869 | 0.937±0.036 | -1.900 | 0.921±0.043 | -1.229 | 0.664 | 4.801 |
| `ang_dispersion_710` | 0.958 | 1.544±0.061 | -9.574 | 1.031±0.062 | -1.175 | 0.813 | 2.339 |
