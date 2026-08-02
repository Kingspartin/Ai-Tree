# Ai-Tree

Visualized mobile ai app — built on a **number modeling system** that works in
both directions:

- **generate** — every number you feed in gets one fixed pattern that repeats forever
- **discover** — hand it any sequence and it tries method after method until one
  maps each term to the next

## Generating

```
1  →  1 2 3 4 5 6 7 8 9 ↺
4  →  4 8 3 7 2 6 1 5 9 ↺
5  →  5 1 6 2 7 3 8 4 9 ↺
```

Same number in, same pattern out — every run, every device, no randomness and no
state anywhere in the system.

### The idea

Pick a ring size (the **modulus**, 9 by default) and fold every value into the
range `1..modulus`. With modulus 9 that fold is the digital root, so `13 → 4` and
`400 → 4`.

A number `n` then generates its pattern by walking the ring in steps of `n`:

```
n, 2n, 3n, 4n, …   each folded back into 1..modulus
```

That walk has to close into a loop, because there are only `modulus` places to
stand. The loop length is exactly:

```
period = modulus / gcd(n, modulus)
```

For `n = 4, modulus = 9`: `gcd(4, 9) = 1`, so the period is 9 and the pattern
`4 8 3 7 2 6 1 5 9` visits every place once before repeating. For `n = 3` the gcd
is 3, so the pattern is the short loop `3 6 9`. Nothing is discovered at runtime —
the period is known from the inputs, which is what makes the whole thing
predictable.

Each model carries three views of its number:

| view | rule | for seed 4 |
| --- | --- | --- |
| **pattern** (ladder) | repeated `+n` around the ring | `4 8 3 7 2 6 1 5 9`, period 9 |
| **orbit** | repeated `×factor` around the ring | `4 8 7 5 1 2`, period 6 |
| **tree** | branch on `×factor`, `+n`, and mirror | 51 nodes at depth 4, closing on repeats |

The tree is the Ai-Tree part: each value branches by every rule, and a branch
stops the moment it reaches a value already on its own path — that's where the
pattern folds back on itself, so the tree is finite and identical on every build.

### Use it

```js
import { model } from './src/index.js';

const m = model(4);

m.pattern;      // [4, 8, 3, 7, 2, 6, 1, 5, 9]  ← the repeating unit
m.period;       // 9
m.at(0);        // 4
m.at(9);        // 4   — same term, one repeat later
m.at(1_000_000) // 8   — the pattern is defined at every index
m.take(12);     // [4, 8, 3, 7, 2, 6, 1, 5, 9, 4, 8, 3]
m.take(3, 2);   // [3, 7, 2]  — 3 terms starting at index 2
m.signature;    // 'm9/f2/s4/4-8-3-7-2-6-1-5-9/4-8-7-5-1-2'

m.orbit.cycle;  // [4, 8, 7, 5, 1, 2]
m.mirror;       // 6
m.tree;         // { value: 4, children: [...], values: [...], size: 51 }
```

Options — `model(seed, options)`:

| option | default | meaning |
| --- | --- | --- |
| `modulus` | `9` | ring size; 9 gives digital roots |
| `factor` | `2` | multiplier used by the orbit and the `grow` branch |
| `depth` | `4` | tree depth |
| `rules` | `['grow', 'shift', 'mirror']` | which branch rules the tree uses |

Other helpers:

```js
import { models, verify, sameShape, families } from './src/index.js';

models([1, 4, 5]);          // model each of several numbers
verify(model(4), 100);      // check 100 repeats term by term → { ok: true, … }
sameShape(model(4), model(13));  // true — 13 folds to 4
families([1, 2, 3, 4, 5]);  // Map of signature → the numbers that produce it
```

## Discovering

The other direction takes any sequence and searches for the rule behind it. Every
method is one hypothesis about how numbers could be organised; the engine runs all
of them, keeps the ones that reproduce the sequence exactly, and ranks what
survives.

```js
import { discover } from './src/index.js';

const found = discover([1, 1, 2, 3, 5, 8, 13]);

found.law.describe;   // 'x[i] = x[i-1] + x[i-2]'
found.law.method;     // 'recurrence(2)'
found.confidence;     // 'verified'
found.next(5);        // [21, 34, 55, 89, 144]
found.candidates;     // everything that fitted, best first
```

### The methods

| method | hypothesis | example |
| --- | --- | --- |
| `constant` | never changes | `7 7 7 7` |
| `arithmetic` | fixed step | `2 4 6 8` |
| `geometric` | fixed ratio | `1 2 4 8 16` |
| `polynomial(k)` | closed form in the index, via finite differences | `1 4 9 16 25` |
| `affine` | `x[i] = a·x[i-1] + b` | `5 17 53 161` |
| `recurrence(k)` | `x[i]` from the previous k terms | `1 1 2 3 5 8` |
| `product` | `x[i] = x[i-1] · (i + c)` | `1 1 2 6 24 120` |
| `periodic(p)` | the sequence is a loop | `3 1 4 3 1 4` |
| `interleaved(k)` | k independent sequences taking turns | `2 9 4 11 6 13` |
| `value-map` | each **value** decides the next value | `3 1 4 3 1 4` |
| `primes` | consecutive primes | `2 3 5 7 11` |
| `modular(m)` | no law in the values, but the ring fold repeats | `3 8 91 2 17 6` |
| `interpolation` | the degree n-1 curve through every point | anything at all |

Adding a method is adding one function to `METHODS` in `src/methods.js`. Nothing
else changes: the engine validates, tests and ranks it like the rest.

### How it decides

Fitting a sequence is easy — the last row of that table fits *any* sequence
exactly, which is precisely why an exact fit proves nothing. So each survivor is
put through two more filters:

1. **Holdout.** The method is refitted on a shortened copy of the sequence and
   asked to predict the terms it was never shown. A rule that only works when it
   can already see the answer is not a rule.
2. **Cost.** Bigger and more numerous parameters mean a bigger claim, so a fit is
   scored on how much it had to assume.

Candidates then land in one of four tiers, best first:

| standing | meaning |
| --- | --- |
| `verified` | reproduces the sequence **and** predicted the withheld terms |
| `exact` | reproduces the sequence, too short to hold anything back |
| `projection` | the raw values follow no rule, but their fold onto a ring repeats |
| `overfit` | as many parameters as terms — fits anything, predicts nothing |

That last tier is the honest answer to "can it always find a pattern?" — yes, and
it will tell you when the pattern it found is worth nothing:

```
$ node cli.js --fit 12,7,19,4,88,3
sequence  12 7 19 4 88 3

  law       x[i] = -47/10i⁵ + 649/12i⁴ - 643/3i³ + 4121/12i² - 2752/15i + 12
  method    interpolation(5)
  standing  overfit  (0/1 withheld terms predicted)
  next      -1477 -7100 -21700 -52761 -110981 -210836
  note      as many parameters as terms — this fits any sequence at all
```

Fitting runs in exact rational arithmetic (`src/rational.js`), so a law with a
ratio of `1/3` reproduces its sequence exactly rather than nearly. Anything that
overflows exact arithmetic is treated as "this method does not fit" rather than
returning a wrong answer.

## Command line

```
node cli.js 1 4 5              # full report per number
node cli.js 1 4 5 --table      # one row each
node cli.js 7 --mod 12 --factor 3 --depth 3
node cli.js --families 1-27    # group a range by the pattern it produces
node cli.js 4 --json

node cli.js --fit 1,1,2,3,5,8       # find the law behind a sequence
node cli.js --fit "3 1 4 3 1 4" --all   # and every other method that fitted
node cli.js --fit 2,9,4,11,6,13 --next 10
```

```
$ node cli.js --fit 2,9,4,11,6,13,8
sequence  2 9 4 11 6 13 8

  law       phase 0 of 2 from 2: x[i] = x[i-1] + 2  ·  phase 1 of 2 from 9: x[i] = x[i-1] + 2
  method    interleaved(2)
  standing  verified  (1/1 withheld terms predicted)
  next      15 10 17 12 19 14

  2 other fits: modular(2), interpolation(6)
```

`--fit` exits non-zero when the only thing that fitted was an overfit, so it can
be used as a test for "is there really a pattern here".

```
$ node cli.js 4 --depth 2
seed 4   root 4   mod 9   factor 2

  pattern   4 8 3 7 2 6 1 5 9   period 9
  repeated  4 8 3 7 2 6 1 5 9 4 8 3 7 2 6 1 5 9
  orbit     4 8 7 5 1 2   period 6
  mirror    6
  signature m9/f2/s4/4-8-3-7-2-6-1-5-9/4-8-7-5-1-2

  tree
    4
    ├─ grow+shift → 8
    │  ├─ grow → 7
    │  ├─ shift → 3
    │  └─ mirror → 2
    └─ mirror → 6
       ├─ grow → 3
       ├─ shift → 1
       └─ mirror → 4  ↺
```

## Visualizer

```
npm run web     # then open http://localhost:8080
```

A mobile-first page. Type a number and watch its pattern draw itself as a closed
figure on the ring, alongside the orbit and the tree; change the ring size or the
factor to reshape every pattern at once. At the bottom, paste any sequence into
**find a law** and the discovered rule appears with its predicted terms drawn in
outline.

## Layout

```
src/pattern.js    ring math — wrap, ladder, orbit, mirror
src/tree.js       deterministic branching tree
src/model.js      the generative model: pattern + orbit + tree + signature
src/rational.js   exact fractions and linear solving
src/methods.js    the method library — one function per hypothesis
src/discover.js   the search engine: fit, hold out, rank
src/format.js     text rendering
cli.js            command line
web/index.html    visualizer
test/             tests
```

## Tests

```
npm test
```

The tests are mostly about the guarantees rather than the examples.

For generating: that the period always equals `modulus / gcd(n, modulus)` across
thousands of seed/modulus pairs, that `at(k) === at(k + period)` for every k, that
every orbit closes into a cycle, that `wrap(n, 9)` agrees with digit-summed
digital roots for the first 5000 integers, and that two models built from the same
input are identical.

For discovering: that every method is found on its own kind of sequence and
predicts the terms that follow, that sequences generated from random parameters
are recovered and extrapolated correctly, that every candidate law reproduces
every term it was fitted to, that the ranking never puts an overfit above a real
fit, and that noise is reported as noise.
