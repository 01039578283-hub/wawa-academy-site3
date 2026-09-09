"""Idempotently enrich only the 28 existing site3 top-level directory hubs.

Requires beautifulsoup4. Curated input contains public facts, never raw reference
exports. No leaf manuscripts, URLs, contact details or existing images are edited.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from datetime import date
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

from bs4 import BeautifulSoup
from build_academy_hubs import load_manifest, REGION_ORDER, CATEGORIES, BASE_URL

ROOT = Path(__file__).resolve().parents[1]
CSS = '/assets/hub-guide-v1.css'
SUBJECTS = ['영수전문학원', '영어전문학원', '수학전문학원', '전문학원', '초등학생학원', '중학생학원', '고등학생학원']
PHOTO_INFO = [
    ('classroom-desks.webp', 500, 300, '개별 책상과 칸막이가 배치된 학습 공간', '개별 책상과 칸막이 배치를 살펴볼 수 있는 공통 학습 공간 사진입니다.'),
    ('classroom-study.webp', 800, 600, '학생들이 각자 교재를 펼쳐 공부하는 학습 공간', '각자의 교재로 공부하는 모습을 담은 공통 학습 공간 사진입니다.'),
]


def e(value):
    return html.escape(str(value), quote=True)


def p(value):
    return f'<p>{e(value)}</p>'


def url(path):
    return BASE_URL + quote(path, safe='/')


@lru_cache(maxsize=64)
def organization_id(target_path):
    """Read the real shared-center identity; a locality URL is not a center ID."""
    source=BeautifulSoup((ROOT/target_path.strip('/')/'index.html').read_text(encoding='utf-8'),'html.parser')
    identifiers=set()
    for script in source.find_all('script',attrs={'type':'application/ld+json'}):
        data=json.loads(script.get_text())
        nodes=data.get('@graph',[data]) if isinstance(data,dict) else data
        for node in nodes:
            types=node.get('@type',[])
            if isinstance(types,str): types=[types]
            if 'EducationalOrganization' in types and node.get('@id'):
                identifiers.add(node['@id'])
    if len(identifiers)!=1:
        raise ValueError(f'Expected one real center identity: {target_path}: {identifiers}')
    return identifiers.pop()


def root_copy(kind):
    if kind == 'national':
        return {
            'label': '전국센터',
            'summary': '전국센터는 371개 동네의 학습 안내를 지역과 학년·과목으로 찾아보는 곳입니다. 동네명은 안내 대상 지역이며 실제 방문 지점명과 같지 않을 수 있습니다. 지역을 선택한 뒤 지점 주소, 과목별 가능 학년, 학생의 학습 상태를 함께 확인하세요.',
            'description': '전국 371개 동네의 학습코칭 안내를 지역·학년·과목별로 찾으세요. 실제 방문 지점과 주소 예시, 영어·수학 학습 점검 방법, 상담 준비자료와 학습 공간을 안내합니다.',
            'sections': [
                {'heading': '동네 이름과 방문할 지점을 구분합니다', 'paragraphs': ['집이나 학교가 있는 동네를 먼저 찾고, 연결된 상세 안내에서 실제 지점명과 주소를 확인하세요. 인접한 여러 동네가 같은 센터의 안내 대상일 수 있으므로 동네 페이지 수를 실제 센터 수로 해석하면 안 됩니다.', '방문을 정할 때는 학교에서 센터까지, 수업 후 센터에서 집까지의 이동을 따로 생각해 보세요. 주소뿐 아니라 도착할 수 있는 시간과 다른 일정의 간격을 적어 두면 상담 시 가능한 일정을 확인하기 쉽습니다.']},
                {'heading': '학년보다 구체적인 학습 상태를 적어 봅니다', 'paragraphs': ['같은 학년이라도 영어 문장을 읽는 어려움과 수학 풀이를 시작하지 못하는 어려움은 다릅니다. 최근에 막힌 문제나 문장을 한두 개 골라 어디까지 혼자 할 수 있었는지 표시해 오세요.', '영어는 어휘·문장 구조·독해 근거, 수학은 개념 설명·계산·조건 해석을 나누어 살펴볼 수 있습니다. 아래 학년·과목별 안내에서 점검 항목을 고른 뒤 해당 센터의 가능 학년과 과목을 확인하세요.']},
                {'heading': '수업 뒤 혼자 할 일까지 연결합니다', 'paragraphs': ['상담에서 확인할 것은 수업 시간표만이 아닙니다. 수업 후 남길 풀이 기록, 집에서 다시 볼 문제, 다음 점검 때 가져갈 자료가 무엇인지 함께 물어보세요.', '플래너는 할 일을 적는 데서 끝나지 않고 완료 여부와 미완료 이유를 돌아보는 데 쓸 수 있습니다. 실제 기록 방식과 상담 주기, 수업 구성은 지점 및 학생 상황에 따라 확인해야 합니다.']},
            ],
            'faq': [
                {'question': '371개 동네 안내가 371개 실제 센터를 뜻하나요?', 'answer': '아닙니다. 371개는 동네별 안내 페이지 수입니다. 여러 동네가 같은 센터에 연결될 수 있으므로 실제 방문 장소는 상세 안내의 지점명과 주소를 기준으로 확인하세요.'},
                {'question': '어느 과목 안내부터 읽으면 좋을까요?', 'answer': '영어 문장을 이해하는 데 어려움이 있다면 영어 안내, 수학 문제의 조건이나 풀이가 막힌다면 수학 안내부터 살펴보세요. 두 과목이 모두 필요하면 과목별 어려움을 따로 적고 영어·수학 통합 학습 안내를 비교할 수 있습니다.'},
                {'question': '집 근처 동네 페이지가 있으면 바로 등록할 수 있나요?', 'answer': '동네 안내의 존재가 현재 모집이나 개설 시간표를 보장하지는 않습니다. 실제 지점, 해당 학년·과목의 수업 가능 여부와 시간은 상담에서 확인해야 합니다.'},
            ],
        }
    return {
        'label': '과목별학원',
        'summary': '과목별학원에서는 영어·수학 전문 안내와 초등·중등·고등 학습 안내를 비교할 수 있습니다. 과목명이 같아도 학생이 어려워하는 지점은 다릅니다. 아래 분류에서 학습 점검 기준을 읽고 동네별 안내로 이동해 실제 지점과 가능 학년을 확인하세요.',
        'description': '영어·수학·영수 전문학원과 초등학생·중학생·고등학생 학원 안내를 비교하세요. 학습 상태별 선택 기준, 과목별 진단·복습 방법, 실제 지점 정보와 상담 준비사항을 정리했습니다.',
        'sections': [
            {'heading': '한 과목의 어려움을 깊게 확인할 때', 'paragraphs': ['영어 단어는 아는데 문장이 연결되지 않는지, 수학 개념은 설명하지만 문제에 적용하지 못하는지에 따라 먼저 볼 기록이 달라집니다. 영어전문학원과 수학전문학원 안내는 과목별로 막힌 지점을 구분하는 데 활용하세요.', '상담 전에 점수만 적기보다 답의 근거를 못 찾았던 지문이나 처음 손을 대지 못한 문제를 남겨 두세요. 풀이 과정과 생각의 흔적이 있으면 다음에 연습할 행동을 더 구체적으로 이야기할 수 있습니다.']},
            {'heading': '두 과목의 공부 시간이 충돌할 때', 'paragraphs': ['영수전문학원 안내에서는 영어와 수학을 한 덩어리로 평가하기보다 각각의 진단 결과와 복습 시간을 구분합니다. 영어 암기를 오래 하느라 수학 복습을 미루는지, 수학 숙제 때문에 영어 독해가 밀리는지 일주일 기록을 살펴보세요.', '전문학원 안내는 진단 이후 계획·실행·재점검이 어떻게 이어지는지 확인할 때 유용합니다. 분류 이름만으로 모든 과목이 개설되어 있다고 판단하지 말고 실제 센터의 과목과 학년 범위를 확인하세요.']},
            {'heading': '학년 변화와 생활 습관을 함께 볼 때', 'paragraphs': ['초등학생 안내는 읽고 설명하는 기초와 과제 시작 습관, 중학생 안내는 학교 진도와 평가에 맞춘 복습, 고등학생 안내는 과목별 우선순위와 시험 이후 보완 계획을 중심으로 읽어 보세요.', '학년 전체의 고민과 한 과목의 고민이 겹칠 수 있습니다. 학년별 안내에서 생활과 일정의 기준을 먼저 정리하고, 과목별 안내에서 구체적인 문제 해결 방법을 보완하는 순서도 가능합니다.']},
        ],
        'faq': [
            {'question': '영수전문학원과 전문학원 안내는 어떻게 다른가요?', 'answer': '영수전문학원 안내는 영어와 수학의 진단·복습 시간 배분에 초점을 둡니다. 전문학원 안내는 진단에서 개인 계획, 수업 실행과 재점검까지 이어지는 학습관리 과정을 살펴보는 데 초점을 둡니다. 실제 개설 과목은 지점별로 확인해야 합니다.'},
            {'question': '학년별 안내와 과목별 안내 중 하나만 보면 되나요?', 'answer': '반드시 하나만 고를 필요는 없습니다. 학년별 안내에서 학교생활과 시험 일정의 기준을 살펴보고, 영어 또는 수학 안내에서 현재 막힌 학습 영역을 구체화할 수 있습니다.'},
            {'question': '모든 동네에서 모든 과목과 학년 수업이 가능한가요?', 'answer': '그렇게 단정할 수 없습니다. 이 페이지의 분류는 학습 안내를 찾기 위한 기준입니다. 실제 수업은 동네별 상세 안내에 연결된 센터의 가능 과목과 학년, 상담 시 확인한 개설 시간을 기준으로 결정하세요.'},
        ],
    }


def region_copy(region, rows):
    districts = list(dict.fromkeys(r['district'] for r in rows))
    display = '·'.join(districts[:5])
    labels = '·'.join(r['display'] for r in rows[:4])
    return {
        'label': f'{region} 지역',
        'summary': f'{region} 지역의 {len(districts)}개 안내 구역, {len(rows)}개 동네 학습 안내를 모았습니다. {display} 등의 목록에서 집이나 학교와 가까운 동네를 고른 뒤 실제 지점명과 주소를 확인하세요. 학습 공간과 상담 준비 방법도 함께 살펴볼 수 있습니다.',
        'description': f'{region} {len(districts)}개 안내 구역의 {len(rows)}개 동네 학습코칭 안내. {display} 등 지역 목록과 실제 지점 확인 방법, 과목별 학년 범위, 상담 준비자료와 학습 공간을 살펴보세요.',
        'sections': [
            {'heading': f'{region}에서 동네와 실제 센터 위치를 확인하는 순서', 'paragraphs': [f'이 지역에는 {labels} 등의 동네 안내가 있습니다. 아래 시·군·구 목록은 동네를 찾는 분류이며, 같은 센터가 주변 여러 동네의 학생에게 안내될 수 있습니다. 페이지 제목의 동네명보다 실제 센터 주소를 방문 기준으로 삼으세요.', f'{display} 등 관심 지역을 찾았다면 학교가 끝나는 시간과 센터에 도착 가능한 시간을 함께 적어 보세요. 다른 시·군·구에 있는 센터가 연결되는 경우에도 안내 주소를 기준으로 이동 가능 여부를 판단해야 합니다.']},
            {'heading': '교재와 오답에서 상담할 질문을 고릅니다', 'paragraphs': ['영어는 단어를 모르는 문제와 문장 구조를 해석하지 못한 문제를 나누고, 수학은 개념을 떠올리지 못한 문제와 계산 중 틀린 문제를 구분해 보세요. 서로 다른 어려움을 모두 숙제 부족으로 묶지 않는 것이 출발점입니다.', '현재 교재의 진도, 최근 시험지, 풀이 흔적을 함께 준비하면 어떤 내용을 되짚을지 구체적으로 이야기할 수 있습니다. 학교명이나 시험 점수만으로 수업을 정하기보다 학생이 실제로 해낸 과정을 보여 주세요.']},
            {'heading': '방문 전 확인할 운영 조건을 정리합니다', 'paragraphs': ['같은 브랜드라도 과목별 가능 학년과 개설 시간은 센터마다 다를 수 있습니다. 영어·수학을 함께 보려면 두 과목의 가능 범위를 각각 확인하고, 형제자매가 함께 상담할 때도 학생별 학년과 과목을 따로 전달하세요.', '교육비는 학년과 주당 횟수, 회당 수업 시간, 별도 교재비 등에 따라 비교해야 합니다. 지점 상세 안내를 살펴본 뒤 실제 적용 금액과 시간표는 방문 전에 다시 확인하세요.']},
        ],
        'faq': [
            {'question': f'{region} 지역에는 어떤 동네 안내가 있나요?', 'answer': f'{display} 등 {len(districts)}개 안내 구역으로 나눈 {len(rows)}개 동네 안내가 있습니다. 지역 목록에서 동네를 선택하면 연결된 실제 센터와 학습 정보를 확인할 수 있습니다.'},
            {'question': f'{region} 목록의 동네마다 별도 센터가 있나요?', 'answer': '반드시 그렇지는 않습니다. 여러 동네가 같은 센터에 연결될 수 있고, 안내 동네와 센터 소재지가 다를 수 있습니다. 실제 방문은 상세 안내의 지점명과 주소를 확인한 후 결정하세요.'},
            {'question': f'{region} 지역 센터에서 영어와 수학을 함께 배울 수 있나요?', 'answer': '과목별 가능 학년은 지점마다 다릅니다. 동네 상세 안내에서 영어와 수학의 학년 범위를 각각 살펴본 뒤, 희망 요일과 현재 개설 여부를 상담에서 확인하세요.'},
        ],
    }


def render_guide(copy, centers, is_region):
    label = copy['label']
    cards = ''.join(f'<article class="hub-guide-card"><span class="hub-guide-number">0{i}</span><h3>{e(x["heading"])}</h3>{"".join(p(t) for t in x["paragraphs"])}</article>' for i, x in enumerate(copy['sections'], 1))
    parts = [f'<section class="hub-guide" data-hub-enrichment="content" id="hub-learning-guide"><div class="wrap"><div class="hub-guide-heading"><p class="eyebrow">LEARNING GUIDE</p><h2>{e(label)} 학습 선택 가이드</h2><p>진도나 점수만으로 결정하기 전에, 학생의 현재 기록과 수업 뒤 할 일을 함께 살펴보세요.</p></div><div class="hub-guide-grid">{cards}</div></div></section>']
    if centers:
        entries = []
        for c in centers:
            subjects = ' / '.join(f'{x["name"]}: {x["summary"]}' for x in c['subjects'])
            entries.append(f'<article class="hub-guide-card hub-center-card"><p class="hub-guide-note">{e(c["region"])} · {e(c["locality"])} 안내 연결</p><h3>{e(c["centerName"])}</h3><dl><dt>방문 주소</dt><dd>{e(c["address"])}</dd><dt>등록 학원명</dt><dd>{e(c["registeredAcademyName"])}</dd><dt>등록번호</dt><dd>{e(c["registrationNumber"])}</dd><dt>자료에 기재된 과목·학년</dt><dd>{e(subjects)}</dd></dl><a href="{e(c["targetPath"])}">{e(c["locality"])} 지점·학습 안내 보기 →</a></article>')
        parts.append(f'<section class="hub-guide" data-hub-enrichment="content" id="hub-center-examples"><div class="wrap"><div class="hub-guide-heading"><p class="eyebrow">CENTER INFORMATION</p><h2>{e(label)} 안내에 연결된 지점 예시</h2><p class="hub-guide-note">아래는 연결 지점의 일부 예시이며 추천 순위가 아닙니다. 기재되지 않은 과목을 미운영으로 단정하지 마세요. 현재 개설 시간과 수강 가능 여부는 상담에서 확인합니다.</p></div><div class="hub-guide-grid hub-center-grid">{"".join(entries)}</div><div class="hub-guide-reading"><p>다른 동네는 <a href="#hub-directory">위의 지역·동네 목록</a>에서 확인할 수 있습니다. 지점이 같은 경우에도 학생별 진도와 상담할 내용은 다를 수 있습니다.</p></div></div></section>')
    else:
        parts.append('<section class="hub-guide" data-hub-enrichment="content" id="hub-center-examples"><div class="wrap"><h2>실제 방문할 지점 확인하기</h2><p>관심 동네의 상세 안내에서 실제 지점명과 주소를 확인하세요. 방문 전에 현재 위치와 개설 시간을 상담으로 확인하면 동네 이름과 방문 장소를 혼동하지 않을 수 있습니다.</p><a class="btn btn-ghost" href="#hub-directory">지역·동네 목록에서 찾기</a></div></section>')
    parts.append('<section class="hub-guide" data-hub-enrichment="content" id="hub-consultation-guide"><div class="wrap"><div class="hub-guide-heading"><p class="eyebrow">BEFORE CONSULTATION</p><h2>상담에서 계획과 복습까지 연결하는 방법</h2></div><div class="hub-guide-grid"><article class="hub-guide-card"><h3>가져갈 자료</h3><p>현재 교재와 최근 시험지, 정답을 지우지 않은 오답 풀이를 준비하세요. 모든 자료를 정리하기 어렵다면 혼자 해결하지 못한 문제 한두 개와 다음 평가 일정을 골라도 좋습니다.</p></article><article class="hub-guide-card"><h3>계획에서 확인할 것</h3><p>한 주에 가능한 공부 시간과 실제로 완료한 분량을 나누어 적어 보세요. 해야 할 일뿐 아니라 어디서 오래 멈췄는지 이야기하면 과제량과 복습 순서를 함께 조정할 기준이 됩니다.</p></article><article class="hub-guide-card"><h3>다시 점검할 것</h3><p>해설을 본 직후의 정답과 시간이 지난 뒤 혼자 푼 정답은 다릅니다. 어떤 문제를 다시 풀고, 틀린 이유와 바꾼 풀이를 무엇에 남길지 확인하세요. 구체적인 기록·소통 방식은 지점별로 상담합니다.</p></article></div><div class="hub-guide-reading"><p><a href="/학습관리/">학습관리 과정 더 알아보기</a> · <a href="/상담문의/">상담 준비 후 문의하기</a></p><p class="hub-guide-note">교육비는 학년, 주당 횟수, 회당 시간과 교재비 포함 여부를 같은 기준으로 비교하세요. 실제 적용 비용과 시간표는 해당 센터 상담에서 확인합니다.</p></div></div></section>')
    pictures = ''.join(f'<figure><img src="/assets/hub-guide/{filename}" width="{w}" height="{h}" alt="{e(label)} {e(alt)}" loading="lazy" decoding="async"><figcaption>{e(caption)}</figcaption></figure>' for filename,w,h,alt,caption in PHOTO_INFO)
    parts.append(f'<section class="hub-guide" data-hub-enrichment="content" id="hub-learning-space"><div class="wrap"><div class="hub-guide-heading"><p class="eyebrow">LEARNING SPACE</p><h2>학습 공간 살펴보기</h2><p class="hub-guide-note">와와 학습 공간의 공통 예시입니다. 선택한 지점의 실제 내부를 보증하는 사진은 아니며, 책상 배치와 시설은 지점별로 다를 수 있습니다.</p></div><div class="hub-guide-gallery">{pictures}</div></div></section>')
    return ''.join(parts)


def parse_fragment(text):
    return BeautifulSoup(text, 'html.parser')


def update_page(rel, copy, centers, modified):
    path = ROOT / rel
    before = path.read_text(encoding='utf-8')
    soup = BeautifulSoup(before, 'html.parser')
    canonical = soup.find('link', rel='canonical')['href']
    fixed = (soup.title.get_text(), soup.h1.get_text(), canonical, soup.find('meta', property='og:url')['content'])
    for old in soup.select('[data-hub-enrichment]'):
        old.decompose()
    # Existing generic hub decision guide is replaced, not stacked with another version.
    old_guide = soup.find(id='hub-decision-guide')
    if old_guide:
        old_guide.decompose()
    main = soup.find('main')
    hero = main.select_one('.center-hero')
    hero_text = hero.find('h1').find_next_sibling('p')
    if not hero_text:
        raise ValueError(f'No hero summary: {rel}')
    hero_text.clear()
    hero_text.append(copy['summary'])
    directory = main.find(id='subject-categories')
    if directory is None:
        search = main.find('input', attrs={'type': 'search'})
        directory = search.find_parent('section') if search else None
    if directory is None:
        directory = next((s for s in main.find_all('section', recursive=False) if s != hero and len(s.find_all('a')) >= 6), None)
    if directory is None:
        raise ValueError(f'No directory detected: {rel}')
    directory.insert_before(parse_fragment('<span id="hub-directory" class="hub-directory-anchor" data-hub-enrichment="anchor"></span>'))
    hero.insert_after(parse_fragment('<nav class="hub-guide-jumps" data-hub-enrichment="navigation" aria-label="이 페이지 빠른 이동"><div class="wrap"><a href="#hub-directory">지역·분류 목록</a><a href="#hub-learning-guide">학습 선택 가이드</a><a href="#hub-center-examples">지점 정보</a><a href="#hub-consultation-guide">상담 준비</a><a href="#hub-learning-space">학습 공간</a><a href="#hub-questions">자주 묻는 질문</a></div></nav>'))
    faq = soup.select_one('#faq-section, #hub-faq-section')
    if faq is None:
        raise ValueError(f'No existing FAQ: {rel}')
    faq.insert_before(parse_fragment(render_guide(copy, centers, len(rel.split('/')) == 3 and rel.split('/')[1] in REGION_ORDER)))
    faq.clear()
    faq['class'] = ['hub-guide', 'hub-guide-faq']
    qa = list(copy['faq']) + [
        {'question': '상담 전 어떤 자료를 준비하면 도움이 되나요?', 'answer': '현재 교재, 최근 시험지나 오답 풀이, 다음 평가 일정과 일주일에 공부 가능한 시간을 준비하세요. 자료가 부족하면 혼자 풀다가 막힌 문제 한두 개를 가져와도 상담할 내용을 구체화하는 데 도움이 됩니다.'},
        {'question': '여기에 나온 사진과 교육 내용이 모든 지점에 똑같이 적용되나요?', 'answer': '아닙니다. 사진은 공통 학습 공간 예시이며 실제 시설과 책상 배치는 지점마다 다를 수 있습니다. 학습 점검 방법은 상담에 참고할 안내이고, 가능 학년·과목·시간표·교습비와 운영 방식은 실제 센터에서 확인해야 합니다.'},
    ]
    faq.append(parse_fragment(f'<div class="wrap" id="hub-questions"><p class="eyebrow">FAQ</p><h2>{e(copy["label"])} 자주 묻는 질문</h2>'+''.join(f'<details><summary>{e(q["question"])}</summary>{p(q["answer"])}</details>' for q in qa)+'</div>'))
    for selector in [('name','description'), ('property','og:description'), ('name','twitter:description')]:
        attr,key = selector
        meta=soup.find('meta',attrs={attr:key})
        if meta:
            meta['content']=copy['description']
    if not soup.find('link',href=CSS):
        soup.head.append(soup.new_tag('link',rel='stylesheet',href=CSS))
    graphs=[]
    scripts=soup.find_all('script',attrs={'type':'application/ld+json'})
    for script in scripts:
        data=json.loads(script.get_text())
        graphs.extend(data.get('@graph',[data]) if isinstance(data,dict) else data)
    graphs=[n for n in graphs if n.get('@type')!='FAQPage' and not str(n.get('@id','')).startswith(canonical+'#hub-')]
    collection=next(n for n in graphs if n.get('@type')=='CollectionPage')
    collection['description']=copy['description']
    collection['dateModified']=modified
    collection['isPartOf']={'@id':BASE_URL+'/#website'}
    # Reuse the organization actually declared on the existing home page.
    collection['publisher']={'@id':BASE_URL+'/#organization'}
    collection['about']=[{'@type':'Thing','name':copy['label']}, {'@type':'Thing','name':'학습 진단과 복습 계획'}]
    old_parts=collection.get('hasPart',[])
    if not isinstance(old_parts,list): old_parts=[old_parts]
    old_parts=[x for x in old_parts if 'hub-' not in str(x.get('@id','')) and 'hub-decision-guide' not in str(x.get('url',''))]
    sections=[('hub-learning-guide',copy['label']+' 학습 선택 가이드'),('hub-center-examples','연결 지점 정보'),('hub-consultation-guide','상담에서 계획과 복습까지 연결하는 방법'),('hub-learning-space','학습 공간 살펴보기')]
    collection['hasPart']=old_parts+[{'@id':canonical+'#'+sid} for sid,_ in sections]+[{'@id':canonical+'#hub-faq'}]
    collection['mentions']=[{'@id':organization_id(c['targetPath'])} for c in centers]
    for sid,label in sections:
        graphs.append({'@type':'WebPageElement','@id':canonical+'#'+sid,'url':canonical+'#'+sid,'name':label,'isPartOf':{'@id':collection['@id']}})
    graphs.append({'@type':'FAQPage','@id':canonical+'#hub-faq','url':canonical+'#hub-questions','isPartOf':{'@id':collection['@id']},'mainEntity':[{'@type':'Question','name':q['question'],'acceptedAnswer':{'@type':'Answer','text':q['answer']}} for q in qa]})
    if not any(n.get('@id')==BASE_URL+'/#website' for n in graphs):
        graphs.append({'@type':'WebSite','@id':BASE_URL+'/#website','url':BASE_URL+'/','name':'와와학습코칭학원','inLanguage':'ko-KR','publisher':{'@id':BASE_URL+'/#organization'}})
    for script in scripts[1:]: script.decompose()
    scripts[0].string=json.dumps({'@context':'https://schema.org','@graph':graphs},ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    # Put the new learning explanation near the top, not below 371 locality links.
    guide=soup.find(id='hub-learning-guide').extract()
    soup.select_one('.hub-guide-jumps').insert_after(guide)
    after=str(BeautifulSoup(str(soup),'html.parser'))
    assert fixed == (soup.title.get_text(),soup.h1.get_text(),soup.find('link',rel='canonical')['href'],soup.find('meta',property='og:url')['content'])
    if before!=after:
        path.write_text(after,encoding='utf-8',newline='\n')
    return {'path':rel,'changed':before!=after,'sha256':hashlib.sha256(after.encode()).hexdigest(),'faq':len(qa),'centers':len(centers)}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--date',default=date.today().isoformat())
    args=parser.parse_args()
    topics=json.loads((ROOT/'tools/data/hub-guides/subject-copy.json').read_text(encoding='utf-8'))
    examples=json.loads((ROOT/'tools/data/hub-guides/center-examples.json').read_text(encoding='utf-8'))
    if isinstance(examples,dict): examples=examples.get('centers',examples.get('examples'))
    manifest=load_manifest(ROOT)
    targets=[('전국센터/index.html',root_copy('national'),[next(c for c in examples if c['region']==r) for r in ['서울','경기','부산']]),('과목별학원/index.html',root_copy('subjects'),[next(c for c in examples if c['region']==r) for r in ['서울','대구','광주']])]
    for region in REGION_ORDER:
        rows=[r for r in manifest if r['region']==region]
        targets.append((f'전국센터/{region}/index.html',region_copy(region,rows),[c for c in examples if c['region']==region]))
    for group, slugs in [('전국센터',CATEGORIES),('과목별학원',SUBJECTS)]:
        for slug in slugs:
            copy=topics[slug]
            # Only show examples whose recorded subjects/grades fit this topic.
            required = ['영어','수학'] if '영수' in slug else ['영어'] if '영어' in slug else ['수학'] if '수학' in slug else []
            stage = next((x for x in ['초','중','고'] if slug.startswith(x)), '')
            candidates=[c for c in examples if all(any(s['name']==name and (not stage or any(g.startswith(stage) for g in s['grades'])) for s in c['subjects']) for name in required)
                        and (not stage or any(any(g.startswith(stage) for g in s['grades']) for s in c['subjects']))]
            offset=list(topics).index(slug)%len(candidates)
            selected=[candidates[(offset+i*7)%len(candidates)] for i in range(3)]
            targets.append((f'{group}/{slug}/index.html',copy,selected))
    assert len(targets)==28 and len({t[0] for t in targets})==28
    results=[update_page(*t,modified=args.date) for t in targets]
    report=ROOT/'tools/reports/hub-enrichment/generation.json'
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps({'date':args.date,'targets':results},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'hubs':len(results),'changed':sum(r['changed'] for r in results),'faq':sum(r['faq'] for r in results)},ensure_ascii=False))


if __name__=='__main__':
    main()
