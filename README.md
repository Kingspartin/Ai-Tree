# Ai-Tree

Visualized mobile ai app — built on a **number modeling system**: every number you
feed in gets one fixed pattern, and that pattern repeats forever.

```
1  →  1 2 3 4 5 6 7 8 9 ↺
4  →  4 8 3 7 2 6 1 5 9 ↺
5  →  5 1 6 2 7 3 8 4 9 ↺
```

Same number in, same pattern out — every run, every device, no randomness and no
state anywhere in the system.

## The idea

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

## Use it

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

## Command line

```
node cli.js 1 4 5              # full report per number
node cli.js 1 4 5 --table      # one row each
node cli.js 7 --mod 12 --factor 3 --depth 3
node cli.js --families 1-27    # group a range by the pattern it produces
node cli.js 4 --json
```

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

A mobile-first page: type a number, watch its pattern draw itself as a closed
figure on the ring, alongside the orbit and the tree. Change the ring size or the
factor to reshape every pattern at once.

## Layout

```
src/pattern.js   ring math — wrap, ladder, orbit, mirror
src/tree.js      deterministic branching tree
src/model.js     the model: pattern + orbit + tree + signature
src/format.js    text rendering
cli.js           command line
web/index.html   visualizer
test/            tests
```

## Tests

```
npm test
```

The tests are mostly about the guarantee rather than the examples: that the
period always equals `modulus / gcd(n, modulus)` across thousands of
seed/modulus pairs, that `at(k) === at(k + period)` for every k, that every orbit
closes into a cycle, that `wrap(n, 9)` agrees with digit-summed digital roots for
the first 5000 integers, and that two models built from the same input are
identical.
