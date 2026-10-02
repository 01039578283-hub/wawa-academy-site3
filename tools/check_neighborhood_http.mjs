/** Full URL response checks. Local mode serves only the reviewed build on loopback.
 * Vercel's public compiler supplies route regexes; this is not a Vercel deployment.
 * Public mode makes read-only GET/HEAD requests, only when explicitly invoked.
 */
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import https from 'node:https';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(import.meta.url);
const sha = b => createHash('sha256').update(b).digest('hex');
const args = Object.fromEntries(process.argv.slice(2).map(a => {
  const i = a.indexOf('='); return i < 0 ? [a.replace(/^--/, ''), true] : [a.slice(2, i), a.slice(i + 1)];
}));
const mode = args.mode || 'local';
if (!['local', 'public'].includes(mode) || !args.inputs || !args.out) throw Error('Use --mode=local|public --inputs=... --out=...');
const inputs = JSON.parse(fs.readFileSync(args.inputs, 'utf8'));
const output = path.resolve(args.out);
fs.mkdirSync(output, { recursive: true });
const save = (name, data) => fs.writeFileSync(path.join(output, name), JSON.stringify(data, null, 2) + '\n');
if (sha(fs.readFileSync(path.join(root, 'vercel.json'))) !== inputs.configSha256 || sha(fs.readFileSync(path.join(root, 'release-public-manifest.json'))) !== inputs.manifestSha256) throw Error('Configuration or reviewed snapshot changed: refresh audit inputs first');
const files = new Map([...inputs.pages, ...inputs.assets].map(row => [row.file, row]));
const textTypes = /\.(html|css|js|json|xml|txt|svg|webmanifest)$/i;
const mime = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.json': 'application/json; charset=utf-8', '.xml': 'application/xml; charset=utf-8', '.txt': 'text/plain; charset=utf-8', '.svg': 'image/svg+xml', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp', '.avif': 'image/avif', '.gif': 'image/gif', '.ico': 'image/x-icon', '.pdf': 'application/pdf', '.woff': 'font/woff', '.woff2': 'font/woff2', '.webmanifest': 'application/manifest+json' };
const query = '?utm_source=naver&phase11=%ED%99%95%EC%9D%B8&value=a%2Bb&repeat=1&repeat=2';
const cases = [];
for (const row of [...inputs.pages, ...inputs.assets]) cases.push({ kind: 'public-file-get', method: 'GET', request: row.path, status: 200, file: row.file });
for (const row of inputs.pages) {
  cases.push({ kind: 'canonical-head', method: 'HEAD', request: row.path, status: 200, file: row.file });
  cases.push({ kind: 'query-head', method: 'HEAD', request: row.path + query, status: 200, file: row.file });
  cases.push({ kind: 'index-alias', method: 'HEAD', request: row.path + 'index.html' + query, status: 308, location: row.path + query });
  if (row.path !== '/') cases.push({ kind: 'without-slash', method: 'HEAD', request: row.path.slice(0, -1) + query, status: 308, location: row.path + query });
}
for (const row of inputs.assets) cases.push({ kind: 'file-with-slash', method: 'HEAD', request: row.path + '/' + query, status: 308, location: row.path + query });
for (const request of ['/not-a-page-phase11/', '/not-a-page-phase11.html', '/전국센터/없는지역/없는동네/', '/tools/', '/tools/data/neighborhood-seo/centers.json', '/reports/', '/outputs/', '/.env', '/.git/config/', '/vercel.json', '/release-public-manifest.json', '/seo-feed-review.json', '/seo-feed-check.mjs', '/release-public-build.mjs', '/NEIGHBORHOOD_SEO_HANDOFF.md', '/assets/not-a-file-phase11.css', '/SITEMAP.xml']) {
  cases.push({ kind: 'missing-or-private', method: 'GET', request: encodeURI(request), status: 404 });
}
for (const request of ['/not-a-page-phase11', '/.git/config']) cases.push({ kind: 'missing-path-normalization', method: 'HEAD', request, status: 308, location: request + '/', terminalStatus: 404 });
cases.push({ kind: 'missing-index-alias', method: 'HEAD', request: '/not-a-page-phase11/index.html', status: 308, location: '/not-a-page-phase11/', terminalStatus: 404 });

let compiled, server, localConnections = 0, reusedConnections = 0;
function resolve(request) {
  const question = request.indexOf('?');
  const pathname = question < 0 ? request : request.slice(0, question);
  const search = question < 0 ? '' : request.slice(question);
  const headers = {};
  for (const rule of compiled) {
    const match = new RegExp(rule.src).exec(pathname);
    if (!match) continue;
    for (const [key, value] of Object.entries(rule.headers || {})) headers[key.toLowerCase()] = value.replace(/\$(\d+)/g, (_, n) => match[Number(n)] || '');
    if (rule.status >= 300 && rule.status < 400) {
      headers.location += search;
      return { status: rule.status, headers };
    }
    if (!rule.continue) break;
  }
  let decoded;
  try { decoded = decodeURIComponent(pathname); } catch { return { status: 404, headers }; }
  if (!decoded.startsWith('/') || decoded.includes('\\') || decoded.includes('\0') || decoded.split('/').some(p => p === '..' || p === '.')) return { status: 404, headers };
  let name = decoded.slice(1);
  if (!name || name.endsWith('/')) name += 'index.html';
  return { status: files.has(name) ? 200 : 404, headers, file: files.has(name) ? name : undefined };
}

let origin;
if (mode === 'local') {
  if (!args['routing-utils']) throw Error('Local mode needs --routing-utils=... pointing to the pinned private @vercel/routing-utils package');
  const packageRoot = path.resolve(args['routing-utils']);
  const packageInfo = JSON.parse(fs.readFileSync(path.join(packageRoot, 'package.json'), 'utf8'));
  if (packageInfo.name !== '@vercel/routing-utils' || packageInfo.version !== '6.6.0') throw Error('Expected @vercel/routing-utils 6.6.0');
  const config = JSON.parse(fs.readFileSync(path.join(root, 'vercel.json'), 'utf8'));
  if (config.rewrites?.length || config.routes?.length) throw Error('This static checker requires explicit support before adding rewrites or raw routes');
  const result = require(packageRoot).getTransformedRoutes(config);
  if (result.error) throw Error(JSON.stringify(result.error));
  compiled = result.routes;
  if (compiled.some(r => r.has || r.missing || r.dest || r.handle || r.env)) throw Error('Unsupported conditional or rewrite rule');
  save('compiled-vercel-routes.json', { compiler: '@vercel/routing-utils', version: packageInfo.version, configSha256: inputs.configSha256, routes: compiled, error: null });
  const errors = [];
  for (const row of cases) {
    const actual = resolve(row.request);
    if (actual.status !== row.status || (row.location && actual.headers.location !== row.location) || (row.file && actual.file !== row.file)) errors.push({ ...row, actual });
    if (row.status === 200 && /\b(noindex|nofollow|none)\b/i.test(actual.headers['x-robots-tag'] || '')) errors.push({ ...row, message: 'Configured crawl-blocking header' });
    if (row.status === 200 && actual.headers['x-content-type-options'] !== 'nosniff') errors.push({ ...row, message: 'Expected configured nosniff header' });
    if (row.location) {
      const target = resolve(row.location);
      if (target.status !== (row.terminalStatus || 200)) errors.push({ ...row, message: 'Redirect destination does not terminate at its expected status', target });
    }
  }
  save('configured-route-audit.json', { cases: cases.length, errors, errorCount: errors.length, interpretation: 'Official route compiler plus local static filesystem model; not a deployment/CDN observation', deployed: false });
  if (errors.length) throw Error(JSON.stringify(errors.slice(0, 5)));
  console.log('Official route compiler and all URL variants passed:', cases.length);
  const builtRoot = path.resolve(inputs.builtRoot);
  if (builtRoot !== path.join(root, '.public-release')) throw Error('Unexpected build output directory');
  server = http.createServer(async (req, res) => {
    const actual = resolve(req.url);
    // Preview-only noindex and no-store never modify production configuration.
    const headers = { ...actual.headers, 'X-Robots-Tag': 'noindex, nofollow', 'Cache-Control': 'no-store' };
    try {
      if (actual.status !== 200) { res.writeHead(actual.status, { ...headers, 'Content-Length': 0 }); res.end(); return; }
      const raw = req.method === 'HEAD' ? null : await fs.promises.readFile(path.join(builtRoot, actual.file));
      const size = raw?.length ?? (await fs.promises.stat(path.join(builtRoot, actual.file))).size;
      res.writeHead(200, { ...headers, 'Content-Type': mime[path.extname(actual.file).toLowerCase()] || 'application/octet-stream', 'Content-Length': size });
      res.end(raw);
    } catch { res.writeHead(500, { ...headers, 'Content-Length': 0 }); res.end(); }
  });
  server.keepAliveTimeout = 60000;
  server.headersTimeout = 65000;
  server.on('connection', () => localConnections++);
  await new Promise((accept, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', accept); });
  origin = 'http://127.0.0.1:' + server.address().port;
} else {
  if (!args.base || args.base !== inputs.canonicalOrigin) throw Error('Public mode requires the exact reviewed canonical HTTPS origin via --base');
  origin = args.base;
}

const workers = args.workers ? Number(args.workers) : 12;
if (!Number.isInteger(workers) || workers < 1 || workers > 24) throw Error('--workers must be an integer from 1 to 24');
const client = origin.startsWith('https:') ? https : http;
const agent = new client.Agent({ keepAlive: true, maxSockets: workers });
function request(row) {
  return new Promise((accept, reject) => {
    const req = client.request(origin + row.request, { method: row.method, agent, headers: { 'User-Agent': 'Site3-ReadOnly-Release-Check/1.0', 'Accept-Encoding': 'identity' } }, res => {
      const chunks = []; let size = 0;
      res.on('data', b => { size += b.length; if (size > 16 * 1024 * 1024) { res.destroy(Error('Response too large')); return; } chunks.push(b); });
      res.on('error', reject);
      res.on('end', () => { if (req.reusedSocket) reusedConnections++; accept({ status: res.statusCode, headers: res.headers, body: Buffer.concat(chunks) }); });
    });
    req.setTimeout(30000, () => req.destroy(Error('Request timeout'))); req.on('error', reject); req.end();
  });
}
const normalizedSha = b => sha(Buffer.from(b.toString('utf8').replaceAll('\r\n', '\n')));
const counters = {}, failures = [], results = []; let cursor = 0, completed = 0;
try {
  await Promise.all(Array.from({ length: workers }, async () => {
    while (cursor < cases.length) {
      const row = cases[cursor++]; const problems = [];
      try {
        const actual = await request(row);
        if (actual.status !== row.status) problems.push('HTTP status');
        if (row.location) {
          const target = new URL(actual.headers.location || '/', origin);
          if (target.origin !== origin || target.pathname + target.search !== row.location) problems.push('Redirect target/query');
        }
        if (row.status === 200) {
          const contentType = String(actual.headers['content-type'] || '').toLowerCase();
          const ext = path.extname(row.file).toLowerCase();
          const allowedMime = ext === '.xml' ? ['application/xml', 'text/xml', 'application/rss+xml'] : ext === '.js' ? ['application/javascript', 'text/javascript'] : ext === '.ico' ? ['image/x-icon', 'image/vnd.microsoft.icon'] : [mime[ext]?.split(';')[0]];
          if (!allowedMime.some(v => v && contentType.split(';')[0].trim() === v)) problems.push('Content-Type');
          if (actual.headers['x-content-type-options'] !== 'nosniff') problems.push('nosniff');
          if (mode === 'public' && /\b(noindex|nofollow|none)\b/i.test(String(actual.headers['x-robots-tag'] || ''))) problems.push('Public X-Robots-Tag');
          if (mode === 'local' && actual.headers['x-robots-tag'] !== 'noindex, nofollow') problems.push('Local preview safety header');
          if (row.method === 'GET' && sha(actual.body) !== files.get(row.file).builtSha256) {
            if (!(mode === 'public' && textTypes.test(row.file) && files.get(row.file).builtTextSha256 === normalizedSha(actual.body))) problems.push('Public file content hash');
          }
          if (row.method === 'HEAD' && actual.body.length !== 0) problems.push('HEAD body');
        }
        counters[row.kind] = (counters[row.kind] || 0) + 1;
        results.push({ kind: row.kind, method: row.method, request: row.request, status: actual.status, location: actual.headers.location || undefined, bytes: actual.body.length, errors: problems });
      } catch (error) { problems.push(error.message); }
      if (problems.length) failures.push({ ...row, errors: problems });
      completed++;
      if (completed % 5000 === 0) console.log('HTTP checks completed:', completed, '/', cases.length);
    }
  }));
} finally {
  agent.destroy();
  if (server) await new Promise(accept => server.close(accept));
}
save('url-response-results.json', results.sort((a, b) => a.request.localeCompare(b.request) || a.kind.localeCompare(b.kind)));
const summary = { mode, origin, inputsSha256: sha(fs.readFileSync(args.inputs)), manifestSha256: inputs.manifestSha256, configSha256: inputs.configSha256, expectedCases: cases.length, completedCases: completed, successfulRequests: results.length, byKind: counters, localConnections, reusedConnections, publicFilesGet: inputs.pages.length + inputs.assets.length, htmlPages: inputs.pages.length, failures, errorCount: failures.length, localServerClosed: Boolean(server), verifiedAt: new Date().toISOString(), scope: mode === 'local' ? 'Loopback HTTP, compiled vercel.json routing, exact reviewed build files; actual Vercel/CDN still requires postdeployment checks' : 'Actual public read-only HTTP responses and reviewed content comparison', deployedByThisTool: false };
save('http-verification.json', summary);
console.log(JSON.stringify({ mode, completed, errorCount: failures.length, byKind: counters, deployed: false }));
if (failures.length) process.exitCode = 1;
