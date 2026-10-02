"""Build authored learning guides locally; no commit, upload or deployment."""
import datetime, hashlib, html as esc, json, re, zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
from email.utils import format_datetime
from lxml import html, etree
from seo_feed_content import body, identity

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'tools/data/learning-guides'
OUT = Path(r'C:\Users\1992k\Desktop\CodexData\outputs\site3-learning-guides-20261002')
DOMAIN = 'https://xn--sp5b72l1taf0p.com'
DATE = '2026-10-02'
CATEGORIES = {
 'exams': ('시험과전환', '시험·방학·학교급 전환', '시험 범위부터 수행평가, 방학 복습과 과목 선택까지 준비합니다.'),
 'math': ('수학학습', '수학 개념·풀이', '계산의 이유, 조건 해석, 그래프와 서술 풀이를 연결합니다.'),
 'english': ('영어학습', '영어 읽기·듣기·쓰기', '단어를 아는 것에서 문장을 읽고 직접 사용하는 것으로 이어갑니다.'),
 'reading': ('읽기와탐구', '국어·사회·과학·발표', '글과 자료의 근거를 확인하고 설명·탐구·발표에 적용합니다.'),
 'habits': ('공부습관', '계획·복습·공부 습관', '시간표와 과제에 확인 가능한 행동을 붙이고 실제 수행으로 조정합니다.'),
 'parents': ('학부모안내', '학부모 상담·선택', '상담 자료, 비용, 수업 방식과 학생의 부담을 함께 살펴봅니다.')
}
AUDIENCES = {'elementary':'초등학생','middle':'중학생','high':'고등학생','parent':'학부모'}
TOPS = ['index.html', *[x+'/index.html' for x in ['학습관리','지점안내','전국센터','과목별학원','상담문의']]]
SOURCES = json.loads((DATA/'sources.json').read_text('utf-8-sig'))['sources']
E = lambda s: esc.escape(str(s), quote=True)
url = lambda path: DOMAIN + quote(path, safe='/')
link = lambda slug: '/학습가이드/'+slug+'/'
digest = lambda b: hashlib.sha256(b).hexdigest()

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = value.encode('utf-8') if isinstance(value,str) else value
    if not path.exists() or path.read_bytes() != raw:
        path.write_bytes(raw)

def dump(path, obj):
    write(path, json.dumps(obj,ensure_ascii=False,indent=2)+'\n')

def articles():
    rows=[]
    for f in sorted(DATA.glob('*.json')):
        if f.name=='sources.json': continue
        for row in json.loads(f.read_text('utf-8-sig')):
            row.setdefault('category',f.stem)
            row.setdefault('audience',' · '.join(AUDIENCES[a] for a in row['audiences']))
            row.setdefault('tags',[CATEGORIES[row['category']][1],row['title']])
            row['related']=['숙제도움범위' if s=='도움줄이기' else s for s in row['related']]
            rows.append(row)
    slugs={r['slug'] for r in rows}
    assert len(rows)==len(slugs)==48
    assert len({r['title'] for r in rows})==48
    for r in rows:
        assert len(r['summary'])<=80 and r['summary'].endswith('.')
        assert len(r['steps'])==4 and len(r['worksheet'])==4 and len(r['faq'])==2
        assert set(r['related'])<=slugs and r['slug'] not in r['related']
        assert set(r['sources'])<=SOURCES.keys()
    assert all(sum(r['category']==c for r in rows)==8 for c in CATEGORIES)
    return rows

def nav():
    return '''<header class="lg-header"><nav class="lg-wrap lg-nav" aria-label="주요 메뉴"><a class="lg-brand" href="/"><span class="lg-mark" aria-hidden="true">W</span><span><small>STUDY COACHING</small>와와학습코칭학원</span></a><div class="lg-nav-links"><a href="/학습관리/">학습관리</a><a href="/학습가이드/" aria-current="page">학습가이드</a><a href="/지점안내/">지점안내</a><a href="/상담문의/">상담문의</a></div></nav></header>'''

def shell(path,title,description,content,graph):
    canonical=url(path)
    return f'''<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)} | 와와학습코칭학원</title><meta name="description" content="{E(description)}"><meta name="robots" content="index, follow">
<link rel="canonical" href="{canonical}"><link rel="alternate" type="application/rss+xml" title="와와학습코칭학원 RSS" href="{DOMAIN}/rss.xml">
<meta property="og:type" content="{'article' if path.count('/')==3 and any(n.get('@type')=='Article' for n in graph) else 'website'}"><meta property="og:title" content="{E(title)}"><meta property="og:url" content="{canonical}"><meta property="og:description" content="{E(description)}"><meta property="og:image" content="{DOMAIN}/assets/brand-upgrade-v1/brand-learning.png"><meta property="og:image:alt" content="와와의 학생 중심 학습을 표현한 브랜드 일러스트"><meta name="twitter:card" content="summary"><meta name="twitter:description" content="{E(description)}">
<link rel="icon" href="/assets/favicon.png"><link rel="stylesheet" href="/assets/learning-guides.css"><script defer src="/assets/learning-guides.js"></script>
<script type="application/ld+json">{json.dumps({'@context':'https://schema.org','@graph':graph},ensure_ascii=False).replace('</','<\\/')}</script></head>
<body class="learning-guides"><a class="lg-skip" href="#main">본문 바로가기</a>{nav()}<main id="main">{content}</main>
<footer class="lg-footer"><div class="lg-wrap"><strong>와와학습코칭학원</strong><p>학생과 학부모가 함께 읽는 학습가이드</p><nav aria-label="하단 메뉴"><a href="/학습가이드/">학습가이드 전체</a><a href="/전국센터/">동네별 학습 안내</a><a href="/지점안내/">실제 지점 안내</a><a href="/상담문의/">상담문의</a></nav></div></footer></body></html>'''

def page_graph(path,title,summary,crumbs,kind='CollectionPage'):
    canonical=url(path)
    return [
      {'@type':kind,'@id':canonical+'#webpage','url':canonical,'name':title,'description':summary,'datePublished':DATE,'dateModified':DATE,'inLanguage':'ko-KR','isPartOf':{'@id':DOMAIN+'/#website'},'publisher':{'@id':DOMAIN+'/#organization'},'breadcrumb':{'@id':canonical+'#breadcrumb'}},
      {'@type':'BreadcrumbList','@id':canonical+'#breadcrumb','itemListElement':[{'@type':'ListItem','position':i,'name':t,'item':url(p)} for i,(t,p) in enumerate(crumbs,1)]}]

def breadcrumbs(crumbs):
    return '<nav class="lg-breadcrumb" aria-label="현재 위치">'+'<span aria-hidden="true">/</span>'.join(f'<a href="{E(p)}">{E(t)}</a>' for t,p in crumbs)+'</nav>'

def card(r):
    c=CATEGORIES[r['category']]
    hay=' '.join([r['title'],r['summary'],r['answer'],*r['tags'],*r['checks'],*(AUDIENCES[a] for a in r['audiences'])])
    return f'''<article class="lg-card" data-guide-card data-category="{r['category']}" data-audiences="{' '.join(r['audiences'])}" data-search="{E(hay)}"><p class="lg-kicker">{E(c[1])}</p><h3><a href="{E(link(r['slug']))}">{E(r['title'])}</a></h3><p>{E(r['summary'])}</p><div class="lg-tags">{''.join('<span>'+AUDIENCES[a]+'</span>' for a in r['audiences'])}</div><a class="lg-read" href="{E(link(r['slug']))}">가이드 읽기 <span aria-hidden="true">↗</span><span class="lg-sr"> · {E(r['title'])}</span></a></article>'''

def listing(rows, category=None):
    title=CATEGORIES[category][1] if category else '학습가이드'
    summary=(CATEGORIES[category][2] if category else '학생과 학부모를 위한 시험·과목 학습·공부 습관·수업 선택 가이드와 실천 기록표를 제공합니다.')
    path='/학습가이드/'+CATEGORIES[category][0]+'/' if category else '/학습가이드/'
    subset=[r for r in rows if not category or r['category']==category]
    crumbs=[('홈','/'),('학습가이드','/학습가이드/')]
    if category: crumbs.append((title,path))
    categories=''.join(f'<a class="lg-category" href="/학습가이드/{slug}/"><b>{name}</b><span>{desc}</span><small>8개 가이드 →</small></a>' for slug,name,desc in CATEGORIES.values())
    options=''.join(f'<option value="{key}">{name}</option>' for key,(_,name,_) in CATEGORIES.items())
    audience_options=''.join(f'<option value="{key}">{value}</option>' for key,value in AUDIENCES.items())
    filters=f'''<form data-guide-filter class="lg-filter" aria-label="학습가이드 찾기" hidden><div><label for="guide-search">고민이나 주제 검색</label><input id="guide-search" type="search" placeholder="예: 오답, 수행평가, 비용, 숙제" autocomplete="off"></div><div><label for="guide-audience">읽는 대상</label><select id="guide-audience"><option value="">전체 대상</option>{audience_options}</select></div><div><label for="guide-category">주제</label><select id="guide-category"><option value="">전체 주제</option>{options}</select></div><button type="reset" class="lg-button lg-secondary">초기화</button><p data-guide-count role="status" aria-live="polite">{len(subset)}개 가이드</p></form>'''
    content=f'''<section class="lg-hero"><div class="lg-wrap">{breadcrumbs(crumbs)}<p class="lg-kicker">LEARNING GUIDES · 학생과 학부모를 위한 공부 자료</p><h1>{E(title)}</h1><p class="lg-lead">{'지금의 고민에서 시작해,<br>다음에 해 볼 행동까지.' if not category else E(summary)}</p><p>{'시험 준비부터 수업 선택까지, 48개 가이드에서 필요한 설명과 실천 기록표를 찾아보세요.' if not category else '각 글에서 직접 해 볼 예시, 확인 질문, 기록표를 함께 살펴보세요.'}</p><div class="lg-hero-actions"><a class="lg-button" href="#guides">필요한 가이드 찾기</a><a class="lg-text-link" href="/학습가이드/">{'6개 주제 · 48개 가이드' if not category else '전체 가이드 보기'} →</a></div></div></section>'''
    if not category:
        starters=['시험4주준비','수학오류기록','영어단어사용','플래너완료기준','학원상담자료','숙제도움범위']
        content+='<section class="lg-section"><div class="lg-wrap"><p class="lg-kicker">START HERE</p><h2>이런 고민부터 찾아보세요</h2><div class="lg-starts">'+''.join(f'<a href="{link(s)}">{E(next(r["title"] for r in rows if r["slug"]==s))}<span aria-hidden="true">→</span></a>' for s in starters)+'</div></div></section>'
        content+='<section class="lg-section lg-tint"><div class="lg-wrap"><h2>주제별로 살펴보기</h2><div class="lg-category-grid">'+categories+'</div></div></section>'
    content+=f'''<section class="lg-section" id="guides"><div class="lg-wrap"><div class="lg-section-heading"><div><p class="lg-kicker">FIND YOUR GUIDE</p><h2>{'전체' if not category else E(title)} 가이드</h2></div><p>읽고 → 한 가지 실행하고 → 다시 확인하세요.</p></div>{filters}<noscript><p>아래 목록에서 모든 가이드를 읽을 수 있습니다. 검색·필터는 자바스크립트를 켜면 사용할 수 있습니다.</p></noscript><p class="lg-no-results" data-guide-empty hidden>조건에 맞는 가이드가 없습니다. 검색어를 짧게 바꾸거나 필터를 초기화해 보세요.</p><div class="lg-card-grid">{''.join(card(r) for r in subset)}</div></div></section><section class="lg-section lg-tint"><div class="lg-wrap lg-reading"><h2>읽은 내용을 기록으로 남겨 보세요</h2><p>각 글의 기록표에서 필요한 항목을 골라 작성하고 텍스트 파일로 저장하거나 인쇄할 수 있습니다. 빈 기록표도 내려받을 수 있습니다.</p><p>이 가이드는 일반적인 학습 방법을 설명합니다. 학교의 평가·과목 운영은 해당 학교의 최신 안내로, 지점의 수강 조건은 실제 지점 안내와 상담으로 확인하세요.</p><a class="lg-text-link" href="/지점안내/">실제 지점의 수강 안내 확인 →</a><p class="lg-date">내용 확인·작성 <time datetime="{DATE}">2026.10.02</time></p></div></section>'''
    graph=page_graph(path,title,summary,crumbs)
    graph.append({'@type':'ItemList','@id':url(path)+'#guides','numberOfItems':len(subset),'itemListElement':[{'@type':'ListItem','position':i,'name':r['title'],'url':url(link(r['slug']))} for i,r in enumerate(subset,1)]})
    return path,summary,shell(path,title,summary,content,graph)

def article(r,by_slug):
    category=CATEGORIES[r['category']]; path=link(r['slug'])
    crumbs=[('홈','/'),('학습가이드','/학습가이드/'),(category[1],'/학습가이드/'+category[0]+'/')]
    titles=[('answer','먼저 확인할 핵심'),('situation','내 상황 살펴보기'),('steps','순서대로 해 보기'),('example','직접 해 볼 예시'),('worksheet','실천 기록표'),('check','확인 질문'),('faq','자주 묻는 질문'),('sources','참고 자료'),('related','다음으로 읽을 가이드')]
    content=f'''<section class="lg-article-hero"><div class="lg-wrap lg-reading">{breadcrumbs(crumbs)}<p class="lg-kicker">{E(category[1])}</p><h1>{E(r['title'])}</h1><p class="lg-lead">{E(r['summary'])}</p><p class="lg-audience"><strong>이런 분께</strong> {E(r['audience'])}</p><p class="lg-date">내용 확인·작성 <time datetime="{DATE}">2026.10.02</time></p></div></section><div class="lg-wrap lg-article-layout"><nav class="lg-toc" aria-label="이 글의 목차"><strong>이 글에서</strong>{''.join(f'<a href="#{i}">{E(t)}</a>' for i,t in titles)}</nav><article class="lg-prose"><section id="answer" class="lg-answer"><p class="lg-kicker">먼저 확인할 핵심</p><h2>어디서 시작하면 좋을까요?</h2><p>{E(r['answer'])}</p></section><section id="situation"><h2>내 상황 살펴보기</h2>{''.join(f'<h3>{E(t)}</h3><p>{E(b)}</p>' for t,b in r['signals'])}</section><section id="steps"><h2>순서대로 해 보기</h2><ol class="lg-steps">{''.join(f'<li><h3>{E(t)}</h3><p>{E(b)}</p></li>' for t,b in r['steps'])}</ol></section>'''
    ex=r['example']
    content+=f'<section id="example"><p class="lg-kicker">PRACTICE</p><h2>{E(ex["title"])}</h2>'+''.join('<p>'+E(p)+'</p>' for p in ex['text'])+f'<div class="lg-table-scroll" tabindex="0" role="region" aria-label="{E(ex["title"])} 비교표"><table><caption>{E(ex["title"])} · 확인할 내용</caption><thead><tr>'+''.join(f'<th scope="col">{E(v)}</th>' for v in ex['headers'])+'</tr></thead><tbody>'+''.join('<tr>'+''.join(f'<td>{E(v)}</td>' for v in row)+'</tr>' for row in ex['rows'])+'</tbody></table></div></section>'
    worksheet='/assets/learning-guide-worksheets/'+r['slug']+'.txt'
    content+='<section id="worksheet"><p class="lg-kicker">TRY & CHECK</p><h2>실천 기록표</h2><p>아래 네 항목에 지금의 상황과 실행 결과를 남겨 보세요. 완성된 답안보다 다음에 확인할 지점을 찾는 기록입니다.</p><dl class="lg-worksheet-outline">'+''.join(f'<dt>{E(t)}</dt><dd>{E(h)}</dd>' for t,h in r['worksheet'])+f'</dl><a class="lg-text-link" href="{E(worksheet)}" download>빈 기록표 내려받기 (.txt) ↓</a>'
    content+=f'''<form data-guide-recorder data-title="{E(r['title'])}" data-slug="{r['slug']}" class="lg-recorder" aria-label="실천 기록 작성" hidden><p class="lg-record-notice">이 칸에 쓴 내용은 사이트로 전송되지 않습니다. 페이지를 떠나면 사라지므로 먼저 파일로 저장하세요. 이름·학교·연락처 등 개인정보는 적지 않아도 됩니다.</p><div class="lg-record-fields"><label for="record-date">실행한 날짜<input id="record-date" type="date" data-record-date></label>{''.join(f'<label for="record-{i}">{E(t)}<textarea id="record-{i}" data-record-field data-label="{E(t)}" rows="3" placeholder="{E(h)}" maxlength="2000"></textarea></label>' for i,(t,h) in enumerate(r['worksheet'],1))}</div><div class="lg-record-actions"><button type="button" data-record-download class="lg-button">작성 내용 저장 (.txt)</button><button type="button" data-record-print class="lg-button lg-secondary">기록표 인쇄</button><button type="reset" class="lg-text-button">작성 내용 지우기</button></div><p data-record-status role="status" aria-live="polite"></p></form></section>'''
    content+='<section id="check"><h2>확인 질문</h2><ul class="lg-checks">'+''.join('<li>'+E(x)+'</li>' for x in r['checks'])+'</ul><div class="lg-next"><h3>다음 확인은 이렇게</h3><p>'+E(r['next'])+'</p></div></section><section id="faq"><h2>자주 묻는 질문</h2>'+''.join(f'<details data-guide-faq><summary>{E(q)}</summary><p>{E(a)}</p></details>' for q,a in r['faq'])+'</section>'
    content+='<section id="sources"><h2>참고 자료</h2><p>학습 방법의 일반 원리와 자료를 찾을 경로를 확인했습니다. 위의 연습 예시와 기록표는 이 글에서 직접 해 볼 수 있도록 구성한 것입니다.</p><ul class="lg-sources">'
    for code in r['sources']:
        s=SOURCES[code]
        content+=f'<li><a href="{E(s["url"])}" target="_blank" rel="noopener noreferrer">{E(s["title"])} <span class="lg-sr">(새 창)</span></a><p>{E(s["date"])} · {E(s["scope"])}</p></li>'
    content+='</ul>'
    if any(SOURCES[c]['type']=='research' for c in r['sources']):
        content+='<p class="lg-note">해외 연구 안내의 대상·언어·수업 환경은 한국 학교와 다를 수 있습니다. 일반 원리를 참고하되 실제 난도와 확인 결과에 맞춰 조정하세요.</p>'
    content+='</section><section id="related"><h2>다음으로 읽을 가이드</h2><ul class="lg-related">'+''.join(f'<li><a href="{E(link(s))}">{E(by_slug[s]["title"])} →</a></li>' for s in r['related'])+'</ul></section><section class="lg-service-note"><h2>학교·지점 안내가 필요하다면</h2><p>학교의 평가·과목 운영은 학교의 최신 안내를 확인하세요. 이 글에서 다루는 과목이나 연습 방법이 모든 지점의 실제 개설 수업을 뜻하지는 않습니다.</p><a href="/지점안내/">지점별 과목·학년·수강 조건 확인 →</a></section></article></div>'
    graph=page_graph(path,r['title'],r['summary'],crumbs+[(r['title'],path)],'WebPage')
    graph.append({'@type':'Article','@id':url(path)+'#article','url':url(path),'mainEntityOfPage':{'@id':url(path)+'#webpage'},'headline':r['title'],'description':r['summary'],'abstract':r['answer'],'datePublished':DATE,'dateModified':DATE,'inLanguage':'ko-KR','articleSection':category[1],'publisher':{'@id':DOMAIN+'/#organization'},'citation':[SOURCES[c]['url'] for c in r['sources']]})
    graph.append({'@type':'FAQPage','@id':url(path)+'#faq','mainEntity':[{'@type':'Question','name':q,'acceptedAnswer':{'@type':'Answer','text':a}} for q,a in r['faq']]})
    blank=r['title']+'\n실천 기록\n\n실행한 날짜: __________\n\n'+'\n\n'.join(f'{i}. {t}\n확인: {h}\n기록: \n' for i,(t,h) in enumerate(r['worksheet'],1))+'\n다음 확인: '+r['next']+'\n출처: '+url(path)+'\n'
    # BOM helps Korean TXT files open correctly in common Windows editors.
    write(ROOT/worksheet.lstrip('/'),blank.encode('utf-8-sig'))
    return path,r['summary'],shell(path,r['title'],r['summary'],content,graph)

def integrate():
    rows=articles(); by_slug={r['slug']:r for r in rows}; pages=[]
    for cat in [None,*CATEGORIES]: pages.append(listing(rows,cat))
    for r in rows: pages.append(article(r,by_slug))
    for path,summary,markup in pages:
        write(ROOT/path.strip('/')/'index.html',markup)
    for name in TOPS:
        text=(ROOT/name).read_text('utf-8')
        if 'data-learning-guide-nav' not in text:
            text,n=re.subn(r'(<div class="nav-links">)',r'\1<a href="/학습가이드/" data-learning-guide-nav>학습가이드</a>',text,count=1);assert n==1,name
        if 'data-learning-guide-entry' not in text:
            entry='<section class="section" data-learning-guide-entry><div class="wrap"><p class="eyebrow">학생과 학부모를 위한 실천 자료</p><h2>지금의 고민을 학습가이드에서 찾아보세요</h2><p>시험·방학 준비, 수학·영어 학습, 읽기·탐구, 공부 습관, 학부모 상담과 선택을 다룬 48개 가이드입니다. 각 글에서 예시·확인 질문·실천 기록표를 함께 확인할 수 있습니다.</p><p><a class="btn" href="/학습가이드/">학습가이드 전체 보기 →</a></p></div></section>'
            assert text.count('</main>')==1
            text=text.replace('</main>',entry+'</main>')
        # Preserve original source formatting and all non-page schema facts.
        def date_patch(m):
            payload=json.loads(m.group(2))
            def visit(x):
                if isinstance(x,list):
                    for y in x:visit(y)
                elif isinstance(x,dict):
                    if x.get('@type') in ['WebPage','CollectionPage','AboutPage','ContactPage'] and x.get('dateModified'):x['dateModified']=DATE
                    for y in x.values():visit(y)
            visit(payload)
            return m.group(1)+json.dumps(payload,ensure_ascii=False,separators=(',',':'))+m.group(3)
        text=re.sub(r'(<script type="application/ld\+json">)(.*?)(</script>)',date_patch,text,flags=re.S)
        write(ROOT/name,text)
    descriptions=json.loads((ROOT/'seo-descriptions.json').read_text('utf-8-sig'))
    for path,summary,_ in pages:descriptions['pages'][path.rstrip('/') or '/']={'description':summary,'sources':[summary]}
    dump(ROOT/'seo-descriptions.json',descriptions)
    # Keep the original XML formatting; only six changed hubs and new URLs differ.
    with zipfile.ZipFile(OUT/'guides-before.zip') as backup:
        sitemap_text=backup.read('sitemap.xml').decode('utf-8')
    sitemap=etree.fromstring(sitemap_text.encode('utf-8'),etree.XMLParser(resolve_entities=False,no_network=True,remove_blank_text=True))
    ns='{http://www.sitemaps.org/schemas/sitemap/0.9}'
    entries={unquote(urlsplit(e.findtext(ns+'loc')).path):e for e in sitemap}
    for name in TOPS:
        path='/' if name=='index.html' else '/'+name[:-10]
        canonical=entries[path].findtext(ns+'loc')
        pattern=r'(<url>\s*<loc>'+re.escape(E(canonical))+r'</loc>\s*<lastmod>)[^<]+(</lastmod>)'
        sitemap_text,count=re.subn(pattern,lambda m:m.group(1)+DATE+m.group(2),sitemap_text)
        assert count==1,name
    for path,_,_ in pages:
        if path not in entries:
            entry='  <url>\n    <loc>'+E(url(path))+'</loc>\n    <lastmod>'+DATE+'</lastmod>\n  </url>\n'
            sitemap_text=sitemap_text.replace('</urlset>',entry+'</urlset>')
    write(ROOT/'sitemap.xml',sitemap_text)
    original_feed=(ROOT/'rss.xml').read_bytes()
    feed=etree.fromstring(original_feed,etree.XMLParser(resolve_entities=False,no_network=True,remove_blank_text=True,strip_cdata=False))
    channel=feed.find('channel');existing={i.findtext('link'):i for i in channel.findall('item')};old=[identity(i) for i in channel.findall('item') if '/%ED%95%99%EC%8A%B5%EA%B0%80%EC%9D%B4%EB%93%9C/' not in i.findtext('link')]
    now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).replace(microsecond=0)
    added=0
    for r in rows:
        canonical=url(link(r['slug']));markup=(ROOT/link(r['slug']).strip('/')/'index.html').read_bytes(); exported,_=body(html.document_fromstring(markup),canonical)
        item=existing.get(canonical)
        if item is None:
            item=etree.SubElement(channel,'item');etree.SubElement(item,'title');etree.SubElement(item,'link').text=canonical;etree.SubElement(item,'guid',isPermaLink='true').text=canonical;etree.SubElement(item,'pubDate').text=format_datetime(now);etree.SubElement(item,'description');added+=1
        item.find('title').text=r['title'];item.find('description').text=etree.CDATA(exported)
    channel.find('description').text='영어·수학 학원의 지점·수강 안내와 학생·학부모를 위한 학습가이드·실천 기록표를 제공합니다.'
    if added or etree.tostring(feed,encoding='UTF-8',xml_declaration=True,pretty_print=True)!=original_feed:channel.find('lastBuildDate').text=format_datetime(now)
    write(ROOT/'rss.xml',etree.tostring(feed,encoding='UTF-8',xml_declaration=True,pretty_print=True))
    assert len(old)==50 and len(channel.findall('item'))==98
    baseline=json.loads((OUT/'baseline-manifest.json').read_text('utf-8-sig'))
    new_names={path.strip('/')+'/index.html' for path,_,_ in pages}|{'assets/learning-guides.css','assets/learning-guides.js'}|{'assets/learning-guide-worksheets/'+r['slug']+'.txt' for r in rows}
    allowed=set(TOPS)|{'sitemap.xml','rss.xml'}
    selected=sorted(set(baseline['files'])|new_names)
    text_names=set(baseline.get('textSha256',{}))|new_names
    def hash_file(name):
        raw=(ROOT/name).read_bytes()
        normalized=digest(raw.decode('utf-8').replace('\r\n','\n').encode('utf-8')) if name in text_names else None
        return name,digest(raw),normalized
    with ThreadPoolExecutor(max_workers=16) as pool:
        hashes=list(pool.map(hash_file,selected))
    hash_map={n:h for n,h,_ in hashes}
    changed=[n for n,h in baseline['files'].items() if hash_map[n]!=h]
    assert set(changed)<=allowed,changed
    manifest=json.loads((ROOT/'release-public-manifest.json').read_text('utf-8-sig'))
    manifest['files']=hash_map
    manifest['textSha256']={n:h for n,_,h in hashes if h is not None}
    manifest['sitemapPages']=8458
    if set(baseline['files'])==set(json.loads((ROOT/'release-public-manifest.json').read_text('utf-8-sig'))['files']):manifest['createdAt']=now.isoformat()
    dump(ROOT/'release-public-manifest.json',manifest)
    dump(OUT/'implementation.json',{'articles':48,'categoryHubs':6,'guidePages':55,'blankWorksheets':48,'publicHtml':8458,'publicFiles':len(manifest['files']),'newPublicFiles':sorted(new_names),'changedExistingPublicFiles':changed,'originalRssItems':old,'deployed':False})
    print(json.dumps({'articles':48,'guidePages':55,'newPublicFiles':len(new_names),'publicFiles':len(manifest['files']),'changedExisting':changed,'deployed':False},ensure_ascii=False))

if __name__=='__main__':integrate()
