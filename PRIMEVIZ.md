# Blind visual search for structure in the primes

An extensible harness for encoding the primes as pictures and then refusing to
believe the pictures.

Every representation is rendered three times side by side — once on the real
primes and once on each of two null control sets — and scored with a statistic
that is recomputed over an ensemble of independent null draws. A pattern is
called structure only when the nulls fail to reproduce it.

```
python3 run.py                    # iteration 1, N = 50,000   (~10 s)
python3 run.py --iteration 2      # adds representations tagged iteration 2
python3 run.py --quick            # N = 20,000                (~5 s)
python3 run.py --umap             # opt in to UMAP beside PCA (~1 min per set)
python3 run.py --only prime_gaps  # re-render one representation
python3 run.py --list             # what is registered
```

PCA is the default projection for the exponent-vector embedding. UMAP is behind
a flag because it costs a minute per set and, on these inputs, spends it
separating exact duplicate vectors into islands that look identical on all
three panels.

Output lands in `out/iteration_NN/`: one PNG per representation, plus
`report.md` and `results.json`.

## The nulls

| null | what it is | what it controls for |
|---|---|---|
| `cramer` | each n kept independently with probability ∝ 1/ln n, rescaled to π(N) | density alone |
| `sieved` | the same, restricted to residues coprime to 2·3·5·7 = 210 | density **and** small-factor avoidance |
| `rough` | **deterministic**: every integer with no prime factor ≤ 47 | density, deep divisibility, and determinism |

The second one is what makes the harness worth running. Almost every striking
picture of the primes is a picture of "these integers have no small factors",
which is the definition of a prime rather than a fact about how they are
distributed. `sieved` already knows that, so anything that separates from it is
saying something else.

Verdicts name the strictest null the primes still separate from, in increasing
order of interest:

- **ARTIFACT** — every null reproduces it. The encoding is drawing itself.
- **COPRIMALITY** — separates from `cramer` only. Real, but it is divisibility by 2,3,5,7.
- **DEEP-COPRIMALITY** — separates from `sieved` but not from `rough`. Still divisibility, just deeper — and `rough` contains no primality at all.
- **SURVIVES** — separates from all three. Owes you a mechanism.
- **INCONCLUSIVE** — the statistic failed or the null spread was degenerate.

`rough` is deterministic, so it has no ensemble and no spread of its own. Its
z is expressed in units of the `sieved` ensemble's spread — a yardstick, not a
significance test. And it is denser than the primes (0.139 vs 0.103), which is
a real confound; the sieve-bound sweep in `calibrate.py` handles it by showing
every statistic sliding smoothly onto the primes' value as the bound rises.

**What the nulls have found so far: nothing that requires primality.** See
`RESULTS.md`. Every statistic here is a monotone function of sieve depth.

The critique line also reports the *direction*: a value below the nulls means
the primes are **more even** than random, which is a different discovery from
being more clumped, and the two are easy to confuse when you only look at |z|.

## Two normalisations that decide most verdicts

Both were added after the first run produced nonsense, and both live in
`stats.dispersion`:

1. **Candidate pool.** Counting statistics use the integers coprime to 210 as
   the denominator, not all integers. Measuring the primes against *all*
   integers builds small-factor avoidance into the answer before the null gets
   a say — it is how the polar plot manufactures a χ²/dof of 21 out of nothing.
2. **The (1−ρ) correction.** The primes occupy about half of the integers
   coprime to 210. Choosing a fraction ρ of a pool is binomial, not Poisson, so
   even a perfectly random choice lands at χ²/dof ≈ (1−ρ) rather than 1. At
   ρ ≈ 0.5 that is a factor-of-two error in exactly the statistic the verdicts
   hang on.

## Adding a representation

Drop a module in `primeviz/reps/`. It is auto-discovered.

```python
from ..registry import Representation

def render(iset, subfig, ctx):
    ax = subfig.subplots(1, 1)
    ax.scatter(...)                      # iset.values is the sorted members

def stats(iset, ctx) -> dict[str, float]:
    return {"my_stat": ...}              # recomputed on every null draw

Representation(
    key="my_rep", title="...", question="what this asks of the integers",
    render=render, stats=stats, headline="my_stat", iteration=2,
    notes="how to read the picture",
    mechanism="why it happens -- printed only if it survives",
)
```

`ctx` carries the shared geometry (`ctx.ulam`, `ctx.sacks`), the candidate mask
(`ctx.admissible`), factorisation (`ctx.exps`) and subsampling.

Rules the harness enforces on itself: no base-10 digit properties anywhere, and
every encoding is derived from the raw integers rather than looked up.

## Layout

```
primeviz/
  numbers.py    sieve, the two null models, exponent vectors
  context.py    run config + cached geometry
  registry.py   the Representation record and auto-discovery
  stats.py      dispersion, z-scores against the null ensemble, verdicts
  runner.py     render 3-up, score, critique, write the report
  theme.py      one palette, validated for colour-vision deficiency
  reps/         one module per family of representations
```

## Cost on this machine

4 cores, 15 GB RAM. N = 50,000 across all 11 representations is **~12 seconds**;
N = 100,000 is ~25 s. Adding `--umap` costs about a minute per set on top,
which is the entire reason it is opt-in. UMAP runs on the members directly at
these sizes; past ~10⁶ it would need `--umap-max`.

## Calibration is where the bugs live

Every statistic in here was wrong the first time it ran, and each bug produced a
confident, plausible-looking result rather than an obvious failure:

| bug | what it looked like |
|---|---|
| counting against all integers rather than the candidate pool | χ²/dof of 21 on the polar plot — reproduced exactly by the null |
| Poisson variance where the sampling is binomial | every set at half its pool looked 2× "more ordered" than random |
| density window saturating at N | tenfold inflation at large scales, with a flat control still reading 1.0 |
| density window overrunning the ends of the range | a red stripe at low n in the fluctuation map |
| reading one noisy draw as a trend | a "systematic large-L deflation" that a 12-draw matched-density ensemble showed does not exist |
| density-matching a deterministic control by running-count | a control that was simultaneously too even (gaps, fluctuation) and too uneven (residues) |

The habit that catches them: build a control whose answer you already know and
check the statistic returns 1.0 before believing anything it says about the
primes. Two refinements learned the hard way — **the control has to match the
property you are testing** (a flat control cannot expose a density-trend
artefact, and it is what hid the first bug), and **one draw is not a control**
(at the widest scales the fluctuation statistic's own sd/mean is 0.26, easily
enough to fake a trend).

## Independence of evidence

The modular sweep, CRT lattice, fluctuation map and gap correlation are **not**
independent tests. They are four views of the same two facts: the members avoid
small residues, and their density is smooth. When they agree, that is not
corroboration — treat them as one claim.
