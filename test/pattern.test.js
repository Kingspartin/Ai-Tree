import test from 'node:test';
import assert from 'node:assert/strict';

import { gcd, wrap, digitalRoot, ladder, orbit, mirror, sequenceAt } from '../src/pattern.js';

test('wrap folds into 1..modulus', () => {
  assert.equal(wrap(1, 9), 1);
  assert.equal(wrap(9, 9), 9);
  assert.equal(wrap(10, 9), 1);
  assert.equal(wrap(0, 9), 9);
  assert.equal(wrap(-1, 9), 8);
  assert.equal(wrap(13, 12), 1);
});

test('wrap(n, 9) is the digital root for every positive n', () => {
  for (let n = 1; n <= 5000; n++) {
    assert.equal(wrap(n, 9), digitalRoot(n), `n=${n}`);
  }
});

test('gcd', () => {
  assert.equal(gcd(0, 9), 9);
  assert.equal(gcd(4, 9), 1);
  assert.equal(gcd(6, 9), 3);
  assert.equal(gcd(-6, 9), 3);
});

test('the worked examples come out right', () => {
  assert.deepEqual(ladder(1).values, [1, 2, 3, 4, 5, 6, 7, 8, 9]);
  assert.deepEqual(ladder(4).values, [4, 8, 3, 7, 2, 6, 1, 5, 9]);
  assert.deepEqual(ladder(5).values, [5, 1, 6, 2, 7, 3, 8, 4, 9]);
});

test('ladder period is modulus / gcd(seed, modulus)', () => {
  for (let modulus = 2; modulus <= 30; modulus++) {
    for (let seed = 1; seed <= 200; seed++) {
      const { values, period } = ladder(seed, modulus);
      assert.equal(period, modulus / gcd(seed % modulus, modulus), `seed=${seed} mod=${modulus}`);
      assert.equal(values.length, period);
      // the term after the last is the first term again
      assert.equal(wrap(seed * (period + 1), modulus), values[0]);
    }
  }
});

test('ladder with period 9 visits every value once', () => {
  for (const seed of [1, 2, 4, 5, 7, 8]) {
    const { values } = ladder(seed);
    assert.deepEqual([...values].sort((a, b) => a - b), [1, 2, 3, 4, 5, 6, 7, 8, 9]);
  }
});

test('ladder collapses when seed shares a factor with the modulus', () => {
  assert.deepEqual(ladder(3).values, [3, 6, 9]);
  assert.deepEqual(ladder(6).values, [6, 3, 9]);
  assert.deepEqual(ladder(9).values, [9]);
});

test('orbit finds the doubling cycle', () => {
  assert.deepEqual(orbit(1, 9, 2).cycle, [1, 2, 4, 8, 7, 5]);
  assert.deepEqual(orbit(4, 9, 2).cycle, [4, 8, 7, 5, 1, 2]);
  assert.deepEqual(orbit(5, 9, 2).cycle, [5, 1, 2, 4, 8, 7]);
  assert.deepEqual(orbit(3, 9, 2).cycle, [3, 6]);
  assert.deepEqual(orbit(9, 9, 2).cycle, [9]);
});

test('orbit always closes into a cycle', () => {
  for (let modulus = 2; modulus <= 20; modulus++) {
    for (let factor = 0; factor <= 6; factor++) {
      for (let seed = 1; seed <= modulus; seed++) {
        const { lead, cycle, period, entry } = orbit(seed, modulus, factor);
        assert.ok(period >= 1, `seed=${seed} mod=${modulus} factor=${factor}`);
        assert.equal(entry, lead.length);
        // stepping off the end of the cycle lands back on its start
        assert.equal(wrap(cycle.at(-1) * factor, modulus), cycle[0]);
      }
    }
  }
});

test('mirror is its own inverse', () => {
  for (let modulus = 2; modulus <= 20; modulus++) {
    for (let value = 1; value <= modulus; value++) {
      assert.equal(mirror(mirror(value, modulus), modulus), value);
    }
  }
  assert.equal(mirror(1), 9);
  assert.equal(mirror(4), 6);
  assert.equal(mirror(5), 5);
});

test('sequenceAt wraps in both directions', () => {
  const values = [4, 8, 3];
  assert.equal(sequenceAt(values, 0), 4);
  assert.equal(sequenceAt(values, 3), 4);
  assert.equal(sequenceAt(values, 300), 4);
  assert.equal(sequenceAt(values, -1), 3);
  assert.equal(sequenceAt(values, -3), 4);
});

test('bad input is rejected', () => {
  assert.throws(() => wrap(1, 1), RangeError);
  assert.throws(() => wrap(1.5, 9), TypeError);
  assert.throws(() => ladder(1.5), TypeError);
  assert.throws(() => sequenceAt([], 0), TypeError);
});
