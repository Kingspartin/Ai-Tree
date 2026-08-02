/**
 * The number model.
 *
 * `model(n)` turns any integer into a fixed, repeating pattern. Two calls with
 * the same arguments always produce the same pattern, and the pattern continues
 * forever by repetition — `m.at(k)` equals `m.at(k + m.period)` for every k.
 */

import { ladder, orbit, mirror, sequenceAt, wrap } from './pattern.js';
import { buildTree, treeValues, treeSize, DEFAULT_RULES } from './tree.js';

export const DEFAULTS = {
  modulus: 9,
  factor: 2,
  depth: 4,
  rules: DEFAULT_RULES,
};

/**
 * @typedef {object} NumberModel
 * @property {number} seed        The input number
 * @property {number} root        The seed folded into 1..modulus
 * @property {number} modulus
 * @property {number} factor
 * @property {number[]} pattern   The repeating unit — the pattern for this number
 * @property {number} period      pattern.length
 * @property {object} ladder      Multiplication ladder: {values, period, step}
 * @property {object} orbit       Multiplicative orbit: {lead, cycle, period, entry}
 * @property {number} mirror      Ring complement of the root
 * @property {object} tree        Deterministic branching tree
 * @property {string} signature   Stable identifier for this pattern
 * @property {(k: number) => number} at        Term k of the endless pattern (0-based)
 * @property {(count: number, start?: number) => number[]} take  A run of terms
 */

/**
 * Build the model for a number.
 *
 * @param {number} seed
 * @param {{modulus?: number, factor?: number, depth?: number, rules?: string[]}} [options]
 * @returns {NumberModel}
 */
export function model(seed, options = {}) {
  const config = { ...DEFAULTS, ...options };
  const { modulus, factor, depth, rules } = config;

  if (!Number.isInteger(seed)) {
    throw new TypeError('seed must be an integer');
  }

  const rungs = ladder(seed, modulus);
  const spin = orbit(seed, modulus, factor);
  const tree = buildTree(seed, { modulus, factor, depth, rules });
  const root = wrap(seed, modulus);

  const pattern = rungs.values;
  const signature = [
    `m${modulus}`,
    `f${factor}`,
    `s${root}`,
    pattern.join('-'),
    spin.cycle.join('-'),
  ].join('/');

  return {
    seed,
    root,
    modulus,
    factor,
    pattern,
    period: rungs.period,
    ladder: rungs,
    orbit: spin,
    mirror: mirror(seed, modulus),
    tree: {
      ...tree,
      values: treeValues(tree),
      size: treeSize(tree),
    },
    signature,
    at: (k) => {
      if (!Number.isInteger(k)) throw new TypeError('k must be an integer');
      return sequenceAt(pattern, k);
    },
    take: (count, start = 0) => {
      if (!Number.isInteger(count) || count < 0) {
        throw new RangeError('count must be an integer >= 0');
      }
      return Array.from({ length: count }, (_, i) => sequenceAt(pattern, start + i));
    },
  };
}

/** Model several numbers at once. */
export function models(seeds, options = {}) {
  return seeds.map((seed) => model(seed, options));
}

/**
 * Prove a model repeats: checks that every term in the first `cycles` repeats
 * of the pattern matches the corresponding term of the repeating unit.
 *
 * @returns {{ok: boolean, checked: number, firstMismatch: null|{index: number, expected: number, actual: number}}}
 */
export function verify(m, cycles = 10) {
  const checked = m.period * cycles;
  for (let k = 0; k < checked; k++) {
    const expected = m.pattern[k % m.period];
    const actual = m.at(k);
    if (actual !== expected) {
      return { ok: false, checked, firstMismatch: { index: k, expected, actual } };
    }
  }
  return { ok: true, checked, firstMismatch: null };
}

/** True when two models produce the same pattern (same signature). */
export function sameShape(a, b) {
  return a.signature === b.signature;
}

/**
 * Group seeds by the pattern they produce. Numbers that share a signature are
 * interchangeable in this model.
 *
 * @returns {Map<string, number[]>}
 */
export function families(seeds, options = {}) {
  const groups = new Map();
  for (const seed of seeds) {
    const key = model(seed, options).signature;
    const bucket = groups.get(key);
    if (bucket) bucket.push(seed);
    else groups.set(key, [seed]);
  }
  return groups;
}
