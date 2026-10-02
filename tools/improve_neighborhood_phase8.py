"""Add scoped finders to existing hubs; preserve original directories and facts."""
import argparse, hashlib, json, re, zipfile
from urllib.parse import unquote, urlsplit
from lxml import html
import improve_neighborhood_pages as impl
import improve_neighborhood_phase7 as prior
from audit_neighborhood_phase8 import OUT, BACKUP, JS
from audit_neighborhood_phase6 import dump
from validate_neighborhood_seo import nodes

JS_TAG = '<script defer src="/assets/neighborhood-seo/find-guide.js?v=20261001-v8"></script>'
CSS_TAG = '<link rel="stylesheet" href="/assets/neighborhood-seo/local.css">'

def configuration(page):
    count = len(page['ids'])
    scope = page['scope']
    if page['type'] == 'grade-subject':
        topic = page['stage'] + ' ' + page['subject']
        heading = topic + ' 동네별 학습 점검과 수강 안내 찾기'
        intro = topic + ' 안내를 먼저 선택했습니다. 학생 답안과 복습 기록을 점검할 동네 안내를 찾고, 실제 지점의 수강 학년·주소·교습비는 수강 안내에서 확인해 주세요.'
        desc = topic + ' 학습 점검을 371개 동네에서 찾고, 해당 지점의 수강 학년·주소·교습비와 비교 기준을 확인하세요.'
    else:
        heading = scope + ' 동네별 ' + ('수강·위치 안내' if page['purpose'] == 'enrollment' else '학습 점검과 수강 안내') + ' 찾기'
        intro = '이 목록에 연결된 ' + scope + ' ' + str(count) + '개 동네에서 찾습니다. 과목과 학교급, 안내 목적을 고른 뒤 실제 지점의 수강 조건이나 학생의 학습 점검 자료를 확인해 주세요.'
        if page['branchesWithoutNeighborhood']:
            intro += ' 동네 찾기에 없는 지점은 아래 지점 목록에서 확인할 수 있습니다.'
        desc = scope + ' ' + str(count) + '개 동네의 수강·위치 안내에서 지점별 주소·안내 학년·교습비를 확인하고 방문 상담을 준비하세요.' if page['purpose'] == 'enrollment' else scope + ' ' + str(count) + '개 동네의 영어·수학 학습 점검을 학년별로 찾고, 학생 답안과 복습 기록을 확인하세요.'
    assert len(desc) <= 80 and desc.endswith('요.')
    return {'heading': heading, 'intro': intro, 'description': desc, 'purpose': page['purpose'], 'category': '전문학원', 'subject': page['subject'], 'stage': page['stage']}

def render(page, config):
    value = prior.render(config)
    for control, selected in [('subject', config['subject']), ('stage', config['stage'])]:
        def preset(match):
            options = match[2].replace(' selected', '')
            options, count = re.subn(r'<option value="' + re.escape(selected) + '">', '<option value="' + selected + '" selected>', options)
            assert count == 1
            return match[1] + options + match[3]
        value, count = re.subn(r'(<select id="nf-' + control + '"[^>]*>)(.*?)(</select>)', preset, value, flags=re.S)
        assert count == 1
    payload = json.dumps({'ids': page['ids']}, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    value = value.replace('<div class="wrap">', '<script type="application/json" data-nf-scope>' + payload + '</script><div class="wrap">', 1)
    return value

def edit(page, old, config):
    main = re.search(r'<main\b[^>]*>', old)
    assert main
    end = old.index('</section>', main.end()) + len('</section>')
    value = old[:end] + render(page, config) + old[end:]
    def meta(match):
        node = html.fromstring(match[0]).xpath('//meta')[0]
        if (node.get('name') or node.get('property')) not in ['description', 'og:description', 'twitter:description']:
            return match[0]
        result, count = re.subn(r'content="[^"]*"', lambda _: 'content="' + impl.E(config['description']) + '"', match[0])
        assert count == 1
        return result
    value = prior.META.sub(meta, value)
    def schema(match):
        obj = json.loads(match[2]); changed = False
        for node in nodes(obj):
            if node.get('@type') in ['WebPage', 'CollectionPage', 'Article']:
                node.update(description=config['description'], dateModified='2026-10-01'); changed = True
        return match[1] + json.dumps(obj, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c') + match[3] if changed else match[0]
    value = prior.SCRIPTS.sub(schema, value)
    value = re.sub(r'<time datetime="\d{4}-\d{2}-\d{2}">\d{4}\.\d{2}\.\d{2}</time>', '<time datetime="2026-10-01">2026.10.01</time>', value)
    if '/assets/neighborhood-seo/local.css' not in value:
        value = value.replace('</head>', CSS_TAG + '</head>', 1)
    return value.replace('</head>', JS_TAG + '</head>', 1)

def scoped_script(old):
    before = '      areas = data.areas;'
    after = '''      const scopeNode = root.querySelector('[data-nf-scope]');
      if (scopeNode) {
        const scope = JSON.parse(scopeNode.textContent);
        if (Object.keys(scope).length !== 1 || !Array.isArray(scope.ids) || !scope.ids.length || scope.ids.some(id => typeof id !== 'string')) throw new Error('Invalid finder scope');
        const ids = new Set(scope.ids);
        if (ids.size !== scope.ids.length) throw new Error('Duplicate finder scope');
        areas = data.areas.filter(area => ids.has(area.id));
        if (areas.length !== ids.size) throw new Error('Unknown finder scope');
      } else areas = data.areas;'''
    assert old.count(before) == 1
    return old.replace(before, after, 1)

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--sample', action='store_true'); args = parser.parse_args()
    pages = impl.load(OUT / 'reviewed-pages.json')
    if args.sample:
        pages = [p for p in pages if p['path'] in ['/전국센터/경상/', '/전국센터/고등영어학원/', '/지점안내/서울/']]
        assert len(pages) == 3
    configs = impl.load(OUT / 'reviewed-configs.json') if (OUT / 'reviewed-configs.json').exists() else {p['path']: configuration(p) for p in impl.load(OUT / 'reviewed-pages.json')}
    dump(OUT / 'reviewed-configs.json', configs)
    result = impl.load(OUT / 'implementation.json') if (OUT / 'implementation.json').exists() else {'pages': []}
    with zipfile.ZipFile(BACKUP) as archive:
        for page in pages:
            old = archive.read(page['file']); assert hashlib.sha256(old).hexdigest() == page['sha256']
            value = edit(page, old.decode('utf-8'), configs[page['path']]).encode('utf-8')
            path = impl.ROOT / page['file']; actual = path.read_bytes()
            previous = next((p for p in result['pages'] if p['path'] == page['path']), None)
            assert actual in [old, value] or previous and hashlib.sha256(actual).hexdigest() == previous['sha256'], page['path']
            path.write_bytes(value)
            result['pages'] = [p for p in result['pages'] if p['path'] != page['path']] + [{'path': page['path'], 'file': page['file'], 'sha256': hashlib.sha256(value).hexdigest()}]
        old_js = archive.read(JS)
        new_js = scoped_script(old_js.decode('utf-8')).encode('utf-8')
        path = impl.ROOT / JS; assert path.read_bytes() in [old_js, new_js]; path.write_bytes(new_js)
        modified = {p['path'] for p in result['pages']}
        def dates(match):
            block = match[0]; loc = re.search(r'<loc>(.*?)</loc>', block)
            if unquote(urlsplit(loc[1]).path) not in modified:
                return block
            return re.sub(r'<lastmod>.*?</lastmod>', '<lastmod>2026-10-01</lastmod>', block) if '<lastmod>' in block else block.replace('</url>', '<lastmod>2026-10-01</lastmod></url>')
        (impl.ROOT / 'sitemap.xml').write_bytes(re.sub(r'<url>.*?</url>', dates, archive.read('sitemap.xml').decode('utf-8'), flags=re.S).encode('utf-8'))
    result.update(changedHtmlPages=len(result['pages']), scopedMemberships=sum(len(p['ids']) for p in impl.load(OUT / 'reviewed-pages.json') if p['path'] in modified), deployed=False)
    dump(OUT / 'implementation.json', result)
    print(json.dumps({k: v for k, v in result.items() if k != 'pages'}), flush=True)

if __name__ == '__main__':
    main()
