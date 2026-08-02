#!/usr/bin/env node
/**
 * Command line front end.
 *
 *   node cli.js 1 4 5
 *   node cli.js 1 4 5 --table
 *   node cli.js 7 --mod 12 --factor 3 --depth 3
 *   node cli.js --families 1-20
 */

import { model, families } from './src/model.js';
import { discover } from './src/discover.js';
import { formatModel, formatTable, formatDiscovery } from './src/format.js';

const USAGE = `ai-tree — number pattern modeling

usage
  node cli.js <number...> [options]         model each number
  node cli.js --fit <sequence> [options]    find the law behind a sequence

options
  --mod <n>        ring size, default 9 (9 gives digital roots)
  --factor <n>     orbit multiplier, default 2
  --depth <n>      tree depth, default 4
  --repeats <n>    how many times to print the repeated pattern, default 2
  --table          one row per number instead of full reports
  --families <a-b> group every number in the range by the pattern it produces
  --fit <seq>      discover the rule mapping each term of a sequence to the next
  --next <n>       how many terms to predict, default 6
  --all            with --fit, list every method that fitted
  --json           emit JSON
  --help

examples
  node cli.js 1 4 5
  node cli.js 1 4 5 --table
  node cli.js 7 --mod 12 --factor 3
  node cli.js --families 1-27
  node cli.js --fit 1,1,2,3,5,8
  node cli.js --fit "3 1 4 3 1 4" --all`;

function parseArgs(argv) {
  const options = {};
  const seeds = [];
  let table = false;
  let json = false;
  let range = null;
  let repeats = 2;
  let sequence = null;
  let next = 6;
  let all = false;

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    switch (arg) {
      case '--help':
      case '-h':
        return { help: true };
      case '--table':
        table = true;
        break;
      case '--json':
        json = true;
        break;
      case '--mod':
        options.modulus = readNumber(argv[++i], '--mod');
        break;
      case '--factor':
        options.factor = readNumber(argv[++i], '--factor');
        break;
      case '--depth':
        options.depth = readNumber(argv[++i], '--depth');
        break;
      case '--repeats':
        repeats = readNumber(argv[++i], '--repeats');
        break;
      case '--families':
        range = readRange(argv[++i]);
        break;
      case '--fit':
        sequence = readSequence(argv[++i]);
        break;
      case '--next':
        next = readNumber(argv[++i], '--next');
        break;
      case '--all':
        all = true;
        break;
      default: {
        if (arg.startsWith('-')) throw new Error(`unknown option: ${arg}`);
        seeds.push(readNumber(arg, 'number'));
      }
    }
  }
  return { seeds, options, table, json, range, repeats, sequence, next, all, help: false };
}

function readNumber(raw, name) {
  const value = Number(raw);
  if (!Number.isInteger(value)) throw new Error(`${name} expects an integer, got: ${raw}`);
  return value;
}

/** `1,1,2,3` or `"1 1 2 3"` — commas, spaces or both. */
function readSequence(raw) {
  const parts = String(raw ?? '')
    .split(/[\s,]+/)
    .filter(Boolean);
  if (parts.length < 2) throw new Error('--fit needs at least 2 terms, e.g. 1,1,2,3,5');
  return parts.map((part) => {
    const value = Number(part);
    if (!Number.isFinite(value)) throw new Error(`--fit expects numbers, got: ${part}`);
    return value;
  });
}

function readRange(raw) {
  const match = /^(-?\d+)-(-?\d+)$/.exec(raw ?? '');
  if (!match) throw new Error(`--families expects a range like 1-20, got: ${raw}`);
  const [from, to] = [Number(match[1]), Number(match[2])];
  if (to < from) throw new Error('--families range must ascend');
  return Array.from({ length: to - from + 1 }, (_, i) => from + i);
}

function main(argv) {
  const args = parseArgs(argv);

  if (args.help || (!args.seeds.length && !args.range && !args.sequence)) {
    console.log(USAGE);
    return 0;
  }

  if (args.sequence) {
    const result = discover(args.sequence);
    if (args.json) {
      console.log(JSON.stringify(serialize(result, args.next), null, 2));
      return 0;
    }
    console.log(formatDiscovery(result, { next: args.next, all: args.all }));
    // an overfit fit is not a finding — exit non-zero so scripts can tell
    return result.law && result.confidence !== 'overfit' ? 0 : 1;
  }

  if (args.range) {
    const groups = families(args.range, args.options);
    if (args.json) {
      console.log(JSON.stringify([...groups].map(([signature, seeds]) => ({ signature, seeds })), null, 2));
      return 0;
    }
    for (const [signature, seeds] of groups) {
      const pattern = signature.split('/')[3].split('-').join(' ');
      console.log(`${seeds.join(', ')}\n  ${pattern}\n`);
    }
    return 0;
  }

  const built = args.seeds.map((seed) => model(seed, args.options));

  if (args.json) {
    console.log(JSON.stringify(built.map(strip), null, 2));
    return 0;
  }

  if (args.table) {
    console.log(formatTable(built));
    return 0;
  }

  console.log(built.map((m) => formatModel(m, { repeats: args.repeats })).join('\n\n'));
  return 0;
}

/** Drop the function members so a model can be serialized. */
function strip(m) {
  const { at, take, ...rest } = m;
  return rest;
}

/** Same idea for a discovery result: keep the findings, drop the machinery. */
function serialize(result, next) {
  const plain = ({ term, termExact, next: _next, ...rest }, count) => ({
    ...rest,
    predicted: _next(count),
  });
  return {
    input: result.input,
    confidence: result.confidence,
    tried: result.tried,
    law: result.law ? plain(result.law, next) : null,
    candidates: result.candidates.map((candidate) => plain(candidate, next)),
  };
}

try {
  process.exitCode = main(process.argv.slice(2));
} catch (error) {
  console.error(`error: ${error.message}\n`);
  console.error(USAGE);
  process.exitCode = 1;
}
