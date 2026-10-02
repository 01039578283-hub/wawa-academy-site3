"""Read-only predeployment census of the reviewed site and crawl settings."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
from urllib.robotparser import RobotFileParser
import hashlib, json, subprocess, sys
from lxml import etree, html
import improve_neighborhood_pages as impl
from audit_neighborhood_phase6 import dump, state
from verify_neighborhood_build import output_files

OUT = Path(r'C:\Users\1992k\Desktop\CodexData\outputs\site3-neighborhood-phase11-20261002')
BASE_SHA = 'ac8b06be27ae7e3c8c4e0e130cbf248707ebd966b00239d655beec20433230a7'
digest = lambda raw: hashlib.sha256(raw).hexdigest()

def main():
    manifest_raw = (impl.ROOT / 'release-public-manifest.json').read_bytes()
    assert digest(manifest_raw) == BASE_SHA
    manifest = json.loads(manifest_raw); selected = set(manifest['files'])
    built = impl.ROOT / '.public-release'; assert output_files(built) == selected
    assert len(selected) == 10624
    # Reuse this phase's exact-byte check, including its one permitted tracker
    # insertion. Every rerun also freshly checks source/build hashes below.
    if not (OUT / 'build-verification.json').exists():
        with (OUT / 'complete-output-verification.log').open('wb') as log:
            done = subprocess.run([sys.executable, '-X', 'utf8', 'tools/verify_neighborhood_build.py'], cwd=impl.ROOT, stdout=log, stderr=subprocess.STDOUT)
        assert done.returncode == 0
        dump(OUT / 'build-verification.json', impl.load(impl.REPORT / 'build-verification.json'))
    verified = impl.load(OUT / 'build-verification.json')
    assert verified['errors'] == [] and verified['reviewedManifestSha256'] == BASE_SHA
    ledger = impl.load(impl.ROOT / 'seo-feed-review.json')
    robots_raw = (built / 'robots.txt').read_text('utf-8')
    robots = RobotFileParser(); robots.parse(robots_raw.splitlines())
    assert robots.site_maps() == [impl.DOMAIN + '/sitemap.xml']
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
    tree = etree.fromstring((built / 'sitemap.xml').read_bytes(), parser)
    locs = tree.xpath('s:url/s:loc/text()', namespaces={'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'})
    assert len(locs) == len(set(locs)) == 8403
    def file_for_path(path):
        name = unquote(path).lstrip('/')
        if not name or name.endswith('/'): name += 'index.html'
        return name
    # Two existing canonicals use literal Korean characters. URI encoding does
    # not change their identity; preserve each actual canonical from the sitemap.
    entries = {file_for_path(urlsplit(url).path): url for url in locs}
    assert len(entries) == len(locs) and set(entries) == {n for n in selected if n.endswith('.html')}
    assert all(urlsplit(url).scheme == 'https' and urlsplit(url).netloc == urlsplit(impl.DOMAIN).netloc and not urlsplit(url).query and not urlsplit(url).fragment for url in locs)
    html_names = sorted(entries); errors = []
    def scan(name):
        raw = (built / name).read_bytes(); doc = html.document_fromstring(raw)
        assert digest((impl.ROOT / name).read_bytes()) == manifest['files'][name], 'Unreviewed source: ' + name
        text_hash = digest(raw.decode('utf-8').replace('\r\n', '\n').encode('utf-8'))
        assert text_hash == ledger['pages'][name]['builtTextSha256'], 'Unreviewed build: ' + name
        route = '/' if name == 'index.html' else '/' + name.removesuffix('index.html')
        canonical = entries[name]; failures = []
        if doc.xpath('//link[@rel="canonical"]/@href') != [canonical]: failures.append('canonical')
        for m in doc.xpath('//meta[@name]'):
            if m.get('name', '').lower() in {'robots', 'yeti', 'googlebot'}:
                tokens = {v.strip().lower() for v in m.get('content', '').split(',')}
                if tokens & {'noindex', 'nofollow', 'none'}: failures.append('crawl meta')
        if doc.xpath('//meta[translate(@http-equiv,"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz")="refresh"]'): failures.append('meta refresh')
        feeds = doc.xpath('//link[@type="application/rss+xml"]/@href')
        if len(feeds) != 1 or urljoin(canonical, feeds[0]) != impl.DOMAIN + '/rss.xml': failures.append('RSS discovery')
        if len(doc.xpath('//h1')) != 1: failures.append('one H1')
        if not robots.can_fetch('Yeti', canonical) or not robots.can_fetch('*', canonical): failures.append('robots.txt denied')
        for href in doc.xpath('//a[@href]/@href'):
            parsed = urlsplit(urljoin(canonical, href))
            if parsed.hostname == urlsplit(impl.DOMAIN).hostname:
                if file_for_path(parsed.path) not in selected: failures.append('unpublished link: ' + href)
        return {'file': name, 'path': impl.U(route), 'canonical': canonical, 'h1': ' '.join(' '.join(doc.xpath('//h1')[0].itertext()).split()), 'builtSha256': digest(raw), 'builtTextSha256': text_hash, 'sourceSha256': manifest['files'][name], 'errors': sorted(set(failures))}
    pages = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for i, row in enumerate(pool.map(scan, html_names), 1):
            pages.append(row)
            if row['errors']: errors.append(row)
            if i % 2000 == 0: print('Crawl and URL settings checked', i, flush=True)
    assert not errors, json.dumps(errors[:5], ensure_ascii=False)
    assets = []
    for name in sorted(selected - set(html_names)):
        raw = (built / name).read_bytes()
        assert digest(raw) == manifest['files'][name] and digest((impl.ROOT / name).read_bytes()) == manifest['files'][name], name
        row = {'file': name, 'path': impl.U('/' + name), 'builtSha256': digest(raw)}
        if Path(name).suffix in {'.css', '.js', '.json', '.xml', '.txt', '.svg', '.webmanifest'}: row['builtTextSha256'] = digest(raw.decode('utf-8').replace('\r\n', '\n').encode('utf-8'))
        assets.append(row)
    assert all(robots.can_fetch('Yeti', impl.DOMAIN + row['path']) for row in assets)
    protected = impl.load(OUT / 'protected-input-hashes.json')
    assert all(digest((impl.ROOT / n).read_bytes()) == value for n, value in protected.items())
    assert state() == impl.load(OUT / 'original-source-state.json')
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=impl.ROOT).decode().strip() == '3c2b4695e058361a77c81afa065f2758735f22bb'
    config = impl.load(impl.ROOT / 'vercel.json')
    assert config['outputDirectory'] == '.public-release' and config['cleanUrls'] is False and config['trailingSlash'] is True
    assert not config.get('rewrites') and not config.get('routes')
    data = {'manifestSha256': BASE_SHA, 'configSha256': digest((impl.ROOT / 'vercel.json').read_bytes()), 'builtRoot': str(built), 'canonicalOrigin': impl.DOMAIN, 'pages': pages, 'assets': assets}
    dump(OUT / 'http-inputs.json', data)
    summary = {'htmlPages': len(pages), 'otherPublicFiles': len(assets), 'publicFiles': len(selected), 'sitemapUrls': len(locs), 'rssDiscoveryPages': len(pages), 'publicNoindexPages': 0, 'deniedByRobots': 0, 'metaRefreshPages': 0, 'brokenPublicPageLinks': 0, 'allExistingCanonicalRoutesPreserved': True, 'sourceAndOutputProtected': True, 'extensions': dict(Counter(Path(r['file']).suffix for r in assets)), 'errors': [], 'deployed': False}
    dump(OUT / 'crawl-audit.json', summary)
    print(json.dumps(summary, ensure_ascii=False), flush=True)

if __name__ == '__main__': main()
