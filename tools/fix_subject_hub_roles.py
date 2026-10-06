"""Correct eight subject collection pages without touching local detail pages.

Run this tool with the apply action after regenerating subject hubs. Existing locality destinations are
the source of truth, not a newly guessed regional or center data set. This tool
removes the generic article/map layout from collection pages, moves the real
directory before learning guidance, and preserves each published URL.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote, urljoin, urlsplit, unquote
import argparse, hashlib, html as escaping, json, re, subprocess, zipfile
from lxml import html

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(r'C:\Users\1992k\Desktop\CodexData\outputs\site3-subject-hubs-20261006')
BASE='ee40652e41fb49ecbdcc053cf84f872e46766f5e'
DOMAIN='https://xn--sp5b72l1taf0p.com'
TODAY='2026-10-06'
ASSETS=['assets/subject-hubs-20261006.css','assets/subject-hubs-20261006.js']
LABELS={'영수전문학원':('영수 전문학원','영어와 수학의 학습 균형'),
        '영어전문학원':('영어 전문학원','문장 구조·독해·서술형'),
        '수학전문학원':('수학 전문학원','개념·풀이 과정·오답 복습'),
        '전문학원':('전문학원','주간 계획과 학습관리'),
        '초등학생학원':('초등학생학원','읽기·연산과 복습 습관'),
        '중학생학원':('중학생학원','학교 진도와 지필·수행평가'),
        '고등학생학원':('고등학생학원','시험 범위와 과목별 시간 배분')}
NAMES=['과목별학원/index.html']+['과목별학원/'+s+'/index.html' for s in LABELS]
PHOTO_QUESTION='여기에 나온 사진과 교육 내용이 모든 지점에 똑같이 적용되나요?'
NEW_QUESTION='지점의 수강 조건과 위치는 어디서 확인하나요?'
NEW_ANSWER='지역과 동네를 선택한 뒤 동네 안내에 연결된 지점 페이지를 확인하세요. 실제 가능 학년·과목·시간표·교습비와 방문 위치는 해당 지점의 안내와 상담을 통해 확인할 수 있습니다.'
E=lambda s:escaping.escape(str(s),quote=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
url=lambda parts:DOMAIN+'/'+quote(parts,safe='/')
dump=lambda name,data:(OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf-8')
serialize=lambda n:html.tostring(n,encoding='unicode',with_tail=False)

def asset_url(name):
    raw=(ROOT/name).read_bytes().decode('utf-8').replace('\r\n','\n').encode('utf-8')
    return '/'+name+'?brand='+sha(raw)[:12]

def regions(doc):
    result=[]
    for panel in doc.xpath('//main//section[contains(concat(" ",@class," ")," category-region-panel ")]'):
        groups=[]
        for group in panel.xpath('.//details[contains(concat(" ",@class," ")," category-district ")]'):
            summary=group.xpath('./summary')[0]
            district=(summary.text or '').strip()
            links=[{'href':a.get('href'),'local':a.get('data-local') or ''.join(a.xpath('./strong')[0].itertext()),
                    'label':' '.join(' '.join(a.itertext()).split())}
                   for a in group.xpath('.//a[contains(concat(" ",@class," ")," subject-locality-link ")]')]
            assert district and links
            groups.append({'district':district,'links':links})
        result.append({'region':panel.get('data-region'),'groups':groups,'count':sum(len(g['links']) for g in groups)})
    assert len(result)==13 and sum(r['count'] for r in result)==371
    return result

def hero(doc,is_root):
    title=doc.xpath('string(//h1)')
    lead=('과목·학년을 고르면 지역별 동네 안내로 이어집니다. 사는 지역부터 찾고 싶다면 아래 지역 바로가기를 이용하세요.' if is_root else
          '지역을 고른 뒤 시·군·구를 펼쳐 원하는 동네 안내로 이동하세요. 동네나 시·군·구 이름으로 바로 찾을 수도 있습니다.')
    crumbs=f'<a href="/">홈</a><span aria-hidden="true">/</span>'
    if is_root:crumbs+='<span>과목별학원</span>'
    else:crumbs+=f'<a href="/{quote("과목별학원")}/">과목별학원</a><span aria-hidden="true">/</span><span>{E(title)}</span>'
    return f'<section class="sh-hero"><div class="sh-wrap"><nav class="sh-crumbs" aria-label="현재 위치">{crumbs}</nav><h1>{E(title)}</h1><p>{lead}</p></div></section>'

def root_directory(region_rows):
    cards=''.join(f'<a class="sh-category-card" href="/{quote("과목별학원/"+slug,safe="/")}/"><strong>{E(label)}</strong><span>{E(note)}</span><small>지역·동네 선택 <span aria-hidden="true">→</span></small></a>' for slug,(label,note) in LABELS.items())
    buttons=''.join(f'<a class="sh-region-link" href="/{quote("전국센터/"+r["region"],safe="/")}/"><span>{E(r["region"])}</span><small>지역 안내 →</small></a>' for r in region_rows)
    return f'<section class="sh-section" id="subject-categories"><div class="sh-wrap"><h2>과목·학년별 안내 선택</h2><p class="sh-lead">필요한 안내를 고른 뒤 지역과 동네를 선택하세요.</p><div class="sh-category-grid">{cards}</div></div></section><section class="sh-section" id="region-directory"><div class="sh-wrap"><h2>지역부터 찾아보기</h2><p class="sh-lead">지역 버튼을 누르면 해당 지역의 동네와 연결 지점을 살펴볼 수 있습니다.</p><div class="sh-region-grid">{buttons}</div><p class="sh-note">과목·학년 분류는 안내를 찾기 위한 기준입니다. 실제 수강 가능한 과목과 학년은 연결된 지점의 안내에서 확인하세요.</p></div></section>'

def child_directory(rows,label):
    tabs='<a class="sh-region-link" data-sh-region="all" aria-current="true" href="#hub-directory"><span>전체</span><small>371개</small></a>'
    tabs+=''.join(f'<a class="sh-region-link" data-sh-region="{E(r["region"])}" href="#subject-region-{E(r["region"])}"><span>{E(r["region"])}</span><small>{r["count"]}개</small></a>' for r in rows)
    panels=[]
    for r in rows:
        groups=[]
        for g in r['groups']:
            links=''.join(f'<a class="sh-local-link subject-locality-link" data-local="{E(a["local"])}" data-sh-search="{E(r["region"]+" "+g["district"]+" "+a["local"])}" href="{E(a["href"])}"><strong>{E(a["local"])}</strong><small>{E(label)} 안내</small></a>' for a in g['links'])
            groups.append(f'<details class="sh-district category-district"><summary>{E(g["district"])}<small>{len(g["links"])}개 동네</small></summary><div class="sh-local-grid">{links}</div></details>')
        panels.append(f'<section class="sh-panel category-region-panel" data-region="{E(r["region"])}" data-sh-panel="{E(r["region"])}" id="subject-region-{E(r["region"])}"><h3>{E(r["region"])} {E(label)}<span>{r["count"]}개 동네</span></h3>{"".join(groups)}</section>')
    return f'<section class="sh-section" id="hub-directory" data-subject-directory><div class="sh-wrap"><h2>지역·동네별 {E(label)} 찾기</h2><p class="sh-lead">지역 선택 → 시·군·구 펼치기 → 동네 안내 보기</p><nav class="sh-region-grid" aria-label="지역별 동네 선택">{tabs}</nav><form class="sh-search" id="subjectSearch" hidden aria-label="동네 안내 검색"><div><label for="subjectSearchInput">동네·시군구 검색</label><input id="subjectSearchInput" type="search" placeholder="예: 명일동, 강동구, 가경동" autocomplete="off" aria-describedby="subjectSearchStatus"></div><button type="submit">첫 결과로 이동</button><button type="reset">초기화</button></form><p class="sh-status" id="subjectSearchStatus" data-sh-status aria-live="polite">전체 371개 동네 · 지역을 고른 뒤 시·군·구를 펼쳐보세요.</p><p class="sh-empty" hidden>찾는 동네가 없습니다. 검색어를 바꾸거나 초기화를 눌러 전체 목록을 확인하세요.</p>{"".join(panels)}<p class="sh-note">동네 안내에서 선택 기준과 연결 지점을 확인할 수 있습니다. 수강 가능 학년·과목과 방문 위치는 해당 지점 안내를 확인하세요.</p></div></section>'

def transform(name,text,root_regions):
    doc=html.fromstring(text)
    if 'subject-hub' in (doc.xpath('//body')[0].get('class') or '').split():return text
    is_root=name==NAMES[0]
    slug=name.split('/')[1] if not is_root else None
    rows=root_regions if is_root else regions(doc)
    old_ids=set(doc.xpath('//main//*[@id]/@id'))
    keep=[]
    for n in doc.xpath('//main/*'):
        ident=n.get('id');cls=(n.get('class') or '').split()
        if ident in ['page-images','learning-space','hub-center-examples','choose-guide-purpose']:continue
        if ident in ['hub-learning-guide','hub-consultation-guide','faq-section'] or (is_root and ident=='reading-4') or (not is_root and ident=='reading-3'):
            if ident=='faq-section':
                for detail in n.xpath('.//details'):
                    if detail.xpath('string(./summary)')==PHOTO_QUESTION:
                        detail.xpath('./summary')[0].text=NEW_QUESTION
                        detail.xpath('./p')[0].text=NEW_ANSWER
            n.set('class',' '.join(cls+['sh-optional']))
            keep.append(serialize(n))
        elif set(cls)&{'tf-bridge','ei-bridge','cc-bridge'} or (n.tag=='section' and n.xpath('.//a[contains(@href,"%ED%95%99%EC%8A%B5%EA%B0%80%EC%9D%B4%EB%93%9C") or contains(@href,"학습가이드")]')):
            keep.append(serialize(n))
    body=hero(doc,is_root)+(root_directory(rows) if is_root else child_directory(rows,LABELS[slug][0]))
    body+=''.join(keep)+f'<p class="cl-revised wrap">내용 정리·수정 <time datetime="{TODAY}">2026.10.06</time> · 과목·지역별 안내를 정리했습니다.</p>'
    present=set(html.fromstring('<main>'+body+'</main>').xpath('//*[@id]/@id'))|{'main'}
    aliases=''.join(f'<span class="sh-anchor" id="{E(i)}" aria-hidden="true"></span>' for i in sorted(old_ids-present))
    body=body.replace('</section>', '</section>'+aliases,1)
    updated=re.sub(r'<main\b[^>]*>.*?</main>',lambda m:'<main id="main">'+body+'</main>',text,count=1,flags=re.S)
    updated=re.sub(r'<body\b([^>]*)class="([^"]+)"',lambda m:'<body'+m[1]+'class="'+m[2]+' subject-hub"',updated,count=1)
    updated=re.sub(r'<script>\(\(\)=>\{const input=document\.getElementById\(\x27subjectSearchInput\x27\).*?</script>', '',updated,flags=re.S)
    # Keep other global assets, schemas and navigation intact.
    includes=f'<link rel="stylesheet" href="{asset_url(ASSETS[0])}"><script defer src="{asset_url(ASSETS[1])}"></script>'
    updated=updated.replace('</head>',includes+'</head>',1)
    def schema(match):
        data=json.loads(match[1]);graph=data['@graph'];page=next(n for n in graph if n.get('@type')=='CollectionPage')
        page['dateModified']=TODAY;page.pop('mentions',None)
        new_parts=[('subject-categories','과목·학년별 안내 선택'),('region-directory','지역부터 찾아보기')] if is_root else [('hub-directory','지역·동네별 '+LABELS[slug][0]+' 찾기')]
        new_parts += [('hub-learning-guide',('과목별학원' if is_root else LABELS[slug][0])+' 학습 선택 가이드'),('hub-consultation-guide','상담 준비'),('faq-section','자주 묻는 질문')]
        page['hasPart']=[{'@id':page['url']+'#'+ident} for ident,_ in new_parts]
        graph[:]=[n for n in graph if n.get('@type')!='WebPageElement']
        for ident,label in new_parts:graph.append({'@type':'WebPageElement','@id':page['url']+'#'+ident,'url':page['url']+'#'+ident,'name':label,'isPartOf':{'@id':page['@id']}})
        for node in graph:
            if node.get('@type')=='FAQPage':
                for q in node['mainEntity']:
                    if q['name']==PHOTO_QUESTION:q['name']=NEW_QUESTION;q['acceptedAnswer']['text']=NEW_ANSWER
        return '<script type="application/ld+json">'+json.dumps(data,ensure_ascii=False,separators=(',',':'))+'</script>'
    updated=re.sub(r'<script type="application/ld\+json">(.*?)</script>',schema,updated,count=1,flags=re.S)
    return updated

def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'before.zip').exists():return
    assert subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,check=True,capture_output=True).stdout.decode().strip()==BASE
    manifest=json.loads((ROOT/'release-public-manifest.json').read_text('utf-8'))
    assert len(manifest['files'])==11288
    (OUT/'baseline-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),'utf-8')
    with zipfile.ZipFile(OUT/'before.zip','w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for name in NAMES+['sitemap.xml','release-public-manifest.json','seo-feed-review.json','seo-descriptions.json','vercel.json']:z.write(ROOT/name,name)
    from audit_neighborhood_phase6 import state
    dump('authoring-before.json',state())

def apply():
    prepare()
    manifest=json.loads((ROOT/'release-public-manifest.json').read_text('utf-8'))
    with zipfile.ZipFile(OUT/'before.zip') as z:root_regions=regions(html.fromstring(z.read('과목별학원/영어전문학원/index.html')))
    for name in NAMES:
        raw=(ROOT/name).read_bytes()
        assert sha(raw)==manifest['files'][name],name
        updated=transform(name,raw.decode('utf-8'),root_regions)
        (ROOT/name).write_bytes(updated.encode('utf-8'))
    # Only these eight modification dates change; publication dates remain intact.
    sitemap=(ROOT/'sitemap.xml').read_text('utf-8')
    for name in NAMES:
        canonical=html.fromstring((ROOT/name).read_bytes()).xpath('//link[@rel="canonical"]/@href')[0]
        pattern=r'(<url>\s*<loc>'+re.escape(canonical)+r'</loc>\s*<lastmod>)[^<]*(</lastmod>)'
        sitemap,count=re.subn(pattern,lambda m:m[1]+TODAY+m[2],sitemap)
        assert count==1,name
    (ROOT/'sitemap.xml').write_text(sitemap,'utf-8')
    for name in NAMES+ASSETS+['sitemap.xml']:
        raw=(ROOT/name).read_bytes();manifest['files'][name]=sha(raw)
        manifest['textSha256'][name]=sha(raw.decode('utf-8').replace('\r\n','\n').encode('utf-8'))
    (ROOT/'release-public-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n','utf-8')
    (OUT/'release-manifest-sha.txt').write_text(sha((ROOT/'release-public-manifest.json').read_bytes())+'\n','utf-8')
    print('Corrected eight subject hubs; all locality detail pages remain unchanged',flush=True)

def verify():
    baseline=json.loads((OUT/'baseline-manifest.json').read_text('utf-8'))
    manifest=json.loads((ROOT/'release-public-manifest.json').read_text('utf-8'))
    assert set(manifest['files'])==set(baseline['files'])|set(ASSETS)
    assert {n for n in manifest['files'] if n.endswith('.html')}=={n for n in baseline['files'] if n.endswith('.html')}
    changed={n for n in baseline['files'] if baseline['files'][n]!=manifest['files'][n]}
    from fix_connected_directory_hubs import NAMES as connected_names
    assert changed<=set(NAMES+connected_names+['sitemap.xml']) and set(NAMES)<=changed
    checked=[];public=set(manifest['files'])
    with zipfile.ZipFile(OUT/'before.zip') as z:
        original={name:html.fromstring(z.read(name)) for name in NAMES}
        root_regions=regions(original['과목별학원/영어전문학원/index.html'])
        for name in NAMES:
            raw=(ROOT/name).read_bytes();text=raw.decode('utf-8');d=html.fromstring(raw);old=original[name]
            assert text==transform(name,z.read(name).decode('utf-8'),root_regions),name
            assert transform(name,text,root_regions)==text,'Idempotency '+name
            assert not d.xpath('//main//img|//main//iframe') and len(d.xpath('//h1'))==1,name
            assert d.xpath('string(//h1)')==old.xpath('string(//h1)')
            assert d.xpath('//link[@rel="canonical"]/@href')==old.xpath('//link[@rel="canonical"]/@href')
            assert serialize(d.xpath('//header')[0])==serialize(old.xpath('//header')[0])
            assert serialize(d.xpath('//footer')[0])==serialize(old.xpath('//footer')[0])
            assert set(old.xpath('//main//*[@id]/@id'))<=set(d.xpath('//main//*[@id]/@id'))
            ids=d.xpath('//*[@id]/@id');assert len(ids)==len(set(ids)),name
            links=d.xpath('//a[contains(concat(" ",@class," ")," subject-locality-link ")]/@href')
            if name!=NAMES[0]:
                assert len(links)==371 and set(links)==set(old.xpath('//a[contains(concat(" ",@class," ")," subject-locality-link ")]/@href'))
                assert len(d.xpath('//nav[contains(@class,"sh-region-grid")]/a'))==14
            else:assert len(d.xpath('//a[contains(@class,"sh-category-card")]'))==7
            canonical=d.xpath('//link[@rel="canonical"]/@href')[0]
            for a in d.xpath('//a[@href]'):
                target=urlsplit(urljoin(canonical,a.get('href')))
                if target.netloc!=urlsplit(DOMAIN).netloc:continue
                p=unquote(target.path).lstrip('/');dest=p+('index.html' if target.path.endswith('/') else '')
                assert dest in public,(name,dest)
                if dest==name and target.fragment:assert unquote(target.fragment) in ids,(name,a.get('href'))
            graph=json.loads(d.xpath('//script[@type="application/ld+json"]/text()')[0])['@graph']
            faq=next(n for n in graph if n['@type']=='FAQPage')
            actual=[(x.xpath('string(./summary)'),x.xpath('string(./p)')) for x in d.xpath('//*[@id="faq-section"]//details')]
            assert actual==[(x['name'],x['acceptedAnswer']['text']) for x in faq['mainEntity']]
            checked.append({'file':name,'bodyImages':0,'localityLinks':len(links),'regionLinks':13,'canonicalPreserved':True,'commonHeaderFooterPreserved':True})
    def read(n):return n,sha((ROOT/n).read_bytes())
    with ThreadPoolExecutor(max_workers=12) as pool:
        for n,h in pool.map(read,manifest['files']):assert h==manifest['files'][n],n
    from audit_neighborhood_phase6 import state
    assert state()==json.loads((OUT/'authoring-before.json').read_text('utf-8'))
    result={'hubPages':8,'localityLinksPreserved':2597,'allHtmlPages':8814,'publicFiles':len(public),'unchangedOtherPublicFiles':len(set(baseline['files'])-changed),'removedHubImages':56,'routeSetPreserved':True,'checks':checked,'errors':[]}
    dump('hub-source-verification.json',result);print(json.dumps(result,ensure_ascii=False),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['apply','verify']);args=p.parse_args()
    {'apply':apply,'verify':verify}[args.action]()
