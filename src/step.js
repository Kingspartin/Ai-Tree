/**
 * Uniform step rules.
 *
 * The strict reading of "a pattern that predicts the next number the same way
 * every time": one single function f, applied to each number of the sequence, so
 * that
 *
 *     x[i+1] = f(x[i])   for every i, with the same f throughout
 *
 * Nothing here may look at the position of a term. A rule that behaves
 * differently at index 3 than at index 4 is not a rule in this sense, so the
 * index-based methods in methods.js (polynomials in i, interleaved phases) are
 * deliberately absent.
 *
 * Two consequences worth knowing:
 *
 *  - If a value ever appears twice followed by two different values, then no
 *    such f exists at all. That is a proof, not a search failure, and
 *    `conflictIn` reports it.
 *  - Once f is fixed, iterating it from any starting number must eventually
 *    repeat a value, and from there the sequence is a loop forever. Folding onto
 *    a ring guarantees it, because a ring has finitely many places to stand.
 */

import { Rational, R, ONE, ZERO, solve, Overflow } from './rational.js';

const MAX_ITERATIONS = 2_000;

/* ------------------------------------------------------------------ */
/* the check that comes before any search                              */
/* ------------------------------------------------------------------ */

/**
 * Find a value that is followed by two different values.
 * @returns {null|{value: string, successors: string[], at: number[]}}
 */
export function conflictIn(sequence) {
  const seen = new Map();
  for (let i = 0; i < sequence.length - 1; i++) {
    const key = String(sequence[i]);
    const previous = seen.get(key);
    const successor = String(sequence[i + 1]);
    if (previous && previous.successor !== successor) {
      return {
        value: key,
        successors: [previous.successor, successor],
        at: [previous.index, i],
      };
    }
    if (!previous) seen.set(key, { successor, index: i });
  }
  return null;
}

/* ------------------------------------------------------------------ */
/* rule families — each fits one shape of f                            */
/* ------------------------------------------------------------------ */

const pairsOf = (seq) => seq.slice(0, -1).map((x, i) => [x, seq[i + 1]]);
const distinctInputs = (pairs) => new Set(pairs.map(([x]) => x.toString())).size;
const holds = (pairs, apply) => {
  try {
    return pairs.every(([x, y]) => apply(x).eq(y));
  } catch {
    return false;
  }
};

/** f(x) = x + d */
function increment(seq) {
  if (seq.length < 3) return null;
  const pairs = pairsOf(seq);
  const d = pairs[0][1].sub(pairs[0][0]);
  const apply = (x) => x.add(d);
  if (!holds(pairs, apply)) return null;
  return {
    name: 'step:add',
    describe: d.isZero() ? 'f(x) = x — every number maps to itself' : `f(x) = x ${plus(d)}`,
    params: { d },
    cost: 2,
    apply,
  };
}

/** f(x) = r · x */
function scale(seq) {
  if (seq.length < 3 || seq[0].isZero()) return null;
  const pairs = pairsOf(seq);
  const r = pairs[0][1].div(pairs[0][0]);
  if (r.eq(ONE)) return null; // that is add 0
  const apply = (x) => x.mul(r);
  if (!holds(pairs, apply)) return null;
  return {
    name: 'step:multiply',
    describe: `f(x) = ${r} · x`,
    params: { r },
    cost: 2,
    apply,
  };
}

/** f(x) = a·x + b */
function affine(seq) {
  if (seq.length < 4) return null;
  const pairs = pairsOf(seq);
  if (distinctInputs(pairs) < 3) return null; // 2 to fit, 1 to confirm

  const [[x0, y0], [x1, y1]] = pickDistinct(pairs, 2);
  const answer = solve(
    [
      [x0, ONE],
      [x1, ONE],
    ],
    [y0, y1],
  );
  if (!answer) return null;
  const [a, b] = answer;
  if (b.isZero() || a.eq(ONE)) return null; // scale / increment already cover these

  const apply = (x) => a.mul(x).add(b);
  if (!holds(pairs, apply)) return null;
  return {
    name: 'step:affine',
    describe: `f(x) = ${a} · x ${plus(b)}`,
    params: { a, b },
    cost: 4,
    apply,
  };
}

/** f(x) = c0 + c1·x + … + ck·x^k */
function polynomialOfDegree(seq, degree) {
  const pairs = pairsOf(seq);
  if (distinctInputs(pairs) < degree + 2) return null; // one spare pair to confirm

  const chosen = pickDistinct(pairs, degree + 1);
  const matrix = chosen.map(([x]) => Array.from({ length: degree + 1 }, (_, p) => x.pow(p)));
  const coefficients = solve(matrix, chosen.map(([, y]) => y));
  if (!coefficients) return null;
  if (coefficients.at(-1).isZero()) return null; // lower degree in disguise

  const apply = (x) =>
    coefficients.reduceRight((total, c) => total.mul(x).add(c), ZERO);
  if (!holds(pairs, apply)) return null;

  return {
    name: `step:polynomial(${degree})`,
    describe: `f(x) = ${formatInX(coefficients)}`,
    params: { degree, coefficients },
    cost: 4 + 2 * degree,
    apply,
  };
}

function polynomialInX(seq) {
  for (let degree = 2; degree <= 3; degree++) {
    const fit = polynomialOfDegree(seq, degree);
    if (fit) return fit;
  }
  return null;
}

/**
 * f(x) = a·x + b, on a ring of m places.
 *
 * This is the generative model of this repo read as a step rule: the pattern
 * `4 8 3 7 2 6 1 5 9` is f(x) = x + 4 on a ring of 9. Because the ring is
 * finite, a rule of this shape is guaranteed to repeat.
 */
function modularAffine(seq) {
  if (seq.length < 4 || !seq.every((value) => value.isInteger())) return null;
  const pairs = pairsOf(seq);

  const search = (wanted) => {
    for (let m = 2; m <= 36; m++) {
      const inRing = seq.every((value) => value.n >= 1 && value.n <= m);
      if (inRing !== wanted) continue;
      const fold = (x) => R(((((x.n % m) - 1) % m) + m) % m + 1);

      for (let a = 1; a < m; a++) {
        for (let b = 0; b < m; b++) {
          if (a === 1 && b === 0) continue; // identity
          const apply = (x) => fold(R(a).mul(fold(x)).add(R(b)));
          const ok = pairs.every(([x, y]) => {
            try {
              return apply(x).eq(fold(y));
            } catch {
              return false;
            }
          });
          if (!ok) continue;

          const rule = a === 1 ? `x + ${b}` : b === 0 ? `${a} · x` : `${a} · x + ${b}`;
          return {
            name: `step:ring(${m})`,
            describe: `f(x) = ${rule}, folded onto a ring of ${m}`,
            params: { modulus: m, a, b },
            cost: 6 + m,
            apply,
            // exact when the sequence already lives on the ring, otherwise it is
            // the fold of the next value that is being predicted
            projection: inRing ? undefined : `value folded into 1..${m}`,
            project: inRing ? undefined : fold,
          };
        }
      }
    }
    return null;
  };

  // an exact rule on a bigger ring beats a projection onto a smaller one
  return search(true) ?? search(false);
}

/** f(x) = x/2 when x is even, a·x + b when it is odd — the Collatz shape. */
function parity(seq) {
  if (seq.length < 4 || !seq.every((value) => value.isInteger())) return null;
  const pairs = pairsOf(seq);
  const odd = pairs.filter(([x]) => Math.abs(x.n % 2) === 1);
  const even = pairs.filter(([x]) => x.n % 2 === 0);
  if (odd.length === 0 || even.length === 0) return null;

  const build = (a, b) => (x) => (x.n % 2 === 0 ? x.div(R(2)) : R(a).mul(x).add(R(b)));

  const candidates = [];
  if (distinctInputs(odd) >= 2) {
    const [[x0, y0], [x1, y1]] = pickDistinct(odd, 2);
    const answer = solve(
      [
        [x0, ONE],
        [x1, ONE],
      ],
      [y0, y1],
    );
    if (answer && answer.every((value) => value.isInteger())) {
      candidates.push([answer[0].n, answer[1].n]);
    }
  }
  candidates.push([3, 1], [3, -1], [5, 1]); // the classics, when there is one odd pair

  for (const [a, b] of candidates) {
    const apply = build(a, b);
    if (!holds(pairs, apply)) continue;
    return {
      name: 'step:parity',
      describe: `f(x) = x/2 when even, ${a}x ${plus(R(b))} when odd`,
      params: { a, b },
      cost: 8,
      apply,
    };
  }
  return null;
}

/** Rules built from the digits of x, with nothing to fit. */
const DIGIT_RULES = [
  ['step:digit-sum', 'f(x) = sum of the digits of x', (n) => digits(n).reduce((a, b) => a + b, 0)],
  ['step:digit-squares', 'f(x) = sum of the squares of the digits of x', (n) => digits(n).reduce((a, b) => a + b * b, 0)],
  ['step:digital-root', 'f(x) = digital root of x', (n) => (n === 0 ? 0 : ((n - 1) % 9) + 1)],
  ['step:reverse', 'f(x) = digits of x reversed', (n) => Number([...String(n)].reverse().join(''))],
  ['step:add-digit-sum', 'f(x) = x + sum of the digits of x', (n) => n + digits(n).reduce((a, b) => a + b, 0)],
];

function digitRule(seq) {
  if (seq.length < 4) return null;
  if (!seq.every((value) => value.isInteger() && value.n >= 0)) return null;
  const pairs = pairsOf(seq);

  for (const [name, describe, fn] of DIGIT_RULES) {
    const apply = (x) => R(fn(x.n));
    if (!holds(pairs, apply)) continue;
    return { name, describe, params: {}, cost: 5, apply };
  }
  return null;
}

/** f(x) = the next prime after x. */
function nextPrime(seq) {
  if (seq.length < 4) return null;
  if (!seq.every((value) => value.isInteger() && value.n >= 0 && value.n < 1e6)) return null;
  const apply = (x) => {
    let n = x.n + 1;
    while (!isPrime(n)) n++;
    return R(n);
  };
  if (!holds(pairsOf(seq), apply)) return null;
  return {
    name: 'step:next-prime',
    describe: 'f(x) = the next prime after x',
    params: {},
    cost: 6,
    apply,
  };
}

/**
 * The rule written out as a table: this value goes to that value.
 *
 * Only counts when values actually recur — a table with one row per term has
 * learned nothing and cannot continue past the end.
 */
function table(seq) {
  if (seq.length < 4) return null;
  const pairs = pairsOf(seq);
  const map = new Map();
  let repeats = 0;

  for (const [x, y] of pairs) {
    const key = x.toString();
    if (map.has(key)) {
      repeats++;
      if (!map.get(key).eq(y)) return null;
    } else {
      map.set(key, y);
    }
  }
  if (repeats === 0) return null;
  if (!map.has(seq.at(-1).toString())) return null; // nothing to continue with

  const apply = (x) => {
    const y = map.get(x.toString());
    if (!y) throw new RangeError('value outside the table');
    return y;
  };
  return {
    name: 'step:table',
    describe: [...map].map(([from, to]) => `${from}→${to}`).join(', '),
    // a table memorises rather than compresses, so it is charged for every
    // number it holds — it stays the simplest answer only while it is short
    params: { rows: map.size, entries: pairs.flat() },
    cost: 5,
    apply,
  };
}

/** Ordered loosely simplest-first; the engine does the real ranking. */
export const STEP_FAMILIES = [
  increment,
  scale,
  affine,
  polynomialInX,
  digitRule,
  parity,
  nextPrime,
  modularAffine,
  table,
];

/* ------------------------------------------------------------------ */
/* adapting a rule to the search engine                                */
/* ------------------------------------------------------------------ */

/**
 * Wrap the families as methods for discover(), so uniform rules are fitted,
 * held out and ranked by exactly the same machinery as everything else.
 */
export const STEP_METHODS = STEP_FAMILIES.map((family) => {
  const method = (seq) => {
    const rule = family(seq);
    if (!rule) return null;

    const cache = [seq[0]];
    const term = (i) => {
      if (i < 0) throw new RangeError('index must be >= 0');
      while (cache.length <= i) cache.push(rule.apply(cache.at(-1)));
      return cache[i];
    };

    return {
      method: rule.name,
      describe: rule.describe,
      params: rule.params,
      cost: rule.cost,
      uniform: true,
      apply: rule.apply,
      projection: rule.projection,
      project: rule.project,
      term,
    };
  };
  Object.defineProperty(method, 'name', { value: family.name });
  return method;
});

/**
 * Follow f from a starting value until a value repeats.
 *
 * @returns {{closes: true, lead: number[], cycle: number[], period: number}
 *          |{closes: false, reason: string}}
 */
export function cycleFrom(apply, start) {
  const seen = new Map();
  const walk = [];
  let value = Rational.from(start);

  for (let step = 0; step < MAX_ITERATIONS; step++) {
    const key = value.toString();
    if (seen.has(key)) {
      const entry = seen.get(key);
      return {
        closes: true,
        lead: walk.slice(0, entry).map((r) => r.toNumber()),
        cycle: walk.slice(entry).map((r) => r.toNumber()),
        period: walk.length - entry,
      };
    }
    seen.set(key, walk.length);
    walk.push(value);
    try {
      value = apply(value);
    } catch (error) {
      return {
        closes: false,
        reason:
          error instanceof Overflow
            ? 'the values grow past exact arithmetic'
            : 'the rule has no value to follow',
      };
    }
  }
  return { closes: false, reason: `no repeat in the first ${MAX_ITERATIONS} steps` };
}

/* ------------------------------------------------------------------ */
/* helpers                                                             */
/* ------------------------------------------------------------------ */

function pickDistinct(pairs, count) {
  const chosen = [];
  const seen = new Set();
  for (const pair of pairs) {
    const key = pair[0].toString();
    if (seen.has(key)) continue;
    seen.add(key);
    chosen.push(pair);
    if (chosen.length === count) break;
  }
  return chosen;
}

function digits(n) {
  return [...String(Math.abs(n))].map(Number);
}

function isPrime(n) {
  if (n < 2) return false;
  if (n % 2 === 0) return n === 2;
  for (let d = 3; d * d <= n; d += 2) if (n % d === 0) return false;
  return true;
}

function plus(value) {
  const r = Rational.from(value);
  return r.n < 0 ? `- ${r.abs()}` : `+ ${r}`;
}

const SUPERSCRIPT = ['', '', '²', '³', '⁴'];

function formatInX(coefficients) {
  const parts = [];
  for (let power = coefficients.length - 1; power >= 0; power--) {
    const c = coefficients[power];
    if (c.isZero()) continue;
    const magnitude = c.abs().toString();
    const symbol = power === 0 ? '' : power === 1 ? 'x' : `x${SUPERSCRIPT[power] ?? `^${power}`}`;
    const body = power === 0 ? magnitude : magnitude === '1' ? symbol : `${magnitude}${symbol}`;
    parts.push(`${parts.length === 0 ? (c.n < 0 ? '-' : '') : c.n < 0 ? ' - ' : ' + '}${body}`);
  }
  return parts.length ? parts.join('') : '0';
}
