import test from 'node:test';
import assert from 'node:assert/strict';

import { model, models, verify, sameShape, families } from '../src/model.js';
import { treeSize, treeValues } from '../src/tree.js';

test('the patterns from the example', () => {
  assert.deepEqual(model(1).pattern, [1, 2, 3, 4, 5, 6, 7, 8, 9]);
  assert.deepEqual(model(4).pattern, [4, 8, 3, 7, 2, 6, 1, 5, 9]);
  assert.deepEqual(model(5).pattern, [5, 1, 6, 2, 7, 3, 8, 4, 9]);
});

test('same input, same output — every time', () => {
  for (const seed of [1, 4, 5, 17, 240, -6]) {
    const a = model(seed);
    const b = model(seed);
    assert.equal(a.signature, b.signature);
    assert.deepEqual(a.pattern, b.pattern);
    assert.deepEqual(a.take(50), b.take(50));
    assert.deepEqual(a.tree.values, b.tree.values);
  }
});

test('the pattern repeats forever', () => {
  for (let modulus = 2; modulus <= 16; modulus++) {
    for (let seed = 1; seed <= 60; seed++) {
      const m = model(seed, { modulus, depth: 0 });
      const check = verify(m, 25);
      assert.ok(check.ok, `seed=${seed} mod=${modulus} ${JSON.stringify(check.firstMismatch)}`);
      for (let k = 0; k < 40; k++) {
        assert.equal(m.at(k), m.at(k + m.period));
        assert.equal(m.at(k), m.at(k + m.period * 7));
      }
    }
  }
});

test('take reads a window of the endless pattern', () => {
  const m = model(4);
  assert.deepEqual(m.take(9), [4, 8, 3, 7, 2, 6, 1, 5, 9]);
  assert.deepEqual(m.take(11), [4, 8, 3, 7, 2, 6, 1, 5, 9, 4, 8]);
  assert.deepEqual(m.take(3, 2), [3, 7, 2]);
  assert.deepEqual(m.take(3, 9), [4, 8, 3]);
  assert.deepEqual(m.take(0), []);
});

test('numbers that reduce to the same root share a pattern', () => {
  assert.ok(sameShape(model(4), model(13)));
  assert.ok(sameShape(model(4), model(400)));
  assert.ok(!sameShape(model(4), model(5)));
  assert.equal(model(400).root, 4);
  assert.deepEqual(model(400).pattern, model(4).pattern);
});

test('negative seeds fold in like any other', () => {
  const m = model(-5);
  assert.equal(m.root, 4);
  assert.deepEqual(m.pattern, model(4).pattern);
});

test('families groups a range by pattern', () => {
  const groups = families([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 13]);
  const bySeed = new Map();
  for (const [signature, seeds] of groups) {
    for (const seed of seeds) bySeed.set(seed, signature);
  }
  assert.equal(bySeed.get(1), bySeed.get(10));
  assert.equal(bySeed.get(4), bySeed.get(13));
  assert.notEqual(bySeed.get(1), bySeed.get(2));
  assert.equal(groups.size, 9);
});

test('other moduli behave', () => {
  const m = model(3, { modulus: 12, factor: 5 });
  assert.equal(m.modulus, 12);
  assert.equal(m.period, 4);
  assert.deepEqual(m.pattern, [3, 6, 9, 12]);
  assert.ok(verify(m, 12).ok);
});

test('the tree is finite, deterministic and closes on repeats', () => {
  const m = model(4, { depth: 5 });
  assert.equal(m.tree.value, 4);
  assert.equal(m.tree.size, treeSize(m.tree));
  assert.deepEqual(m.tree.values, treeValues(m.tree));
  assert.deepEqual(m.tree.values, model(4, { depth: 5 }).tree.values);

  const paths = [];
  const walk = (node, path) => {
    const next = [...path, node.value];
    if (node.repeat) {
      assert.ok(path.includes(node.value), 'a repeat node must close a loop on its own path');
      paths.push(next);
      return;
    }
    if (!node.children.length) paths.push(next);
    node.children.forEach((child) => walk(child, next));
  };
  walk(m.tree, []);
  assert.ok(paths.length > 0);
  for (const path of paths) {
    // no value occurs twice on a path except as the closing repeat
    const body = path.slice(0, -1);
    assert.equal(new Set(body).size, body.length);
  }
});

test('sibling branches that land on the same value are merged', () => {
  // for seed 1 the grow rule (x2) and the shift rule (+1) both reach 2
  const m = model(1, { depth: 1 });
  assert.deepEqual(m.tree.children.map((child) => child.value), [2, 9]);
  assert.equal(m.tree.children[0].rule, 'grow+shift');
  for (const node of [m.tree, ...m.tree.children]) {
    const values = node.children.map((child) => child.value);
    assert.equal(new Set(values).size, values.length);
  }
});

test('tree depth 0 is just the root', () => {
  const m = model(7, { depth: 0 });
  assert.equal(m.tree.size, 1);
  assert.deepEqual(m.tree.children, []);
});

test('rules can be chosen', () => {
  const m = model(1, { depth: 3, rules: ['grow'] });
  const walk = (node) => {
    assert.ok(node.children.length <= 1);
    node.children.forEach(walk);
  };
  walk(m.tree);
});

test('models maps a list', () => {
  const list = models([1, 4, 5]);
  assert.deepEqual(list.map((m) => m.seed), [1, 4, 5]);
  assert.deepEqual(list.map((m) => m.period), [9, 9, 9]);
});

test('verify reports a mismatch when the pattern is tampered with', () => {
  const m = model(4);
  const broken = { ...m, pattern: [...m.pattern], at: (k) => (k === 3 ? 0 : m.at(k)) };
  const check = verify(broken, 2);
  assert.equal(check.ok, false);
  assert.deepEqual(check.firstMismatch, { index: 3, expected: 7, actual: 0 });
});

test('bad input is rejected', () => {
  assert.throws(() => model(1.5), TypeError);
  assert.throws(() => model(1, { modulus: 1 }), RangeError);
  assert.throws(() => model(1, { depth: -1 }), RangeError);
  assert.throws(() => model(1, { rules: ['nope'] }), RangeError);
  assert.throws(() => model(1).at(0.5), TypeError);
  assert.throws(() => model(1).take(-1), RangeError);
});
