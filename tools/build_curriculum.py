"""Publish curriculum guidance from the private workbook, preserving current pages.

Needs tools/data/curriculum/workbook.json and the frozen current publication ZIP.
Learning levels are examples, never declarations of a center's offered courses.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from urllib.parse import quote,unquote,urlsplit
from email.utils import format_datetime
import datetime,json,re,html as escape
from lxml import html,etree
from build_education_info import ROOT,DOMAIN,write,dump,load,digest,patch_dates
from improve_neighborhood_pages import inventory,FACTS,center_path
from seo_feed_content import body,identity

OUT=Path(r'C:\Users\1992k\Desktop\CodexData\outputs\site3-curriculum-20261003')
DATA=ROOT/'tools/data/curriculum/workbook.json'
DATE='2026-10-03'
BASE='/공부커리큘럼/'
E=lambda v:escape.escape(str(v),quote=True)
U=lambda p:quote(p,safe='/#')
url=lambda p:DOMAIN+U(p)
STAGES={'초':'초등','중':'중등','고':'고등'}
SCHOOL={'초':'초등학교','중':'중학교','고':'고등학교'}
SUBJECTS=['국어','영어','수학','사회','과학','역사']
MOE22='https://www.moe.go.kr/boardCnts/viewRenew.do?boardID=141&boardSeq=93458&lev=0'
MOE15='https://www.moe.go.kr/boardCnts/view.do?boardID=141&boardSeq=60747&lev=0&m=040401&opType=N&page=5&s=moe&searchType=S'
NCIC26='https://www.ne.go.kr/new/user/bbs/BD_selectBbs.do?q_bbsDocNo=20260121102419070&q_bbsSn=1016'
NAV='<a href="/공부커리큘럼/" data-curriculum-nav>공부커리큘럼</a>'
CSS='<link rel="stylesheet" href="/assets/curriculum.css" data-curriculum-style>'

def rows(sheet):return [r['values'] for r in load(DATA)['sheets'][sheet]['rows']]
def grade_name(g):return SCHOOL[g[0]]+' '+g[1]+'학년'
def stage_path(s):return BASE+s+'/'
def grade_path(g):return stage_path(STAGES[g[0]])+g+'/'
def subject_path(g,s):return grade_path(g)+s+'/'
def choice_path(s=None):return BASE+'고등과목/'+(s+'/' if s else '')
def filtered(path,subject):return U(path)+'?subject='+quote(subject)+'#subjects'
def anchor(p,t,cls='cc-button'):return f'<a class="{cls}" href="{U(p)}">{E(t)}</a>'
def actions(items):return '<div class="cc-actions">'+''.join(anchor(p,t) for p,t in items)+'</div>'
def paras(values):return ''.join('<p>'+E(v)+'</p>' for v in values)
def sequence(value):return '<ol class="cc-sequence">'+''.join('<li>'+E(v.strip())+'</li>' for v in value.split('→'))+'</ol>'

def school_check(g):
    wanted={'모든 학교','모든 학생'}
    wanted.add({'초':'초등학교','중':'중학교','고':'고등학교'}[g[0]])
    if g[0] in '중고':wanted.add('중·고등학교')
    if g in ['초1','초2']:wanted.add('초1·초2')
    selected=[r for r in rows('학교별적용') if r[0] in wanted]
    return '<section id="school-check"><h2>학교 자료와 함께 확인할 것</h2><p>현재 학년·학기와 실제 학교의 안내를 기준으로 공부 범위를 조정해 보세요.</p><dl class="cc-checks">'+''.join('<div><dt>'+E(r[1])+'</dt><dd>'+E(r[2])+'<br>'+E(r[3])+'</dd></div>' for r in selected)+'</dl></section>'

def references(source,section=None,materials=None):
    links=[(MOE22 if '2015' not in (section or '') else MOE15,'교육부 · '+('2015' if '2015' in (section or '') else '2022')+' 개정 교육과정 고시',section or '적용 학년 및 교과 교육과정')]
    if source not in [MOE22,MOE15]:
        links.append((source,'경기도교육청 · 수업·평가 계획 예시','초3·4는 2025년 2학기, 초5·6은 2026년 예시 자료입니다. 학교의 실제 진도와 함께 확인하세요.'))
    if materials:links.append((materials,'EBS · 학습 자료 안내','교재·강좌의 학년, 과목명과 개정판을 확인하는 참고 경로입니다.'))
    links.append((NCIC26,'국가교육위원회 · 2026-1호 일부개정 고시','고등학교 총론·편제 등의 후속 개정과 적용 시기를 확인하는 자료입니다.'))
    return '<section id="references" class="cc-references"><h2>교육과정·학습 자료 확인</h2><ul>'+''.join('<li><a href="'+E(p)+'">'+E(t)+'</a><p>'+E(note)+'</p></li>' for p,t,note in links)+'</ul></section>'

def locator():
    return '''<section id="local-info" class="cc-local"><p class="cc-kicker">공부 범위를 살펴본 다음</p><h2>우리 동네와 지점의 수업 안내도 확인하세요</h2><p>현재 학년, 배우는 과목과 혼자 해결하기 어려운 과제를 준비해 보세요. 실제 수업 가능 학년·과목·교재는 지점 안내와 상담에서 확인할 수 있습니다.</p><div class="cc-actions"><a class="cc-button" href="/전국센터/">동네별 안내 찾기</a><a class="cc-button cc-outline" href="/지점안내/">지점별 수강 정보 보기</a><a class="cc-text-link" href="/선생님찾기/">선생님 소개 보기 →</a></div><form data-curriculum-locator class="cc-locator" hidden><div><label for="cc-region">지역</label><select id="cc-region"><option value="">지역을 선택하세요</option></select></div><div><label for="cc-kind">찾는 안내</label><select id="cc-kind"><option value="neighborhood">동네 안내</option><option value="center">지점 안내</option></select></div><div><label for="cc-place">동네·지점</label><select id="cc-place" disabled><option value="">지역을 먼저 선택하세요</option></select></div><a class="cc-button" data-cc-location-go href="/전국센터/" aria-disabled="true">선택한 안내로 이동</a><p class="cc-small" data-cc-location-status role="status" aria-live="polite">지역을 선택하면 홈페이지의 동네·지점 안내를 찾을 수 있습니다.</p></form></section>'''

def shell(path,title,summary,content,parents,kind='CollectionPage',citation=None):
    assert len(summary)<=80 and summary.endswith('.'),(path,summary)
    crumbs=[('홈','/'),('공부커리큘럼',BASE)]+parents
    if path!=BASE:crumbs.append((title,path))
    graph=[{'@type':kind,'@id':url(path)+'#webpage','url':url(path),'name':title,'description':summary,'inLanguage':'ko-KR','datePublished':DATE,'dateModified':DATE,'isPartOf':{'@id':DOMAIN+'/#website'},'breadcrumb':{'@id':url(path)+'#breadcrumb'}},
           {'@type':'BreadcrumbList','@id':url(path)+'#breadcrumb','itemListElement':[{'@type':'ListItem','position':i,'name':t,'item':url(p)} for i,(t,p) in enumerate(crumbs,1)]}]
    if kind=='WebPage':
        graph.append({'@type':'Article','@id':url(path)+'#article','headline':title,'description':summary,'datePublished':DATE,'dateModified':DATE,'inLanguage':'ko-KR','mainEntityOfPage':{'@id':url(path)+'#webpage'},'publisher':{'@id':DOMAIN+'/#organization'},'citation':citation or [],'learningResourceType':'학습 안내'})
    else:
        doc=html.fragment_fromstring(content,create_parent='div');listed=doc.xpath('//*[@data-cc-card]//h3/a')
        graph.append({'@type':'ItemList','@id':url(path)+'#list','numberOfItems':len(listed),'itemListElement':[{'@type':'ListItem','position':i,'name':' '.join(a.itertext()),'url':DOMAIN+a.get('href')} for i,a in enumerate(listed,1)]})
    breadcrumb='<nav class="cc-crumbs" aria-label="현재 위치">'+'<span aria-hidden="true">/</span>'.join(f'<a href="{U(p)}">{E(t)}</a>' for t,p in crumbs)+'</nav>'
    schema=json.dumps({'@context':'https://schema.org','@graph':graph},ensure_ascii=False).replace('</','<\\/')
    head=f'''<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{E(title)} | 와와학습코칭학원</title><meta name="description" content="{E(summary)}"><meta name="robots" content="index, follow"><link rel="canonical" href="{url(path)}"><link rel="alternate" type="application/rss+xml" title="와와학습코칭학원 RSS" href="{DOMAIN}/rss.xml"><meta property="og:type" content="{'article' if kind=='WebPage' else 'website'}"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(summary)}"><meta property="og:url" content="{url(path)}"><meta property="og:image" content="{DOMAIN}/assets/brand-upgrade-v1/brand-learning.png"><meta property="og:image:alt" content="와와의 학생 중심 학습을 표현한 브랜드 일러스트"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:description" content="{E(summary)}"><link rel="icon" href="/assets/favicon.png">{CSS}<script defer src="/assets/curriculum.js"></script><script type="application/ld+json">{schema}</script></head>'''
    return head+f'''<body class="curriculum-page"><a class="cc-skip" href="#main">본문 바로가기</a><header class="cc-header"><nav class="cc-wrap cc-nav" aria-label="주요 메뉴"><a class="cc-brand" href="/"><span class="cc-mark" aria-hidden="true">W</span><span><small>STUDY COACHING</small>와와학습코칭학원</span></a><div class="cc-nav-links"><a href="/">홈</a><a href="/학습가이드/">학습가이드</a><a href="/교육정보/">교육정보</a><a href="/공부커리큘럼/" aria-current="page" data-curriculum-nav>공부커리큘럼</a><a href="/선생님찾기/">선생님찾기</a><a href="/지점안내/">지점안내</a><a href="/상담문의/">상담문의</a></div></nav></header><main id="main"><div class="cc-wrap">{breadcrumb}</div>{content}</main><footer class="cc-footer"><div class="cc-wrap"><strong>와와학습코칭학원</strong><p>학생과 학부모가 함께 살펴보는 공부 순서와 점검 방법</p><nav aria-label="하단 메뉴"><a href="/공부커리큘럼/">공부커리큘럼 전체</a><a href="/학습가이드/">학습가이드</a><a href="/교육정보/">교육정보</a><a href="/전국센터/">동네별 안내</a><a href="/지점안내/">지점 안내</a></nav></div></footer></body></html>'''

def title_for(r):
    g,s=r[:2];suffix='공부 커리큘럼'
    if g in ['초1','초2'] and s=='영어':suffix='선택 활동 안내'
    if g in ['초1','초2'] and s in ['사회','과학']:suffix='연계 활동 안내'
    return grade_name(g)+' '+s+' '+suffix

def subject_card(r):
    g,s=r[:2];t=title_for(r)
    return f'<article class="cc-card" data-cc-card data-grade="{g}" data-stage="{STAGES[g[0]]}" data-subject="{s}" data-search="{E(t+" "+r[4])}"><p class="cc-kicker">{E(grade_name(g))} · {s}</p><h3><a href="{U(subject_path(g,s))}">{E(t)}</a></h3><p>{E(r[4])}</p><p class="cc-small">{E(r[3])}</p><a class="cc-card-link" href="{U(subject_path(g,s))}">공부 순서와 확인 과제 보기<span class="cc-sr"> · {E(t)}</span> →</a></article>'

def filter_form(grades):
    return '<form class="cc-filter" data-curriculum-filter hidden><div><label for="cc-search">찾는 내용</label><input type="search" id="cc-search" placeholder="예: 분수, 중2, 공통수학" autocomplete="off"></div><div><label for="cc-grade">학년</label><select id="cc-grade"><option value="">전체 학년</option>'+''.join('<option value="'+g+'">'+grade_name(g)+'</option>' for g in grades)+'</select></div><div><label for="cc-subject">과목</label><select id="cc-subject"><option value="">전체 과목</option>'+''.join('<option>'+s+'</option>' for s in SUBJECTS)+'</select></div><button type="reset">초기화</button><p data-cc-count role="status" aria-live="polite"></p></form><p data-cc-empty hidden>조건에 맞는 안내가 없습니다. 검색어를 바꾸거나 필터를 초기화해 보세요.</p>'

def hero(title,lead,note,links=None):
    return '<section class="cc-hero"><div class="cc-wrap"><p class="cc-kicker">2026학년도 · 학년과 과목에 맞춘 공부 안내</p><h1>'+E(title)+'</h1><p class="cc-lead">'+E(lead)+'</p><p class="cc-hero-note">'+E(note)+'</p>'+(actions(links) if links else '')+'</div></section>'

def grade_card(r):
    g=r[1]
    return '<article class="cc-grade-card" data-cc-card><p class="cc-kicker">2026학년도 · '+E(r[2])+'</p><h3><a href="'+U(grade_path(g))+'">'+grade_name(g)+'</a></h3><p>'+E(r[4])+'</p><a class="cc-card-link" href="'+U(grade_path(g))+'">과목별 안내 보기 →</a></article>'

def directories(all_subjects):
    overview=rows('학년별개요');pages=[]
    for stage in [None,'초등','중등','고등']:
        part=[r for r in overview if stage is None or STAGES[r[1][0]]==stage]
        subjects=[r for r in all_subjects if stage is None or STAGES[r[0][0]]==stage]
        path=stage_path(stage) if stage else BASE
        title=(stage+' 공부커리큘럼') if stage else '공부커리큘럼'
        summary=(stage+' 학년·과목별 공부 범위와 기초·표준·심화 학습 순서, 학생·학부모의 점검 방법을 안내합니다.') if stage else '초등·중등·고등 학년별 공부 범위와 과목별 학습 순서, 기초·표준·심화 점검 방법을 안내합니다.'
        content=hero(title,'무엇을 배울지, 어디부터 시작할지 함께 살펴보세요.','학교 교과서와 현재 진도를 기준으로 사용할 학습 참고 안내입니다. 학년별 중점과 공부 순서는 학생의 상황에 맞게 조정하세요.',[(path+'#grades','학년별로 보기'),(path+'#subjects','과목과 내용으로 찾기')])
        if not stage:content+='<section class="cc-section"><div class="cc-wrap"><h2>학교급별로 시작하기</h2>'+actions([(stage_path(s),s+' 커리큘럼') for s in STAGES.values()])+actions([(choice_path(),'고등 공통·선택과목 비교')])+'</div></section>'
        content+='<section class="cc-section cc-tint" id="grades"><div class="cc-wrap"><h2>학년별 공부 범위</h2><div class="cc-grid">'+''.join(grade_card(r) for r in part)+'</div></div></section>'
        content+='<section class="cc-section" id="subjects"><div class="cc-wrap"><h2>과목별 공부 순서 찾기</h2><p>학년과 과목을 선택하거나, 지금 막히는 개념을 검색해 보세요.</p>'+filter_form([r[1] for r in part])+'<div class="cc-grid">'+''.join(subject_card(r) for r in subjects)+'</div></div></section>'
        content+='<section class="cc-section cc-tint"><div class="cc-wrap cc-reading"><h2>기초·표준·심화를 고르는 방법</h2>'+paras(['개념이나 낱말의 뜻을 설명하기 어렵다면 기초 내용을 확인하고, 익숙한 예제를 혼자 풀 수 있다면 조건을 바꾼 적용 과제를 해 보세요. 답의 근거와 다른 풀이를 비교할 수 있다면 심화 과제를 선택할 수 있습니다.','수준은 과목과 영역마다 다를 수 있습니다. 각 과목 안내의 확인 과제를 해 본 뒤 도움이 필요했던 부분을 기록해 보세요. 세 수준은 학습 예시이며 지점의 개설 반이나 공식 성취등급을 뜻하지 않습니다.'])+'<h2>2026학년도 교육과정 확인</h2>'+paras(['초1~6·중1~2·고1~2는 2022 개정 교육과정, 중3·고3은 2015 개정 교육과정을 기준으로 살펴봅니다. 2027학년도 중3·고3부터는 2022 개정 범위를 확인해야 합니다.','초1·2 영어는 선택 활동이며 사회·과학은 통합교과 연계 활동입니다. 중학교 사회·역사는 이수 학년을, 고등학교는 실제 공통·선택과목과 학교 편제를 먼저 확인하세요.'])+references(MOE22)+'</div></section><section class="cc-section"><div class="cc-wrap cc-reading">'+locator()+'</div></section>'
        pages.append((path,title,summary,shell(path,title,summary,content,[])))
    for r in overview:
        g=r[1];stage=STAGES[g[0]];title=grade_name(g)+' 공부커리큘럼';summary=grade_name(g)+'의 과목별 공부 범위와 확인 과제, 학교 자료에 맞춘 학습 계획을 안내합니다.'
        content=hero(title,r[4],f'2026학년도 기준 · {r[2]}. '+r[5],[(grade_path(g)+'#subjects','과목별 공부 순서 보기')])
        content+='<section class="cc-section" id="subjects"><div class="cc-wrap"><h2>'+grade_name(g)+' 과목별 안내</h2><p>'+E(r[3])+'</p><div class="cc-grid">'+''.join(subject_card(v) for v in all_subjects if v[0]==g)+'</div></div></section><section class="cc-section cc-tint"><div class="cc-wrap cc-reading">'+school_check(g)+'</div></section>'
        others=[v for v in overview if STAGES[v[1][0]]==stage and v[1]!=g]
        content+='<section class="cc-section"><div class="cc-wrap"><h2>같은 학교급의 다른 학년</h2>'+actions([(grade_path(v[1]),grade_name(v[1])) for v in others])+(actions([(choice_path(),'고등 공통·선택과목 안내')]) if g[0]=='고' else '')+'</div></section><section class="cc-section cc-tint"><div class="cc-wrap cc-reading">'+locator()+'</div></section>'
        pages.append((grade_path(g),title,summary,shell(grade_path(g),title,summary,content,[(stage+' 커리큘럼',stage_path(stage))])))
    return pages

PARENT={
 '국어':('내용을 어디에서 찾았는지 물어보세요.','읽은 글에서 답을 뒷받침하는 낱말이나 문장을 표시했는지 살펴봅니다. 요약문에는 중요한 내용이 남았는지, 자신의 의견과 글의 사실을 구별했는지 함께 확인하세요.'),
 '영어':('외운 표현을 새 상황에서도 사용할 수 있는지 살펴보세요.','읽기·듣기에서 찾은 정보를 자신의 말로 설명해 보게 합니다. 직접 쓴 문장은 뜻뿐 아니라 어순과 동사 형태를 살펴보고, 모르겠는 낱말과 구조를 따로 남겨 주세요.'),
 '수학':('첫 식을 세운 이유와 단위를 물어보세요.','답을 맞힌 문제도 조건을 식·그림·그래프 중 하나로 바꾸어 설명해 봅니다. 틀린 문제는 조건 해석, 개념 선택, 계산과 표현 중 처음 막힌 곳을 표시하고 시간이 지난 뒤 다시 풀어 보세요.'),
 '사회':('자료에서 읽은 사실과 자신의 해석을 나눠 보세요.','지도·사진·통계의 제목, 기준과 시점을 먼저 확인합니다. 배운 개념으로 설명할 수 있는 부분과 더 알아봐야 할 부분을 나누고, 다른 자료에서도 같은 설명이 가능한지 비교하세요.'),
 '과학':('본 사실과 그 이유를 구분해서 설명해 보게 하세요.','관찰·측정 결과에 단위가 있는지, 비교할 조건이 같은지 살펴봅니다. 실험은 학교의 안전 안내에 따라 진행하고, 결과에서 말할 수 있는 결론과 더 확인할 것을 구분해 보세요.'),
 '역사':('사건의 순서와 그 이유를 함께 물어보세요.','연표·지도와 사료의 단서를 연결해 봅니다. 자료가 만들어진 때와 관점을 확인하고, 사건의 배경·전개·결과를 자신의 말로 설명할 수 있는지 살펴보세요.')}

def levels(g,s):
    low=g in ['초1','초2'] and s in ['영어','사회','과학']
    if low:
        prompts={'영어':['그림이나 노래에서 친숙한 소리에 반응하기','관심 있는 낱말을 듣고 말해 보기','좋아하는 상황의 표현을 놀이로 바꿔 보기'],
                 '사회':['주변 장소나 생활 모습을 말해 보기','다른 장소·사람의 생활과 비교하기','함께 지킬 약속과 그 이유를 설명하기'],
                 '과학':['안전하게 관찰한 특징 말하기','같은 기준으로 비교하고 그림으로 기록하기','다시 관찰한 결과와 처음 기록을 비교하기']}[s]
        return '<section id="levels"><h2>아이의 반응에 맞춰 활동을 조절하기</h2><p>선택·연계 활동은 흥미와 참여 정도에 맞춰 조절하세요. 이 활동의 진도가 정규 교과의 선행 필수 조건은 아닙니다.</p><ol class="cc-sequence">'+''.join('<li>'+E(p)+'</li>' for p in prompts)+'</ol></section>',[]
    level_rows=[r for r in rows('반별운영') if r[0]=={'초':'초등학생','중':'중학생','고':'고등학생'}[g[0]] and r[1]==('사회' if s=='역사' else s)]
    assert len(level_rows)==3
    note='사회·역사에서 함께 사용할 수 있는 자료 읽기와 설명 예시입니다. 실제 역사 이수 범위에 맞춰 적용하세요.' if s=='역사' else '과목의 같은 영역에서도 이해한 부분과 도움이 필요한 부분을 나누어 사용해 보세요.'
    content='<section id="levels"><h2>기초·표준·심화로 조절하는 학습 예시</h2><p>'+note+'</p><p class="cc-small">아래 세 수준은 학습 방향을 고르는 예시입니다. 공식 성취등급이나 지점의 실제 개설 반을 뜻하지 않습니다.</p><div class="cc-levels">'
    for r in level_rows:
        level=r[2].removesuffix('반')
        content+='<article class="cc-level"><p class="cc-kicker">'+E(level)+' 학습</p><h3>'+E(r[3])+'</h3><h4>공부 순서</h4>'+sequence(r[4])+'<dl><dt>확인 과제</dt><dd>'+E(r[5])+'</dd><dt>다음 단계로 넓힐 때</dt><dd>'+E(r[6])+'</dd></dl><details><summary>교재·자료를 고를 때</summary><p>'+E(r[7])+'</p><p>학년·학기·과목명·개정판과 지금의 학습 수준을 확인하는 후보입니다. 실제 지점의 사용 교재는 상담에서 확인하세요.</p></details></article>'
    return content+'</div></section>',level_rows

def subject_page(r):
    g,s,revision,scope,focus,order,task,adjust,summary,source,source_section=r
    path=subject_path(g,s);stage=STAGES[g[0]];title=title_for(r)
    content=hero(title,focus,'2026학년도 기준 · '+revision+' · '+scope,[(path+'#learning-order','공부 순서'),(path+'#levels','수준에 맞춘 학습'),(path+'#local-info','동네·지점 안내')])
    content+='<div class="cc-wrap cc-reading cc-prose"><p class="cc-intro">'+E(summary)+'</p><section id="learning-order"><h2>이 순서로 공부해 보세요</h2>'+sequence(order)+'<p>현재 학교 진도에 해당하는 부분부터 골라 보세요. 앞 단계에서 설명하기 어려운 개념은 짧게 보완하고, 이해한 내용을 다음 과제에 적용해 봅니다.</p></section><section id="check-task" class="cc-task"><p class="cc-kicker">직접 해 볼 확인 과제</p><h2>'+E(task)+'</h2><p>과제를 해 본 뒤 혼자 완성한 부분과 도움이 필요했던 부분을 표시해 보세요. 정답이나 결과와 함께 설명 과정도 남기면 다음 공부에서 무엇을 바꿀지 정하기 쉽습니다.</p></section>'
    level_content,level_rows=levels(g,s);content+=level_content
    pt,pp=PARENT[s]
    content+='<section id="parent"><h2>학부모가 함께 살펴볼 부분</h2><h3>'+E(pt)+'</h3><p>'+E(pp)+'</p><ul class="cc-list"><li>오늘 확인한 범위와 사용한 교재·자료를 적었나요?</li><li>답이나 결과를 설명하면서 도움이 필요했던 부분은 어디였나요?</li><li>다음에 다시 확인할 과제와 시점을 정했나요?</li></ul></section><section id="adjust"><h2>학교 진도에 맞춰 조정하기</h2><p>'+E(adjust)+'</p><p>학습 기간과 숙제 분량은 학생의 현재 이해와 학교 일정에 맞춰 정하세요. 같은 학년이라도 교과서와 학기별 이수 범위가 다를 수 있습니다.</p></section>'
    content+=school_check(g)
    related=[(grade_path(g),grade_name(g)+' 다른 과목'),('/학습가이드/','실천 기록표가 있는 학습가이드'),('/교육정보/','시험·공부 습관 교육정보')]
    if g[0]=='고':related.insert(1,(choice_path(s),s+' 공통·선택과목 비교'))
    content+='<section id="related"><h2>공부 범위를 이어서 살펴보기</h2>'+actions(related)+'</section>'+references(source,source_section,level_rows[0][9] if level_rows else None)+locator()+'</div>'
    return path,title,summary,shell(path,title,summary,content,[(stage+' 커리큘럼',stage_path(stage)),(grade_name(g),grade_path(g))],'WebPage',[source,NCIC26])

def choices():
    choices=rows('고등선택과목');pages=[]
    for s in [None]+SUBJECTS:
        selected=[r for r in choices if s is None or r[0]==s];assert selected
        path=choice_path(s);title=('2022 개정 '+s+' 공통·선택과목 안내') if s else '고등 공통·선택과목 안내'
        summary=('2022 개정 '+s+' 공통·선택과목의 내용과 준비 개념, 학교 과목 선택에서 확인할 사항을 안내합니다.') if s else '2022 개정 고등 공통·선택과목 29개 묶음의 내용과 준비 개념, 학교 편제 확인 방법을 안내합니다.'
        content=hero(title,'과목의 이름과 준비 개념을 함께 비교하세요.','2022 개정 교육과정의 주요 공통·선택과목을 묶은 안내입니다. 2026학년도 고3의 2015 개정 과목명·범위와 구분하고, 실제 개설 학년·학기와 선이수는 학교 안내로 확인하세요.')
        content+='<section class="cc-section"><div class="cc-wrap"><h2>교과별로 보기</h2>'+actions([(choice_path(v),v+' 과목') for v in SUBJECTS if v!=s])+'</div></section><section class="cc-section cc-tint"><div class="cc-wrap"><h2>과목의 내용과 학습 연결</h2><div class="cc-choice-grid">'
        for r in selected:
            course_id='course-'+str(choices.index(r)+1)
            content+='<article class="cc-choice" data-cc-card id="'+course_id+'"><p class="cc-kicker">'+E(r[0]+' · '+r[1])+'</p><h3><a href="'+U(path+'#'+course_id)+'">'+E(r[2])+'</a></h3><dl><dt>배우는 내용</dt><dd>'+E(r[3])+'</dd><dt>준비할 개념</dt><dd>'+E(r[4])+'</dd><dt>연결해 볼 공부</dt><dd>'+E(r[5])+'</dd><dt>학교에서 확인할 것</dt><dd>'+E(r[6])+'</dd></dl></article>'
        content+='</div></div></section><section class="cc-section"><div class="cc-wrap cc-reading"><h2>과목 선택 전에 확인하세요</h2>'+paras(['학교의 입학 연도별 교육과정 편제표에서 과목명·개설 학년·학기와 선택 가능 범위를 확인하세요. 먼저 이수할 과목이 있는지, 선택 안내의 신청 일정과 변경 조건은 무엇인지 학교의 안내를 함께 살펴봅니다.','학교 수업 범위와 수능 응시 범위는 각각 확인해야 합니다. 특정 학년에 위 과목 모두를 배우는 것으로 생각하지 말고, 현재 이수할 과목과 필요한 준비 개념을 나란히 적어 보세요.'])+actions([(grade_path(g),grade_name(g)+' 커리큘럼') for g in ['고1','고2','고3']])+references(MOE22,'2022 개정 국어·수학·영어·사회·과학 각론의 공통·선택과목')+locator()+'</div></section>'
        pages.append((path,title,summary,shell(path,title,summary,content,[] if not s else [('고등 공통·선택과목',choice_path())])))
    return pages

def bridge(path,context,center=None):
    stage=context.get('stage') if context else None;subject=context.get('subject') if context else None
    target=stage_path(stage) if stage else BASE
    items=[]
    if subject:items.append((filtered(target,subject),(stage+' ' if stage else '')+subject+' 학년별 공부 순서'))
    elif stage:items.append((U(target),stage+' 학년별 공부 범위'))
    elif center:
        grades=set(g for v in center['subjects'].values() for g in v)
        for prefix,s in STAGES.items():
            if any(g.startswith(prefix) for g in grades):items.append((U(stage_path(s)),s+' 학년별 공부 범위'))
    else:items=[(U(stage_path(s)),s+' 학년별 공부 범위') for s in STAGES.values()]
    if not items:items=[(U(BASE),'전체 학년·과목 커리큘럼')]
    label=(context['neighborhood']+'에서 수업을 알아보며') if context and context.get('neighborhood') else '현재 공부 범위를 확인하고 싶다면'
    return '<section class="cc-bridge" data-curriculum-bridge><div class="cc-bridge-wrap"><p class="cc-bridge-kicker">'+E(label)+'</p><h2>우리 아이 학년의 공부 순서도 살펴보세요</h2><p>배우는 내용과 확인 과제를 먼저 살펴보고, 학교 진도와 현재 이해에 맞는 공부 방향을 정해 보세요.</p><div class="cc-bridge-links">'+''.join('<a href="'+p+'">'+E(t)+'<span aria-hidden="true">→</span></a>' for p,t in items)+'</div><p class="cc-bridge-small">커리큘럼은 학습 참고 안내입니다. 실제 수업 가능 학년·과목과 교재는 지점 안내에서 확인하세요.</p><a class="cc-bridge-all" href="/공부커리큘럼/">공부커리큘럼 전체 보기 →</a></div></section>'

def build():
    baseline=load(OUT/'baseline-manifest.json');contexts={r['path']:r for r in inventory()};centers={center_path(c):c for c in FACTS['centers']}
    subjects=rows('초등과목')+rows('중등과목')+rows('고등과목');assert len(subjects)==66
    pages=directories(subjects)+[subject_page(r) for r in subjects]+choices();assert len(pages)==89 and len({p for p,*_ in pages})==89
    changed=[];bridged=[];counts=Counter()
    def integrate(name):
        p=ROOT/name;original=p.read_text('utf-8-sig');text=original;path='/' if name=='index.html' else '/'+name.removesuffix('index.html')
        if 'data-curriculum-nav' not in text:
            text,count=re.subn(r'(<div\b[^>]*class="(?:nav-links|lg-nav-links|tf-nav-links|ei-nav-links)"[^>]*>)',lambda m:m.group(1)+NAV,text,count=1);assert count==1,name
        if 'data-curriculum-style' not in text:text=text.replace('</head>',CSS+'</head>',1)
        should_bridge=path in contexts or path.startswith('/지점안내/') or path in ['/', '/전국센터/','/과목별학원/']
        if should_bridge and 'data-curriculum-bridge' not in text:
            assert text.count('</main>')==1,name
            text=text.replace('</main>',bridge(path,contexts.get(path),centers.get(path))+'</main>',1)
        text=patch_dates(text)
        write(p,text)
        return name,digest(p.read_bytes())!=baseline['files'][name],should_bridge
    old_html=[n for n in baseline['files'] if n.endswith('.html')]
    with ThreadPoolExecutor(max_workers=8) as pool:
        for i,(name,did_change,did_bridge) in enumerate(pool.map(integrate,old_html),1):
            if did_change:changed.append(name)
            if did_bridge:bridged.append(name)
            counts[name.split('/')[0] if '/' in name else '/']+=1
            if i%2000==0:print('Integrated curriculum menu through',i,'pages',flush=True)
    new={'assets/curriculum.css','assets/curriculum.js'};descriptions=load(ROOT/'seo-descriptions.json')
    for path,title,summary,content in pages:
        name=path.strip('/')+'/index.html';write(ROOT/name,content);new.add(name)
        descriptions['pages'][path.rstrip('/')]=dict(description=summary,sources=[summary])
    dump(ROOT/'seo-descriptions.json',descriptions)
    sitemap_raw=(ROOT/'sitemap.xml').read_text('utf-8');existing={unquote(urlsplit(u).path):u for u in etree.fromstring(sitemap_raw.encode()).xpath('//*[local-name()="loc"]/text()')}
    modified={existing['/' if n=='index.html' else '/'+n.removesuffix('index.html')] for n in changed}
    modified|={existing[path] for path,*_ in pages if path in existing}
    def update(m):return m.group(1)+DATE+m.group(3) if escape.unescape(m.group(2)) in modified else m.group(0)
    sitemap=re.sub(r'(<url>\s*<loc>([^<]+)</loc>\s*<lastmod>)[^<]+(</lastmod>)',update,sitemap_raw)
    for path,*_ in pages:
        if path not in existing:sitemap=sitemap.replace('</urlset>',f'  <url>\n    <loc>{url(path)}</loc>\n    <lastmod>{DATE}</lastmod>\n  </url>\n</urlset>')
    write(ROOT/'sitemap.xml',sitemap)
    raw=(ROOT/'rss.xml').read_bytes();feed=etree.fromstring(raw,etree.XMLParser(resolve_entities=False,no_network=True,remove_blank_text=True,strip_cdata=False));channel=feed.find('channel');old_ids=[identity(it) for it in channel.findall('item')]
    for item in channel.findall('item'):
        canonical=item.findtext('link');path=unquote(urlsplit(canonical).path);name='index.html' if path=='/' else path.strip('/')+'/index.html'
        content,_=body(html.document_fromstring((ROOT/name).read_bytes()),canonical);item.find('description').text=etree.CDATA(content)
    # RSS keeps the existing article cohort and adds the six regional learning entrances.
    cohort=[p for p in pages if p[0] in [BASE,*[stage_path(s) for s in STAGES.values()],choice_path(),choice_path('수학')]]
    existing_links={item.findtext('link') for item in channel.findall('item')}
    published=OUT/'publication.json'
    if not published.exists():dump(published,{'rssPublication':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).replace(microsecond=0).isoformat()})
    for path,title,*_ in cohort:
        canonical=url(path)
        if canonical in existing_links:continue
        item=etree.SubElement(channel,'item');etree.SubElement(item,'title').text=title;etree.SubElement(item,'link').text=canonical;etree.SubElement(item,'guid',isPermaLink='true').text=canonical;etree.SubElement(item,'pubDate').text=format_datetime(datetime.datetime.fromisoformat(load(published)['rssPublication']));content,_=body(html.document_fromstring((ROOT/path.strip('/')/'index.html').read_bytes()),canonical);etree.SubElement(item,'description').text=etree.CDATA(content)
    if etree.tostring(feed,encoding='UTF-8',xml_declaration=True,pretty_print=True)!=raw:channel.find('lastBuildDate').text=format_datetime(datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).replace(microsecond=0))
    write(ROOT/'rss.xml',etree.tostring(feed,encoding='UTF-8',xml_declaration=True,pretty_print=True));assert [identity(it) for it in channel.findall('item')][:129]==old_ids[:129]
    names=sorted(set(baseline['files'])|new);text_names=set(baseline['textSha256'])|new
    def hashes(n):
        raw=(ROOT/n).read_bytes();return n,digest(raw),digest(raw.decode('utf-8').replace('\r\n','\n').encode()) if n in text_names else None
    with ThreadPoolExecutor(max_workers=12) as pool:values=list(pool.map(hashes,names))
    manifest=load(ROOT/'release-public-manifest.json');manifest['files']={n:h for n,h,_ in values};manifest['textSha256']={n:h for n,_,h in values if h};manifest['sitemapPages']=sum(n.endswith('.html') for n in names);dump(ROOT/'release-public-manifest.json',manifest)
    result={'newHtmlPages':len(pages),'gradePages':12,'gradeSubjectPages':66,'schoolStagePages':3,'highSubjectGroups':6,'highCourseEntries':29,'sourceLearningLevelExamples':45,'legacyPagesWithMenu':len(old_html),'legacyContextualBridgePages':len(bridged),'publicFiles':len(names),'sitemapPages':manifest['sitemapPages'],'rssItems':len(channel.findall('item')),'oldRssIdentitiesPreserved':129,'legacyFamilies':dict(counts),'newPublicFiles':sorted(new),'modifiedHtml':changed,'bridgeHtml':bridged,'pages':[{'path':p,'title':t,'description':d} for p,t,d,_ in pages],'deployed':False}
    dump(OUT/'implementation.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ['newPublicFiles','modifiedHtml','bridgeHtml','pages']},ensure_ascii=False))
if __name__=='__main__':build()
