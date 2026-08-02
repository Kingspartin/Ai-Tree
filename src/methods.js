/**
 * The method library.
 *
 * Each method is one hypothesis about how a sequence could be organised. Given a
 * sequence it either declines (returns null) or hands back a candidate law with
 * a `term(i)` function that reproduces the sequence and keeps going past its
 * end. The engine in discover.js is what decides which candidate wins — a method
 * never judges itself.
 *
 * A candidate looks like:
 *
 *   {
 *     method:   name of the method
 *     describe: human readable rule
 *     params:   the fitted numbers, for display
 *     cost:     base complexity, before parameter size is added
 *     term(i):  value at index i as a Rational, i beyond the input allowed
 *     project:  optional — validate against project(x) instead of x, used by
 *               methods that model a projection of the sequence rather than the
 *               values themselves
 *     overfit:  optional — true when the law has as many knobs as data points
 *   }
 */

import { Rational, R, ZERO, ONE, solve } from './rational.js';

/** Memoise a term function so recurrences stay linear in the index. */
function memo(compute) {
  const cache = new Map();
  return function term(index) {
    if (cache.has(index)) return cache.get(index);
    const value = compute(index, term);
    cache.set(index, value);
    return value;
  };
}

const isConstantRow = (row) => row.length > 0 && row.every((value) => value.eq(row[0]));

/** One row of finite differences. */
const differences = (values) => values.slice(1).map((value, i) => value.sub(values[i]));

/* ------------------------------------------------------------------ */
/* closed form in the index                                            */
/* ------------------------------------------------------------------ */

/** Every term the same. */
function constant(seq) {
  if (seq.length < 2 || !isConstantRow(seq)) return null;
  return {
    method: 'constant',
    describe: `x[i] = ${seq[0]}`,
    params: { value: seq[0] },
    cost: 1,
    term: () => seq[0],
  };
}

/** Constant step: x[i] = x[i-1] + d. */
function arithmetic(seq) {
  if (seq.length < 3) return null;
  const deltas = differences(seq);
  if (!isConstantRow(deltas) || deltas[0].isZero()) return null;
  const step = deltas[0];
  return {
    method: 'arithmetic',
    describe: `x[i] = x[i-1] ${sign(step)}`,
    params: { start: seq[0], step },
    cost: 2,
    term: (i) => seq[0].add(step.mul(R(i))),
  };
}

/** Constant ratio: x[i] = r * x[i-1]. */
function geometric(seq) {
  if (seq.length < 3 || seq.some((value) => value.isZero())) return null;
  const ratio = seq[1].div(seq[0]);
  if (ratio.eq(ONE)) return null;
  for (let i = 1; i < seq.length; i++) {
    if (!seq[i].div(seq[i - 1]).eq(ratio)) return null;
  }
  return {
    method: 'geometric',
    describe: `x[i] = ${ratio} · x[i-1]`,
    params: { start: seq[0], ratio },
    cost: 2,
    term: (i) => seq[0].mul(ratio.pow(i)),
  };
}

/**
 * Polynomial in the index, found by finite differences.
 * `confirm` is how many constant differences must show up beyond the fit, so a
 * degree is only claimed when the data actually backs it.
 */
function polynomialOfDegree(seq, degree, confirm = 2) {
  if (seq.length < degree + 1 + confirm) return null;
  let row = seq;
  const leading = [];
  for (let level = 0; level < degree; level++) {
    leading.push(row[0]);
    row = differences(row);
  }
  leading.push(row[0]);
  if (!isConstantRow(row) || row.length < confirm) return null;
  if (degree > 0 && row[0].isZero()) return null; // really a lower degree

  const coefficients = newtonToStandard(leading);
  return {
    method: `polynomial(${degree})`,
    describe: `x[i] = ${formatPolynomial(coefficients)}`,
    params: { degree, coefficients },
    cost: 2 + degree,
    term: (i) => evaluate(coefficients, R(i)),
  };
}

function polynomial(seq) {
  for (let degree = 2; degree <= 6; degree++) {
    const fit = polynomialOfDegree(seq, degree);
    if (fit) return fit;
  }
  return null;
}

/**
 * The escape hatch every finite sequence has: a degree n-1 polynomial through
 * all n points. Always exact, never evidence of anything — reported as overfit
 * so it ranks last and so the report can say so out loud.
 */
function interpolation(seq) {
  if (seq.length < 2) return null;
  const degree = seq.length - 1;
  let row = seq;
  const leading = [];
  for (let level = 0; level < degree; level++) {
    leading.push(row[0]);
    row = differences(row);
  }
  leading.push(row[0]);

  const coefficients = newtonToStandard(leading);
  return {
    method: `interpolation(${degree})`,
    describe: `x[i] = ${formatPolynomial(coefficients)}`,
    params: { degree, coefficients },
    cost: 40 + degree,
    overfit: true,
    term: (i) => evaluate(coefficients, R(i)),
  };
}

/* ------------------------------------------------------------------ */
/* recurrences                                                         */
/* ------------------------------------------------------------------ */

/** x[i] = a·x[i-1] + b — covers arithmetic and geometric, and everything between. */
function affine(seq) {
  if (seq.length < 4) return null;
  const matrix = [
    [seq[0], ONE],
    [seq[1], ONE],
  ];
  const answer = solve(matrix, [seq[1], seq[2]]);
  if (!answer) return null;
  const [a, b] = answer;
  if (b.isZero() || a.eq(ONE)) return null; // plain geometric / arithmetic

  return {
    method: 'affine',
    describe: `x[i] = ${a} · x[i-1] ${sign(b)}`,
    params: { a, b, start: seq[0] },
    cost: 4,
    term: memo((i, term) => (i === 0 ? seq[0] : a.mul(term(i - 1)).add(b))),
  };
}

/** x[i] = c1·x[i-1] + … + ck·x[i-k] — Fibonacci and friends. */
function linearRecurrenceOfOrder(seq, order) {
  if (seq.length < 2 * order + 1) return null;

  const matrix = [];
  const vector = [];
  for (let row = 0; row < order; row++) {
    const i = order + row;
    matrix.push(Array.from({ length: order }, (_, j) => seq[i - 1 - j]));
    vector.push(seq[i]);
  }
  const coefficients = solve(matrix, vector);
  if (!coefficients) return null;
  if (coefficients.at(-1).isZero()) return null; // a shorter recurrence in disguise

  const seeds = seq.slice(0, order);
  const body = coefficients
    .map((c, j) => (c.isZero() ? null : `${term(c)}x[i-${j + 1}]`))
    .filter(Boolean)
    .join(' + ')
    .replace(/\+ -/g, '- ');

  return {
    method: `recurrence(${order})`,
    describe: `x[i] = ${body}`,
    params: { order, coefficients, seeds },
    cost: 3 + 2 * order,
    term: memo((i, term) => {
      if (i < order) return seeds[i];
      return coefficients.reduce((total, c, j) => total.add(c.mul(term(i - 1 - j))), ZERO);
    }),
  };
}

function linearRecurrence(seq) {
  for (let order = 2; order <= 4; order++) {
    const fit = linearRecurrenceOfOrder(seq, order);
    if (fit) return fit;
  }
  return null;
}

/** x[i] = x[i-1] · (i + c) — factorials and rising products. */
function productRecurrence(seq) {
  if (seq.length < 4 || seq.some((value) => value.isZero())) return null;
  // x[1] = x[0] · (0 + c)
  const c = seq[1].div(seq[0]);
  const offset = c.sub(ONE);
  return {
    method: 'product',
    describe: `x[i] = x[i-1] · ${offset.isZero() ? 'i' : `(i ${sign(offset)})`}`,
    params: { c, start: seq[0] },
    cost: 5,
    term: memo((i, term) => (i === 0 ? seq[0] : term(i - 1).mul(R(i - 1).add(c)))),
  };
}

/* ------------------------------------------------------------------ */
/* structure rather than formula                                       */
/* ------------------------------------------------------------------ */

/** The sequence itself is a loop of length p, seen at least twice. */
function periodic(seq) {
  for (let p = 1; p <= Math.floor(seq.length / 2); p++) {
    let ok = true;
    for (let i = p; i < seq.length && ok; i++) {
      if (!seq[i].eq(seq[i - p])) ok = false;
    }
    if (!ok) continue;
    if (p === 1) return null; // that is `constant`
    const cycle = seq.slice(0, p);
    return {
      method: `periodic(${p})`,
      describe: `repeats every ${p}: ${cycle.join(' ')}`,
      params: { period: p, cycle },
      cost: 2 + p,
      term: (i) => cycle[((i % p) + p) % p],
    };
  }
  return null;
}

/**
 * Interleaving: the sequence is `phases` independent sequences taking turns.
 * Each phase is fitted with the simple closed forms.
 */
function interleavedBy(seq, phases) {
  if (seq.length < phases * 3) return null;

  const fits = [];
  const starts = [];
  for (let phase = 0; phase < phases; phase++) {
    const slice = seq.filter((_, i) => i % phases === phase);
    const fit =
      constant(slice) ?? arithmetic(slice) ?? geometric(slice) ?? polynomial(slice);
    if (!fit) return null;
    if (!reproduces(fit, slice)) return null;
    fits.push(fit);
    starts.push(slice[0]);
  }
  if (fits.every((fit) => fit.method === 'constant')) return null; // that is `periodic`

  return {
    method: `interleaved(${phases})`,
    describe: fits
      .map((fit, phase) => `phase ${phase} of ${phases} from ${starts[phase]}: ${fit.describe}`)
      .join('  ·  '),
    params: { phases, parts: fits.map((fit) => fit.describe) },
    cost: 3 + fits.reduce((total, fit) => total + fit.cost, 0),
    term: (i) => fits[((i % phases) + phases) % phases].term(Math.floor(i / phases)),
  };
}

function interleaved(seq) {
  for (const phases of [2, 3, 4]) {
    const fit = interleavedBy(seq, phases);
    if (fit) return fit;
  }
  return null;
}

/**
 * The most literal reading of "each number maps to the next": a lookup from
 * value to successor. It only counts as a law when values actually recur, and
 * when the final value has been seen before — otherwise there is nothing to
 * continue with.
 */
function valueMap(seq) {
  if (seq.length < 4) return null;

  const next = new Map();
  let repeats = 0;
  for (let i = 0; i < seq.length - 1; i++) {
    const key = seq[i].toString();
    const known = next.get(key);
    if (known) {
      repeats++;
      if (!known.eq(seq[i + 1])) return null; // same value, different successor
    } else {
      next.set(key, seq[i + 1]);
    }
  }
  if (repeats === 0) return null;
  if (!next.has(seq.at(-1).toString())) return null;

  return {
    method: 'value-map',
    describe: [...next.entries()].map(([from, to]) => `${from}→${to}`).join(', '),
    params: { pairs: next.size },
    cost: 4 + next.size,
    term: memo((i, term) => (i === 0 ? seq[0] : next.get(term(i - 1).toString()))),
  };
}

/**
 * The fallback that almost always finds something: stop looking at the values
 * and look at where they land on a ring. This is the ai-tree model applied in
 * reverse — it predicts the fold of the next term, not the term itself, so it is
 * marked as a projection.
 */
function modular(seq) {
  if (!seq.every((value) => value.isInteger())) return null;

  for (let modulus = 2; modulus <= 16; modulus++) {
    const fold = (value) => R(((((value.n % modulus) - 1) % modulus) + modulus) % modulus + 1);
    const residues = seq.map(fold);
    if (isConstantRow(residues)) continue;

    const cycle = periodic(residues) ?? arithmetic(residues);
    if (!cycle) continue;
    if (!reproduces(cycle, residues)) continue;

    return {
      method: `modular(${modulus})`,
      describe: `folded onto a ring of ${modulus}: ${cycle.describe}`,
      params: { modulus, inner: cycle.method },
      cost: 8 + modulus + cycle.cost,
      projection: `value folded into 1..${modulus}`,
      project: fold,
      term: (i) => cycle.term(i),
    };
  }
  return null;
}

/* ------------------------------------------------------------------ */
/* catalogue                                                           */
/* ------------------------------------------------------------------ */

const PRIMES = sievePrimes(100_000);

/** Consecutive primes — the one classic family no formula above reaches. */
function primes(seq) {
  if (seq.length < 4) return null;
  if (!seq.every((value) => value.isInteger() && value.n >= 2 && value.n <= PRIMES.at(-1))) return null;

  const start = PRIMES.indexOf(seq[0].n);
  if (start === -1) return null;
  for (let i = 0; i < seq.length; i++) {
    if (PRIMES[start + i] !== seq[i].n) return null;
  }

  return {
    method: 'primes',
    describe: `consecutive primes from ${seq[0]}`,
    params: { start },
    cost: 6,
    term: (i) => {
      const prime = PRIMES[start + i];
      if (prime === undefined) throw new RangeError('past the prime table');
      return R(prime);
    },
  };
}

function sievePrimes(limit) {
  const composite = new Uint8Array(limit + 1);
  const list = [];
  for (let n = 2; n <= limit; n++) {
    if (composite[n]) continue;
    list.push(n);
    for (let multiple = n * n; multiple <= limit; multiple += n) composite[multiple] = 1;
  }
  return list;
}

/* ------------------------------------------------------------------ */

/** Does a candidate reproduce the sequence it was fitted to? */
export function reproduces(fit, seq) {
  try {
    for (let i = 0; i < seq.length; i++) {
      const expected = fit.project ? fit.project(seq[i]) : seq[i];
      if (!fit.term(i).eq(expected)) return false;
    }
    return true;
  } catch {
    return false;
  }
}

/** Order matters only as a tie-break; the engine ranks on evidence and cost. */
export const METHODS = [
  constant,
  arithmetic,
  geometric,
  polynomial,
  affine,
  linearRecurrence,
  productRecurrence,
  periodic,
  interleaved,
  valueMap,
  primes,
  modular,
  interpolation,
];

/* ------------------------------------------------------------------ */
/* polynomial helpers                                                  */
/* ------------------------------------------------------------------ */

/** Newton forward-difference form → standard coefficients, ascending powers. */
export function newtonToStandard(leading) {
  let coefficients = [ZERO];
  let basis = [ONE]; // C(x, j) expanded, built up one factor at a time
  let factorial = ONE;

  for (let j = 0; j < leading.length; j++) {
    if (j > 0) {
      factorial = factorial.mul(R(j));
      basis = multiplyPolynomial(basis, [R(-(j - 1)), ONE]);
    }
    const scale = leading[j].div(factorial);
    coefficients = addPolynomial(
      coefficients,
      basis.map((c) => c.mul(scale)),
    );
  }
  return trim(coefficients);
}

function multiplyPolynomial(a, b) {
  const out = Array.from({ length: a.length + b.length - 1 }, () => ZERO);
  for (let i = 0; i < a.length; i++) {
    for (let j = 0; j < b.length; j++) {
      out[i + j] = out[i + j].add(a[i].mul(b[j]));
    }
  }
  return out;
}

function addPolynomial(a, b) {
  const out = [];
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    out.push((a[i] ?? ZERO).add(b[i] ?? ZERO));
  }
  return out;
}

function trim(coefficients) {
  const out = [...coefficients];
  while (out.length > 1 && out.at(-1).isZero()) out.pop();
  return out;
}

/** Horner evaluation. */
export function evaluate(coefficients, x) {
  let total = ZERO;
  for (let i = coefficients.length - 1; i >= 0; i--) {
    total = total.mul(x).add(coefficients[i]);
  }
  return total;
}

const SUPERSCRIPT = ['', '', '²', '³', '⁴', '⁵', '⁶', '⁷', '⁸'];

export function formatPolynomial(coefficients) {
  const parts = [];
  for (let power = coefficients.length - 1; power >= 0; power--) {
    const c = coefficients[power];
    if (c.isZero()) continue;
    const magnitude = c.abs().toString();
    const symbol = power === 0 ? '' : power === 1 ? 'i' : `i${SUPERSCRIPT[power] ?? `^${power}`}`;
    const body = power === 0 ? magnitude : magnitude === '1' ? symbol : `${magnitude}${symbol}`;
    parts.push(`${parts.length === 0 ? (c.n < 0 ? '-' : '') : c.n < 0 ? ' - ' : ' + '}${body}`);
  }
  return parts.length ? parts.join('') : '0';
}

/** ` + 3` / ` - 3`, for rules written as x[i-1] plus something. */
function sign(value) {
  const r = Rational.from(value);
  return r.n < 0 ? `- ${r.abs()}` : `+ ${r}`;
}

/** A coefficient in front of a term: 1 and -1 are written as nothing and `-`. */
function term(value) {
  const r = Rational.from(value);
  if (r.eq(ONE)) return '';
  if (r.eq(ONE.neg())) return '-';
  return `${r} · `;
}
