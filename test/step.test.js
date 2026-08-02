import test from 'node:test';
import assert from 'node:assert/strict';

import { stepRule, discover } from '../src/discover.js';
import { conflictIn, cycleFrom, STEP_METHODS } from '../src/step.js';
import { R } from '../src/rational.js';
import { model } from '../src/model.js';

const ruleFor = (sequence) => stepRule(sequence).rule;

test('one rule, applied to each number the same way', () => {
  assert.equal(ruleFor([2, 4, 6, 8, 10]).method, 'step:add');
  assert.equal(ruleFor([1, 2, 4, 8, 16]).method, 'step:multiply');
  assert.equal(ruleFor([5, 17, 53, 161, 485]).method, 'step:affine');
  assert.equal(ruleFor([2, 5, 26, 677, 458330]).method, 'step:polynomial(2)');
  assert.equal(ruleFor([6, 3, 10, 5, 16, 8, 4, 2, 1]).method, 'step:parity');
  assert.equal(ruleFor([7, 49, 97, 130, 10, 1, 1]).method, 'step:digit-squares');
  assert.equal(ruleFor([2, 3, 5, 7, 11, 13]).method, 'step:next-prime');
  assert.equal(ruleFor([4, 8, 3, 7, 2, 6, 1, 5, 9, 4, 8]).method, 'step:ring(9)');
  assert.equal(ruleFor([10, 3, 7, 10, 3, 7, 10]).method, 'step:table');
});

test('the rule really is the same at every step', () => {
  for (const sequence of [
    [2, 4, 6, 8, 10],
    [1, 2, 4, 8, 16],
    [5, 17, 53, 161, 485],
    [6, 3, 10, 5, 16, 8, 4, 2, 1],
    [4, 8, 3, 7, 2, 6, 1, 5, 9, 4, 8],
    [3, 1, 4, 3, 1, 4, 3, 1, 4],
  ]) {
    const found = stepRule(sequence);
    assert.ok(found.rule, sequence.join(' '));
    assert.ok(found.rule.uniform);
    for (let i = 0; i < sequence.length - 1; i++) {
      assert.equal(found.apply(sequence[i]), sequence[i + 1], `${sequence.join(' ')} at ${i}`);
    }
  }
});

test('the same number always gets the same successor, wherever it appears', () => {
  const sequence = [4, 8, 3, 7, 2, 6, 1, 5, 9, 4, 8, 3, 7];
  const { apply } = stepRule(sequence);
  const seen = new Map();
  for (const value of sequence) {
    const next = apply(value);
    if (seen.has(value)) assert.equal(seen.get(value), next, `${value} moved`);
    seen.set(value, next);
  }
  // and applying it 9 times returns every number to itself
  for (const value of [1, 2, 3, 4, 5, 6, 7, 8, 9]) {
    let walked = value;
    for (let i = 0; i < 9; i++) walked = apply(walked);
    assert.equal(walked, value);
  }
});

test('a uniform rule settles into a loop that repeats forever', () => {
  const ring = stepRule([4, 8, 3, 7, 2, 6, 1, 5, 9, 4, 8]);
  assert.equal(ring.cycle.closes, true);
  assert.equal(ring.cycle.period, 9);
  assert.deepEqual(ring.cycle.cycle, [4, 8, 3, 7, 2, 6, 1, 5, 9]);
  assert.deepEqual(ring.cycle.lead, []);

  const collatz = stepRule([6, 3, 10, 5, 16, 8, 4, 2, 1]);
  assert.equal(collatz.cycle.closes, true);
  assert.deepEqual(collatz.cycle.cycle, [4, 2, 1]);
  assert.deepEqual(collatz.cycle.lead, [6, 3, 10, 5, 16, 8]);

  const open = stepRule([2, 4, 6, 8, 10]);
  assert.equal(open.cycle.closes, false);
  assert.match(open.cycle.reason, /no repeat/);
});

test('predictions continue the sequence and keep obeying the rule', () => {
  const found = stepRule([4, 8, 3, 7, 2, 6, 1, 5, 9, 4, 8]);
  assert.deepEqual(found.next(6), [3, 7, 2, 6, 1, 5]);

  const whole = [...found.input, ...found.next(20)];
  for (let i = 0; i < whole.length - 1; i++) {
    assert.equal(found.apply(whole[i]), whole[i + 1]);
  }
});

test('when the next term is not decided by the current one, it says so and why', () => {
  const found = stepRule([1, 1, 2, 3, 5, 8, 13]);
  assert.equal(found.rule, null);
  assert.ok(found.impossible);
  assert.equal(found.impossible.value, '1');
  assert.deepEqual(found.impossible.successors, ['1', '2']);
  assert.deepEqual(found.impossible.at, [0, 1]);

  // the same sequence does have an index-based law — it is uniformity that fails
  assert.equal(discover([1, 1, 2, 3, 5, 8, 13]).law.method, 'recurrence(2)');
});

test('conflictIn finds a repeated value with two different successors', () => {
  assert.equal(conflictIn([1, 2, 3, 4]), null);
  assert.equal(conflictIn([3, 1, 4, 3, 1, 4]), null);
  const conflict = conflictIn([5, 9, 5, 2]);
  assert.equal(conflict.value, '5');
  assert.deepEqual(conflict.successors, ['9', '2']);
});

test('no uniform rule is claimed for noise', () => {
  const found = stepRule([12, 7, 19, 4, 88, 3]);
  assert.equal(found.rule, null);
  assert.equal(found.impossible, null); // nothing forbids one, none was found
});

test('index-based laws are excluded — they are not the same rule at every step', () => {
  for (const sequence of [
    [1, 4, 9, 16, 25, 36], // polynomial in the index
    [1, 10, 2, 20, 3, 30], // interleaved phases
  ]) {
    const found = stepRule(sequence);
    if (found.rule) {
      assert.ok(found.rule.uniform, `${sequence.join(' ')} claimed a non-uniform rule`);
      assert.ok(
        found.rule.projection,
        `${sequence.join(' ')} claimed an exact rule that does not exist`,
      );
    }
    assert.ok(discover(sequence).law, 'the index-based search should still find it');
  }
});

test('every pattern the generator produces is recovered as a uniform rule', () => {
  for (const seed of [1, 2, 4, 5, 7, 8]) {
    const m = model(seed);
    const sequence = m.take(m.period + 3);
    const found = stepRule(sequence);
    assert.ok(found.rule, `seed ${seed}`);
    assert.equal(found.rule.method, 'step:ring(9)');
    assert.equal(found.cycle.period, m.period);
    assert.deepEqual(found.cycle.cycle, m.pattern);
    assert.deepEqual(found.next(m.period), m.take(m.period, sequence.length));
  }
});

test('the doubling orbit is recovered as multiplication on the ring', () => {
  const m = model(1);
  const orbit = [...m.orbit.cycle, ...m.orbit.cycle];
  const found = stepRule(orbit);
  assert.equal(found.rule.method, 'step:ring(9)');
  assert.match(found.rule.describe, /2 · x/);
  assert.equal(found.cycle.period, m.orbit.period);
});

test('cycleFrom walks a rule to its loop', () => {
  const halve = (x) => (x.n % 2 === 0 ? x.div(R(2)) : R(1));
  const walk = cycleFrom(halve, R(8));
  assert.equal(walk.closes, true);
  assert.deepEqual(walk.lead, [8, 4, 2]);
  assert.deepEqual(walk.cycle, [1]);
  assert.equal(walk.period, 1);

  const runaway = cycleFrom((x) => x.add(R(1)), R(0));
  assert.equal(runaway.closes, false);
});

test('uniform rules are held out and ranked like everything else', () => {
  const found = stepRule([4, 8, 3, 7, 2, 6, 1, 5, 9, 4, 8]);
  assert.equal(found.confidence, 'verified');
  assert.equal(found.rule.holdout.passed, found.rule.holdout.tested);

  const tiers = found.candidates.map((c) => c.tier);
  assert.deepEqual(tiers, [...tiers].sort((a, b) => a - b));
  assert.ok(found.candidates.every((c) => c.uniform));
});

test('a rule that compresses beats one that memorises', () => {
  // a ring rule holds three numbers; the table holding the same loop holds many
  const ring = stepRule([4, 8, 3, 7, 2, 6, 1, 5, 9, 4, 8]);
  assert.equal(ring.rule.method, 'step:ring(9)');
  const table = ring.candidates.find((c) => c.method === 'step:table');
  assert.ok(table, 'the table should still be offered');
  assert.ok(table.score > ring.rule.score);

  // when nothing compresses it, the table is the rule
  const memorised = stepRule([10, 3, 7, 10, 3, 7, 10]);
  assert.equal(memorised.rule.method, 'step:table');
  assert.equal(memorised.cycle.period, 3);
  assert.deepEqual(memorised.next(3), [3, 7, 10]);
});

test('discover can be restricted to uniform rules', () => {
  const restricted = discover([1, 4, 9, 16, 25, 36], { uniform: true });
  assert.ok(restricted.candidates.every((c) => c.uniform));
  assert.ok(restricted.candidates.length <= STEP_METHODS.length);
  assert.equal(restricted.tried, STEP_METHODS.length);

  const open = discover([1, 4, 9, 16, 25, 36]);
  assert.equal(open.law.method, 'polynomial(2)');
  assert.equal(open.law.uniform, false);
});

test('short and malformed input is rejected', () => {
  assert.throws(() => stepRule([1]), RangeError);
  assert.throws(() => stepRule([]), RangeError);
});
