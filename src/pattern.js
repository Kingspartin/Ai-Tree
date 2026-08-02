/**
 * Core pattern math.
 *
 * Everything here is pure and deterministic: the same arguments always produce
 * the same result, which is what makes the generated patterns repeatable.
 *
 * Values live in the range 1..modulus (not 0..modulus-1). With modulus 9 that
 * range is the classic digital-root range, so `wrap(n, 9)` is the digital root
 * of any positive integer n.
 */

/** Greatest common divisor of two integers. */
export function gcd(a, b) {
  a = Math.abs(a);
  b = Math.abs(b);
  while (b) {
    [a, b] = [b, a % b];
  }
  return a;
}

/**
 * Fold a value into the range 1..modulus.
 * Multiples of the modulus land on `modulus` itself rather than 0.
 */
export function wrap(value, modulus) {
  assertModulus(modulus);
  if (!Number.isInteger(value)) throw new TypeError('value must be an integer');
  return (((value - 1) % modulus) + modulus) % modulus + 1;
}

/**
 * Digital root by repeated digit summing. Kept as an independent implementation
 * so the tests can prove `wrap(n, 9)` agrees with it for every positive n.
 */
export function digitalRoot(value) {
  let n = Math.abs(Math.trunc(value));
  while (n >= 10) {
    let sum = 0;
    while (n > 0) {
      sum += n % 10;
      n = Math.floor(n / 10);
    }
    n = sum;
  }
  return n;
}

/**
 * The multiplication ladder: wrap(seed * 1), wrap(seed * 2), wrap(seed * 3)...
 *
 * This is the primary pattern for a number. It is exactly periodic from the
 * first term — no lead-in — with period `modulus / gcd(seed, modulus)`.
 *
 * @returns {{values: number[], period: number, step: number}}
 */
export function ladder(seed, modulus = 9) {
  assertModulus(modulus);
  assertInteger(seed, 'seed');
  const step = wrap(seed, modulus);
  const period = modulus / gcd(step % modulus, modulus);
  const values = [];
  for (let k = 1; k <= period; k++) {
    values.push(wrap(seed * k, modulus));
  }
  return { values, period, step };
}

/**
 * The multiplicative orbit: repeatedly multiply by `factor` and fold.
 *
 * Because the state space is finite and each step is deterministic, the walk
 * always falls into a cycle. `lead` holds the terms before the loop closes
 * (usually empty), `cycle` holds the repeating unit.
 *
 * @returns {{lead: number[], cycle: number[], period: number, entry: number}}
 */
export function orbit(seed, modulus = 9, factor = 2) {
  assertModulus(modulus);
  assertInteger(seed, 'seed');
  assertInteger(factor, 'factor');

  const seen = new Map();
  const walk = [];
  let value = wrap(seed, modulus);

  while (!seen.has(value)) {
    seen.set(value, walk.length);
    walk.push(value);
    value = wrap(value * factor, modulus);
  }

  const entry = seen.get(value);
  return {
    lead: walk.slice(0, entry),
    cycle: walk.slice(entry),
    period: walk.length - entry,
    entry,
  };
}

/** The complement of a value within the ring: 1 <-> modulus, 4 <-> modulus-3. */
export function mirror(value, modulus = 9) {
  return wrap(modulus + 1 - wrap(value, modulus), modulus);
}

/**
 * Read a periodic sequence at any index, including far past its length.
 * `sequenceAt(values, k)` === `sequenceAt(values, k + values.length)`.
 */
export function sequenceAt(values, index) {
  if (!Array.isArray(values) || values.length === 0) {
    throw new TypeError('values must be a non-empty array');
  }
  const i = ((index % values.length) + values.length) % values.length;
  return values[i];
}

function assertModulus(modulus) {
  if (!Number.isInteger(modulus) || modulus < 2) {
    throw new RangeError('modulus must be an integer >= 2');
  }
}

function assertInteger(value, name) {
  if (!Number.isInteger(value)) {
    throw new TypeError(`${name} must be an integer`);
  }
}
