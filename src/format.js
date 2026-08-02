/**
 * Text rendering for models — used by the CLI and handy in tests.
 */

/** One-line summary: `4  ladder 4 8 3 7 2 6 1 5 9  (period 9)` */
export function formatLine(m) {
  return `${String(m.seed).padStart(4)}  ${m.pattern.join(' ')}  (period ${m.period})`;
}

/** Full report for a single model. */
export function formatModel(m, { repeats = 2 } = {}) {
  const lines = [];
  const width = String(m.modulus).length;
  const pad = (n) => String(n).padStart(width);

  lines.push(`seed ${m.seed}   root ${m.root}   mod ${m.modulus}   factor ${m.factor}`);
  lines.push('');
  lines.push(`  pattern   ${m.pattern.map(pad).join(' ')}   period ${m.period}`);
  lines.push(`  repeated  ${m.take(m.period * repeats).map(pad).join(' ')}`);
  lines.push(
    `  orbit     ${m.orbit.cycle.map(pad).join(' ')}   period ${m.orbit.period}` +
      (m.orbit.lead.length ? `   lead ${m.orbit.lead.join(' ')}` : ''),
  );
  lines.push(`  mirror    ${pad(m.mirror)}`);
  lines.push(`  signature ${m.signature}`);
  lines.push('');
  lines.push('  tree');
  lines.push(...formatTree(m.tree).map((line) => `    ${line}`));
  return lines.join('\n');
}

/** Render a tree node as box-drawing lines. */
export function formatTree(node) {
  const label = (n) =>
    (n.rule ? `${n.rule} → ${n.value}` : String(n.value)) + (n.repeat ? '  ↺' : '');

  const lines = [label(node)];
  const walk = (children, prefix) => {
    children.forEach((child, index) => {
      const last = index === children.length - 1;
      lines.push(`${prefix}${last ? '└─ ' : '├─ '}${label(child)}`);
      walk(child.children, `${prefix}${last ? '   ' : '│  '}`);
    });
  };
  walk(node.children, '');
  return lines;
}

/**
 * Report for a discovery run: the winning law, then everything else that fitted.
 * @param {import('./discover.js').discover} result
 */
export function formatDiscovery(result, { next = 6, all = false } = {}) {
  const lines = [`sequence  ${result.input.join(' ')}`, ''];

  if (!result.law) {
    lines.push(`  no law found — ${result.tried} methods tried`);
    return lines.join('\n');
  }

  const law = result.law;
  lines.push(`  law       ${law.describe}`);
  lines.push(`  method    ${law.method}`);
  lines.push(`  standing  ${result.confidence}${badge(law)}`);
  lines.push(`  next      ${law.next(next).join(' ')}`);
  if (law.projection) lines.push(`  note      predicts the ${law.projection}, not the raw value`);
  if (law.overfit) {
    lines.push('  note      as many parameters as terms — this fits any sequence at all');
  }

  const others = result.candidates.slice(1);
  if (all && others.length) {
    lines.push('', `  ${others.length} other fit${others.length === 1 ? '' : 's'}`);
    for (const candidate of others) {
      lines.push(
        `    ${candidate.method.padEnd(18)} ${String(candidate.score).padStart(6)}  ${candidate.describe}`,
      );
    }
  } else if (others.length) {
    lines.push('', `  ${others.length} other fit${others.length === 1 ? '' : 's'}: ${others.map((c) => c.method).join(', ')}`);
  }
  return lines.join('\n');
}

function badge(law) {
  if (!law.holdout.tested) return '';
  return `  (${law.holdout.passed}/${law.holdout.tested} withheld terms predicted)`;
}

/** Side-by-side table of several models. */
export function formatTable(list) {
  const rows = list.map((m) => [String(m.seed), m.pattern.join(' '), String(m.period)]);
  const headers = ['seed', 'pattern', 'period'];
  const widths = headers.map((header, column) =>
    Math.max(header.length, ...rows.map((row) => row[column].length)),
  );
  const line = (cells) =>
    cells.map((cell, column) => cell.padEnd(widths[column])).join('  ').trimEnd();

  return [
    line(headers),
    line(widths.map((width) => '─'.repeat(width))),
    ...rows.map(line),
  ].join('\n');
}
