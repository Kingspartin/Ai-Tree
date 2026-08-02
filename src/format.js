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

  if (law.uniform) {
    lines.push('  uniform   yes — the same f applied to each number');
  } else {
    const uniform = result.candidates.find(
      (candidate) => candidate.uniform && !candidate.overfit && !candidate.projection,
    );
    lines.push(
      uniform
        ? `  uniform   this law reads the index, but ${uniform.describe} works at every step too`
        : '  uniform   no — this law reads the position, not just the previous number',
    );
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

/**
 * Report for a uniform step rule: one f, applied to each number the same way
 * every time, plus the loop that iterating it settles into.
 * @param {import('./discover.js').stepRule} result
 */
export function formatStep(result, { next = 6, all = false } = {}) {
  const lines = [`sequence  ${result.input.join(' ')}`, ''];

  if (!result.rule) {
    if (result.impossible) {
      const { value, successors, at } = result.impossible;
      lines.push('  no rule of the form f(x) — and there cannot be one');
      lines.push(`  because   ${value} is followed by ${successors[0]} at index ${at[0]}`);
      lines.push(`            and by ${successors[1]} at index ${at[1]}`);
      lines.push('            so the next term is not decided by the current one alone');
    } else {
      lines.push(`  no rule of the form f(x) found — ${result.tried} shapes tried`);
    }
    return lines.join('\n');
  }

  const rule = result.rule;
  lines.push(`  rule      ${rule.describe}`);
  lines.push(`  applied   to every number, the same way, at every step`);
  lines.push(`  method    ${rule.method}   (${result.confidence})`);
  lines.push(`  next      ${result.next(next).join(' ')}`);

  const cycle = result.cycle;
  if (cycle?.closes) {
    const lead = cycle.lead.length ? `${cycle.lead.join(' ')} → then ` : '';
    lines.push(`  repeats   ${lead}${cycle.cycle.join(' ')} ↺   (period ${cycle.period})`);
  } else if (cycle) {
    lines.push(`  repeats   never — ${cycle.reason}`);
  }
  if (rule.projection) {
    lines.push(`  note      predicts the ${rule.projection}, not the raw value`);
  }

  const others = result.candidates.slice(1);
  if (all && others.length) {
    lines.push('', `  ${others.length} other rule${others.length === 1 ? '' : 's'}`);
    for (const candidate of others) {
      lines.push(
        `    ${candidate.method.padEnd(22)} ${String(candidate.score).padStart(6)}  ${candidate.describe}`,
      );
    }
  } else if (others.length) {
    lines.push('', `  also fits: ${others.map((c) => c.method).join(', ')}`);
  }
  return lines.join('\n');
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
