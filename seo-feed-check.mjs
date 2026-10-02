/** Non-mutating, dependency-free source/output gate for reviewed pages and feeds.
 * XML, canonical and date semantics are independently reviewed by lxml locally.
 * This build uses the resulting private ledger, never auto-approves new hashes.
 */
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';

const PROJECT = path.dirname(fileURLToPath(import.meta.url));
const DOMAIN = 'https://xn--sp5b72l1taf0p.com';
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
class CheckError extends Error {
  constructor(code, message) { super(message); this.code = code; }
}
function requireCheck(condition, code, message) {
  if (!condition) throw new CheckError(code, message);
}
function text(bytes) {
  const decoded = bytes.toString('utf8');
  requireCheck(Buffer.from(decoded, 'utf8').equals(bytes), 'INVALID_UTF8', 'UTF-8 파일을 확인하세요.');
  return decoded.replaceAll('\r\n', '\n');
}
function safeName(name) {
  requireCheck(typeof name === 'string' && name && !name.includes('\\') && !name.includes('\0') && !name.split('/').some(p => !p || p.startsWith('.')) && !path.isAbsolute(name), 'UNSAFE_PATH', '안전하지 않은 공개 파일 경로: ' + name);
  requireCheck(!/^(?:tools|reports|outputs|work|tmp)\//i.test(name) && !/\.(?:xlsx|xls|csv|zip)$/i.test(name), 'PRIVATE_PUBLIC_FILE', '비공개 파일이 공개 목록에 있습니다: ' + name);
}
async function checkedRead(root, name, checkedDirectories) {
  safeName(name);
  const parts = name.split('/');
  for (let i = 0; i < parts.length - 1; i++) {
    const directory = path.join(root, ...parts.slice(0, i + 1));
    if (!checkedDirectories.has(directory)) {
      const stat = await fs.promises.lstat(directory);
      requireCheck(stat.isDirectory() && !stat.isSymbolicLink(), 'SYMLINK', '공개 디렉터리 링크는 허용되지 않습니다: ' + name);
      checkedDirectories.add(directory);
    }
  }
  const file = path.join(root, ...parts);
  const stat = await fs.promises.lstat(file);
  requireCheck(stat.isFile() && !stat.isSymbolicLink(), 'SYMLINK', '공개 파일 링크는 허용되지 않습니다: ' + name);
  return fs.promises.readFile(file);
}
function checkedJson(file) {
  requireCheck(fs.lstatSync(file).isFile() && !fs.lstatSync(file).isSymbolicLink(), 'REVIEW_INPUT_INVALID', '검토 입력을 확인하세요.');
  return JSON.parse(fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));
}
function validateLedger(review, manifest) {
  requireCheck(review.schemaVersion === 1 && review.domain === DOMAIN && review.pages && typeof review.pages === 'object', 'REVIEW_INVALID', 'RSS·사이트맵 검토 입력 버전 또는 도메인을 확인하세요.');
  const selected = new Set(Object.keys(manifest.files));
  for (const name of selected) safeName(name);
  requireCheck(!selected.has('seo-feed-review.json') && !selected.has('seo-feed-check.mjs'), 'PRIVATE_PUBLIC_FILE', '검토 입력과 검사 도구는 공개 목록에서 제외해야 합니다.');
  const names = [...selected].filter(n => n.endsWith('.html')).sort();
  requireCheck(JSON.stringify(names) === JSON.stringify(Object.keys(review.pages).sort()) && review.htmlPages === names.length && review.sitemap.urls === names.length, 'SITEMAP_SCOPE_CHANGED', '공개 HTML 범위와 사이트맵 검토 범위가 다릅니다.');
  requireCheck(names.length > 0 && names.length < 50000, 'SITEMAP_LIMIT', '검토할 HTML 범위를 확인하세요.');
  const canonicalSet = new Set();
  for (const name of names) {
    const record = review.pages[name]; const url = new URL(record.canonical);
    requireCheck(url.origin === DOMAIN && !url.search && !url.hash && url.pathname.endsWith('/') && !/%(?:2f|5c|00)/i.test(url.pathname), 'REVIEW_INVALID', '검토 canonical을 확인하세요: ' + name);
    const decoded = decodeURIComponent(url.pathname);
    const expected = decoded === '/' ? 'index.html' : decoded.slice(1) + 'index.html';
    requireCheck(expected === name && !canonicalSet.has(record.canonical), 'REVIEW_INVALID', '검토 URL 중복 또는 경로 불일치: ' + name);
    canonicalSet.add(record.canonical);
    requireCheck(/^[a-f0-9]{64}$/.test(record.sourceTextSha256) && /^[a-f0-9]{64}$/.test(record.builtTextSha256), 'REVIEW_INVALID', '검토 본문 해시를 확인하세요: ' + name);
  }
  requireCheck(review.sitemap.file === 'sitemap.xml' && review.rss.file === 'rss.xml' && selected.has('sitemap.xml') && selected.has('rss.xml'), 'REVIEW_INVALID', '피드 공개 파일을 확인하세요.');
  requireCheck(/^[a-f0-9]{64}$/.test(review.sitemap.textSha256) && /^[a-f0-9]{64}$/.test(review.rss.textSha256), 'REVIEW_INVALID', '피드 검토 해시를 확인하세요.');
  requireCheck(Array.isArray(review.rss.items) && review.rss.items.length > 0, 'REVIEW_INVALID', '검토된 RSS 항목이 없습니다.');
  const urls = new Set(); const guids = new Set();
  for (const item of review.rss.items) {
    requireCheck(review.pages[item.file]?.canonical === item.link && !urls.has(item.link) && !guids.has(item.guid), 'REVIEW_INVALID', 'RSS 항목·canonical·사이트맵 연결을 확인하세요.');
    urls.add(item.link); guids.add(item.guid);
  }
  return {names, selected};
}
function outputFiles(root) {
  const found = new Set(); const pending = [root];
  while (pending.length) {
    const directory = pending.pop();
    for (const entry of fs.readdirSync(directory, {withFileTypes: true})) {
      requireCheck(!entry.isSymbolicLink(), 'SYMLINK', '출력에 파일 시스템 링크가 있습니다.');
      const full = path.join(directory, entry.name);
      if (entry.isDirectory()) pending.push(full);
      else if (entry.isFile()) found.add(path.relative(root, full).replaceAll('\\', '/'));
      else throw new CheckError('OUTPUT_SET_CHANGED', '예상하지 못한 출력 파일 형식입니다.');
    }
  }
  return found;
}

export async function checkFeeds({root = PROJECT, manifestPath = path.join(PROJECT, 'release-public-manifest.json'), reviewPath = path.join(PROJECT, 'seo-feed-review.json'), builtOutput = false} = {}) {
  root = path.resolve(root);
  const review = checkedJson(reviewPath); const manifest = checkedJson(manifestPath);
  const {names, selected} = validateLedger(review, manifest);
  requireCheck(fs.lstatSync(root).isDirectory() && !fs.lstatSync(root).isSymbolicLink(), 'SYMLINK', '검사할 루트 디렉터리를 확인하세요.');
  const errors = []; const directories = new Set();
  const error = (code, file, message) => errors.push({code, file, message});
  if (builtOutput) {
    const actual = outputFiles(root);
    for (const name of actual) if (!selected.has(name)) error('PRIVATE_OR_UNEXPECTED_OUTPUT', name, '검토하지 않은 공개 출력 파일입니다.');
    for (const name of selected) if (!actual.has(name)) error('MISSING_OUTPUT', name, '검토한 공개 출력 파일이 없습니다.');
  }
  for (const [name, code, approvedHash] of [['rss.xml', 'RSS_CHANGED', review.rss.textSha256], ['sitemap.xml', 'SITEMAP_CHANGED', review.sitemap.textSha256]]) {
    try {
      const raw = await checkedRead(root, name, directories);
      if (raw.byteLength >= 10000000) error('NAVER_FEED_LIMIT', name, '네이버 피드 용량 제한을 초과했습니다.');
      if (digest(Buffer.from(text(raw))) !== approvedHash) error(code, name, 'RSS·사이트맵 XML 또는 내용이 마지막 검토 이후 변경되었습니다.');
    } catch (e) { error(e.code ?? 'MISSING_FEED', name, e.message); }
  }
  let cursor = 0;
  await Promise.all(Array.from({length: 8}, async () => {
    while (cursor < names.length) {
      const name = names[cursor++];
      try {
        const bytes = await checkedRead(root, name, directories);
        const approved = review.pages[name][builtOutput ? 'builtTextSha256' : 'sourceTextSha256'];
        if (digest(Buffer.from(text(bytes))) !== approved) error(builtOutput ? 'OUTPUT_HTML_CHANGED' : 'SOURCE_HTML_CHANGED', name, '본문·제목·canonical·변경일 검토가 필요합니다. RSS에 포함된 페이지라면 전체 본문도 맞춰 주세요.');
      } catch (e) { error(e.code ?? 'MISSING_HTML', name, e.message); }
    }
  }));
  errors.sort((a, b) => a.file.localeCompare(b.file) || a.code.localeCompare(b.code));
  return {ok: errors.length === 0, mode: builtOutput ? 'built-output' : 'source', htmlPages: names.length, sitemapUrls: review.sitemap.urls, rssItems: review.rss.items.length, reviewedAt: review.reviewedAt, sourceAndFeedReviewedTogether: true, automaticContentOrDateChanges: false, publicFiles: selected.size, errorCount: errors.length, errors: errors.slice(0, 10), hint: errors.length ? '본문·RSS·사이트맵을 맞추고 공개 manifest를 검토한 뒤, 로컬에서 python -X utf8 tools/review_seo_feeds.py를 실행하세요. 해시만 고쳐서 검사를 건너뛰지 마세요.' : undefined};
}

function options(args) {
  const result = {}; const seen = new Set();
  for (const argument of args) {
    const [key, ...parts] = argument.split('=');
    requireCheck(!seen.has(key), 'ARGUMENT', '중복 검사 옵션: ' + key); seen.add(key);
    if (key === '--built-output' && !parts.length) result.builtOutput = true;
    else if (['--root', '--manifest', '--review'].includes(key) && parts.join('=')) {
      result[{'--root': 'root', '--manifest': 'manifestPath', '--review': 'reviewPath'}[key]] = path.resolve(PROJECT, parts.join('='));
    } else throw new CheckError('ARGUMENT', '알 수 없는 검사 옵션: ' + argument);
  }
  return result;
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const result = await checkFeeds(options(process.argv.slice(2)));
    console.log(JSON.stringify(result));
    if (!result.ok) process.exitCode = 1;
  } catch (e) {
    console.error(JSON.stringify({ok: false, errorCount: 1, errors: [{code: e.code ?? 'CHECK_INPUT_MISSING_OR_INVALID', message: e.message}], automaticContentOrDateChanges: false}));
    process.exitCode = 1;
  }
}
