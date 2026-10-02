"""Locally review current pages/feeds before refreshing the private build ledger.

This command never writes a public page, feed, sitemap, manifest or date. The
deployment build needs only Node and the resulting root-level private JSON;
tools/ is excluded from Vercel uploads. Full RSS export comparison uses the
already reviewed phase-9 transformation, not a guessed summary.
"""
import argparse, datetime, hashlib, json, re, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import unquote, urlsplit
from lxml import etree, html
from email.utils import parsedate_to_datetime
from seo_feed_content import body, spaced, identity

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = 'https://xn--sp5b72l1taf0p.com'
TRACKER = '<script defer src="https://wawa-visit-collector.clean-peach-8202.chatgpt.site/tracker.js" data-site="wawa-04" crossorigin="anonymous" referrerpolicy="no-referrer"></script>'
PAGE_TYPES = {'WebPage', 'CollectionPage', 'Article', 'BlogPosting', 'AboutPage', 'ContactPage'}

def digest(value):
    return hashlib.sha256(value).hexdigest()

def normalized(raw):
    return raw.decode('utf-8').replace('\r\n', '\n')

def xml(raw):
    assert len(raw) < 10_000_000, 'Naver feed must be below 10MB'
    assert b'<!DOCTYPE' not in raw.upper() and b'<!ENTITY' not in raw.upper()
    return etree.fromstring(raw, etree.XMLParser(resolve_entities=False, no_network=True, remove_blank_text=True))

def nodes(value):
    if isinstance(value, list):
        for item in value:
            yield from nodes(item)
    elif isinstance(value, dict):
        yield value
        for child in value.values():
            yield from nodes(child)

def safe_name(name):
    assert isinstance(name, str) and name and '\\' not in name
    assert all(part and not part.startswith('.') for part in name.split('/'))
    assert not name.startswith(('tools/', 'reports/', 'outputs/', 'work/', 'tmp/'))
    assert not name.lower().endswith(('.xlsx', '.xls', '.csv', '.zip'))

def safe_url(url):
    parsed = urlsplit(url)
    assert parsed.scheme == 'https' and parsed.netloc == urlsplit(DOMAIN).netloc
    assert not parsed.query and not parsed.fragment and parsed.path.endswith('/')
    assert not re.search(r'%2f|%5c|%00', parsed.path, re.I)
    path = unquote(parsed.path)
    assert all(part not in ['.', '..'] for part in path.split('/'))
    return path

def date_key(value):
    assert re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2}))?', value), 'Invalid page/sitemap date: ' + value
    return datetime.date.fromisoformat(value[:10])

def review(root=ROOT, destination=None):
    destination = destination or root / 'seo-feed-review.json'
    previous = json.loads(destination.read_text('utf-8-sig')) if destination.exists() else None
    manifest = json.loads((root / 'release-public-manifest.json').read_text('utf-8-sig'))
    public = set(manifest['files'])
    for name in public:
        safe_name(name)
    assert {'rss.xml', 'sitemap.xml', 'robots.txt'} <= public
    # This private build ledger must never become a served file.
    assert 'seo-feed-review.json' not in public and 'seo-feed-check.mjs' not in public
    sitemap_raw = (root / 'sitemap.xml').read_bytes(); sitemap = xml(sitemap_raw)
    assert digest(sitemap_raw) == manifest['files']['sitemap.xml'] or digest(normalized(sitemap_raw).encode('utf-8')) == manifest.get('textSha256', {}).get('sitemap.xml'), 'Refresh reviewed public sitemap manifest first'
    assert sitemap.tag == '{http://www.sitemaps.org/schemas/sitemap/0.9}urlset'
    namespace = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
    entries = {}
    for element in sitemap:
        assert element.tag == namespace + 'url'
        assert len(element.findall(namespace + 'loc')) == 1 and len(element.findall(namespace + 'lastmod')) <= 1
        url = element.findtext(namespace + 'loc'); lastmod = element.findtext(namespace + 'lastmod')
        path = safe_url(url); name = 'index.html' if path == '/' else path.strip('/') + '/index.html'
        assert name not in entries, 'Duplicate sitemap URL'
        if lastmod:
            date_key(lastmod)
        entries[name] = {'canonical': url, 'sitemapLastmod': lastmod}
    html_names = {name for name in public if name.endswith('.html')}
    assert html_names == set(entries), 'Sitemap must match the complete reviewed public HTML set'
    assert manifest['sitemapPages'] == len(entries), 'Manifest sitemap page count mismatch'
    assert 0 < len(entries) < 50_000
    def read_page(name):
        raw = (root / name).read_bytes(); text = normalized(raw)
        assert digest(raw) == manifest['files'][name] or digest(text.encode('utf-8')) == manifest.get('textSha256', {}).get(name), 'Refresh reviewed public manifest first: ' + name
        doc = html.document_fromstring(raw)
        assert doc.xpath('//link[@rel="canonical"]/@href') == [entries[name]['canonical']], 'Canonical mismatch: ' + name
        assert len(doc.xpath('//h1')) == 1, 'H1 count: ' + name
        assert not doc.xpath('//meta[contains(translate(@content,"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz"),"noindex")]'), 'Noindex page unexpectedly in public sitemap: ' + name
        dates = set()
        for script in doc.xpath('//script[@type="application/ld+json"]'):
            for node in nodes(json.loads(script.text)):
                types = node.get('@type', []); types = [types] if isinstance(types, str) else types
                if set(types) & PAGE_TYPES and node.get('dateModified'):
                    date_key(node['dateModified']); dates.add(node['dateModified'])
        lastmod = entries[name]['sitemapLastmod']
        if dates and lastmod:
            for date in dates:
                assert date_key(date) == date_key(lastmod), 'Page/sitemap modification date mismatch: ' + name
                if 'T' in lastmod:
                    assert 'T' in date and datetime.datetime.fromisoformat(date.replace('Z', '+00:00')) == datetime.datetime.fromisoformat(lastmod.replace('Z', '+00:00')), 'Precise page/sitemap modification time mismatch: ' + name
        if dates:
            assert lastmod, 'Page with recorded modification date missing sitemap lastmod: ' + name
        trackers = re.findall(r'<script\b[^>]*wawa-visit-collector[^>]*>[\s\S]*?</script>', text, re.I)
        assert trackers in [[], [TRACKER]], 'Unexpected tracker: ' + name
        built = text if trackers else re.sub(r'</head\s*>', lambda m: TRACKER + m[0], text, count=1, flags=re.I)
        assert built != text or trackers
        return name, {**entries[name], 'pageModifiedDates': sorted(dates), 'sourceTextSha256': digest(text.encode('utf-8')), 'builtTextSha256': digest(built.encode('utf-8'))}
    records = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for index, (name, record) in enumerate(pool.map(read_page, sorted(html_names)), 1):
            records[name] = record
            if index % 2000 == 0:
                print('Reviewed page/feed metadata', index, flush=True)
    rss_raw = (root / 'rss.xml').read_bytes(); rss = xml(rss_raw)
    assert digest(rss_raw) == manifest['files']['rss.xml'] or digest(normalized(rss_raw).encode('utf-8')) == manifest.get('textSha256', {}).get('rss.xml'), 'Refresh reviewed public RSS manifest first'
    assert rss.tag == 'rss' and rss.get('version') == '2.0' and len(rss.findall('channel')) == 1
    channel = rss.find('channel')
    assert channel.findtext('link') == DOMAIN + '/' and channel.findtext('language') == 'ko-KR'
    assert channel.findtext('title') and channel.findtext('description')
    parsedate_to_datetime(channel.findtext('lastBuildDate'))
    items = []; urls = set(); guids = set()
    for element in channel.findall('item'):
        for required in ['title', 'link', 'guid', 'pubDate', 'description']:
            assert len(element.findall(required)) == 1, 'RSS field missing/duplicated: ' + required
        url = element.findtext('link'); path = safe_url(url); name = 'index.html' if path == '/' else path.strip('/') + '/index.html'
        assert name in records and records[name]['canonical'] == url and url not in urls
        assert element.findtext('guid') not in guids
        urls.add(url); guids.add(element.findtext('guid'))
        doc = html.document_fromstring((root / name).read_bytes())
        assert element.findtext('title') == spaced(' '.join(doc.xpath('//h1')[0].itertext())), 'RSS title differs from current H1: ' + name
        expected, _ = body(doc, url)
        assert element.findtext('description') == expected, 'RSS full body differs from current page: ' + name
        published = parsedate_to_datetime(element.findtext('pubDate'))
        assert published.tzinfo and published <= parsedate_to_datetime(channel.findtext('lastBuildDate'))
        items.append({'file': name, **identity(element), 'title': element.findtext('title'), 'fullBodyTextSha256': digest(expected.encode('utf-8'))})
    assert items
    if previous:
        prior_identities = {item['link']: {key: item[key] for key in ['guid', 'guidAttributes', 'pubDate']} for item in previous['rss']['items']}
        for item in items:
            if item['link'] in prior_identities:
                assert {key: item[key] for key in ['guid', 'guidAttributes', 'pubDate']} == prior_identities[item['link']], 'Keep the existing RSS publication date and GUID: ' + item['link']
        if urls == set(prior_identities):
            assert [item['link'] for item in items] == [item['link'] for item in previous['rss']['items']], 'Keep the existing RSS cohort order'
    result = {'schemaVersion': 1, 'domain': DOMAIN, 'reviewedAt': datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(), 'policy': 'Review-only ledger. Public content/dates are never rewritten. Hashes accept CRLF/LF only. Node build checks these independently of the release manifest; refresh only after all current RSS bodies and sitemap metadata pass this review.', 'htmlPages': len(records), 'sitemap': {'file': 'sitemap.xml', 'textSha256': digest(normalized(sitemap_raw).encode('utf-8')), 'urls': len(records)}, 'rss': {'file': 'rss.xml', 'textSha256': digest(normalized(rss_raw).encode('utf-8')), 'items': items, 'lastBuildDate': channel.findtext('lastBuildDate')}, 'pages': records}
    # Preserve a successful review without inventing a new review timestamp.
    if destination.exists():
        old = json.loads(destination.read_text('utf-8-sig'))
        comparable = lambda obj: {k: v for k, v in obj.items() if k != 'reviewedAt'}
        if comparable(old) == comparable(result):
            print('Current page/feed review unchanged; ledger timestamp preserved', flush=True)
            return old
    pending = destination.with_suffix('.json.review-tmp')
    pending.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', 'utf-8'); pending.replace(destination)
    print(json.dumps({'htmlPages': len(records), 'rssItems': len(items), 'sitemapUrls': len(records), 'privateLedger': str(destination), 'publicFilesChanged': 0}, ensure_ascii=False), flush=True)
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--root', type=Path, default=ROOT); parser.add_argument('--output', type=Path); args = parser.parse_args()
    review(args.root.resolve(), args.output)
