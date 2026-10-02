"""Behavioral failure tests in private disposable fixtures, never authoring HTML."""
import contextlib, copy, hashlib, io, json, shutil, subprocess, sys, uuid
from pathlib import Path
from lxml import etree, html
from review_seo_feeds import ROOT, DOMAIN, digest, normalized, review

OUT = Path(r'C:\Users\1992k\Desktop\CodexData\outputs\site3-neighborhood-phase10-20261002')
POWERSHELL = Path(r'C:\Users\1992k\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe')
WORK = OUT / ('feed-check-fixtures-' + uuid.uuid4().hex[:8])

def manifest(root):
    file = root / 'release-public-manifest.json'; data = json.loads(file.read_text('utf-8'))
    for name in data['files']:
        if (root / name).is_file():
            raw = (root / name).read_bytes(); data['files'][name] = digest(raw); data['textSha256'][name] = digest(normalized(raw).encode('utf-8'))
    file.write_text(json.dumps(data, ensure_ascii=False), 'utf-8')

def tree_hashes(root):
    return {p.relative_to(root).as_posix(): digest(p.read_bytes()) for p in root.rglob('*') if p.is_file()}

def gate(root, output=False):
    command = ['node', 'seo-feed-check.mjs'] + (['--root=.public-release', '--built-output'] if output else [])
    before = tree_hashes(root)
    done = subprocess.run(command, cwd=root, capture_output=True)
    assert before == tree_hashes(root), 'The checker must not mutate files'
    text = (done.stdout + done.stderr).decode('utf-8')
    result = json.loads(text.strip().splitlines()[-1])
    return done.returncode, result

def main():
    assert WORK.resolve().is_relative_to(OUT.resolve()) and not WORK.exists()
    WORK.mkdir(); baseline = WORK / 'baseline'; baseline.mkdir()
    actual = json.loads((ROOT / 'seo-feed-review.json').read_text('utf-8'))
    chosen = [actual['rss']['items'][0], actual['rss']['items'][32]]
    names = [item['file'] for item in chosen] + [name for name, r in actual['pages'].items() if r['sitemapLastmod'] == '2026-07-31'][:1]
    assert len(set(names)) == 3
    for name in names:
        (baseline / name).parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(ROOT / name, baseline / name)
    sitemap = etree.parse(str(ROOT / 'sitemap.xml')); original = list(sitemap.getroot())
    for element in original:
        if element.findtext('{*}loc') not in {actual['pages'][name]['canonical'] for name in names}:
            sitemap.getroot().remove(element)
    (baseline / 'sitemap.xml').write_bytes(etree.tostring(sitemap, encoding='UTF-8', xml_declaration=True))
    rss = etree.parse(str(ROOT / 'rss.xml')); channel = rss.find('channel')
    for item in list(channel.findall('item')):
        if item.findtext('link') not in {x['link'] for x in chosen}:
            channel.remove(item)
    (baseline / 'rss.xml').write_bytes(etree.tostring(rss, encoding='UTF-8', xml_declaration=True))
    public = names + ['rss.xml', 'sitemap.xml', 'robots.txt']
    shutil.copyfile(ROOT / 'robots.txt', baseline / 'robots.txt')
    data = {'sitemapPages': 3, 'files': {name: digest((baseline / name).read_bytes()) for name in public}, 'textSha256': {name: digest(normalized((baseline / name).read_bytes()).encode('utf-8')) for name in public}}
    (baseline / 'release-public-manifest.json').write_text(json.dumps(data, ensure_ascii=False), 'utf-8')
    for name in ['seo-feed-check.mjs', 'release-public-build.mjs', 'wawa-analytics-build.mjs', 'seo-descriptions.mjs', 'seo-descriptions.json', 'vercel.json']:
        shutil.copyfile(ROOT / name, baseline / name)
    with contextlib.redirect_stdout(io.StringIO()):
        review(baseline)
    code, value = gate(baseline); assert code == 0 and value['ok']
    records = [{'case': 'reviewed baseline source', 'passed': True, 'checker': value}]
    command = json.loads((baseline / 'vercel.json').read_text('utf-8'))['buildCommand']
    build = subprocess.run([str(POWERSHELL), '-NoProfile', '-Command', command], cwd=baseline, capture_output=True)
    (OUT / 'fixture-normal-build.log').write_bytes(build.stdout + build.stderr)
    assert build.returncode == 0, (build.stdout + build.stderr).decode('utf-8')
    code, value = gate(baseline, True); assert code == 0 and value['ok']
    records.append({'case': 'actual configured build with expected tracker insertion', 'passed': True, 'checker': value})
    def case(label, mutate, expected, output=False, reject_review=False, stop_build=False):
        target = WORK / ('case-' + str(len(records))); shutil.copytree(baseline, target)
        mutate(target); manifest(target)
        before_ledger = (target / 'seo-feed-review.json').read_bytes() if (target / 'seo-feed-review.json').exists() else None
        code, result = gate(target, output)
        assert code != 0 and any(e['code'] == expected for e in result['errors']), (label, result)
        item = {'case': label, 'passed': True, 'expectedFailureCode': expected, 'checker': result, 'sourceAndOutputUntouchedByChecker': True}
        if reject_review:
            failed = False
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    review(target)
            except (AssertionError, etree.XMLSyntaxError, ValueError) as exc:
                failed = True; item['reviewFailure'] = str(exc)
            assert failed and (target / 'seo-feed-review.json').read_bytes() == before_ledger
            item['localReviewRejectsMismatchWithoutWritingLedger'] = True
        if stop_build:
            before = tree_hashes(target / '.public-release')
            rejected = subprocess.run([str(POWERSHELL), '-NoProfile', '-Command', command], cwd=target, capture_output=True)
            (OUT / 'fixture-rejected-build.log').write_bytes(rejected.stdout + rejected.stderr)
            assert rejected.returncode != 0 and before == tree_hashes(target / '.public-release')
            assert b'"privateSourcesIncluded"' not in rejected.stdout  # Public copier was never invoked.
            item['actualConfiguredBuildStoppedBeforeOutputMutation'] = True
        records.append(item)
        print('Passed failure scenario:', label, flush=True)
    def mutate_xml(root, filename, fn):
        file = root / filename; tree = etree.parse(str(file)); fn(tree.getroot()); file.write_bytes(etree.tostring(tree, encoding='UTF-8', xml_declaration=True))
    def change_html(root):
        file = root / names[0]; value = file.read_text('utf-8'); assert '<h1>' in value
        file.write_text(value.replace('<h1>', '<h1>제목 변경 ', 1), 'utf-8')
    case('edited page after refreshing public manifest, stale RSS', change_html, 'SOURCE_HTML_CHANGED', reject_review=True, stop_build=True)
    case('RSS title no longer matches H1', lambda r: mutate_xml(r, 'rss.xml', lambda x: setattr(x.find('channel/item/title'), 'text', '다른 제목')), 'RSS_CHANGED', reject_review=True)
    case('RSS full body replaced with a short summary', lambda r: mutate_xml(r, 'rss.xml', lambda x: setattr(x.find('channel/item/description'), 'text', '간단한 요약입니다.')), 'RSS_CHANGED', reject_review=True)
    case('well-formed RSS with invented original publication date', lambda r: mutate_xml(r, 'rss.xml', lambda x: setattr(x.find('channel/item/pubDate'), 'text', 'Tue, 22 Sep 2026 00:00:00 +0900')), 'RSS_CHANGED', reject_review=True)
    case('RSS item GUID changed', lambda r: mutate_xml(r, 'rss.xml', lambda x: setattr(x.find('channel/item/guid'), 'text', 'replacement-guid')), 'RSS_CHANGED', reject_review=True)
    case('RSS item outside the verified domain', lambda r: mutate_xml(r, 'rss.xml', lambda x: setattr(x.find('channel/item/link'), 'text', 'https://example.invalid/')), 'RSS_CHANGED', reject_review=True)
    case('malformed RSS XML', lambda r: (r / 'rss.xml').write_text('<rss><channel>', 'utf-8'), 'RSS_CHANGED', reject_review=True)
    case('sitemap missing a retained page', lambda r: mutate_xml(r, 'sitemap.xml', lambda x: x.remove(x[0])), 'SITEMAP_CHANGED', reject_review=True)
    case('duplicate sitemap URL', lambda r: mutate_xml(r, 'sitemap.xml', lambda x: x.append(copy.deepcopy(x[0]))), 'SITEMAP_CHANGED', reject_review=True)
    case('sitemap modification date differs from page', lambda r: mutate_xml(r, 'sitemap.xml', lambda x: setattr(x.find('{*}url/{*}lastmod'), 'text', '2026-08-01')), 'SITEMAP_CHANGED', reject_review=True)
    case('sitemap wrong domain', lambda r: mutate_xml(r, 'sitemap.xml', lambda x: setattr(x.find('{*}url/{*}loc'), 'text', 'https://example.invalid/')), 'SITEMAP_CHANGED', reject_review=True)
    case('missing public HTML', lambda r: (r / names[0]).unlink(), 'ENOENT')
    case('missing private review ledger', lambda r: (r / 'seo-feed-review.json').unlink(), 'ENOENT')
    def add_private(root):
        file = root / '.public-release/seo-feed-review.json'; shutil.copyfile(root / 'seo-feed-review.json', file)
    case('private review ledger leaked into output', add_private, 'PRIVATE_OR_UNEXPECTED_OUTPUT', output=True)
    case('postprocessor changed built HTML', lambda r: (r / '.public-release' / names[0]).write_text('unexpected changed page', 'utf-8'), 'OUTPUT_HTML_CHANGED', output=True)
    case('postprocessor changed built RSS', lambda r: (r / '.public-release/rss.xml').write_text('changed RSS', 'utf-8'), 'RSS_CHANGED', output=True)
    def unsafe_manifest(root):
        file = root / 'release-public-manifest.json'; value = json.loads(file.read_text('utf-8')); value['files']['../outside.html'] = '0' * 64; file.write_text(json.dumps(value), 'utf-8')
    # The negative fixture is read-only; the checker rejects the path before IO.
    target = WORK / 'unsafe-path'; shutil.copytree(baseline, target); unsafe_manifest(target)
    code, result = gate(target); assert code != 0 and result['errors'][0]['code'] == 'UNSAFE_PATH'
    records.append({'case': 'manifest path outside project', 'passed': True, 'checker': result})
    target = WORK / 'crlf'; shutil.copytree(baseline, target)
    for name in public:
        value = normalized((target / name).read_bytes()); (target / name).write_bytes(value.replace('\n', '\r\n').encode('utf-8'))
    manifest(target); code, result = gate(target); assert code == 0 and result['ok']
    records.append({'case': 'Windows CRLF and Linux LF checkout compatibility', 'passed': True, 'checker': result})
    before = (baseline / 'seo-feed-review.json').read_bytes()
    with contextlib.redirect_stdout(io.StringIO()):
        review(baseline)
    assert (baseline / 'seo-feed-review.json').read_bytes() == before
    records.append({'case': 'review refresh unchanged, timestamp and bytes preserved', 'passed': True})
    result = {'scenarios': len(records), 'passed': len(records), 'failed': 0, 'fixturesOnly': True, 'authoringFilesMutated': False, 'actualBuildCommandTested': command, 'cases': records, 'deployed': False}
    (OUT / 'failure-tests.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), 'utf-8')
    # Keep private fixtures for reproducible inspection; none are served.
    assert WORK.resolve().is_relative_to(OUT.resolve()) and WORK.name.startswith('feed-check-fixtures-')
    result['fixtureDirectory'] = str(WORK)
    (OUT / 'failure-tests.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), 'utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'cases'}, ensure_ascii=False), flush=True)

if __name__ == '__main__':
    main()
