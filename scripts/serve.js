#!/usr/bin/env node
/**
 * Minimal static file server for the visualizer — no dependencies.
 *
 *   npm run web     then open http://localhost:8080
 */

import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { extname, join, normalize, sep } from 'node:path';

const ROOT = new URL('..', import.meta.url).pathname.replace(/\/$/, '');
const PORT = Number(process.env.PORT) || 8080;

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
};

const server = createServer(async (request, response) => {
  const url = new URL(request.url, `http://${request.headers.host}`);
  const requested = url.pathname === '/' ? '/web/index.html' : url.pathname;
  const path = join(ROOT, normalize(requested).replace(/^(\.\.[/\\])+/, ''));

  if (!path.startsWith(ROOT + sep) && path !== ROOT) {
    response.writeHead(403).end('forbidden');
    return;
  }

  try {
    const body = await readFile(path);
    response.writeHead(200, { 'content-type': TYPES[extname(path)] ?? 'application/octet-stream' });
    response.end(body);
  } catch {
    response.writeHead(404, { 'content-type': 'text/plain' }).end('not found');
  }
});

server.listen(PORT, () => {
  console.log(`ai-tree visualizer → http://localhost:${PORT}`);
});
