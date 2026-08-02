import test from 'node:test';
import assert from 'node:assert/strict';

import { functionalGraph, graphOf, reachableFrom, layout, toDot } from '../src/graph.js';
import { stepRule } from '../src/discover.js';
import { model } from '../src/model.js';

/** f(x) = a·x + b folded into 1..m */
const ring = (m, a, b) => (x) => ((((a * x + b - 1) % m) + m) % m) + 1;
const upTo = (m) => Array.from({ length: m }, (_, i) => i + 1);

test('a rule with one arrow out of every number is one cycle per component', () => {
  const graph = functionalGraph(ring(9, 1, 4), upTo(9));
  assert.equal(graph.nodes.size, 9);
  assert.equal(graph.cycles.length, 1);
  assert.equal(graph.cycles[0].period, 9);
  assert.equal(graph.components.length, 1);
  for (const node of graph.nodes.values()) {
    assert.equal(node.onCycle, true);
    assert.equal(node.depth, 0);
  }
});

test('doubling on a ring of 9 splits into its three known loops', () => {
  const graph = functionalGraph(ring(9, 2, 0), upTo(9));
  const periods = graph.cycles.map((cycle) => cycle.period).sort((a, b) => a - b);
  assert.deepEqual(periods, [1, 2, 6]);
  assert.equal(graph.components.length, 3);
  const six = graph.cycles.find((cycle) => cycle.period === 6);
  assert.deepEqual([...six.values].sort((a, b) => a - b), [1, 2, 4, 5, 7, 8]);
});

test('numbers that are not on a loop fall into one, and their distance is recorded', () => {
  // doubling on a ring of 10 is not reversible, so odd numbers feed in
  const graph = functionalGraph(ring(10, 2, 0), upTo(10));
  const cycle = graph.cycles.find((c) => c.period === 4);
  assert.deepEqual(cycle.values.sort((a, b) => a - b), [2, 4, 6, 8]);

  for (const value of [1, 3, 5, 7, 9]) {
    const node = graph.nodes.get(value);
    assert.equal(node.onCycle, false);
    assert.equal(node.depth, 1, `${value} should be one step from a loop`);
    assert.notEqual(node.cycle, null);
  }
  // following the arrows from anywhere lands on a loop
  for (const start of upTo(10)) {
    let value = start;
    for (let step = 0; step < 20; step++) value = ring(10, 2, 0)(value);
    assert.ok(graph.nodes.get(value).onCycle, `${start} never reached a loop`);
  }
});

test('every node has exactly one arrow out, and the edges say so', () => {
  const graph = functionalGraph(ring(12, 5, 3), upTo(12));
  assert.equal(graph.edges.length, graph.nodes.size);
  const sources = graph.edges.map(([from]) => from);
  assert.equal(new Set(sources).size, sources.length);
});

test('a rule that leaves the drawn numbers is marked rather than guessed at', () => {
  const graph = functionalGraph((x) => x + 1, [1, 2, 3]);
  assert.equal(graph.nodes.get(3).escapes, true);
  assert.equal(graph.nodes.get(3).next, null);
  assert.equal(graph.cycles.length, 0);
  assert.equal(graph.components.length, 1);
  assert.equal(graph.components[0].cycle, null);
});

test('reachableFrom follows the rule and stops at the limit', () => {
  assert.deepEqual(reachableFrom(ring(9, 2, 0), [1]).sort((a, b) => a - b), [1, 2, 4, 5, 7, 8]);
  assert.equal(reachableFrom((x) => x + 1, [0], 25).length, 25);
  assert.deepEqual(reachableFrom((x) => x, [7]), [7]);
});

test('graphOf draws the whole ring for a ring rule', () => {
  const found = stepRule([4, 8, 3, 7, 2, 6, 1, 5, 9, 4, 8]);
  const graph = graphOf(found);
  assert.equal(graph.order.length, 9);
  assert.equal(graph.cycles[0].period, 9);
});

test('graphOf follows the numbers actually reached for other rules', () => {
  const found = stepRule([6, 3, 10, 5, 16, 8, 4, 2, 1]);
  const graph = graphOf(found);
  assert.ok(graph.order.includes(16));
  const cycle = graph.cycles.find((c) => c.period === 3);
  assert.deepEqual(cycle.values.sort((a, b) => a - b), [1, 2, 4]);
  // the lead-in numbers hang off the loop
  assert.equal(graph.nodes.get(6).onCycle, false);
  assert.ok(graph.nodes.get(6).depth > 0);
});

test('the generator and the graph agree about every seed', () => {
  for (const seed of [1, 2, 3, 4, 5, 6, 7, 8, 9]) {
    const m = model(seed);
    const found = stepRule(m.take(m.period + 3));
    const graph = graphOf(found);
    const cycle = graph.cycles.find((c) => c.values.includes(m.pattern[0]));
    assert.equal(cycle.period, m.period, `seed ${seed}`);
    assert.deepEqual([...cycle.values].sort((a, b) => a - b), [...m.pattern].sort((a, b) => a - b));
  }
});

test('coordinates are inside the box, and every edge joins two of them', () => {
  const graph = functionalGraph(ring(10, 2, 0), upTo(10));
  const placed = layout(graph);

  assert.equal(placed.nodes.length, 10);
  for (const node of placed.nodes) {
    assert.ok(node.x >= 0 && node.x <= 1, `x out of range: ${node.x}`);
    assert.ok(node.y >= 0 && node.y <= 1, `y out of range: ${node.y}`);
  }
  const points = new Set(placed.nodes.map((node) => `${node.x.toFixed(4)},${node.y.toFixed(4)}`));
  assert.equal(points.size, placed.nodes.length, 'two numbers landed on the same spot');

  const byValue = new Map(placed.nodes.map((node) => [node.value, node]));
  for (const edge of placed.edges) {
    assert.equal(edge.x1, byValue.get(edge.from).x);
    assert.equal(edge.y2, byValue.get(edge.to).y);
  }
  // the 4-loop plus the self-loop at 10, which doubling leaves where it is
  assert.equal(placed.edges.filter((edge) => edge.onCycle).length, 5);
});

test('the layout is the same every time', () => {
  const graph = functionalGraph(ring(12, 5, 3), upTo(12));
  assert.deepEqual(layout(graph).nodes, layout(graph).nodes);
});

test('DOT output names every node and edge', () => {
  const graph = functionalGraph(ring(9, 1, 4), upTo(9));
  const dot = toDot(graph);
  assert.match(dot, /^digraph pattern \{/);
  assert.match(dot, /\}$/);
  for (const [from, to] of graph.edges) {
    assert.ok(dot.includes(`"${from}" -> "${to}"`), `missing edge ${from}→${to}`);
  }
});

test('a graph of one number is still a graph', () => {
  const graph = functionalGraph((x) => x, [5]);
  assert.equal(graph.cycles.length, 1);
  assert.equal(graph.cycles[0].period, 1);
  assert.equal(layout(graph).nodes.length, 1);
});

test('graphOf declines when there is no rule to draw', () => {
  assert.equal(graphOf(stepRule([1, 1, 2, 3, 5, 8])), null);
  assert.equal(graphOf(null), null);
});
