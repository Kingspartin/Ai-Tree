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
