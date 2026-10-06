"""Review and refresh the existing RSS cohort from current, verified HTML.

No new item, URL, publication date or center fact is invented. The reviewed
snapshot is immutable; another content change requires another review.
"""
import argparse, copy, datetime, hashlib, json, re, shutil, sys, zipfile
from collections import Counter
from email.utils import format_datetime, parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit
from lxml import etree, html
import improve_neighborhood_pages as impl
from audit_neighborhood_phase5 import filename
from audit_neighborhood_phase6 import dump, state
from validate_neighborhood_seo import nodes

OUT = Path(r'C:\Users\1992k\Desktop\CodexData\outputs\site3-neighborhood-phase9-20261001')
PRIOR = OUT.parent / 'site3-neighborhood-phase8-20261001'
BACKUP = OUT / 'phase8-before-phase9.zip'
BASE_SHA = '77bd5a42a6454039b26f287c76d2492b13874198e32d04ac80a9b30411cbd792'
XML_PARSER = lambda: etree.XMLParser(resolve_entities=False, no_network=True, remove_blank_text=True)
TAGS = {'div', 'section', 'article', 'nav', 'p', 'h1', 'h2', 'h3', 'h4', 'dl', 'dt', 'dd', 'a', 'table', 'caption', 'thead', 'tbody', 'tr', 'th', 'td', 'small', 'br', 'ul', 'ol', 'li', 'strong', 'em', 'img', 'figure', 'figcaption', 'span'}
ATTRS = {'a': {'href', 'title'}, 'img': {'src', 'alt', 'width', 'height'}, 'th': {'scope', 'colspan', 'rowspan'}, 'td': {'colspan', 'rowspan'}}
HIDDEN = './/*[@hidden or @aria-hidden="true" or contains(translate(@style," ",""),"display:none")]'

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def spaced(value):
    return re.sub(r'\s+', ' ', value).strip()

def parsed(raw):
    assert b'<!DOCTYPE' not in raw.upper() and b'<!ENTITY' not in raw.upper()
    tree = etree.fromstring(raw, XML_PARSER())
    assert tree.tag == 'rss' and tree.get('version') == '2.0'
    assert len(tree.findall('channel')) == 1
    return tree

def identity(item):
    return {'link': item.findtext('link'), 'guid': item.findtext('guid'), 'guidAttributes': dict(item.find('guid').attrib), 'pubDate': item.findtext('pubDate')}

def absolute(value, page):
    # Native consultation links are part of the visible page body. Keep a
    # validated phone URI in the feed without treating it as a web address.
    if value.startswith('tel:'):
        assert re.fullmatch(r'tel:\+?[0-9(). -]+', value), value
        return value
    parts = urlsplit(urljoin(page, value))
    assert parts.scheme == 'https' and parts.netloc and not parts.username and not parts.password, value
    # Keep literal plus signs and parentheses encoded in path segments, just
    # like canonical page URLs. A raw '+' alias is not a stable Vercel asset
    # path even though generic URL parsers consider it equivalent.
    return urlunsplit((parts.scheme, parts.netloc, quote(unquote(parts.path), safe='/'), parts.query, quote(unquote(parts.fragment), safe='-._~')))

def body(doc, page):
    mains = doc.xpath('//main'); assert len(mains) == 1
    content = copy.deepcopy(mains[0]); hidden = content.xpath(HIDDEN)
    for element in hidden:
        if element.getparent() is not None:
            element.drop_tree()
    assert not content.xpath('.//script | .//style | .//iframe | .//button | .//input')
    # A feed has no page CSS or accordion script. Expose every answer/table.
    for element in content.xpath('.//details'):
        element.tag = 'div'
    for element in content.xpath('.//summary'):
        element.tag = 'p'
        strong = etree.Element('strong'); strong.text = element.text; element.text = None
        for child in list(element):
            strong.append(child)
        element.append(strong)
    for element in content.xpath('.//source'):
        element.drop_tree()
    for element in content.xpath('.//picture'):
        element.drop_tag()
    content.tag = 'div'
    for element in content.iter():
        assert isinstance(element.tag, str) and element.tag in TAGS, element.tag
        allowed = ATTRS.get(element.tag, set())
        for name in list(element.attrib):
            if name not in allowed:
                del element.attrib[name]
        for name in ['href', 'src']:
            if element.get(name) is not None:
                element.set(name, absolute(element.get(name), page))
        if element.tag == 'a':
            # Page buttons use CSS gaps. Feed readers must also see a gap
            # after a link when they render this without the page stylesheet.
            element.tail = ' ' + (element.tail or '')
    return html.tostring(content, encoding='unicode', method='html', with_tail=False), len(hidden)

def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    assert not (OUT / 'reviewed-feed.json').exists(), 'Review already exists; do not overwrite it'
    manifest_raw = (impl.ROOT / 'release-public-manifest.json').read_bytes()
    assert digest(manifest_raw) == BASE_SHA
    manifest = json.loads(manifest_raw); rss_raw = (impl.ROOT / 'rss.xml').read_bytes()
    assert digest(rss_raw) == manifest['files']['rss.xml']
    feed = parsed(rss_raw); old_items = feed.xpath('./channel/item')
    assert len(old_items) == 50
    rows = {r['path']: r for r in impl.inventory()}; records = []
    page_bytes = {}; channel = feed.find('channel')
    for index, item in enumerate(old_items, 1):
        url = item.findtext('link'); path = unquote(urlsplit(url).path)
        assert urlsplit(url).netloc == urlsplit(impl.DOMAIN).netloc
        name = filename(path); raw = (impl.ROOT / name).read_bytes()
        assert digest(raw) == manifest['files'][name]
        doc = html.document_fromstring(raw); h1 = doc.xpath('//h1')
        assert len(h1) == 1 and doc.xpath('//link[@rel="canonical"]/@href') == [url]
        assert rows[path]['role'] == 'enrollment'
        content, removed = body(doc, url)
        updates = {n['dateModified'] for s in doc.xpath('//script[@type="application/ld+json"]') for n in nodes(json.loads(s.text)) if n.get('@type') in ['WebPage', 'Article'] and n.get('dateModified')}
        parsedate_to_datetime(item.findtext('pubDate'))
        records.append({'index': index, 'file': name, 'path': path, 'sourceSha256': digest(raw), 'identity': identity(item), 'oldTitle': item.findtext('title'), 'title': spaced(' '.join(h1[0].itertext())), 'oldDescriptionSha256': digest((item.findtext('description') or '').encode('utf-8')), 'oldDescriptionCharacters': len(item.findtext('description') or ''), 'description': content, 'descriptionSha256': digest(content.encode('utf-8')), 'currentPageModifiedDates': sorted(updates), 'hiddenElementsOmitted': removed, 'role': rows[path]['role'], 'schoolStage': rows[path].get('stage'), 'subject': rows[path]['subject']})
        page_bytes[name] = raw
    assert len({r['identity']['link'] for r in records}) == len({r['identity']['guid'] for r in records}) == 50
    home = html.document_fromstring((impl.ROOT / 'index.html').read_bytes())
    review = {'baselineManifestSha256': BASE_SHA, 'baselineRssSha256': digest(rss_raw), 'items': records, 'channelTitle': home.findtext('.//title'), 'channelDescription': '영어·수학 학원의 실제 지점, 안내 학년, 교습비 자료와 수강 전 확인 사항을 안내합니다.', 'originalLastBuildDate': channel.findtext('lastBuildDate'), 'datePolicy': 'Keep original pubDate, GUID, link and item order. lastBuildDate records an actual feed content change. Page dates are never rewritten.', 'fullBodyPolicy': 'Current main content, all factual text, tables, FAQ answers and visible images. Omit hidden elements; flatten accordions; remove page-specific styling and scripts; make all URLs absolute.', 'sources': ['https://searchadvisor.naver.com/guide/request-feed', 'https://www.rssboard.org/rss-specification'], 'deployed': False}
    assert not BACKUP.exists()
    with zipfile.ZipFile(BACKUP, 'x', zipfile.ZIP_DEFLATED, compresslevel=5) as archive:
        archive.writestr('release-public-manifest.json', manifest_raw)
        archive.writestr('rss.xml', rss_raw)
        for name, raw in page_bytes.items():
            archive.writestr(name, raw)
        archive.write(impl.ROOT / 'sitemap.xml', 'sitemap.xml')
        archive.write(impl.ROOT / 'seo-descriptions.json', 'editorial/seo-descriptions.json')
        for path in impl.DATA.glob('*.json'):
            archive.write(path, 'inputs/' + path.name)
    with zipfile.ZipFile(BACKUP) as archive:
        assert archive.testzip() is None and archive.read('rss.xml') == rss_raw and archive.read('release-public-manifest.json') == manifest_raw
        for name, raw in page_bytes.items():
            assert archive.read(name) == raw
    dump(OUT / 'reviewed-feed.json', review)
    dump(OUT / 'backup-verification.json', {'sha256': digest(BACKUP.read_bytes()), 'bytes': BACKUP.stat().st_size, 'destinationPages': len(page_bytes), 'crcVerified': True, 'sourcePageBytesVerified': True, 'deployed': False})
    dump(OUT / 'original-source-state.json', state())
    dump(OUT / 'input-hashes.json', {str(p.relative_to(impl.ROOT)).replace('\\', '/'): digest(p.read_bytes()) for p in [impl.ROOT / 'seo-descriptions.json', *impl.DATA.glob('*.json')]})
    print(json.dumps({'items': len(records), 'titlesToAlign': sum(r['title'] != r['oldTitle'] for r in records), 'gradeItems': sum(bool(r['schoolStage']) for r in records), 'hiddenElementsOmitted': sum(r['hiddenElementsOmitted'] for r in records), 'backupVerified': True}, ensure_ascii=False), flush=True)

def apply():
    review = impl.load(OUT / 'reviewed-feed.json')
    review_hash = digest((OUT / 'reviewed-feed.json').read_bytes())
    current = (impl.ROOT / 'rss.xml').read_bytes()
    existing = impl.load(OUT / 'implementation.json') if (OUT / 'implementation.json').exists() else None
    if existing and digest(current) == existing['rssSha256'] and existing.get('reviewedInputSha256') == review_hash:
        print('Reviewed RSS already applied; no content/date changes', flush=True)
        return
    assert digest(current) == review['baselineRssSha256'] or existing and digest(current) == existing['rssSha256']
    manifest_hash = digest((impl.ROOT / 'release-public-manifest.json').read_bytes())
    frozen = impl.load(OUT / 'reviewed-release-state.json') if (OUT / 'reviewed-release-state.json').exists() else None
    assert manifest_hash == BASE_SHA or frozen and manifest_hash == frozen['manifestSha256']
    with zipfile.ZipFile(BACKUP) as archive:
        original = archive.read('rss.xml')
    assert digest(original) == review['baselineRssSha256']
    feed = parsed(original); channel = feed.find('channel')
    for item, record in zip(channel.findall('item'), review['items'], strict=True):
        assert identity(item) == record['identity']
        assert digest((impl.ROOT / record['file']).read_bytes()) == record['sourceSha256']
        item.find('title').text = record['title']
        item.find('description').text = etree.CDATA(record['description'])
    channel.find('title').text = review['channelTitle']
    channel.find('description').text = review['channelDescription']
    changed_at = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).replace(microsecond=0)
    channel.find('lastBuildDate').text = format_datetime(changed_at)
    raw = etree.tostring(feed, encoding='UTF-8', xml_declaration=True, pretty_print=True)
    assert raw != current and len(raw) < 10_000_000
    pending = impl.ROOT / 'rss.xml.phase9-tmp'; pending.write_bytes(raw); pending.replace(impl.ROOT / 'rss.xml')
    dump(OUT / 'implementation.json', {'items': 50, 'rssBytes': len(raw), 'rssSha256': digest(raw), 'reviewedInputSha256': review_hash, 'changedAt': changed_at.isoformat(), 'lastBuildDate': channel.findtext('lastBuildDate'), 'changedPublicFiles': ['rss.xml'], 'datesPreserved': True, 'deployed': False})
    print('Current titles and full bodies applied; publication dates preserved', flush=True)

def visible(main):
    clean = copy.deepcopy(main)
    for element in clean.xpath(HIDDEN):
        if element.getparent() is not None:
            element.drop_tree()
    return clean

def validate(output=False):
    root = impl.ROOT / '.public-release' if output else impl.ROOT
    review = impl.load(OUT / 'reviewed-feed.json'); implementation = impl.load(OUT / 'implementation.json')
    raw = (root / 'rss.xml').read_bytes(); feed = parsed(raw); channel = feed.find('channel'); records = []; errors = []
    assert digest(raw) == implementation['rssSha256'] and len(raw) < 10_000_000
    assert channel.findtext('title') == review['channelTitle'] and channel.findtext('description') == review['channelDescription']
    assert channel.findtext('lastBuildDate') == implementation['lastBuildDate']
    assert parsedate_to_datetime(channel.findtext('lastBuildDate')) == datetime.datetime.fromisoformat(implementation['changedAt'])
    assert channel.findtext('link') == impl.DOMAIN + '/' and channel.findtext('language') == 'ko-KR'
    links = 0; fragments = 0; images = 0; faqs = 0; tables = 0; destinations = set()
    items = channel.findall('item'); assert len(items) == 50
    with zipfile.ZipFile(BACKUP) as archive:
        original = parsed(archive.read('rss.xml'))
    assert [identity(i) for i in items] == [identity(i) for i in original.xpath('./channel/item')]
    public = set(impl.load(impl.ROOT / 'release-public-manifest.json')['files']); docs = {}
    sitemap = set(etree.parse(str(root / 'sitemap.xml')).xpath('//*[local-name()="loc"]/text()'))
    assert len(sitemap) == 8403
    for item, r in zip(items, review['items'], strict=True):
        assert identity(item) == r['identity'] and item.findtext('title') == r['title']
        url = item.findtext('link'); assert url in sitemap; destinations.add(url)
        src = html.document_fromstring((root / r['file']).read_bytes()); clean = visible(src.xpath('//main')[0])
        assert item.findtext('title') == spaced(' '.join(src.xpath('//h1')[0].itertext()))
        description = item.findtext('description'); exported = html.fromstring(description)
        assert description == r['description'] and digest(description.encode('utf-8')) == r['descriptionSha256']
        assert spaced(' '.join(exported.itertext())) == spaced(' '.join(clean.itertext())), r['file']
        assert exported.xpath('.//h1/text()') == [r['title']]
        assert not exported.xpath(HIDDEN) and not exported.xpath('.//script | .//style | .//details | .//summary | .//source | .//picture')
        assert exported.xpath('.//a/@href') == [absolute(h, url) for h in clean.xpath('.//a/@href')]
        expected_images = [(absolute(im.get('src'), url), im.get('alt')) for im in clean.xpath('.//img')]
        assert [(im.get('src'), im.get('alt')) for im in exported.xpath('.//img')] == expected_images
        for element in exported.iter():
            assert element.tag in TAGS and set(element.attrib) <= ATTRS.get(element.tag, set())
        # Independently compare full tables and FAQ questions/answers in order.
        table_texts = [spaced(' '.join(t.itertext())) for t in clean.xpath('.//table')]
        assert [spaced(' '.join(t.itertext())) for t in exported.xpath('.//table')] == table_texts
        all_text = spaced(' '.join(exported.itertext()))
        for faq in clean.xpath('.//*[@data-faq-kind]'):
            assert spaced(' '.join(faq.itertext())) in all_text
        for element in exported.xpath('.//a[@href] | .//img[@src]'):
            value = element.get('href') or element.get('src'); parts = urlsplit(value)
            assert parts.scheme == 'https' and parts.netloc
            if element.tag == 'a':
                links += 1
            else:
                images += 1
            if parts.netloc != urlsplit(impl.DOMAIN).netloc:
                assert element.tag == 'a', 'Unexpected external image'
                continue  # Already existing external consultation links, no account access.
            path = unquote(parts.path)
            name = filename(path) if path.endswith('/') else path.lstrip('/')
            assert name in public and (root / name).is_file(), value
            if parts.fragment:
                fragments += 1
                if name not in docs:
                    docs[name] = html.document_fromstring((root / name).read_bytes())
                assert unquote(parts.fragment) in docs[name].xpath('//*[@id]/@id'), value
        count = len(clean.xpath('.//*[@data-faq-kind]')); faqs += count; tables += len(table_texts)
        records.append({'file': r['file'], 'title': r['title'], 'bodyCharacters': len(description), 'fullVisibleTextPreserved': True, 'publicationIdentityPreserved': True, 'faqAnswers': count, 'feeTables': len(table_texts), 'visibleImages': len(expected_images), 'sourceModifiedDates': r['currentPageModifiedDates']})
    assert len(destinations) == 50
    assert all(digest((impl.ROOT / name).read_bytes()) == expected for name, expected in impl.load(OUT / 'input-hashes.json').items())
    result = {'items': 50, 'rssBytes': len(raw), 'underNaver10MBLimit': True, 'fullBodyItems': 50, 'publicationDatesGuidsLinksAndOrderPreserved': True, 'titlesMatchCurrentH1': True, 'actualFeedUpdateRecorded': True, 'internalAndOriginalExternalLinks': links, 'checkedInternalFragments': fragments, 'checkedVisibleImages': images, 'faqAnswersPreserved': faqs, 'feeTablesPreserved': tables, 'allSitemapUrlsPreserved': 8403, 'hiddenElementsExcluded': sum(r['hiddenElementsOmitted'] for r in review['items']), 'privateFactInputsPreserved': True, 'output': output, 'errors': errors, 'pages': records, 'deployed': False}
    dump(OUT / ('output-feed-validation.json' if output else 'validation.json'), result)
    print(json.dumps({k: v for k, v in result.items() if k != 'pages'}, ensure_ascii=False), flush=True)

def preview():
    review = impl.load(OUT / 'reviewed-feed.json')
    for index in [0, 32, 49]:
        r = review['items'][index]; content = html.fromstring(r['description'])
        for image in content.xpath('.//img'):
            parts = urlsplit(image.get('src')); image.set('src', 'http://127.0.0.1:8852' + parts.path)
        markup = '<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex"><title>RSS 본문 검토</title><style>body{font:16px/1.65 sans-serif;margin:0 auto;padding:20px;max-width:960px;color:#152238}h1{font-size:26px}section{margin:24px 0}img{max-width:100%;height:auto}table{border-collapse:collapse;display:block;overflow-x:auto}td,th{padding:8px;border:1px solid #bbb}a{overflow-wrap:anywhere}dl{margin:14px 0}dd{margin-left:18px}.review{padding:12px;background:#e7edf7}</style><p class="review">비공개 RSS 검토용 화면 · 현재 피드 본문 그대로 표시 · 이미지 경로만 로컬 검증 서버로 연결</p>' + html.tostring(content, encoding='unicode') + '</html>'
        (OUT / ('rss-review-' + str(index + 1) + '.html')).write_text(markup, 'utf-8')
    print('Private RSS body previews created; no public HTML changed', flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['prepare', 'apply', 'validate', 'validate-output', 'preview']); action = parser.parse_args().action
    if action == 'validate-output':
        validate(True)
    else:
        globals()[action]()
