# Blind visual search for structure in the primes

An extensible harness for encoding the primes as pictures and then refusing to
believe the pictures.

Every representation is rendered three times side by side — once on the real
primes and once on each of two null control sets — and scored with a statistic
that is recomputed over an ensemble of independent null draws. A pattern is
called structure only when the nulls fail to reproduce it.

```
python3 run.py                    # iteration 1, N = 100,000  (~3.5 min)
python3 run.py --quick            # N = 20,000, no UMAP       (~10 s)
python3 run.py --only prime_gaps  # re-render one representation
python3 run.py --list             # what is registered
```

Output lands in `out/iteration_NN/`: one PNG per representation, plus
`report.md` and `results.json`.

## The nulls

| null | what it is | what it controls for |
|---|---|---|
| `cramer` | each n kept independently with probability ∝ 1/ln n, rescaled to π(N) | density alone |
| `sieved` | the same, restricted to residues coprime to 2·3·5·7 = 210 | density **and** small-factor avoidance |

The second one is what makes the harness worth running. Almost every striking
picture of the primes is a picture of "these integers have no small factors",
which is the definition of a prime rather than a fact about how they are
distributed. `sieved` already knows that, so anything that separates from it is
saying something else.

Verdicts, in increasing order of interest:

- **ARTIFACT** — both nulls reproduce it. The encoding is drawing itself.
- **COPRIMALITY** — separates from `cramer` only. Real, but it is divisibility.
- **SURVIVES** — separates from both. Owes you a mechanism.
- **INCONCLUSIVE** — the statistic failed or the null spread was degenerate.

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

4 cores, 15 GB RAM. N = 100,000 end to end is ~3m20s, of which **UMAP is ~3
minutes** — everything else together is under 20 seconds. UMAP is run on the
~9.6k members directly (no subsampling needed at this N); at N = 10⁶ it would
need `--umap-max`. Use `--no-umap` for fast iteration and `--quick` for a
10-second smoke test.
