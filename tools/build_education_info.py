"""Add reviewed education articles without regenerating existing local content.

The private manuscript selection, authored content, and pre-change public ZIP
are required inputs. Existing routes and RSS publication identities are kept.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from urllib.parse import quote,unquote,urlsplit
from email.utils import format_datetime
import datetime,json,re,hashlib,html as escape,time
from lxml import html,etree
from build_teacher_finder import load,DOMAIN,ROOT,digest
from improve_neighborhood_pages import inventory,FACTS,center_path
from seo_feed_content import body,identity

OUT=Path(r'C:\Users\1992k\Desktop\CodexData\outputs\site3-education-info-20261002')
SOURCE=Path(r'C:\Users\1992k\Desktop\WAWA_유용한정보_블로그_2026-09-11')
DATA=ROOT/'tools/data/education-info/content.json'
DATE='2026-10-03'
E=lambda s:escape.escape(str(s),quote=True)
U=lambda s:quote(s,safe='/#')
url=lambda p:DOMAIN+U(p)
NAV='<a href="/교육정보/" data-education-nav>교육정보</a>'
CSS='<link rel="stylesheet" href="/assets/education-info.css" data-education-style>'
CATEGORIES=['시험과 오답','과목 공부','계획과 습관','학년 전환','방학 준비','학부모와 수업 선택']

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=value.encode('utf-8') if isinstance(value,str) else value
    if path.exists() and path.read_bytes()==raw:return
    pending=path.with_name(path.name+'.education-tmp')
    for attempt in range(8):
        try:
            pending.write_bytes(raw);pending.replace(path);return
        except OSError as error:
            if error.errno not in [13,22] or attempt==7:raise
            # Windows readers can allow updates while preventing handle replacement.
            # Keep the original inode in that case and verify the complete new bytes.
            if path.exists():
                try:
                    with path.open('r+b') as handle:
                        handle.write(raw);handle.truncate()
                    assert path.read_bytes()==raw
                    pending.unlink(missing_ok=True);return
                except OSError as update_error:
                    if update_error.errno not in [13,22]:raise
            time.sleep(.2*(attempt+1))

def dump(path,value):write(path,json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def patch_dates(text):
    def patch(match):
        data=json.loads(match.group(2))
        def visit(value):
            if isinstance(value,list):
                for item in value:visit(item)
            elif isinstance(value,dict):
                if value.get('@type') in ['WebPage','CollectionPage','AboutPage','ContactPage','Article'] and value.get('dateModified'):value['dateModified']=DATE
                for item in value.values():visit(item)
        visit(data)
        return match.group(1)+json.dumps(data,ensure_ascii=False,separators=(',',':'))+match.group(3)
    text=re.sub(r'(<script\b[^>]*type="application/ld\+json"[^>]*>)(.*?)(</script>)',patch,text,flags=re.S)
    return re.sub(r'(내용 수정 )2026\.\d{2}\.\d{2}',lambda m:m.group(1)+DATE.replace('-','.'),text)

def crumbs(parts):
    return '<nav class="ei-crumbs" aria-label="현재 위치">'+'<span aria-hidden="true">/</span>'.join(f'<a href="{U(p)}">{E(t)}</a>' for t,p in parts)+'</nav>'

def shell(path,title,summary,markup,graph,image=None):
    return f'''<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{E(title)} | 와와학습코칭학원</title>
<meta name="description" content="{E(summary)}"><meta name="robots" content="index, follow"><link rel="canonical" href="{url(path)}"><link rel="alternate" type="application/rss+xml" title="와와학습코칭학원 RSS" href="{DOMAIN}/rss.xml">
<meta property="og:type" content="{'article' if path!='/교육정보/' else 'website'}"><meta property="og:title" content="{E(title)}"><meta property="og:url" content="{url(path)}"><meta property="og:description" content="{E(summary)}"><meta property="og:image" content="{DOMAIN+image['path'] if image else DOMAIN+'/assets/brand-upgrade-v1/brand-learning.png'}"><meta property="og:image:alt" content="{E(image['alt']) if image else '와와의 학생 중심 학습을 표현한 브랜드 일러스트'}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:description" content="{E(summary)}"><link rel="icon" href="/assets/favicon.png">{CSS}<script defer src="/assets/education-info.js"></script>
<script type="application/ld+json">{json.dumps({'@context':'https://schema.org','@graph':graph},ensure_ascii=False).replace('</','<\\/')}</script></head>
<body class="education-info"><a class="ei-skip" href="#main">본문 바로가기</a><header class="ei-header"><nav class="ei-wrap ei-nav" aria-label="주요 메뉴"><a class="ei-brand" href="/"><span class="ei-mark" aria-hidden="true">W</span><span><small>STUDY COACHING</small>와와학습코칭학원</span></a><div class="ei-nav-links"><a href="/">홈</a><a href="/학습가이드/">학습가이드</a><a href="/교육정보/" aria-current="page" data-education-nav>교육정보</a><a href="/선생님찾기/">선생님찾기</a><a href="/지점안내/">지점안내</a><a href="/상담문의/">상담문의</a></div></nav></header><main id="main">{markup}</main><footer class="ei-footer"><div class="ei-wrap"><strong>와와학습코칭학원</strong><p>학생과 학부모가 함께 읽는 교육정보</p><nav aria-label="하단 메뉴"><a href="/교육정보/">교육정보 전체</a><a href="/학습가이드/">학습가이드</a><a href="/전국센터/">동네별 안내</a><a href="/지점안내/">지점 안내</a><a href="/선생님찾기/">선생님찾기</a></nav></div></footer></body></html>'''

def graph(path,title,summary,kind,published):
    parts=[('홈','/'),('교육정보','/교육정보/')]+([] if path=='/교육정보/' else [(title,path)])
    return [{'@type':kind,'@id':url(path)+'#webpage','url':url(path),'name':title,'description':summary,'datePublished':published,'dateModified':DATE,'inLanguage':'ko-KR','publisher':{'@id':DOMAIN+'/#organization'},'isPartOf':{'@id':DOMAIN+'/#website'},'breadcrumb':{'@id':url(path)+'#breadcrumb'}},
            {'@type':'BreadcrumbList','@id':url(path)+'#breadcrumb','itemListElement':[{'@type':'ListItem','position':i,'name':t,'item':url(p)} for i,(t,p) in enumerate(parts,1)]}]

def locator():
    return '''<section class="ei-locator" id="local-info"><p class="ei-kicker">우리 동네의 수업을 알아볼 때</p><h2>읽은 내용을 가까운 수업 안내와 연결해 보세요</h2><p>현재 공부에서 막힌 부분과 사용 교재를 준비하고, 실제 지점의 과목·학년·교습비 안내를 함께 확인해 보세요.</p><div class="ei-actions"><a class="ei-button" href="/전국센터/">동네별 학습 안내 찾기</a><a class="ei-button ei-secondary" href="/지점안내/">실제 지점 안내 보기</a><a class="ei-text-link" href="/선생님찾기/">지점별 선생님 소개 →</a></div><form class="ei-location-form" data-education-locator hidden><div><label for="ei-location-region">지역</label><select id="ei-location-region"><option value="">지역을 선택하세요</option></select></div><div><label for="ei-location-kind">찾는 안내</label><select id="ei-location-kind"><option value="neighborhood">동네 안내</option><option value="center">지점 안내</option></select></div><div><label for="ei-location-place">동네·지점</label><select id="ei-location-place" disabled><option value="">지역을 먼저 선택하세요</option></select></div><a class="ei-button" data-location-go href="/전국센터/" aria-disabled="true">선택한 안내로 이동</a><p class="ei-small" data-location-status role="status" aria-live="polite">지역을 고르면 홈페이지에 있는 동네와 지점 안내를 찾을 수 있습니다.</p></form></section>'''

def card(r,thumb=True):
    image=r['images'][0]
    hay=' '.join([r['title'],r['summary'],r['category'],r['audience'],*r['checks']])
    return f'''<article class="ei-card" data-education-card data-category="{E(r['category'])}" data-audience="{E(r['audience'])}" data-search="{E(hay)}">{'<img src="'+image['path']+'" alt="" width="'+str(image['width'])+'" height="'+str(image['height'])+'" loading="lazy" decoding="async">' if thumb else ''}<div><p class="ei-kicker">{E(r['category'])}</p><h3><a href="{U(r['path'])}">{E(r['title'])}</a></h3><p>{E(r['summary'])}</p><span class="ei-small">{E(r['audience'])}</span><a class="ei-card-link" href="{U(r['path'])}">자세히 읽기 <span aria-hidden="true">↗</span><span class="ei-sr"> · {E(r['title'])}</span></a></div></article>'''

def listing(data,published):
    rows=data['articles'];summary='학생과 학부모를 위한 시험 준비, 과목 공부, 방학 계획과 수업 선택 정보를 제공합니다.'
    counts=Counter(r['category'] for r in rows)
    filters=''.join(f'<option value="{E(c)}">{E(c)} · {counts[c]}개</option>' for c in CATEGORIES)
    starters=[rows[n-1] for n in [30,20,11]]
    content=f'''<section class="ei-hero"><div class="ei-wrap">{crumbs([('홈','/'),('교육정보','/교육정보/')])}<p class="ei-kicker">EDUCATION JOURNAL · 학생과 학부모를 위한 읽을거리</p><h1>교육정보</h1><p class="ei-lead">공부의 고민을,<br>다음에 해 볼 행동으로.</p><p class="ei-hero-copy">시험 준비부터 방학 계획과 자녀와의 대화까지.<br> 30개 글에서 지금 필요한 설명과 점검 질문을 찾아보세요.</p><div class="ei-actions"><a class="ei-button" href="#articles">교육정보 찾아보기</a><a class="ei-text-link" href="/학습가이드/">기록표가 있는 학습가이드 48개 →</a></div><div class="ei-stats"><span><strong>30</strong>교육정보 글</span><span><strong>6</strong>읽기 주제</span><span><strong>48</strong>연결된 학습가이드</span></div></div></section><section class="ei-section"><div class="ei-wrap"><p class="ei-kicker">이런 고민부터 시작하세요</p><h2>지금 필요한 글 한 편</h2><div class="ei-grid">{''.join(card(r) for r in starters)}</div></div></section><section class="ei-section ei-tint" id="articles"><div class="ei-wrap"><div class="ei-section-heading"><div><p class="ei-kicker">FIND YOUR TOPIC</p><h2>교육정보 전체</h2></div><p>주제와 읽는 대상을 골라 보세요.</p></div><form class="ei-filter" data-education-filter hidden><div><label for="ei-search">고민이나 키워드</label><input id="ei-search" type="search" placeholder="예: 중간고사, 듣기, 플래너, 방학" autocomplete="off"></div><div><label for="ei-category">주제</label><select id="ei-category"><option value="">전체 주제</option>{filters}</select></div><div><label for="ei-audience">읽는 대상</label><select id="ei-audience"><option value="">전체 대상</option><option>초등</option><option>중등</option><option>고등</option><option>학부모</option></select></div><button type="reset">초기화</button><p data-education-count role="status" aria-live="polite">30개 글</p></form><noscript data-education-fallback><p>아래 목록에서 모든 교육정보를 읽을 수 있습니다.</p></noscript><p class="ei-empty" data-education-empty hidden>조건에 맞는 글이 없습니다. 검색어를 짧게 바꾸거나 필터를 초기화해 보세요.</p><div class="ei-grid" data-education-list>{''.join(card(r) for r in rows)}</div></div></section><section class="ei-section"><div class="ei-wrap ei-guide-bridge"><p class="ei-kicker">읽은 뒤 직접 연습하고 싶다면</p><h2>학습가이드와 실천 기록표도 함께 보세요</h2><p>기존 학습가이드 48개에는 단계별 예시와 직접 작성해 저장할 수 있는 기록표가 있습니다. 교육정보 글에서 필요한 가이드를 연결해 두었습니다.</p><div class="ei-actions"><a class="ei-button" href="/학습가이드/">학습가이드 48개 보기</a><a class="ei-text-link" href="/학습가이드/공부습관/">공부 습관 가이드 →</a></div></div></section><section class="ei-section ei-tint"><div class="ei-wrap ei-reading">{locator()}</div></section>'''
    # Resolve the existing category route by its real H1 instead of assuming a slug.
    category_names=[n for n in load(OUT/'baseline-manifest.json')['files'] if n.startswith('학습가이드/') and n.count('/')==2 and n.endswith('index.html')]
    hit=next((n for n in category_names if '공부 습관' in html.fromstring((ROOT/n).read_bytes()).xpath('string(//h1)')),None)
    assert hit;content=content.replace('/학습가이드/공부습관/','/'+hit[:-10])
    g=graph('/교육정보/','교육정보',summary,'CollectionPage',published)
    g.append({'@type':'ItemList','@id':url('/교육정보/')+'#articles','numberOfItems':30,'itemListElement':[{'@type':'ListItem','position':i,'name':r['title'],'url':url(r['path'])} for i,r in enumerate(rows,1)]})
    return '/교육정보/',summary,shell('/교육정보/','교육정보',summary,content,g)

def article(r,data,published):
    image=r['images'][0]
    toc=[(f'section-{i}',s['title']) for i,s in enumerate(r['sections'],1)]+[('practice-table','실천 내용을 한눈에 보기'),('checklist','확인 질문'),('questions','자주 묻는 질문'),('references','참고 자료'),('related','함께 읽을 글'),('local-info','동네·지점 안내 찾기')]
    content=f'''<section class="ei-article-hero"><div class="ei-wrap ei-reading">{crumbs([('홈','/'),('교육정보','/교육정보/')])}<p class="ei-kicker">{E(r['category'])}</p><h1>{E(r['title'])}</h1><p class="ei-summary">{E(r['summary'])}</p><p class="ei-meta">읽는 대상 · {E(r['audience'])}<br>내용 작성·확인 <time datetime="{DATE}">{DATE.replace('-','.')}</time></p><a class="ei-text-link" href="#local-info">동네·지점 안내 함께 찾기 ↓</a></div></section><div class="ei-wrap ei-article-layout"><nav class="ei-toc" aria-label="이 글의 목차"><strong>이 글에서</strong>{''.join(f'<a href="#{id}">{E(t)}</a>' for id,t in toc)}</nav><article class="ei-prose" data-education-article>'''
    content+='<div class="ei-intro">'+''.join('<p>'+E(p)+'</p>' for p in r['intro'])+'</div>'
    def photo(i):
        im=r['images'][i]
        return f'<figure class="ei-photo"><img src="{im["path"]}" alt="{E(im["alt"])}" width="{im["width"]}" height="{im["height"]}" loading="lazy" decoding="async"><figcaption>{E(im["alt"])}</figcaption></figure>'
    for i,s in enumerate(r['sections'],1):
        content+=f'<section id="section-{i}"><h2>{E(s["title"])}</h2>'+''.join('<p>'+E(p)+'</p>' for p in s['paragraphs'])+'</section>'
        if i in [1,3,5]:content+=photo([1,3,5].index(i))
    table=r['table']
    content+='<section id="practice-table"><h2>실천 내용을 한눈에 보기</h2><p class="ei-small">공부 순서를 정리해 보는 예시입니다. 현재 자료와 가능한 시간에 맞게 바꿔 보세요.</p><div class="ei-table-scroll" tabindex="0" role="region" aria-label="실천 예시 표"><table><thead><tr>'+''.join('<th scope="col">'+E(t)+'</th>' for t in table['headers'])+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+E(t)+'</td>' for t in row)+'</tr>' for row in table['rows'])+'</tbody></table></div></section>'
    content+='<section class="ei-checklist" id="checklist"><h2>확인 질문</h2><ul>'+''.join('<li>'+E(t)+'</li>' for t in r['checks'])+'</ul></section><section id="questions"><h2>자주 묻는 질문</h2>'+''.join('<details><summary>'+E(q)+'</summary><p>'+E(a)+'</p></details>' for q,a in r['faq'])+'</section>'
    refs=[data['sources'][s] for s in r['sources']]
    content+='<section class="ei-references" id="references"><h2>참고 자료</h2><ul>'+''.join(f'<li><a href="{E(s["url"])}">{E(s["title"])}</a><span>{E(s["scope"])}</span></li>' for s in refs)+'</ul></section>'
    related=sorted((o for o in data['articles'] if o['number']!=r['number']),key=lambda o:(o['category']!=r['category'],abs(o['number']-r['number'])))[:2]
    content+='<section id="related"><h2>함께 읽을 글</h2><div class="ei-related">'+''.join(f'<a href="{U(o["path"])}"><small>교육정보 · {E(o["category"])}</small>{E(o["title"])}<span aria-hidden="true">→</span></a>' for o in related)+''.join(f'<a href="{U(data["guides"][s]["path"])}"><small>실천 기록표가 있는 학습가이드</small>{E(data["guides"][s]["title"])}<span aria-hidden="true">→</span></a>' for s in r['guides'])+'</div><a class="ei-text-link" href="/교육정보/">교육정보 전체 목록 →</a></section>'+locator()+'</article></div>'
    g=graph(r['path'],r['title'],r['summary'],'WebPage',published)
    g.append({'@type':'Article','@id':url(r['path'])+'#article','mainEntityOfPage':{'@id':url(r['path'])+'#webpage'},'headline':r['title'],'description':r['summary'],'abstract':r['intro'][0],'datePublished':published,'dateModified':DATE,'author':{'@id':DOMAIN+'/#organization'},'publisher':{'@id':DOMAIN+'/#organization'},'inLanguage':'ko-KR','articleSection':r['category'],'image':[DOMAIN+im['path'] for im in r['images']],'citation':[s['url'] for s in refs]})
    g.append({'@type':'FAQPage','@id':url(r['path'])+'#questions','mainEntity':[{'@type':'Question','name':q,'acceptedAnswer':{'@type':'Answer','text':a}} for q,a in r['faq']]})
    return r['path'],r['summary'],shell(r['path'],r['title'],r['summary'],content,g,image)

def recommendation(path,context,rows):
    if context:
        if context.get('subject')=='영어':numbers=[10,6]
        elif context.get('subject')=='수학':numbers=[20,6]
        elif context.get('stage')=='고등':numbers=[21,27]
        elif context.get('stage')=='초등':numbers=[13,15]
        elif context.get('stage')=='중등':numbers=[2,30]
        else:numbers=[17,25]
    elif path.startswith('/지점안내/'):numbers=[19,24]
    elif path.startswith('/선생님찾기/'):numbers=[11,19]
    elif path.startswith('/학습가이드/'):
        guide=next((s for s in load(DATA)['guides'].values() if s['path']==path),None)
        hits=[r for r in rows if guide and guide['slug'] in r['guides']]
        numbers=[r['number'] for r in hits[:2]] or [17,6]
        if len(numbers)==1:numbers.append(15 if numbers[0]!=15 else 17)
    else:numbers=[30,11,20] if path=='/' else [17,24]
    return [rows[n-1] for n in numbers]

def bridge(path,context,rows):
    selected=recommendation(path,context,rows)
    label=(context['neighborhood']+'에서 수업을 살펴보기 전에') if context else '공부와 수업 선택에 도움이 되는 읽을거리'
    return '<section class="ei-bridge" data-education-bridge><div class="ei-bridge-wrap"><p class="ei-bridge-label">'+E(label)+'</p><h2>함께 읽는 교육정보</h2><p>시험 준비와 공부 습관, 학부모의 점검 질문을 지금의 고민에 맞춰 살펴보세요.</p><div class="ei-bridge-links">'+''.join(f'<a href="{U(r["path"])}">{E(r["title"])}<span aria-hidden="true">→</span></a>' for r in selected)+'</div><a class="ei-bridge-all" href="/교육정보/">교육정보 30개 전체 보기 →</a></div></section>'

def integrate():
    baseline=load(OUT/'baseline-manifest.json');data=load(DATA);rows=data['articles'];contexts={r['path']:r for r in inventory()}
    stamp=OUT/'publication.json'
    if not stamp.exists():dump(stamp,{'publishedAt':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).replace(microsecond=0).isoformat()})
    published=load(stamp)['publishedAt']
    new=set();locations=[]
    for r in contexts.values():
        if r['role']=='overview':locations.append({'kind':'neighborhood','region':r['region'],'label':r['neighborhood'],'path':U(r['path'])})
    locations += [{'kind':'center','region':c['region'],'label':c['routeName'],'path':U(center_path(c))} for c in FACTS['centers']]
    locations.sort(key=lambda r:(r['region'],r['kind'],r['label']));assert len(locations)==564
    dump(ROOT/'assets/education-locations.json',locations);new.add('assets/education-locations.json')
    for r in rows:
        for im in r['images']:
            original=SOURCE/'1 이미지'/im['source'];raw=original.read_bytes();assert digest(raw)==im['sha256']
            write(ROOT/im['path'].lstrip('/'),raw);new.add(im['path'].lstrip('/'))
    changed=[];context_counts=Counter()
    def integrate_existing(name):
        p=ROOT/name;old=p.read_text('utf-8-sig');text=old;path='/' if name=='index.html' else '/'+name[:-10]
        if 'data-education-nav' not in text:
            text,count=re.subn(r'(<div\b[^>]*class="(?:nav-links|lg-nav-links|tf-nav-links)"[^>]*>)',lambda m:m.group(1)+NAV,text,count=1)
            assert count==1,name
        if 'data-education-style' not in text:text=text.replace('</head>',CSS+'</head>',1)
        if 'data-education-bridge' not in text:
            assert text.count('</main>')==1,name
            text=text.replace('</main>',bridge(path,contexts.get(path),rows)+'</main>')
        text=patch_dates(text)
        if text!=old:write(p,text)
        return name,digest(p.read_bytes())!=baseline['files'][name]
    html_names=[n for n in baseline['files'] if n.endswith('.html')]
    with ThreadPoolExecutor(max_workers=8) as pool:
        for i,(name,was_changed) in enumerate(pool.map(integrate_existing,html_names),1):
            if was_changed:changed.append(name)
            context_counts[name.split('/')[0] if '/' in name else '/']+=1
            if i%2000==0:print('Integrated education links through',i,'HTML pages',flush=True)
    pages=[listing(data,published)]+[article(r,data,published) for r in rows]
    descriptions=load(ROOT/'seo-descriptions.json')
    for path,summary,markup in pages:
        name=path.strip('/')+'/index.html';write(ROOT/name,markup);new.add(name)
        descriptions['pages'][path.rstrip('/')]=dict(description=summary,sources=[summary])
    dump(ROOT/'seo-descriptions.json',descriptions)
    sitemap=(ROOT/'sitemap.xml').read_text('utf-8');existing={unquote(urlsplit(u).path):u for u in etree.fromstring(sitemap.encode()).xpath('//*[local-name()="loc"]/text()')}
    changed_urls={existing['/' if n=='index.html' else '/'+n[:-10]] for n in changed}
    changed_urls|={existing[path] for path,_,_ in pages if path in existing};seen=set()
    def date(m):
        if escape.unescape(m.group(2)) in changed_urls:seen.add(escape.unescape(m.group(2)));return m.group(1)+DATE+m.group(3)
        return m.group(0)
    sitemap=re.sub(r'(<url>\s*<loc>([^<]+)</loc>\s*<lastmod>)[^<]+(</lastmod>)',date,sitemap);assert seen==changed_urls
    for path,_,_ in pages:
        if path not in existing:sitemap=sitemap.replace('</urlset>',f'  <url>\n    <loc>{url(path)}</loc>\n    <lastmod>{DATE}</lastmod>\n  </url>\n</urlset>')
    write(ROOT/'sitemap.xml',sitemap)
    raw=(ROOT/'rss.xml').read_bytes();feed=etree.fromstring(raw,etree.XMLParser(resolve_entities=False,no_network=True,remove_blank_text=True,strip_cdata=False));channel=feed.find('channel')
    identities=[identity(item) for item in channel.findall('item')];assert len(identities) in [99,129]
    for item in channel.findall('item'):
        canonical=item.findtext('link');path=unquote(urlsplit(canonical).path);name='index.html' if path=='/' else path.strip('/')+'/index.html'
        content,_=body(html.document_fromstring((ROOT/name).read_bytes()),canonical);item.find('description').text=etree.CDATA(content)
    existing_links={item.findtext('link') for item in channel.findall('item')}
    for r in rows:
        canonical=url(r['path'])
        if canonical in existing_links:continue
        item=etree.SubElement(channel,'item');etree.SubElement(item,'title').text=r['title'];etree.SubElement(item,'link').text=canonical;etree.SubElement(item,'guid',isPermaLink='true').text=canonical;etree.SubElement(item,'pubDate').text=format_datetime(datetime.datetime.fromisoformat(published));content,_=body(html.document_fromstring((ROOT/r['path'].strip('/')/'index.html').read_bytes()),canonical);etree.SubElement(item,'description').text=etree.CDATA(content)
    channel.find('description').text='지점·수강 안내, 선생님 소개, 학생·학부모를 위한 학습가이드와 교육정보를 제공합니다.'
    if etree.tostring(feed,encoding='UTF-8',xml_declaration=True,pretty_print=True)!=raw:channel.find('lastBuildDate').text=format_datetime(datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).replace(microsecond=0))
    write(ROOT/'rss.xml',etree.tostring(feed,encoding='UTF-8',xml_declaration=True,pretty_print=True))
    assert [identity(item) for item in channel.findall('item')][:99]==identities[:99]
    new|={'assets/education-info.css','assets/education-info.js'}
    names=sorted(set(baseline['files'])|new);text_names=set(baseline['textSha256'])|{n for n in new if not n.endswith('.jpg')}
    def hashes(n):
        b=(ROOT/n).read_bytes();return n,digest(b),digest(b.decode('utf-8').replace('\r\n','\n').encode()) if n in text_names else None
    with ThreadPoolExecutor(max_workers=12) as pool:values=list(pool.map(hashes,names))
    manifest=load(ROOT/'release-public-manifest.json');manifest['files']={n:h for n,h,_ in values};manifest['textSha256']={n:h for n,_,h in values if h};manifest['sitemapPages']=sum(n.endswith('.html') for n in names);dump(ROOT/'release-public-manifest.json',manifest)
    report={'articles':30,'newHtmlPages':31,'photos':90,'photosPerArticle':3,'publicFiles':len(names),'htmlPages':manifest['sitemapPages'],'rssItems':len(channel.findall('item')),'existingRssIdentitiesPreserved':99,'existingHtmlWithMenuAndRelatedLinks':len(changed),'existingPageFamilies':dict(context_counts),'locationOptions':len(locations),'newPublicFiles':sorted(new),'modifiedHtml':changed,'sourceContent':str(DATA),'deployed':False}
    dump(OUT/'implementation.json',report);print(json.dumps({k:v for k,v in report.items() if k not in ['newPublicFiles','modifiedHtml','sourceContent']},ensure_ascii=False))

if __name__=='__main__':integrate()
