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
import { formatModel, formatTable } from './src/format.js';

const USAGE = `ai-tree — number pattern modeling

usage
  node cli.js <number...> [options]

options
  --mod <n>        ring size, default 9 (9 gives digital roots)
  --factor <n>     orbit multiplier, default 2
  --depth <n>      tree depth, default 4
  --repeats <n>    how many times to print the repeated pattern, default 2
  --table          one row per number instead of full reports
  --families <a-b> group every number in the range by the pattern it produces
  --json           emit JSON
  --help

examples
  node cli.js 1 4 5
  node cli.js 1 4 5 --table
  node cli.js 7 --mod 12 --factor 3
  node cli.js --families 1-27`;

function parseArgs(argv) {
  const options = {};
  const seeds = [];
  let table = false;
  let json = false;
  let range = null;
  let repeats = 2;

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
      default: {
        if (arg.startsWith('-')) throw new Error(`unknown option: ${arg}`);
        seeds.push(readNumber(arg, 'number'));
      }
    }
  }
  return { seeds, options, table, json, range, repeats, help: false };
}

function readNumber(raw, name) {
  const value = Number(raw);
  if (!Number.isInteger(value)) throw new Error(`${name} expects an integer, got: ${raw}`);
  return value;
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

  if (args.help || (!args.seeds.length && !args.range)) {
    console.log(USAGE);
    return 0;
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

try {
  process.exitCode = main(process.argv.slice(2));
} catch (error) {
  console.error(`error: ${error.message}\n`);
  console.error(USAGE);
  process.exitCode = 1;
}
