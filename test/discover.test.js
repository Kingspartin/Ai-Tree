import test from 'node:test';
import assert from 'node:assert/strict';

import { discover, explain } from '../src/discover.js';
import { Rational, R, solve, ZERO, ONE } from '../src/rational.js';

const law = (sequence) => discover(sequence).law;
const found = (sequence) => law(sequence).method;
const nextOf = (sequence, count = 4) => discover(sequence).next(count);

test('rationals stay exact', () => {
  assert.equal(R(1, 3).add(R(1, 6)).toString(), '1/2');
  assert.equal(R(2, 4).toString(), '1/2');
  assert.equal(R(1, 3).mul(R(3)).toString(), '1');
  assert.equal(R(1, 3).sub(R(1, 3)).toString(), '0');
  assert.equal(R(2, 3).pow(3).toString(), '8/27');
  assert.equal(R(-1, -2).toString(), '1/2');
  assert.ok(R(1, 3).add(R(1, 3)).add(R(1, 3)).eq(ONE));
  assert.equal(Rational.from(0.25).toString(), '1/4');
  assert.equal(Rational.from(-2.5).toString(), '-5/2');
  assert.throws(() => R(1, 0), RangeError);
});

test('linear systems solve over rationals', () => {
  const answer = solve(
    [
      [R(2), R(1)],
      [R(1), R(3)],
    ],
    [R(5), R(10)],
  );
  assert.equal(answer[0].toString(), '1');
  assert.equal(answer[1].toString(), '3');
  assert.equal(solve([[ZERO, ZERO], [ZERO, ZERO]], [ZERO, ZERO]), null);
});

test('each method is found on its own kind of sequence', () => {
  assert.equal(found([7, 7, 7, 7, 7]), 'constant');
  assert.equal(found([2, 4, 6, 8, 10]), 'arithmetic');
  assert.equal(found([1, 2, 4, 8, 16, 32]), 'geometric');
  assert.equal(found([1, 4, 9, 16, 25, 36]), 'polynomial(2)');
  assert.equal(found([0, 1, 8, 27, 64, 125, 216]), 'polynomial(3)');
  assert.equal(found([5, 17, 53, 161, 485]), 'affine');
  assert.equal(found([1, 1, 2, 3, 5, 8, 13, 21]), 'recurrence(2)');
  assert.equal(found([1, 1, 2, 6, 24, 120]), 'product');
  assert.equal(found([2, 3, 5, 7, 11, 13, 17]), 'primes');
  assert.equal(found([2, 9, 4, 11, 6, 13, 8, 15]), 'interleaved(2)');
  assert.equal(found([3, 1, 4, 3, 1, 4, 3, 1, 4]), 'value-map');
});

test('and predicts the terms that come next', () => {
  assert.deepEqual(nextOf([2, 4, 6, 8, 10]), [12, 14, 16, 18]);
  assert.deepEqual(nextOf([1, 2, 4, 8, 16, 32]), [64, 128, 256, 512]);
  assert.deepEqual(nextOf([1, 4, 9, 16, 25, 36]), [49, 64, 81, 100]);
  assert.deepEqual(nextOf([1, 1, 2, 3, 5, 8, 13, 21]), [34, 55, 89, 144]);
  assert.deepEqual(nextOf([1, 1, 2, 6, 24, 120]), [720, 5040, 40320, 362880]);
  assert.deepEqual(nextOf([2, 3, 5, 7, 11, 13, 17]), [19, 23, 29, 31]);
  assert.deepEqual(nextOf([5, 17, 53, 161, 485]), [1457, 4373, 13121, 39365]);
  assert.deepEqual(nextOf([3, 1, 4, 3, 1, 4, 3, 1, 4]), [3, 1, 4, 3]);
  assert.deepEqual(nextOf([2, 9, 4, 11, 6, 13, 8, 15]), [10, 17, 12, 19]);
});

test('a law reproduces every term it was fitted to', () => {
  const sequences = [
    [7, 7, 7, 7, 7],
    [2, 4, 6, 8, 10],
    [1, 2, 4, 8, 16, 32],
    [1, 4, 9, 16, 25, 36],
    [1, 1, 2, 3, 5, 8, 13, 21],
    [5, 17, 53, 161, 485],
    [3, 1, 4, 3, 1, 4, 3, 1, 4],
    [1, 10, 2, 20, 3, 30, 4, 40],
    [-3, -6, -12, -24, -48],
  ];
  for (const sequence of sequences) {
    for (const candidate of discover(sequence).candidates) {
      const rebuilt = sequence.map((_, i) => candidate.term(i));
      if (candidate.projection) continue; // models a fold of the values, not the values
      assert.deepEqual(rebuilt, sequence, `${candidate.method} on ${sequence.join(' ')}`);
    }
  }
});

test('generated sequences are recovered whatever the parameters', () => {
  for (let a = -3; a <= 3; a++) {
    for (let b = -3; b <= 3; b++) {
      if (a === 0) continue;
      const sequence = [1];
      for (let i = 1; i < 8; i++) sequence.push(a * sequence[i - 1] + b);
      const result = discover(sequence);
      assert.ok(result.law, `no law for a=${a} b=${b}`);
      const predicted = result.next(3);
      const expected = [];
      let last = sequence.at(-1);
      for (let i = 0; i < 3; i++) expected.push((last = a * last + b));
      assert.deepEqual(predicted, expected, `a=${a} b=${b} via ${result.law.method}`);
    }
  }
});

test('polynomials of any small degree are recovered', () => {
  const evaluate = (coefficients, i) =>
    coefficients.reduce((total, c, power) => total + c * i ** power, 0);
  const cases = [
    [3, -2],
    [1, 0, 2],
    [0, 1, -1, 1],
    [5, 0, 0, 2],
  ];
  for (const coefficients of cases) {
    const sequence = Array.from({ length: 10 }, (_, i) => evaluate(coefficients, i));
    const result = discover(sequence);
    assert.ok(result.law, `no law for ${coefficients}`);
    assert.deepEqual(
      result.next(3),
      [10, 11, 12].map((i) => evaluate(coefficients, i)),
      `${coefficients} via ${result.law.method}`,
    );
  }
});

test('the holdout test separates a law from a coincidence', () => {
  const real = discover([2, 4, 6, 8, 10, 12]);
  assert.equal(real.confidence, 'verified');
  assert.equal(real.law.holdout.passed, real.law.holdout.tested);

  const noise = discover([12, 7, 19, 4, 88, 3]);
  assert.equal(noise.confidence, 'overfit');
  assert.ok(noise.law.overfit);
  assert.equal(noise.law.holdout.passed, 0);
});

test('an exact fit through every point is reported as overfit, never as a finding', () => {
  const result = discover([5, 2, 9, 1, 40, 6]);
  const interpolation = result.candidates.find((c) => c.method.startsWith('interpolation'));
  assert.ok(interpolation.overfit);
  assert.equal(interpolation.tier, 3);
  for (const candidate of result.candidates) {
    if (candidate === interpolation) continue;
    assert.ok(candidate.tier <= interpolation.tier);
  }
});

test('when only the fold repeats, the projection says so', () => {
  // odd, even, odd, even… with values that follow no rule of their own
  const result = discover([3, 8, 91, 2, 17, 6, 45, 4], { holdout: 2 });
  const projection = result.candidates.find((c) => c.projection);
  assert.ok(projection, 'expected a modular projection');
  assert.match(projection.projection, /folded into 1\.\.2/);
  assert.ok(projection.tier < 3, 'a projection should outrank plain overfitting');
});

test('candidates are ranked: verified before exact before projection before overfit', () => {
  for (const sequence of [
    [1, 1, 2, 3, 5, 8, 13],
    [3, 1, 4, 3, 1, 4, 3, 1, 4],
    [2, 4, 6, 8, 10, 12],
  ]) {
    const tiers = discover(sequence).candidates.map((c) => c.tier);
    assert.deepEqual(tiers, [...tiers].sort((a, b) => a - b), sequence.join(' '));
  }
});

test('discovery is deterministic', () => {
  const sequence = [1, 3, 7, 15, 31, 63];
  const a = discover(sequence);
  const b = discover(sequence);
  assert.equal(a.law.describe, b.law.describe);
  assert.deepEqual(a.next(10), b.next(10));
  assert.deepEqual(
    a.candidates.map((c) => c.method),
    b.candidates.map((c) => c.method),
  );
});

test('extend appends to the input', () => {
  const result = discover([2, 4, 6, 8]);
  assert.deepEqual(result.extend(2), [2, 4, 6, 8, 10, 12]);
});

test('explain writes it out in words', () => {
  const text = explain(discover([1, 1, 2, 3, 5, 8, 13]));
  assert.match(text, /x\[i\] = x\[i-1\] \+ x\[i-2\]/);
  assert.match(text, /next\s+21 34 55 89 144/);
});

test('huge or unrepresentable values fail the method instead of the run', () => {
  const result = discover([1, 1e15, 2e15, 3e15, 4e15]);
  assert.ok(result.candidates.every((c) => Number.isFinite(c.term(0))));
  const runaway = discover([2, 4, 16, 256, 65536]);
  assert.ok(Array.isArray(runaway.next(50)));
});

test('short and malformed input is rejected', () => {
  assert.throws(() => discover([1]), RangeError);
  assert.throws(() => discover([]), RangeError);
  assert.throws(() => discover('nope'), RangeError);
});
