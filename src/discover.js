/**
 * The search engine.
 *
 * Hand it any sequence. It runs every method in the library, keeps the ones that
 * reproduce the sequence exactly, tests each survivor by refitting it on a
 * shortened copy and asking it to predict the terms it was not shown, and ranks
 * what is left by how much it had to assume.
 *
 * Nothing here knows how any individual method works — methods are added to
 * `METHODS` and the ranking takes care of itself.
 */

import { Rational, R, toRationals } from './rational.js';
import { METHODS, reproduces } from './methods.js';
import { STEP_METHODS, conflictIn, cycleFrom } from './step.js';

/** How strongly a candidate is believed, best first. */
export const TIERS = ['verified', 'exact', 'projection', 'overfit'];

/**
 * @param {number[]} sequence
 * @param {{holdout?: number, methods?: Function[], uniform?: boolean}} [options]
 *   `uniform: true` restricts the search to rules of the form x[i+1] = f(x[i]),
 *   one f applied the same way at every step.
 */
export function discover(sequence, options = {}) {
  if (!Array.isArray(sequence) || sequence.length < 2) {
    throw new RangeError('need at least 2 terms');
  }

  const methods = options.methods ?? (options.uniform ? STEP_METHODS : [...METHODS, ...STEP_METHODS]);
  const seq = toRationals(sequence);
  const holdout = options.holdout ?? Math.min(3, Math.max(1, Math.floor(seq.length / 4)));

  const candidates = [];
  for (const method of methods) {
    const fit = attempt(method, seq);
    if (!fit) continue;
    candidates.push(describeCandidate(fit, seq, methods, holdout));
  }

  candidates.sort(
    (a, b) => a.tier - b.tier || a.score - b.score || a.method.localeCompare(b.method),
  );

  const law = candidates[0] ?? null;
  return {
    input: [...sequence],
    law,
    candidates,
    tried: methods.length,
    confidence: law ? TIERS[law.tier] : 'none',
    next: (count = 5) => (law ? law.next(count) : []),
    extend: (count = 5) => [...sequence, ...(law ? law.next(count) : [])],
  };
}

/** Run one method, ignoring the ways a hypothesis can legitimately blow up. */
function attempt(method, seq) {
  let fit;
  try {
    fit = method(seq);
  } catch {
    return null;
  }
  if (!fit) return null;
  return reproduces(fit, seq) ? fit : null;
}

function describeCandidate(fit, seq, methods, holdout) {
  const check = testHoldout(fit, seq, methods, holdout);
  const overfit = Boolean(fit.overfit);
  const projection = fit.projection ?? null;
  const verified = check.tested > 0 && check.passed === check.tested;

  const tier = overfit ? 3 : projection ? 2 : verified ? 0 : 1;

  return {
    method: fit.method,
    describe: fit.describe,
    params: readableParams(fit.params),
    exact: true,
    verified,
    overfit,
    projection,
    holdout: check,
    cost: fit.cost,
    score: fit.cost + weight(fit.params),
    tier,
    /** true when the rule is one f applied to each value, the same way every time */
    uniform: Boolean(fit.uniform),
    apply: fit.apply ? (x) => fit.apply(Rational.from(x)).toNumber() : null,
    /** where iterating the rule starts repeating, for uniform rules */
    cycle: fit.apply ? cycleFrom(fit.apply, seq[0]) : null,
    term: (i) => fit.term(i).toNumber(),
    termExact: (i) => fit.term(i).toString(),
    next: (count = 5) => {
      const out = [];
      for (let k = 0; k < count; k++) {
        try {
          out.push(fit.term(seq.length + k).toNumber());
        } catch {
          break; // ran past what the law can represent
        }
      }
      return out;
    },
  };
}

/**
 * Refit the same method on a shortened sequence and see whether it predicts the
 * terms that were withheld. A law that only works when it can see the answer is
 * not a law, and this is what separates the two top tiers.
 */
function testHoldout(fit, seq, methods, holdout) {
  const shown = seq.length - holdout;
  if (holdout < 1 || shown < 2) return { tested: 0, passed: 0, refit: false };

  const source = methods.find((method) => {
    const attempt = safeCall(method, seq);
    return attempt?.method === fit.method;
  });
  if (!source) return { tested: 0, passed: 0, refit: false };

  const refit = safeCall(source, seq.slice(0, shown));
  if (!refit || refit.method !== fit.method) return { tested: holdout, passed: 0, refit: false };
  if (!reproduces(refit, seq.slice(0, shown))) return { tested: holdout, passed: 0, refit: false };

  let passed = 0;
  for (let i = shown; i < seq.length; i++) {
    try {
      const expected = refit.project ? refit.project(seq[i]) : seq[i];
      if (refit.term(i).eq(expected)) passed++;
    } catch {
      break;
    }
  }
  return { tested: holdout, passed, refit: true };
}

function safeCall(method, seq) {
  try {
    return method(seq);
  } catch {
    return null;
  }
}

/** Bigger and more numerous parameters mean a bigger claim. */
function weight(params) {
  let total = 0;
  const visit = (value) => {
    if (value instanceof Rational) {
      total += Math.log2(1 + Math.abs(value.n)) + Math.log2(value.d);
      return;
    }
    if (Array.isArray(value)) {
      value.forEach(visit);
      return;
    }
    if (typeof value === 'number') {
      total += Math.log2(1 + Math.abs(value));
      return;
    }
    if (value && typeof value === 'object') Object.values(value).forEach(visit);
  };
  visit(params ?? {});
  return Math.round(total * 100) / 100;
}

function readableParams(params) {
  const out = {};
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value instanceof Rational) out[key] = value.toString();
    else if (Array.isArray(value)) out[key] = value.map((item) => String(item));
    else out[key] = value;
  }
  return out;
}

/**
 * The strict search: one rule f, applied to each number the same way every time,
 * such that f(x[i]) is x[i+1] at every single step.
 *
 * Unlike `discover`, this can answer "no" for a reason. If some value in the
 * sequence is followed by two different values, no such f exists — that is a
 * fact about the sequence, not a limit of the search, and it is reported as
 * `impossible` rather than as an empty result.
 *
 * @param {number[]} sequence
 * @param {{holdout?: number}} [options]
 */
export function stepRule(sequence, options = {}) {
  const impossible = conflictIn(sequence);
  const result = discover(sequence, { ...options, uniform: true });
  const rule = result.law;

  return {
    input: [...sequence],
    rule,
    candidates: result.candidates,
    tried: result.tried,
    confidence: result.confidence,
    impossible: impossible
      ? {
          reason: `${impossible.value} is followed by ${impossible.successors.join(' and by ')}`,
          ...impossible,
        }
      : null,
    /** where the rule starts repeating itself, iterated from the first term */
    cycle: rule?.cycle ?? null,
    apply: rule?.apply ?? null,
    next: (count = 5) => (rule ? rule.next(count) : []),
  };
}

/**
 * Discover, then say it in words.
 * @param {ReturnType<discover>} result
 */
export function explain(result, { next = 5 } = {}) {
  if (!result.law) {
    return `no law found for ${result.input.join(' ')} after ${result.tried} methods`;
  }
  const law = result.law;
  const lines = [
    `sequence   ${result.input.join(' ')}`,
    `law        ${law.describe}`,
    `method     ${law.method}   (${result.confidence})`,
    `next       ${law.next(next).join(' ')}`,
  ];
  if (law.projection) {
    lines.push(`note       predicts the ${law.projection}, not the raw value`);
  }
  if (law.overfit) {
    lines.push('note       as many parameters as terms — fits anything, predicts nothing');
  }
  if (law.holdout.tested) {
    lines.push(
      `holdout    ${law.holdout.passed}/${law.holdout.tested} withheld terms predicted correctly`,
    );
  }
  return lines.join('\n');
}

/** Fold a raw value onto a ring, the bridge back to the generative model. */
export function fold(value, modulus = 9) {
  return R(((((value % modulus) - 1) % modulus) + modulus) % modulus + 1).toNumber();
}
