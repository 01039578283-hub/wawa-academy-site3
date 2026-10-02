"""Import supplied masked teacher introductions and add bounded local navigation.

All rows remain independent. Portraits are explicitly representative images,
never asserted to identify named teachers. Raw imports and release evidence are
private. Old guide-only builders must not replace the combined release manifest.
"""
from pathlib import Path
from collections import defaultdict, Counter
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote, unquote, urlsplit
from email.utils import format_datetime
import datetime, hashlib, html as escape, json, re, shutil, struct, sys
import openpyxl
from lxml import html, etree
from seo_feed_content import body, identity
from improve_neighborhood_pages import inventory, FACTS, SUBJECTS, center_path

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(r'C:\Users\1992k\Desktop\CodexData\outputs\site3-teachers-guides-release-20261002')
INPUT=Path(r'C:\Users\1992k\Desktop\홈페이지 작업 폴더\교사 프로필')
DATA=ROOT/'tools/data/teacher-finder'
DOMAIN='https://xn--sp5b72l1taf0p.com'
DATE='2026-10-02'
E=lambda s:escape.escape(str(s),quote=True)
U=lambda s:quote(s,safe='/#')
digest=lambda b:hashlib.sha256(b).hexdigest()
url=lambda p:DOMAIN+U(p)
norm=lambda s:re.sub(r'\s+','',s).removesuffix('점')
TEACHER_NAV='<a href="/%EC%84%A0%EC%83%9D%EB%8B%98%EC%B0%BE%EA%B8%B0/" data-teacher-nav>선생님찾기</a>'
CSS='<link rel="stylesheet" href="/assets/teacher-finder.css" data-teacher-style>'

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=value.encode('utf-8') if isinstance(value,str) else value
    if not path.exists() or path.read_bytes()!=raw:path.write_bytes(raw)

def dump(path,value):write(path,json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def load(path):return json.loads(path.read_text('utf-8-sig'))

def import_data():
    source=INPUT/'교사 프로필.xlsx'
    assert digest(source.read_bytes())=='b64e270952dd8857f304dc737671c3587dba98253bc6d9b55ddd769bf2772da1'
    workbook=openpyxl.load_workbook(source,read_only=True,data_only=True)
    raw=list(workbook.active.iter_rows(values_only=True));workbook.close()
    assert len(raw)==1002 and all(len(r)==4 and all(isinstance(v,str) and v.strip() for v in r) for r in raw)
    grouped=defaultdict(list)
    for i,(branch,name,focus,intro) in enumerate(raw,1):
        assert '*' in name and intro.endswith('.')
        grouped[branch].append({'id':f'teacher-{i:04}','sourceRow':i,'branch':branch,'name':name,'focus':[v.strip() for v in focus.split('/')],'intro':intro})
    assert len(grouped)==205
    # Ten clearly distinct supplied portrait files cover the largest ten-row roster.
    # Omit visually similar variants 06/09 rather than using both at one branch.
    pool=[]
    for i in [1,2,3,4,5,7,8,10,11,12]:
        source=INPUT/f'collage-profile-{i:02}.png';rawimage=source.read_bytes()
        assert rawimage.startswith(b'\x89PNG\r\n\x1a\n')
        width,height=struct.unpack('>II',rawimage[16:24]);name=f'assets/teacher-profiles/representative-{i:02}.png'
        write(ROOT/name,rawimage);pool.append({'path':'/'+name,'sha256':digest(rawimage),'width':width,'height':height,'sourceFile':source.name})
    assert len({p['sha256'] for p in pool})==10 and max(map(len,grouped.values()))==10
    branches=[]
    neighborhoods=defaultdict(set)
    for row in SUBJECTS:neighborhoods[(row['path'].strip('/').split('/')[1],row['center'])].add(row['neighborhood'])
    for label,teachers in grouped.items():
        hits={c['key']:c for c in FACTS['centers'] if norm(label) in [norm(c.get(k,'')) for k in ['sourceName','routeName','key']]}
        assert len(hits)<=1
        center=next(iter(hits.values())) if hits else None
        if center:assert (ROOT/center_path(center).strip('/')/'index.html').is_file()
        offset=int(digest(label.encode())[:8],16)%len(pool)
        for index,t in enumerate(teachers):t['image']=pool[(offset+index)%len(pool)]
        branch={'label':label,'path':'/선생님찾기/'+label+'/','teachers':teachers,'region':center['region'] if center else '',
                'centerKey':center['key'] if center else None,'branchPath':center_path(center) if center else None,
                'address':center['address'] if center else None,'district':center['district'] if center else None}
        branch['neighborhoods']=sorted(neighborhoods[(center['region'],center['routeName'])]) if center else []
        branches.append(branch)
    branches.sort(key=lambda b:(not bool(b['region']),b['region'],b['label']))
    data={'sourceSha256':digest((INPUT/'교사 프로필.xlsx').read_bytes()),'sourceRows':1002,'branches':branches,'images':pool,
          'photoMeaning':'User authorized representative profile images; no verified teacher-photo identity association.',
          'rowPolicy':'Retain every row, including same-branch equal masked names; row counts do not prove unique people.'}
    dump(DATA/'import.json',data)
    return data

def crumbs(items):return '<nav class="tf-breadcrumb" aria-label="현재 위치">'+'<span aria-hidden="true">/</span>'.join(f'<a href="{U(p)}">{E(n)}</a>' for n,p in items)+'</nav>'

def shell(path,title,desc,content,items):
    graph=[{'@type':'CollectionPage','@id':url(path)+'#webpage','url':url(path),'name':title,'description':desc,'inLanguage':'ko-KR',
            'datePublished':DATE,'dateModified':DATE,'isPartOf':{'@id':DOMAIN+'/#website'},'publisher':{'@id':DOMAIN+'/#organization'},'breadcrumb':{'@id':url(path)+'#breadcrumb'}},
           {'@type':'BreadcrumbList','@id':url(path)+'#breadcrumb','itemListElement':[{'@type':'ListItem','position':i,'name':n,'item':url(p)} for i,(n,p) in enumerate([('홈','/'),('선생님찾기','/선생님찾기/')]+([] if path=='/선생님찾기/' else [(title,path)]),1)]},
           {'@type':'ItemList','@id':url(path)+'#introductions','numberOfItems':len(items),'itemListElement':[{'@type':'ListItem','position':i,'name':n,'url':url(p)} for i,(n,p) in enumerate(items,1)]}]
    return f'''<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{E(title)} | 와와학습코칭학원</title>
<meta name="description" content="{E(desc)}"><meta name="robots" content="index, follow"><link rel="canonical" href="{url(path)}"><link rel="alternate" type="application/rss+xml" title="와와학습코칭학원 RSS" href="{DOMAIN}/rss.xml">
<meta property="og:type" content="website"><meta property="og:title" content="{E(title)}"><meta property="og:url" content="{url(path)}"><meta property="og:description" content="{E(desc)}"><meta property="og:image" content="{DOMAIN}/assets/brand-upgrade-v1/brand-learning.png"><meta property="og:image:alt" content="와와의 학생 중심 학습을 표현한 브랜드 일러스트"><meta name="twitter:card" content="summary"><meta name="twitter:description" content="{E(desc)}"><link rel="icon" href="/assets/favicon.png">{CSS}<script defer src="/assets/teacher-finder.js"></script>
<script type="application/ld+json">{json.dumps({'@context':'https://schema.org','@graph':graph},ensure_ascii=False).replace('</','<\\/')}</script></head>
<body class="teacher-finder"><a class="tf-skip" href="#main">본문 바로가기</a><header class="tf-header"><nav class="tf-wrap tf-nav" aria-label="주요 메뉴"><a class="tf-brand" href="/"><span class="tf-mark" aria-hidden="true">W</span><span><small>STUDY COACHING</small>와와학습코칭학원</span></a><div class="tf-nav-links"><a href="/학습관리/">학습관리</a><a href="/학습가이드/">학습가이드</a><a href="/선생님찾기/" aria-current="page">선생님찾기</a><a href="/지점안내/">지점안내</a><a href="/상담문의/">상담문의</a></div></nav></header><main id="main">{content}</main>
<footer class="tf-footer"><div class="tf-wrap"><strong>와와학습코칭학원</strong><p>학생의 이해에서 시작하는 학습코칭</p><nav aria-label="하단 메뉴"><a href="/선생님찾기/">선생님찾기 전체</a><a href="/지점안내/">지점별 수강 안내</a><a href="/학습가이드/">학생·학부모 학습가이드</a><a href="/상담문의/">상담문의</a></nav></div></footer></body></html>'''

def directory(data):
    branches=data['branches'];regions=sorted({b['region'] for b in branches if b['region']});focus=sorted({v for b in branches for t in b['teachers'] for v in t['focus']})
    title='선생님찾기';desc='지점별 선생님의 학습 지도 방향과 소개를 살펴보고, 학생에게 필요한 상담 질문을 준비해 보세요.'
    cards=[]
    for b in branches:
        names=[t['name'] for t in b['teachers']];topics=list(dict.fromkeys(v for t in b['teachers'] for v in t['focus']))
        area=b['region']+' · '+b['district'] if b['region'] else '지점명으로 찾기'
        hay=' '.join([b['label'],b['region'],b['district'] or '',b['address'] or '',*b['neighborhoods'],*names,*topics])
        cards.append(f'''<article class="tf-branch-card" data-teacher-branch data-region="{E(b['region'] or 'unmatched')}" data-focus="{E('|'.join(topics))}" data-search="{E(hay)}"><p class="tf-eyebrow">{E(area)}</p><h3><a href="{U(b['path'])}">{E(b['label'])} 선생님</a></h3><p class="tf-names">{E(' · '.join(names))}</p><div class="tf-tags">{''.join('<span>'+E(v)+'</span>' for v in topics[:3])}</div><a class="tf-card-link" href="{U(b['path'])}">소개 {len(b['teachers'])}건 살펴보기 <span aria-hidden="true">↗</span><span class="tf-sr"> · {E(b['label'])}</span></a></article>''')
    filters=f'''<form data-teacher-filter class="tf-filter" aria-label="지점과 선생님 찾기" hidden><div><label for="teacher-search">지점·동네·선생님 이름 검색</label><input type="search" id="teacher-search" placeholder="예: 명일, 강릉, 심*우, 질문" autocomplete="off"></div><div><label for="teacher-region">지역</label><select id="teacher-region"><option value="">전체 지역</option>{''.join(f'<option value="{E(r)}">{E(r)}</option>' for r in regions)}<option value="unmatched">지점명으로 찾기</option></select></div><div><label for="teacher-focus">학습 지도 방향</label><select id="teacher-focus"><option value="">전체 지도 방향</option>{''.join(f'<option value="{E(v)}">{E(v)}</option>' for v in focus)}</select></div><button type="reset">초기화</button><p data-teacher-count role="status" aria-live="polite">205개 지점</p></form>'''
    content=f'''<section class="tf-hero"><div class="tf-wrap">{crumbs([('홈','/'),('선생님찾기','/선생님찾기/')])}<p class="tf-eyebrow">MEET OUR TEACHERS</p><h1>선생님찾기</h1><p class="tf-lead">어떻게 듣고, 설명하고,<br>함께 확인하는지.</p><p class="tf-hero-copy">학생의 질문과 이해를 살피는 선생님들의 이야기를 만나보세요.<br>지점별 소개에서 학습 지도 방향을 읽고, 상담에서 나눌 질문을 준비할 수 있습니다.</p><a class="tf-button" href="#branches">우리 동네 선생님 찾기 <span aria-hidden="true">↓</span></a><div class="tf-stats"><p><strong>205</strong><span>지점별 소개</span></p><p><strong>1,002</strong><span>교사 소개 항목</span></p><p><strong>이해에서 시작</strong><span>질문 · 설명 · 다시 확인</span></p></div></div></section>
<section class="tf-section"><div class="tf-wrap"><p class="tf-eyebrow">BEFORE YOU CHOOSE</p><h2>이름보다 먼저, 지도 방향을 읽어보세요</h2><div class="tf-principles"><div><span>01</span><h3>학생의 말을 듣는 방법</h3><p>무엇을 알고 어디에서 막혔는지, 학생의 설명과 질문을 어떻게 확인하려는지 살펴보세요.</p></div><div><span>02</span><h3>도움을 조절하는 기준</h3><p>설명의 속도와 분량, 과제와 복습을 학생의 현재 이해에 맞추려는 방향을 읽어보세요.</p></div><div><span>03</span><h3>다음 상담에 가져갈 질문</h3><p>최근 답안이나 복습 기록을 준비하고, 소개에서 궁금한 지도 방법을 구체적으로 물어보세요.</p></div></div></div></section>
<section id="branches" class="tf-section tf-tint"><div class="tf-wrap"><div class="tf-section-heading"><div><p class="tf-eyebrow">FIND YOUR BRANCH</p><h2>지점별 선생님 소개</h2></div><p>지역과 학습 지도 방향으로 좁혀보세요.</p></div>{filters}<noscript data-teacher-fallback><p>아래 목록에서 모든 지점의 소개를 볼 수 있습니다. 검색·필터는 자바스크립트를 켜면 사용할 수 있습니다.</p></noscript><p data-teacher-empty class="tf-empty" hidden>조건에 맞는 지점이 없습니다. 검색어를 줄이거나 필터를 초기화해 보세요.</p><div class="tf-branch-grid">{''.join(cards)}</div></div></section>
<section class="tf-section"><div class="tf-wrap tf-reading"><h2>소개를 살펴볼 때 궁금한 점</h2><details><summary>사진은 해당 선생님의 실제 사진인가요?</summary><p>사진은 대표 프로필 이미지입니다. 해당 이름의 교사를 식별하는 실제 사진으로 연결한 것은 아닙니다.</p></details><details><summary>담당 과목과 학년은 어디에서 확인하나요?</summary><p>이 페이지는 선생님의 학습 지도 방향을 소개합니다. 실제 담당 과목·학년, 배정과 상담 가능 여부는 해당 지점에 확인해 주세요.</p></details><details><summary>같은 이름의 소개가 여러 개 보일 수 있나요?</summary><p>이름 일부를 가려 표기하므로 같은 이름처럼 보이는 소개가 있을 수 있습니다. 각 소개의 지점과 지도 방향을 함께 살펴보세요.</p></details><p class="tf-note">이름은 제공된 표기 그대로 일부를 가렸습니다. 소개 항목 수는 고유 인원 수를 뜻하지 않습니다.</p><a class="tf-text-link" href="/학습가이드/학원상담자료/">상담 전에 준비할 자료 읽기 →</a></div></section>'''
    return '/선생님찾기/',desc,shell('/선생님찾기/',title,desc,content,[(b['label']+' 선생님',b['path']) for b in branches])

def branch_page(b,nearby):
    title=b['label']+' 선생님 소개';desc=f'{b["label"]} 선생님의 학습 지도 방향과 소개를 살펴보고, 상담에서 확인할 질문을 준비해 보세요.'
    assert len(desc)<=80
    content=f'''<section class="tf-branch-hero"><div class="tf-wrap">{crumbs([('홈','/'),('선생님찾기','/선생님찾기/'),(b['label'],b['path'])])}<p class="tf-eyebrow">{'지점별 선생님 소개 · '+E(b['region']) if b['region'] else '지점별 선생님 소개'}</p><h1>{E(title)}</h1><p class="tf-lead tf-branch-lead">학생의 이해를 살피는<br>선생님들의 지도 방향.</p><p class="tf-hero-copy">각 선생님이 어떤 질문을 듣고, 어떤 과정을 함께 확인하려는지 소개를 읽어보세요.</p><div class="tf-hero-actions"><a class="tf-button" href="#teachers">선생님 소개 {len(b['teachers'])}건 보기 ↓</a>{f'<a class="tf-text-link" href="{U(b["branchPath"])}">지점 위치·과목·학년 확인 →</a>' if b['branchPath'] else '<a class="tf-text-link" href="/상담문의/">지점 위치·수강 조건 문의 →</a>'}</div></div></section>'''
    content+='<section id="teachers" class="tf-section tf-tint"><div class="tf-wrap"><div class="tf-section-heading"><div><p class="tf-eyebrow">TEACHING & LEARNING</p><h2>선생님을 소개합니다</h2></div><p>사진은 대표 프로필 이미지입니다.</p></div><div class="tf-teacher-grid">'
    for t in b['teachers']:
        im=t['image']
        content+=f'''<article class="tf-teacher-card" id="{t['id']}" data-teacher-id="{t['id']}"><div class="tf-teacher-heading"><figure><img src="{im['path']}" width="{im['width']}" height="{im['height']}" alt="대표 프로필 이미지" loading="lazy" decoding="async"><figcaption>대표 프로필 이미지</figcaption></figure><div><p class="tf-eyebrow">{E(b['label'])}</p><h3>{E(t['name'])} 선생님</h3><p class="tf-focus-label">학습 지도 방향</p><div class="tf-tags">{''.join('<span>'+E(v)+'</span>' for v in t['focus'])}</div></div></div><p class="tf-introduction" data-teacher-intro>{E(t['intro'])}</p></article>'''
    content+='</div></div></section><section class="tf-section"><div class="tf-wrap tf-reading"><h2>소개를 읽고, 상담에서 이어가세요</h2><p>최근 과제나 답안에서 학생이 혼자 설명할 수 있었던 부분과 도움을 요청한 부분을 나눠 준비해 보세요. 관심 있는 선생님의 지도 방향에서 한 가지 질문을 골라 상담에서 확인할 수 있습니다.</p><ul class="tf-checks"><li>학생이 막힌 지점을 어떤 질문과 자료로 확인하나요?</li><li>설명을 들은 뒤 혼자 다시 해 볼 내용은 어떻게 정하나요?</li><li>현재 담당 과목·학년과 실제 배정 가능 여부는 무엇인가요?</li></ul>'
    if b['branchPath']:
        content+=f'<div class="tf-branch-info"><h3>{E(b["label"])} 지점 안내</h3><p>{E(b["address"])}</p><a class="tf-text-link" href="{U(b["branchPath"])}">위치·과목별 수강 학년·교습비 안내 →</a></div>'
    else:
        content+='<p>지점 위치와 실제 수강 조건은 상담에서 확인해 주세요.</p>'
    content+='<p class="tf-note">이름은 제공된 표기 그대로 일부를 가렸습니다. 사진은 대표 프로필 이미지이며, 실제 교사를 식별하는 사진이 아닙니다. 소개 내용은 지도 방향을 담고 있으며 담당 과목·학년, 현재 배정과 상담 가능 여부는 지점에 확인해 주세요.</p><div class="tf-next-links"><a href="/학습가이드/학원상담자료/">학원 상담에 가져갈 자료</a><a href="/학습가이드/숙제도움범위/">학생에게 필요한 도움의 범위</a><a href="/상담문의/">상담문의</a></div>'
    if b['neighborhoods']:
        content+='<div class="tf-branch-info"><h3>동네 학습 안내도 함께 읽어보세요</h3><div class="tf-next-links">'+''.join(f'<a href="{U("/전국센터/"+"".join(n.split())+"/")}">{E(n)} 학습 안내 →</a>' for n in b['neighborhoods'])+'</div></div>'
    content+='</div></section>'
    if nearby:
        content+='<section class="tf-section tf-tint"><div class="tf-wrap"><h2>같은 지역의 다른 지점도 살펴보세요</h2><div class="tf-next-links">'+''.join(f'<a href="{U(o["path"])}">{E(o["label"])} 선생님 소개 →</a>' for o in nearby)+'</div></div></section>'
    content+='<section class="tf-section"><div class="tf-wrap"><a class="tf-text-link" href="/선생님찾기/">전체 지점 선생님찾기로 돌아가기 →</a></div></section>'
    return b['path'],desc,shell(b['path'],title,desc,content,[(t['name']+' 선생님',b['path']+'#'+t['id']) for t in b['teachers']])

def bridge(branch,kind):
    if not branch:
        return '<section data-teacher-bridge class="tf-bridge"><div class="wrap"><h2>선생님의 학습 지도 방향이 궁금하다면</h2><p>지점별 선생님 소개에서 질문·설명·복습을 함께 확인하려는 지도 방향을 읽어보세요.</p><a href="/선생님찾기/">지점별 선생님찾기 →</a></div></section>'
    lead='이 지점의 선생님을 만나보세요' if kind=='center' else '수업 상담 전에 선생님의 지도 방향도 살펴보세요'
    content=f'<section data-teacher-bridge class="tf-bridge"><div class="wrap"><p class="tf-bridge-eyebrow">{E(branch["label"])} 선생님 소개</p><h2>{lead}</h2><p>{E(branch["label"])} 선생님들이 학생의 질문·설명·복습을 어떻게 함께 확인하려는지 소개를 읽어보세요. 실제 담당 과목·학년과 배정 가능 여부는 지점에 확인해 주세요.</p>'
    if kind=='center':
        content+='<ul class="tf-bridge-previews">'+''.join(f'<li><strong>{E(t["name"])} 선생님</strong><span>{E(" · ".join(t["focus"]))}</span><a href="{U(branch["path"])}#{t["id"]}">소개 읽기 →</a></li>' for t in branch['teachers'][:2])+'</ul>'
    return content+f'<a class="tf-bridge-link" href="{U(branch["path"])}">{E(branch["label"])} 선생님 소개 전체 보기 →</a></div></section>'

def patch_dates(text):
    def patch(m):
        payload=json.loads(m.group(2))
        def visit(value):
            if isinstance(value,list):
                for v in value:visit(v)
            elif isinstance(value,dict):
                if value.get('@type') in ['WebPage','CollectionPage','AboutPage','ContactPage','Article'] and value.get('dateModified'):value['dateModified']=DATE
                for v in value.values():visit(v)
        visit(payload)
        return m.group(1)+json.dumps(payload,ensure_ascii=False,separators=(',',':'))+m.group(3)
    text=re.sub(r'(<script\b[^>]*type="application/ld\+json"[^>]*>)(.*?)(</script>)',patch,text,flags=re.S)
    text=re.sub(r'(내용 수정 )2026\.\d{2}\.\d{2}',r'\g<1>2026.10.02',text)
    return text

def integrate():
    baseline=load(OUT/'baseline-manifest.json');data=import_data();branches=data['branches']
    rows=inventory();contexts={}
    # Center route name is authoritative for neighborhood relationships.
    byroute={(b['region'],b['branchPath'].strip('/').split('/')[-1]):b for b in branches if b['branchPath']}
    for r in rows:contexts[r['path']]=(byroute.get(tuple(r['centerKey'])),'local')
    for c in FACTS['centers']:contexts[center_path(c)]=(byroute.get((c['region'],c['routeName'])),'center')
    tops=['/','/학습관리/','/지점안내/','/전국센터/','/과목별학원/','/상담문의/']
    for p in tops:contexts[p]=(None,'top')
    modified=[];bridged=[];menu=[]
    for number,name in enumerate(baseline['files'],1):
        if not name.endswith('.html'):continue
        source=ROOT/name;old=source.read_text('utf-8');text=old;path='/' if name=='index.html' else '/'+name[:-10]
        if 'data-teacher-nav' not in text:
            text,count=re.subn(r'(<div\b[^>]*class="(?:nav-links|lg-nav-links)"[^>]*>)',lambda m:m.group(1)+TEACHER_NAV,text,count=1)
            assert count==1,name
        menu.append(name)
        if 'data-teacher-style' not in text:text=text.replace('</head>',CSS+'</head>',1)
        if path in contexts and 'data-teacher-bridge' not in text:
            assert text.count('</main>')==1,name
            b,kind=contexts[path];text=text.replace('</main>',bridge(b,kind)+'</main>')
        if path in contexts:
            b,kind=contexts[path];bridged.append({'file':name,'branch':b['label'] if b else None,'kind':kind})
        if text!=old:text=patch_dates(text)
        if text!=old:write(source,text)
        # Compare with the preserved pre-teacher snapshot, including on resume.
        if digest(source.read_bytes())!=baseline['files'][name]:modified.append(name)
        if number%2000==0:print('Applied teacher menu/context through',number,'public files',flush=True)
    pages=[directory(data)]
    for b in branches:
        nearby=[other for other in branches if other is not b and other['region'] and other['region']==b['region']][:4]
        pages.append(branch_page(b,nearby))
    for path,desc,markup in pages:
        assert len(desc)<=80 and desc.endswith('.')
        write(ROOT/path.strip('/')/'index.html',markup)
    descriptions=load(ROOT/'seo-descriptions.json')
    for path,desc,_ in pages:descriptions['pages'][path.rstrip('/') or '/']={'description':desc,'sources':[desc]}
    dump(ROOT/'seo-descriptions.json',descriptions)
    # Existing XML identities and ordering are retained; only changed page dates and new URLs are added.
    sitemap_text=(ROOT/'sitemap.xml').read_text('utf-8');existing=set(etree.fromstring(sitemap_text.encode()).xpath('//*[local-name()="loc"]/text()'));by_path={unquote(urlsplit(u).path):u for u in existing}
    changed_urls={by_path['/' if name=='index.html' else '/'+name[:-10]] for name in modified};seen=set()
    def sitemap_date(m):
        canonical=escape.unescape(m.group(2))
        if canonical in changed_urls:
            seen.add(canonical);return m.group(1)+DATE+m.group(3)
        return m.group(0)
    sitemap_text=re.sub(r'(<url>\s*<loc>([^<]+)</loc>\s*<lastmod>)[^<]+(</lastmod>)',sitemap_date,sitemap_text)
    assert seen==changed_urls
    for path,_,_ in pages:
        if url(path) not in existing:sitemap_text=sitemap_text.replace('</urlset>','  <url>\n    <loc>'+url(path)+'</loc>\n    <lastmod>'+DATE+'</lastmod>\n  </url>\n</urlset>')
    write(ROOT/'sitemap.xml',sitemap_text)
    original=(ROOT/'rss.xml').read_bytes();feed=etree.fromstring(original,etree.XMLParser(resolve_entities=False,no_network=True,remove_blank_text=True,strip_cdata=False));channel=feed.find('channel');identities=[identity(i) for i in channel.findall('item')]
    for item in channel.findall('item'):
        canonical=item.findtext('link');name=unquote(urlsplit(canonical).path).strip('/')+'/index.html';name='index.html' if name=='/index.html' else name
        exported,_=body(html.document_fromstring((ROOT/name).read_bytes()),canonical);item.find('description').text=etree.CDATA(exported)
    # Keep the full directory available through a single feed item; avoid duplicating every teacher biography in RSS.
    canonical=url('/선생님찾기/');now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).replace(microsecond=0)
    if canonical not in [i.findtext('link') for i in channel.findall('item')]:
        item=etree.SubElement(channel,'item');etree.SubElement(item,'title').text='선생님찾기';etree.SubElement(item,'link').text=canonical;etree.SubElement(item,'guid',isPermaLink='true').text=canonical;etree.SubElement(item,'pubDate').text=format_datetime(now);exported,_=body(html.document_fromstring((ROOT/'선생님찾기/index.html').read_bytes()),canonical);etree.SubElement(item,'description').text=etree.CDATA(exported)
    channel.find('description').text='지점·수강 안내, 선생님 소개와 학생·학부모를 위한 학습가이드·실천 기록표를 제공합니다.'
    fresh=etree.tostring(feed,encoding='UTF-8',xml_declaration=True,pretty_print=True)
    if fresh!=original:channel.find('lastBuildDate').text=format_datetime(now)
    write(ROOT/'rss.xml',etree.tostring(feed,encoding='UTF-8',xml_declaration=True,pretty_print=True))
    assert [identity(i) for i in channel.findall('item')][:98]==identities[:98]
    new={p.strip('/')+'/index.html' for p,_,_ in pages}|{'assets/teacher-finder.css','assets/teacher-finder.js'}|{i['path'].lstrip('/') for i in data['images']}
    names=sorted(set(baseline['files'])|new);textnames=set(baseline['textSha256'])|{n for n in new if not n.endswith('.png')}
    def hashes(name):
        raw=(ROOT/name).read_bytes();return name,digest(raw),digest(raw.decode('utf-8').replace('\r\n','\n').encode()) if name in textnames else None
    with ThreadPoolExecutor(max_workers=16) as pool:values=list(pool.map(hashes,names))
    manifest=load(ROOT/'release-public-manifest.json');manifest['files']={n:h for n,h,_ in values};manifest['textSha256']={n:h for n,_,h in values if h};manifest['sitemapPages']=sum(n.endswith('.html') for n in names)
    dump(ROOT/'release-public-manifest.json',manifest)
    report={'excelRows':1002,'teacherBranchPages':205,'teacherPages':206,'matchedBranches':192,'unmatchedBranches':[b['label'] for b in branches if not b['centerKey']],
            'representativePortraits':10,'withinBranchPhotosUnique':all(len({t['image']['path'] for t in b['teachers']})==len(b['teachers']) for b in branches),'menuPages':len(menu),'modifiedHtml':modified,'contextualLinks':bridged,'newPublicFiles':sorted(new),'publicFiles':len(names),'publicHtml':manifest['sitemapPages'],'rssItems':len(channel.findall('item')),'deployed':False}
    dump(OUT/'implementation.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ['modifiedHtml','contextualLinks','newPublicFiles']},ensure_ascii=False))

if __name__=='__main__':integrate()
