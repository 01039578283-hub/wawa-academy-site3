"""Verify all original HTML bytes and independently check scoped membership."""
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import unquote, urlsplit
import argparse, copy, hashlib, json, re, zipfile
from lxml import html, etree
import improve_neighborhood_pages as impl
from audit_neighborhood_phase8 import OUT, BACKUP, JS, DATA, destination
from audit_neighborhood_phase6 import dump
from validate_neighborhood_seo import nodes

SECTION = re.compile(r'<section\b(?=[^>]*\bid="choose-guide-purpose")[^>]*>.*?</section>', re.S)
META = re.compile(r'<meta\b[^>]*>', re.I)
SCHEMA = re.compile(r'(<script\b[^>]*type="application/ld\+json"[^>]*>)(.*?)(</script>)', re.S)
JS_TAG = '<script defer src="/assets/neighborhood-seo/find-guide.js?v=20261001-v8"></script>'
CSS_TAG = '<link rel="stylesheet" href="/assets/neighborhood-seo/local.css">'

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--sample', action='store_true'); args = parser.parse_args()
    pages = {p['file']: p for p in impl.load(OUT / 'reviewed-pages.json')}
    configs = impl.load(OUT / 'reviewed-configs.json')
    active = {p['file'] for p in impl.load(OUT / 'implementation.json')['pages']}
    data = json.loads((impl.ROOT / DATA).read_bytes())
    with zipfile.ZipFile(BACKUP) as archive:
        manifest = json.loads(archive.read('release-public-manifest.json'))
        names = sorted(active) if args.sample else [n for n in manifest['files'] if n.endswith('.html')]
        def check(name):
            old = archive.read(name); new = (impl.ROOT / name).read_bytes()
            assert hashlib.sha256(old).hexdigest() == manifest['files'][name]
            if name not in active:
                assert old == new, (name, 'unapproved HTML changed')
                return False
            page = pages[name]; config = configs[page['path']]
            before = old.decode('utf-8'); after = new.decode('utf-8')
            doc = html.document_fromstring(new); previous = html.document_fromstring(old)
            finder = doc.xpath('//section[@id="choose-guide-purpose"]')
            assert len(finder) == 1 and doc.xpath('//main')[0].index(finder[0]) == 1
            scope_node = finder[0].xpath('./script[@type="application/json" and @data-nf-scope]')
            assert len(scope_node) == 1
            scope = json.loads(scope_node[0].text)
            assert set(scope) == {'ids'} and scope['ids'] == page['ids'] and len(set(scope['ids'])) == len(scope['ids'])
            if page['type'] == 'regional':
                regions = {'경상': {'경남', '경북'}, '전라': {'전북', '전남'}, '충청': {'충남', '충북', '세종'}}.get(page['scope'], {page['scope']})
                expected_ids = {a['id'] for a in data['areas'] if a['region'] in regions}
            else:
                expected_ids = {a['id'] for a in data['areas']}
            assert set(scope['ids']) == expected_ids
            # Compare the original directory itself with the approved scope.
            links = [destination(page['path'], a.get('href')) for a in previous.xpath('//*[@id="' + page['section'] + '"]//a[@href]')]
            if page['section'] == 'find-centers':
                assert expected_ids == {a['id'] for a in data['areas'] if a['branch'] in links}
                assert page['branchesWithoutNeighborhood'] == [p for p in links if p not in {a['branch'] for a in data['areas']}]
            else:
                targets = {a['id']: a['overview'] if page['type'] == 'regional' else a['study'][page['subject']][page['stage']]['href'] for a in data['areas']}
                assert expected_ids == {key for key, path in targets.items() if path in links}
            for control, value in [('purpose', page['purpose']), ('subject', page['subject']), ('stage', page['stage'])]:
                assert finder[0].xpath('.//select[@id="nf-' + control + '"]/option[@selected]/@value') == [value]
            assert len(finder[0].xpath('.//label[@for]')) == 6
            assert finder[0].xpath('.//h2/text()') == [config['heading']]
            assert not finder[0].xpath('.//section')
            restored, count = SECTION.subn('', after); assert count == 1
            assert restored.count(JS_TAG) == 1; restored = restored.replace(JS_TAG, '', 1)
            if '/assets/neighborhood-seo/local.css' not in before:
                assert restored.count(CSS_TAG) == 1; restored = restored.replace(CSS_TAG, '', 1)
            oldmeta = list(META.finditer(before)); newmeta = list(META.finditer(restored)); assert len(oldmeta) == len(newmeta)
            descriptions = 0
            for a, b in reversed(list(zip(oldmeta, newmeta))):
                oldnode = html.fromstring(a[0]).xpath('//meta')[0]; newnode = html.fromstring(b[0]).xpath('//meta')[0]
                if (oldnode.get('name') or oldnode.get('property')) in ['description', 'og:description', 'twitter:description']:
                    attrs = dict(newnode.attrib); assert attrs.pop('content') == config['description'] and len(config['description']) <= 80
                    attrs['content'] = oldnode.get('content'); assert attrs == dict(oldnode.attrib)
                    restored = restored[:b.start()] + a[0] + restored[b.end():]; descriptions += 1
                else:
                    assert a[0] == b[0]
            assert descriptions == 3
            oldschema = list(SCHEMA.finditer(before)); newschema = list(SCHEMA.finditer(restored)); assert len(oldschema) == len(newschema)
            for a, b in reversed(list(zip(oldschema, newschema))):
                expected = json.loads(a[2])
                for node in nodes(expected):
                    if node.get('@type') in ['WebPage', 'CollectionPage', 'Article']:
                        node.update(description=config['description'], dateModified='2026-10-01')
                assert json.loads(b[2]) == expected, (name, 'schema changed beyond description and date')
                restored = restored[:b.start()] + a[0] + restored[b.end():]
            times = re.compile(r'<time datetime="\d{4}-\d{2}-\d{2}">\d{4}\.\d{2}\.\d{2}</time>')
            oldtimes = list(times.finditer(before)); newtimes = list(times.finditer(restored)); assert len(oldtimes) == len(newtimes)
            for a, b in reversed(list(zip(oldtimes, newtimes))):
                assert b[0] == '<time datetime="2026-10-01">2026.10.01</time>'
                restored = restored[:b.start()] + a[0] + restored[b.end():]
            assert restored.encode('utf-8') == old, (name, 'original HTML changed outside approved fields')
            return True
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(check, names))
        for name in ['assets/neighborhood-seo/local.css', DATA] + [n for n in archive.namelist() if n.startswith('tools/data/neighborhood-seo/')]:
            assert archive.read(name) == (impl.ROOT / name).read_bytes(), name
        old_js = archive.read(JS).decode('utf-8'); new_js = (impl.ROOT / JS).read_bytes().decode('utf-8')
        prefix, suffix = old_js.split('      areas = data.areas;')
        assert new_js.startswith(prefix) and new_js.endswith(suffix)
        added = new_js[len(prefix):len(new_js) - len(suffix)]
        assert added.startswith("      const scopeNode = root.querySelector('[data-nf-scope]');") and added.endswith('} else areas = data.areas;')
        assert 'areas.length !== ids.size' in added and 'ids.size !== scope.ids.length' in added and 'scope.ids.some' in added
        original_map = etree.fromstring(archive.read('sitemap.xml')); current_map = etree.fromstring((impl.ROOT / 'sitemap.xml').read_bytes())
        before_urls = original_map.xpath('//*[local-name()="url"]'); after_urls = current_map.xpath('//*[local-name()="url"]')
        assert len(before_urls) == len(after_urls) == 8403
        paths = {pages[n]['path'] for n in active}
        for a, b in zip(before_urls, after_urls):
            loc = a.find('{*}loc').text; assert b.find('{*}loc').text == loc
            if unquote(urlsplit(loc).path) in paths:
                assert b.find('{*}lastmod').text == '2026-10-01'
                if a.find('{*}lastmod') is None:
                    etree.SubElement(a, '{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod').text = '2026-10-01'
                else:
                    a.find('{*}lastmod').text = '2026-10-01'
            assert etree.tostring(a) == etree.tostring(b)
    output = {'sitemapPages': len(results), 'changedHtmlPages': sum(results), 'unchangedHtmlPages': len(results) - sum(results), 'scopedMemberships': sum(len(pages[n]['ids']) for n in active), 'regionalHubs': sum(pages[n]['type'] == 'regional' for n in active), 'gradeSubjectHubs': sum(pages[n]['type'] == 'grade-subject' for n in active), 'branchesWithoutNeighborhood': sum(len(pages[n]['branchesWithoutNeighborhood']) for n in active), 'originalHTMLBytePreservedOutsideApprovedFields': True, 'originalDirectoriesUnchanged': True, 'existingURLsAndOrderPreserved': True, 'finderDataAndCenterInputsByteExact': True, 'previous11HubHTMLByteExact': True, 'errors': [], 'deployed': False}
    if not args.sample:
        assert output['changedHtmlPages'] == 35 and output['scopedMemberships'] == 2968 and output['branchesWithoutNeighborhood'] == 5
    dump(OUT / ('sample-validation.json' if args.sample else 'validation.json'), output)
    print(json.dumps(output), flush=True)

if __name__ == '__main__':
    main()
