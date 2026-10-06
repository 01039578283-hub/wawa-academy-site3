"""Apply the homepage identity without reserializing any page's main content.

The baseline is a complete reviewed public archive outside the repository.
Only the shared landmarks, two head assets, body marker and reviewed CSS
palette may change. The verifier compares every other byte with that archive.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote, urljoin, urlsplit, unquote
import argparse, collections, hashlib, html as escape_html, json, re, zipfile
from lxml import html

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(r'C:\Users\1992k\Desktop\CodexData\outputs\site3-design-unification-20261006')
ASSETS = ['assets/site-brand-20261006.css', 'assets/site-brand-20261006.js']
HEAD = '<link rel="stylesheet" href="/assets/site-brand-20261006.css">\n<script defer src="/assets/site-brand-20261006.js"></script>\n'
MENU = [('홈', ''), ('학습관리', '학습관리'), ('과목별학원', '과목별학원'), ('전국센터', '전국센터'), ('지점안내', '지점안내'), ('선생님찾기', '선생님찾기'), ('공부커리큘럼', '공부커리큘럼'), ('학습가이드', '학습가이드'), ('교육정보', '교육정보'), ('상담문의', '상담문의')]
FORM = 'https://docs.google.com/forms/d/e/1FAIpQLSdb2oE5Qk5YS0TfYDxyV1w-IOTkhkjOCmmpAKTI9FmqpVj6Yg/viewform'
CSS = ['learning-guides.css', 'education-info.css', 'teacher-finder.css', 'curriculum.css', 'home-content-20261003.css', 'home-reference-20261003.css', 'brand-upgrade-v1.css']
INK = set('#23362f #243e31 #263b33 #273832 #283e34 #23342b #213c2e #193632 #193c33 #294537 #284f3a #232b31'.split())
ACCENT = set('#20674b #28634c #284f3e #2e6754 #356953 #275944 #265543 #225144 #527249 #628359 #839e66 #739a72 #42614f #a53d2e #ae6c27 #a35522'.split())
DEEP = set('#18593f #853124 #1269b4 #196a92 #1b789e'.split())
KEEP = set('#10161d #20262f #aa3b19 #e1e4e8 #fff0e5 #fffdf9 #fff #ccc #faf9f4 #d4d9d8'.split())
digest = lambda raw: hashlib.sha256(raw).hexdigest()

def dump(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', 'utf-8')

def href(path):
    return '/' + (quote(path, safe='') + '/' if path else '')

def brand():
    return '<a class="brand-home" href="/" aria-label="와와학습코칭학원 홈"><span class="brand-symbol" aria-hidden="true">W</span><span class="brand-name"><small>STUDY COACHING</small>와와학습코칭학원</span></a>'

def header(name):
    parent = '' if name == 'index.html' else name.split('/')[0]
    links = ''.join('<a href="' + href(path) + '"' + (' aria-current="' + ('page' if name in ['index.html', path + '/index.html'] else 'location') + '"' if parent == path else '') + '>' + label + '</a>' for label, path in MENU)
    return '<header class="brand-shell"><div class="brand-shell-inner"><div class="brand-topline">' + brand() + '<a class="brand-header-cta" href="' + FORM + '" target="_blank" rel="noopener">상담 신청</a><button class="brand-menu-toggle" type="button" aria-controls="brand-navigation" aria-expanded="false"><span class="brand-menu-icon" aria-hidden="true"><i></i><i></i><i></i></span><span class="brand-menu-label">메뉴</span></button></div><nav class="brand-navigation" id="brand-navigation" aria-label="주요 메뉴">' + links + '</nav></div></header>'

def footer(raw):
    doc = html.fromstring(raw)
    # Preserve all original non-navigation copy, including local facts if any.
    copy = [' '.join(t.split()) for t in doc.xpath('.//text()[not(ancestor::a)]')]
    copy = [t for t in copy if t and t not in ['W', 'STUDY COACHING', '와와학습코칭학원']]
    paragraph = ' '.join(copy)
    ident = doc.get('id')
    services = MENU[1:6]
    reading = MENU[6:9]
    nav = lambda items: ''.join('<a href="' + href(p) + '">' + label + '</a>' for label, p in items)
    tagline = '초중고 영어수학 학습코칭 · 진단상담 · 플래너 관리'
    contextual = '<p class="brand-page-note">' + escape_html.escape(paragraph) + '</p>' if paragraph and paragraph != tagline else ''
    return '<footer class="brand-footer"' + (' id="' + escape_html.escape(ident, quote=True) + '"' if ident else '') + '><div class="brand-footer-inner"><div class="brand-footer-intro">' + brand() + '<p>' + tagline + '</p>' + contextual + '<a class="brand-phone" href="tel:010-3957-8283">010-3957-8283</a><a class="brand-contact-button" href="' + href('상담문의') + '">상담 안내 보기</a></div><div><h2>학원과 수업 살펴보기</h2><nav aria-label="하단 학원 안내">' + nav(services) + '</nav></div><div><h2>공부에 도움이 되는 정보</h2><nav aria-label="하단 학습 정보">' + nav(reading) + '</nav></div></div></footer>'

def landmark(text, tag):
    found = re.findall(r'<' + tag + r'\b[^>]*>.*?</' + tag + r'>', text, re.S | re.I)
    assert found, tag
    # The direct-body landmark is first, checked again using the parsed DOM.
    return found[0] if tag in ['header', 'main'] else found[-1]

def transform(name, text):
    old_header, old_footer = landmark(text, 'header'), landmark(text, 'footer')
    doc = html.document_fromstring(text)
    assert len(doc.xpath('/html/body/header')) == len(doc.xpath('/html/body/footer')) == len(doc.xpath('/html/body/main')) == 1, name
    assert len(html.fromstring(old_header).xpath('.//a')) == len(doc.xpath('/html/body/header//a')), name
    text = text.replace(old_header, header(name), 1).replace(old_footer, footer(old_footer), 1)
    text = text.replace('</head>', HEAD + '</head>', 1)
    def add_class(m):
        tag = m[0]
        if re.search(r'\bclass=', tag):
            return re.sub(r'(\bclass=["\'])([^"\']*)(["\'])', lambda x: x[1] + x[2] + ' site-brand-unified' + x[3], tag, count=1)
        return tag[:-1] + ' class="site-brand-unified">'
    return re.sub(r'<body\b[^>]*>', add_class, text, count=1)

def color(value):
    value = value.lower()
    if value in KEEP: return value
    if value in INK: return '#20262f'
    if value in ACCENT: return '#c94f2a'
    if value in DEEP: return '#a83a1b'
    if value == '#1936320d': return '#20262f0d'
    assert len(value) == 7, value
    rgb = [int(value[n:n+2], 16) for n in [1, 3, 5]]
    if min(rgb) > 240: return '#fffdf9'
    if min(rgb) > 224: return '#f5efe0'
    if min(rgb) > 215: return '#fff3eb'
    if min(rgb) > 155: return '#dedbd3'
    return '#5c6672'

def recolor(text):
    colors = sorted(set(re.findall(r'#[0-9a-fA-F]{3,8}\b', text)))
    mapping = {c: color(c) for c in colors if color(c) != c.lower()}
    text = re.sub(r'#[0-9a-fA-F]{3,8}\b', lambda m: mapping.get(m[0], m[0]), text)
    text = re.sub(r'(?<![\w-])color\s*:\s*(?:#c94f2a|var\(--(?:lg-accent|tf-green|cc-green)\))', 'color:var(--brand-deep)', text)
    return text.encode('utf-8'), mapping

def palette():
    manifest = json.loads((ROOT / 'release-public-manifest.json').read_text('utf-8'))
    mappings = {}
    with zipfile.ZipFile(OUT / 'public-before.zip') as archive:
        for filename in CSS:
            name = 'assets/' + filename
            raw, mapping = recolor(archive.read(name).decode('utf-8'))
            (ROOT / name).write_bytes(raw); mappings[name] = mapping
    for name in ['assets/' + f for f in CSS] + ASSETS:
        raw = (ROOT / name).read_bytes(); manifest['files'][name] = digest(raw); manifest['textSha256'][name] = digest(raw.decode('utf-8').replace('\r\n', '\n').encode('utf-8'))
    (ROOT / 'release-public-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    dump('palette-mapping.json', mappings)
    (OUT / 'release-manifest-sha.txt').write_text(digest((ROOT / 'release-public-manifest.json').read_bytes()) + '\n', 'utf-8')
    print('Reviewed palette and shared-asset hashes refreshed', flush=True)

def apply():
    baseline = json.loads((OUT / 'baseline-manifest.json').read_text('utf-8'))
    changed = []; mappings = {}
    with zipfile.ZipFile(OUT / 'public-before.zip') as archive:
        for name in baseline['files']:
            if not name.endswith('.html'): continue
            raw = archive.read(name)
            assert digest(raw) == baseline['files'][name], name
            result = transform(name, raw.decode('utf-8')).encode('utf-8')
            (ROOT / name).write_bytes(result); changed.append(name)
        for filename in CSS:
            name = 'assets/' + filename
            text = archive.read(name).decode('utf-8')
            colors = sorted(set(re.findall(r'#[0-9a-fA-F]{3,8}\b', text)))
            mapping = {c: color(c) for c in colors if color(c) != c.lower()}
            mappings[name] = mapping
            recolored = re.sub(r'#[0-9a-fA-F]{3,8}\b', lambda m: mapping.get(m[0], m[0]), text)
            # Coral text needs the deeper brand shade on cream backgrounds.
            recolored = re.sub(r'(?<![\w-])color\s*:\s*(?:#c94f2a|var\(--(?:lg-accent|tf-green|cc-green)\))', 'color:var(--brand-deep)', recolored)
            result = recolored.encode('utf-8')
            (ROOT / name).write_bytes(result); changed.append(name)
    manifest = baseline.copy(); manifest['files'] = baseline['files'].copy(); manifest['textSha256'] = baseline['textSha256'].copy()
    for name in changed + ASSETS:
        raw = (ROOT / name).read_bytes(); manifest['files'][name] = digest(raw); manifest['textSha256'][name] = digest(raw.decode('utf-8').replace('\r\n', '\n').encode('utf-8'))
    (ROOT / 'release-public-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    dump('palette-mapping.json', mappings)
    dump('design-change-set.json', {'htmlPages': len(changed)-len(CSS), 'stylesheetsUpdated': CSS, 'newAssets': ASSETS, 'publicFiles': len(manifest['files']), 'homepageContentPreserved': True})
    (OUT / 'release-manifest-sha.txt').write_text(digest((ROOT / 'release-public-manifest.json').read_bytes()) + '\n', 'utf-8')
    print('Applied shared homepage design to', len(changed)-len(CSS), 'HTML pages', flush=True)

def verify():
    baseline = json.loads((OUT / 'baseline-manifest.json').read_text('utf-8'))
    manifest = json.loads((ROOT / 'release-public-manifest.json').read_text('utf-8'))
    assert set(manifest['files']) == set(baseline['files']) | set(ASSETS)
    with zipfile.ZipFile(OUT / 'public-before.zip') as archive:
        originals = {name: archive.read(name) for name in baseline['files'] if name.endswith('.html')}
        for filename in CSS:
            name = 'assets/' + filename
            assert (ROOT / name).read_bytes() == recolor(archive.read(name).decode('utf-8'))[0], ('unreviewed CSS change', name)
    ids = {}; pages = {}; contacts = 0
    def scan(item):
        name, before = item; raw = (ROOT / name).read_bytes(); text = raw.decode('utf-8')
        assert text == transform(name, before.decode('utf-8')), ('unreviewed page change', name)
        assert landmark(text, 'main').encode('utf-8') == landmark(before.decode('utf-8'), 'main').encode('utf-8'), ('body changed', name)
        doc = html.document_fromstring(raw)
        assert len(doc.xpath('/html/body/header[@class="brand-shell"]')) == len(doc.xpath('/html/body/footer[@class="brand-footer"]')) == 1
        assert doc.xpath('//head/link[@rel="stylesheet"]/@href')[-1] == '/' + ASSETS[0]
        assert len(doc.xpath('//head/script[@src="/' + ASSETS[1] + '"][@defer]')) == 1
        links = doc.xpath('//nav[@id="brand-navigation"]/a')
        assert [(a.text, a.get('href')) for a in links] == [(label, href(p)) for label, p in MENU]
        active = [a for a in links if a.get('aria-current')]
        assert len(active) == 1, name
        assert unquote(active[0].get('href')).strip('/') == ('' if name == 'index.html' else name.split('/')[0]), name
        assert doc.xpath('//footer//a[starts-with(@href,"tel:")]/@href') == ['tel:010-3957-8283']
        assert len(doc.xpath('//*[@id="brand-navigation"]')) == 1
        resources = doc.xpath('//a[@href]/@href | //link[@rel="stylesheet"]/@href | //script[@src]/@src | //img[@src]/@src')
        return name, resources, set(doc.xpath('//*[@id]/@id'))
    with ThreadPoolExecutor(max_workers=8) as pool:
        for name, resources, ident in pool.map(scan, originals.items()):
            ids[name] = ident; pages[name] = resources
    for name, resources in pages.items():
        base = 'https://xn--sp5b72l1taf0p.com/' + ('' if name == 'index.html' else name.removesuffix('index.html'))
        for value in resources:
            target = urlsplit(urljoin(base, value))
            if target.netloc != 'xn--sp5b72l1taf0p.com': continue
            decoded = unquote(target.path); dest = decoded.lstrip('/') + ('index.html' if decoded.endswith('/') else '')
            assert dest in manifest['files'], (name, value, dest)
            if target.fragment and dest in ids:
                assert unquote(target.fragment) in ids[dest], ('broken anchor', name, value)
    allowed = {'assets/' + f for f in CSS} | set(originals)
    untouched = 0
    for name, value in baseline['files'].items():
        if name not in allowed:
            assert digest((ROOT / name).read_bytes()) == value, ('preservation', name)
            untouched += 1
    for name, value in manifest['files'].items(): assert digest((ROOT / name).read_bytes()) == value, name
    result = {'htmlPages':len(pages),'publicFiles':len(manifest['files']),'sharedNavigationPages':len(pages),'sharedFooterPages':len(pages),'unchangedMainContentPages':len(pages),'unchangedOtherPublicFiles':untouched,'brokenLinksOrAnchors':0,'originalContactFactsPreserved':True,'metadataDatesCanonicalAndSchemaPreserved':True,'errors':[]}
    dump('design-source-verification.json', result); print(json.dumps(result, ensure_ascii=False), flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['apply', 'palette', 'verify']); args = parser.parse_args()
    {'apply':apply, 'palette':palette, 'verify':verify}[args.action]()
