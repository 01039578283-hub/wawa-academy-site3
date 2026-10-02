"""Review existing regional membership and preserve the completed phase-7 baseline."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
import hashlib, json, zipfile
from lxml import html
import improve_neighborhood_pages as impl
from audit_neighborhood_phase5 import filename
from audit_neighborhood_phase6 import dump, state

OUT = Path(r'C:\Users\1992k\Desktop\CodexData\outputs\site3-neighborhood-phase8-20261001')
PRIOR = OUT.parent / 'site3-neighborhood-phase7-20261001'
BACKUP = OUT / 'phase7-before-phase8.zip'
BASE_SHA = '8d32981b05f5698f6bda5c67b9ce61ffcf0a43ba5830bfbee019cb3cf82df7d9'
JS = 'assets/neighborhood-seo/find-guide.js'
DATA = 'assets/neighborhood-seo/find-guide.json'

def destination(path, href):
    parsed = urlsplit(urljoin(impl.DOMAIN + impl.U(path), href))
    return unquote(parsed.path) if parsed.netloc == urlsplit(impl.DOMAIN).netloc else None

def membership(doc, path, data):
    name = path.strip('/').split('/')[-1]
    stage = next((g for g in ['초등', '중등', '고등'] if name.startswith(g)), '전체')
    subject = '영어' if '영어' in name else '수학'
    grade = stage != '전체'
    section_id = 'find-centers' if path.startswith('/지점안내/') else 'reading-5' if grade else 'reading-4'
    section = doc.xpath('//*[@id="' + section_id + '"]')
    assert len(section) == 1, (path, section_id)
    links = [destination(path, a.get('href')) for a in section[0].xpath('.//a[@href]')]
    route_ids = {}
    for a in data['areas']:
        route = a['branch'] if section_id == 'find-centers' else a['study'][subject][stage]['href'] if grade else a['overview']
        route_ids.setdefault(route, set()).add(a['id'])
    known_branches = {impl.center_path(c) for c in impl.FACTS['centers']}
    assert links and all(p in route_ids or section_id == 'find-centers' and p in known_branches for p in links), (path, 'directory scope')
    unmapped = [p for p in links if p not in route_ids]
    ids = set().union(*(route_ids.get(p, set()) for p in links))
    assert len(links) == len(set(links)), path
    if grade:
        assert len(ids) == len(links) == 371
    else:
        regions = {'경상': {'경남', '경북'}, '전라': {'전북', '전남'}, '충청': {'충남', '충북', '세종'}}.get(name, {name})
        assert ids == {a['id'] for a in data['areas'] if a['region'] in regions}, path
    return {'type': 'grade-subject' if grade else 'regional', 'scope': name, 'stage': stage, 'subject': subject, 'purpose': 'enrollment' if path.startswith('/지점안내/') else 'study', 'section': section_id, 'directoryLinks': len(links), 'branchesWithoutNeighborhood': unmapped, 'ids': [a['id'] for a in data['areas'] if a['id'] in ids]}

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    raw = (impl.ROOT / 'release-public-manifest.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == BASE_SHA
    manifest = json.loads(raw)
    data = json.loads((impl.ROOT / DATA).read_bytes())
    assert data == impl.load(PRIOR / 'reviewed-finder-data.json')
    local = {r['path'] for r in impl.inventory()}
    names = sorted(n for n in manifest['files'] if n.endswith('/index.html') and len(n.split('/')) == 3 and n.split('/')[0] in ['전국센터', '지점안내'] and '/' + n.removesuffix('index.html') not in local)
    assert len(names) == 35
    pages = []
    for name in names:
        value = (impl.ROOT / name).read_bytes()
        assert hashlib.sha256(value).hexdigest() == manifest['files'][name]
        doc = html.document_fromstring(value)
        path = '/' + name.removesuffix('index.html')
        assert not doc.xpath('//*[@data-neighborhood-finder]')
        pages.append({'path': path, 'file': name, 'sha256': manifest['files'][name], 'oldDescription': doc.xpath('//meta[@name="description"]/@content')[0], 'h1': ' '.join(doc.xpath('//h1')[0].itertext()), **membership(doc, path, data)})
    assert sum(p['type'] == 'regional' for p in pages) == 29
    assert sum(p['type'] == 'grade-subject' for p in pages) == 6
    all_ids = {a['id'] for a in data['areas']}
    for prefix in ['/전국센터/', '/지점안내/']:
        group = [p for p in pages if p['type'] == 'regional' and p['path'].startswith(prefix)]
        assert set().union(*(set(p['ids']) for p in group)) == all_ids and sum(len(p['ids']) for p in group) == 371
    dump(OUT / 'reviewed-pages.json', pages)
    dump(OUT / 'original-source-state.json', state())
    (OUT / 'seo-descriptions-before-phase8.json').write_bytes((impl.ROOT / 'seo-descriptions.json').read_bytes())
    snapshot_names = [n for n in manifest['files'] if n.endswith('.html')] + ['sitemap.xml', JS, DATA, 'assets/neighborhood-seo/local.css', 'release-public-manifest.json']
    snapshot_names += ['tools/data/neighborhood-seo/' + p.name for p in impl.DATA.glob('*.json')]
    assert not BACKUP.exists(), 'Never overwrite a completed baseline'
    with zipfile.ZipFile(BACKUP, 'x', zipfile.ZIP_DEFLATED, compresslevel=5) as archive:
        with ThreadPoolExecutor(max_workers=8) as pool:
            for name, value in pool.map(lambda n: (n, (impl.ROOT / n).read_bytes()), snapshot_names):
                if name in manifest['files']:
                    assert hashlib.sha256(value).hexdigest() == manifest['files'][name], name
                archive.writestr(name, value)
    with zipfile.ZipFile(BACKUP) as archive:
        assert archive.testzip() is None and archive.read('release-public-manifest.json') == raw
    dump(OUT / 'backup-verification.json', {'name': BACKUP.name, 'sha256': hashlib.sha256(BACKUP.read_bytes()).hexdigest(), 'bytes': BACKUP.stat().st_size, 'htmlPages': 8403})
    print(json.dumps({'pages': len(pages), 'regional': 29, 'gradeSubject': 6, 'memberships': sum(len(p['ids']) for p in pages), 'regionalPartitionsVerified': True, 'deployed': False}), flush=True)

if __name__ == '__main__':
    main()
