// Local static server that applies the headers from vercel.json, so CSP problems show up before deploy.
import http from 'node:http'; import { readFile, stat } from 'node:fs/promises'; import { extname, join, normalize } from 'node:path';
import { fileURLToPath } from 'node:url';
const root = normalize(fileURLToPath(new URL('..', import.meta.url))).replace(/[\/]$/, ''), cfg = JSON.parse(await readFile(new URL('../vercel.json', import.meta.url), 'utf8'));
const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg', '.mp4': 'video/mp4', '.svg': 'image/svg+xml', '.txt': 'text/plain' };
const rx = s => new RegExp('^' + s.replace(/\(\.\*\)/g, '.*') + '$');
http.createServer(async (req, res) => {
  let p = decodeURIComponent(new URL(req.url, 'http://x').pathname); const path = p;
  for (const h of cfg.headers) if (rx(h.source).test(path)) for (const { key, value } of h.headers) res.setHeader(key, value);
  if (p.endsWith('/')) p += 'index.html'; if (!extname(p)) p += '.html';
  const f = normalize(join(root, p)); if (!f.startsWith(root)) { res.writeHead(403); return res.end(); }
  try { await stat(f); res.setHeader('Content-Type', types[extname(f)] || 'application/octet-stream'); res.end(await readFile(f)); }
  catch { res.writeHead(404); res.end('not found'); }
}).listen(5173, () => console.log('http://localhost:5173'));
