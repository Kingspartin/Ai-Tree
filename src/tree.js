/**
 * Deterministic branching tree.
 *
 * Each node applies every rule in the rule set to its own value to produce its
 * children. When a child's value already appeared on the path from the root,
 * the branch is closed and marked `repeat: true` — that is the point where the
 * pattern folds back on itself, so the tree is always finite and always
 * identical for the same inputs.
 */

import { wrap, mirror } from './pattern.js';

/**
 * Branch rules. Each takes the current value plus the model context and returns
 * the child value.
 */
export const RULES = {
  grow: (value, { modulus, factor }) => wrap(value * factor, modulus),
  shift: (value, { modulus, seed }) => wrap(value + seed, modulus),
  mirror: (value, { modulus }) => mirror(value, modulus),
};

export const DEFAULT_RULES = ['grow', 'shift', 'mirror'];

/**
 * @typedef {object} TreeNode
 * @property {number} value
 * @property {string|null} rule   Rule that produced this node (null at the root)
 * @property {number} depth
 * @property {boolean} repeat     True when this value already occurs on its own path
 * @property {TreeNode[]} children
 */

/**
 * Build the tree for a seed.
 *
 * @param {number} seed
 * @param {{modulus?: number, factor?: number, depth?: number, rules?: string[]}} [options]
 * @returns {TreeNode}
 */
export function buildTree(seed, options = {}) {
  const { modulus = 9, factor = 2, depth = 4, rules = DEFAULT_RULES } = options;

  if (!Number.isInteger(depth) || depth < 0) {
    throw new RangeError('depth must be an integer >= 0');
  }
  for (const name of rules) {
    if (!Object.hasOwn(RULES, name)) {
      throw new RangeError(`unknown rule: ${name}`);
    }
  }

  const context = { modulus, factor, seed };
  const root = wrap(seed, modulus);

  const expand = (value, level, path) => {
    const node = { value, rule: null, depth: level, repeat: false, children: [] };
    if (level >= depth) return node;

    const nextPath = new Set(path).add(value);

    // Rules that land on the same value share one branch, labelled with both.
    const branches = new Map();
    for (const name of rules) {
      const childValue = RULES[name](value, context);
      const existing = branches.get(childValue);
      if (existing) existing.push(name);
      else branches.set(childValue, [name]);
    }

    for (const [childValue, names] of branches) {
      const rule = names.join('+');
      if (nextPath.has(childValue)) {
        node.children.push({
          value: childValue,
          rule,
          depth: level + 1,
          repeat: true,
          children: [],
        });
        continue;
      }
      const child = expand(childValue, level + 1, nextPath);
      child.rule = rule;
      node.children.push(child);
    }
    return node;
  };

  return expand(root, 0, new Set());
}

/** Every distinct value the tree reaches, in ascending order. */
export function treeValues(node) {
  const values = new Set();
  const visit = (n) => {
    values.add(n.value);
    n.children.forEach(visit);
  };
  visit(node);
  return [...values].sort((a, b) => a - b);
}

/** Total node count, repeats included. */
export function treeSize(node) {
  return 1 + node.children.reduce((total, child) => total + treeSize(child), 0);
}
