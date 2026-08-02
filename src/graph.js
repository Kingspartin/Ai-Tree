/**
 * The pattern as a graph, and as coordinates.
 *
 * A rule where every number has exactly one successor is a directed graph in
 * which every node has out-degree 1. Graphs of that shape have a known
 * structure, and it is the structure this whole repo keeps running into:
 *
 *     every component is exactly one cycle, with trees feeding into it
 *
 * So the pattern is the cycle, and the numbers that fall into the pattern are
 * the trees hanging off it. Nothing else can happen — following arrows from a
 * finite set of numbers has nowhere to go but round.
 *
 * `functionalGraph` builds that structure, `layout` gives every node an (x, y)
 * so it can be drawn, and `toDot` hands the same thing to graphviz.
 */

/**
 * @typedef {object} GraphNode
 * @property {number} value
 * @property {number|null} next     successor, or null when it leaves the domain
 * @property {boolean} onCycle
 * @property {number|null} depth    steps to reach the cycle (0 on the cycle itself)
 * @property {number|null} cycle    id of the cycle this node falls into
 * @property {boolean} escapes      true when following the rule leaves the graph
 */

/**
 * Build the graph of a rule over a set of numbers.
 *
 * @param {(value: number) => number} apply
 * @param {number[]} domain
 * @returns {{nodes: Map<number, GraphNode>, order: number[], edges: Array<[number, number]>,
 *            cycles: Array<{id: number, values: number[], period: number}>,
 *            components: Array<{cycle: number, values: number[]}>,
 *            children: Map<number, number[]>}}
 */
export function functionalGraph(apply, domain) {
  const order = [...new Set(domain)];
  const nodes = new Map();

  for (const value of order) {
    let next = null;
    try {
      const candidate = apply(value);
      if (Number.isFinite(candidate)) next = candidate;
    } catch {
      next = null;
    }
    nodes.set(value, { value, next, onCycle: false, depth: null, cycle: null, escapes: false });
  }

  // successors that left the domain are not edges of this graph
  for (const node of nodes.values()) {
    if (node.next !== null && !nodes.has(node.next)) {
      node.escapes = true;
      node.next = null;
    }
  }

  const cycles = findCycles(nodes);
  assignDepths(nodes, cycles);

  const edges = [];
  const children = new Map(order.map((value) => [value, []]));
  for (const node of nodes.values()) {
    if (node.next === null) continue;
    edges.push([node.value, node.next]);
    children.get(node.next).push(node.value);
  }

  const components = cycles.map((cycle) => ({
    cycle: cycle.id,
    values: order.filter((value) => nodes.get(value).cycle === cycle.id),
  }));
  const loose = order.filter((value) => nodes.get(value).cycle === null);
  if (loose.length) components.push({ cycle: null, values: loose });

  return { nodes, order, edges, cycles, components, children };
}

/** Walk every node forward until the walk repeats or leaves the graph. */
function findCycles(nodes) {
  const cycles = [];
  const state = new Map(); // value → 'open' while walking, or settled
  let nextId = 0;

  for (const start of nodes.keys()) {
    if (state.has(start)) continue;

    const path = [];
    const seen = new Map();
    let value = start;

    while (value !== null && !state.has(value) && !seen.has(value)) {
      seen.set(value, path.length);
      path.push(value);
      value = nodes.get(value).next;
    }

    if (value !== null && seen.has(value)) {
      // the walk closed on itself — everything from that point is a cycle
      const from = seen.get(value);
      const values = path.slice(from);
      const id = nextId++;
      cycles.push({ id, values, period: values.length });
      for (const member of values) {
        const node = nodes.get(member);
        node.onCycle = true;
        node.cycle = id;
        node.depth = 0;
        state.set(member, id);
      }
      for (const member of path.slice(0, from)) state.set(member, id);
    } else {
      const settled = value === null ? null : state.get(value);
      for (const member of path) state.set(member, settled ?? null);
    }
  }
  return cycles;
}

/** Distance to the cycle, walking backwards from it. */
function assignDepths(nodes, cycles) {
  const queue = [];
  for (const cycle of cycles) {
    for (const value of cycle.values) queue.push(value);
  }

  const incoming = new Map();
  for (const node of nodes.values()) {
    if (node.next === null) continue;
    if (!incoming.has(node.next)) incoming.set(node.next, []);
    incoming.get(node.next).push(node.value);
  }

  for (let head = 0; head < queue.length; head++) {
    const value = queue[head];
    const node = nodes.get(value);
    for (const source of incoming.get(value) ?? []) {
      const feeder = nodes.get(source);
      if (feeder.onCycle || feeder.depth !== null) continue;
      feeder.depth = node.depth + 1;
      feeder.cycle = node.cycle;
      queue.push(source);
    }
  }
}

/**
 * Every number reachable by following the rule from these starting points.
 * Bounded, so an unbounded rule gives a finite window rather than hanging.
 */
export function reachableFrom(apply, starts, limit = 200) {
  const seen = new Set();
  const queue = [...starts];

  while (queue.length && seen.size < limit) {
    const value = queue.shift();
    if (seen.has(value)) continue;
    seen.add(value);
    try {
      const next = apply(value);
      if (Number.isFinite(next) && !seen.has(next)) queue.push(next);
    } catch {
      // the rule has nothing to say here; the node simply has no outgoing edge
    }
  }
  return [...seen];
}

/**
 * The graph of a discovered rule.
 *
 * A rule on a ring gets its whole ring drawn, because that is the complete
 * picture and it is guaranteed finite. Any other rule gets the numbers actually
 * reachable from the sequence.
 *
 * @param {{rule: object, input: number[]}} found  a stepRule result
 */
export function graphOf(found, { limit = 200 } = {}) {
  if (!found?.rule?.apply) return null;
  const modulus = found.rule.params?.modulus;
  const domain = modulus
    ? Array.from({ length: Number(modulus) }, (_, i) => i + 1)
    : reachableFrom(found.rule.apply, found.input, limit);
  return functionalGraph(found.rule.apply, domain);
}

/* ------------------------------------------------------------------ */
/* coordinates                                                         */
/* ------------------------------------------------------------------ */

/**
 * Give every node an (x, y).
 *
 * Each component is drawn as its cycle on a circle, with the trees that feed
 * into it fanning outwards from the cycle node they land on. Components are
 * tiled left to right. Coordinates come back normalised to a 0..1 box, so the
 * caller picks the pixel size.
 *
 * @returns {{nodes: Array<{value: number, x: number, y: number, onCycle: boolean, depth: number|null, cycle: number|null}>,
 *            edges: Array<{from: number, to: number, x1: number, y1: number, x2: number, y2: number, onCycle: boolean}>,
 *            width: number, height: number}}
 */
export function layout(graph, { layerGap = 1.6, minRadius = 2.2 } = {}) {
  const placed = new Map();
  const boxes = [];

  for (const component of graph.components) {
    const cycle = graph.cycles.find((c) => c.id === component.cycle);
    const local = new Map();

    if (cycle) {
      const radius = Math.max(minRadius, (cycle.period * 1.1) / (2 * Math.PI) + minRadius);
      cycle.values.forEach((value, index) => {
        const angle = (index / cycle.period) * Math.PI * 2 - Math.PI / 2;
        local.set(value, { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius, angle });
      });
      // the wedge each cycle node may spread its feeding tree into
      const wedge = (Math.PI * 2) / cycle.period;
      for (const value of cycle.values) {
        placeFeeders(graph, value, local.get(value).angle, wedge, radius, layerGap, local);
      }
    } else {
      // no cycle: a chain or a fragment, laid out as a simple arc
      component.values.forEach((value, index) => {
        const angle = (index / Math.max(1, component.values.length)) * Math.PI * 2 - Math.PI / 2;
        const radius = minRadius + index * 0.05;
        local.set(value, { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius, angle });
      });
    }

    const xs = [...local.values()].map((p) => p.x);
    const ys = [...local.values()].map((p) => p.y);
    boxes.push({
      local,
      minX: Math.min(...xs),
      maxX: Math.max(...xs),
      minY: Math.min(...ys),
      maxY: Math.max(...ys),
    });
  }

  // tile the components in a row, keeping a gap between them
  let offset = 0;
  let height = 0;
  for (const box of boxes) {
    const width = box.maxX - box.minX;
    for (const [value, point] of box.local) {
      placed.set(value, { x: point.x - box.minX + offset, y: point.y - box.minY });
    }
    offset += width + 2;
    height = Math.max(height, box.maxY - box.minY);
  }

  const width = Math.max(1, offset - 2);
  const nodes = graph.order
    .filter((value) => placed.has(value))
    .map((value) => {
      const node = graph.nodes.get(value);
      const point = placed.get(value);
      return {
        value,
        x: point.x / width,
        y: height === 0 ? 0.5 : point.y / height,
        onCycle: node.onCycle,
        depth: node.depth,
        cycle: node.cycle,
      };
    });

  const byValue = new Map(nodes.map((node) => [node.value, node]));
  const edges = graph.edges
    .filter(([from, to]) => byValue.has(from) && byValue.has(to))
    .map(([from, to]) => ({
      from,
      to,
      x1: byValue.get(from).x,
      y1: byValue.get(from).y,
      x2: byValue.get(to).x,
      y2: byValue.get(to).y,
      onCycle: byValue.get(from).onCycle && byValue.get(to).onCycle,
    }));

  return { nodes, edges, width, height: height || 1 };
}

/** Fan the tree feeding a cycle node outwards, splitting the wedge by size. */
function placeFeeders(graph, root, angle, wedge, radius, layerGap, local) {
  const stack = [{ value: root, angle, wedge, radius }];

  while (stack.length) {
    const { value, angle: centre, wedge: span, radius: r } = stack.pop();
    const feeders = (graph.children.get(value) ?? []).filter(
      (child) => !graph.nodes.get(child).onCycle && !local.has(child),
    );
    if (feeders.length === 0) continue;

    const weights = feeders.map((child) => Math.max(1, subtreeSize(graph, child, local)));
    const total = weights.reduce((sum, weight) => sum + weight, 0);
    let cursor = centre - span / 2;

    feeders.forEach((child, index) => {
      const share = (weights[index] / total) * span;
      const childAngle = cursor + share / 2;
      cursor += share;
      const childRadius = r + layerGap;
      local.set(child, {
        x: Math.cos(childAngle) * childRadius,
        y: Math.sin(childAngle) * childRadius,
        angle: childAngle,
      });
      stack.push({ value: child, angle: childAngle, wedge: share * 0.9, radius: childRadius });
    });
  }
}

function subtreeSize(graph, value, placedAlready) {
  let count = 0;
  const stack = [value];
  while (stack.length) {
    const current = stack.pop();
    count++;
    for (const child of graph.children.get(current) ?? []) {
      if (graph.nodes.get(child).onCycle || placedAlready.has(child)) continue;
      stack.push(child);
    }
  }
  return count;
}

/* ------------------------------------------------------------------ */
/* handing it to other tools                                           */
/* ------------------------------------------------------------------ */

/** The graph in graphviz's DOT language, cycles drawn bold. */
export function toDot(graph, { name = 'pattern' } = {}) {
  const lines = [`digraph ${name} {`, '  node [shape=circle fontname="monospace"];'];

  for (const cycle of graph.cycles) {
    lines.push(`  // cycle ${cycle.id}, period ${cycle.period}`);
    for (const value of cycle.values) {
      lines.push(`  "${value}" [penwidth=2];`);
    }
  }
  for (const [from, to] of graph.edges) {
    const bold = graph.nodes.get(from).onCycle && graph.nodes.get(to).onCycle;
    lines.push(`  "${from}" -> "${to}"${bold ? ' [penwidth=2]' : ''};`);
  }
  lines.push('}');
  return lines.join('\n');
}

/** Every node with its coordinates, as plain data. */
export function toCoordinates(graph, options) {
  return layout(graph, options).nodes;
}
