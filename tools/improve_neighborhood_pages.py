"""Preserve routes; distinguish enrollment pages from useful local study guides.

Inputs are reviewed center/route snapshots. Transform existing published HTML,
never regenerate it from old manuscripts. --sample is the representative pass;
--all applies the same bounded transform. Run validate_neighborhood_seo.py before
--refresh-manifest. Re-running is intentionally byte-stable.
"""
from __future__ import annotations
from pathlib import Path
from urllib.parse import quote,unquote,urlsplit
from collections import Counter
import argparse,hashlib,json,re,datetime,time
from lxml import html,etree
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'tools/data/neighborhood-seo'
REPORT=ROOT/'tools/reports/neighborhood-seo'
DOMAIN='https://xn--sp5b72l1taf0p.com'
DAY='2026-09-30'
VERSION='20260930-v1'
load=lambda p:json.loads(p.read_text('utf-8-sig'))
def dump(p,d):
 value=json.dumps(d,ensure_ascii=False,indent=2)+'\n'
 if p.exists() and p.read_text('utf-8')==value:return
 pending=p.with_name(p.name+'.tmp');pending.write_text(value,'utf-8');pending.replace(p)
def write_page(path,value):
 assert path.resolve().is_relative_to(ROOT.resolve()) and path.name=='index.html'
 pending=path.with_name('index.html.neighborhood-tmp')
 for attempt in range(3):
  try:
   pending.write_text(value,'utf-8');pending.replace(path);return
  except OSError as error:
   if error.errno not in [13,22] or attempt==2:raise
   time.sleep(.2)
norm=lambda s:re.sub(r'\s+','',s)
E=lambda s:__import__('html').escape(str(s),quote=True)
U=lambda p:quote(p,safe='/#')
FACTS=load(DATA/'centers.json')
CENTERS={(c['region'],c['routeName']):c for c in FACTS['centers']}
SUBJECTS=load(DATA/'subjects.json'); GRADES=load(DATA/'grades.json')
SUB_BY_PATH={r['path']:r for r in SUBJECTS}
GRADE_BY_PATH={r['path']:r for r in GRADES}
PROFILES=load(DATA/'learning-profiles.json')
CONFLICTS=load(DATA/'source-conflicts.json') if (DATA/'source-conflicts.json').exists() else []
CATEGORIES={
 '전문학원':('학습관리 비교','과목별 목표와 복습 시간','현재 교재, 과제 완료 기록과 일주일 공부 시간표',[
  ('시작이 늦어지는 이유','정한 시각에 공부를 시작했는지, 시작한 뒤 어느 부분에서 멈췄는지 나누어 기록합니다. 실행하지 못한 계획은 분량·난도·시간 중 무엇을 바꾸면 좋을지 상담해 보세요.'),
  ('확인하는 사람과 시점','과제를 제출한 뒤 틀린 이유를 누가 확인하는지, 피드백을 받은 문제를 언제 다시 풀어 보는지 물어보세요. 관리 횟수와 실제 복습 행동을 함께 비교합니다.'),
  ('다음 계획의 기준','완료한 양과 혼자 설명할 수 있는 내용을 각각 남깁니다. 다음 주 계획에서 줄일 것과 다시 확인할 것을 학생이 구분할 수 있는지 살펴보세요.')]),
 '영수전문학원':('영어·수학 시간 배분','영어와 수학의 공백을 따로 확인','영어 답안과 어휘 기록, 수학 풀이와 과목별 시간표',[
  ('과목별 출발점','영어는 어휘·문장 구조·독해 근거를, 수학은 개념·조건 해석·계산 과정을 나누어 표시합니다. 두 과목에 같은 시간을 배정하기 전에 도움 없이 해결한 부분을 비교하세요.'),
  ('일주일 시간 배분','학교 수업과 다른 일정 뒤에 남는 시간을 적고, 어려운 과목의 복습 시간을 먼저 확보합니다. 한 과목의 과제가 다른 과목 공부를 계속 미루게 하는지도 확인합니다.'),
  ('수강 조건을 각각 확인','같은 지점에서도 영어와 수학의 안내 학년이 다를 수 있습니다. 두 과목의 수업 가능 학년과 요일, 시간, 교습비를 각각 질문해 보세요.')]),
 '영어전문학원':('영어 학습 비교','어휘·구문·독해의 근거','최근 영어 답안, 어휘 기록과 직접 쓴 문장',[
  ('읽기와 이해를 구분','낱말을 읽을 수 있는 것과 문맥에 맞는 뜻을 찾는 것을 따로 확인합니다. 짧은 글에서 모르는 어휘와 구조를 표시하고 도움이 필요한 부분을 좁혀 보세요.'),
  ('선택지의 근거','맞힌 문제도 답을 뒷받침하는 문장을 찾아봅니다. 오답은 어휘, 수식 관계, 글의 흐름 가운데 무엇을 놓쳤는지 기록해 수업 상담에 활용하세요.'),
  ('직접 표현한 답안','예문을 외운 뒤 조건이 바뀌어도 문장을 완성할 수 있는지 확인합니다. 철자·동사 형태·어순을 고친 흔적과 다음 복습 날짜를 함께 남깁니다.')]),
 '수학전문학원':('수학 학습 비교','개념 선택과 풀이 과정','풀이가 남은 수학 교재, 최근 평가와 재풀이 기록',[
  ('첫 식을 선택한 이유','문제의 조건에 표시하고 어떤 개념을 사용했는지 말로 설명합니다. 공식을 기억한 경우와 적용 조건을 판단한 경우를 구분해 보세요.'),
  ('오류가 시작된 단계','정답만 고치지 말고 조건 해석·개념 선택·계산·답안 표현 중 처음 어긋난 단계를 표시합니다. 수업에서는 그 단계를 어떻게 확인하는지 질문하세요.'),
  ('혼자 다시 푼 기록','해설을 본 직후와 며칠 뒤의 풀이를 비교합니다. 수나 조건이 바뀌어도 풀이를 시작할 수 있는지 확인하고 다음 단원 전에 보완할 개념을 정합니다.')]),
 '초등학생학원':('초등 학습 비교','읽기·연산과 짧은 복습','현재 읽기 자료, 연산장과 아이가 직접 설명한 기록',[
  ('아이의 말로 확인','배운 문장을 읽고 뜻을 설명하거나, 계산 전에 무엇을 구하는 문제인지 말해 보게 합니다. 답을 맞힌 것과 스스로 설명한 것을 따로 남겨 주세요.'),
  ('과목별 학년 확인','초등 수업이라고 모든 과목이 같은 학년부터 가능한 것은 아닙니다. 영어와 수학의 안내 학년을 각각 확인하고 아이의 학년에 맞는지 먼저 질문하세요.'),
  ('짧게 다시 해 보기','부담 없이 다시 확인할 낱말이나 문제 몇 개를 정합니다. 숙제를 늘리기 전에 아이가 혼자 끝낸 부분과 도움을 요청한 부분을 함께 살펴보세요.')]),
 '중학생학원':('중등 학습 비교','학교 진도와 답안 과정','학교 진도표, 최근 평가와 서술형 답안',[
  ('진도와 개념 연결','학교에서 배운 범위와 현재 교재의 범위를 나란히 적습니다. 영어의 문장 구조, 수학의 앞 단원 개념 중 먼저 보완할 부분을 찾으세요.'),
  ('서술형 답안 점검','영어는 조건에 맞는 문장 형태를, 수학은 식이 바뀌는 이유를 직접 써 봅니다. 정답 여부와 설명 과정의 빈틈을 따로 확인합니다.'),
  ('평가 뒤 복습 기준','틀린 문항을 다시 풀 날짜와 혼자 해결했는지 확인할 방법을 정합니다. 다음 시험 범위가 안내되면 복습할 단원과 새로 배울 단원의 순서를 조정하세요.')]),
 '고등학생학원':('고등 학습 비교','이수 과목과 시험 준비','현재 이수 과목, 학교 자료와 최근 시험지',[
  ('학년과 이수 과목 확인','고등학생 수강 가능 여부는 과목과 학년에 따라 다릅니다. 현재 이수 과목과 선택한 학습 목표를 전달하고 그 범위를 상담에서 다룰 수 있는지 확인하세요.'),
  ('학교 자료와 목표 분리','학교 시험 범위와 별도 평가 자료의 목적을 구분합니다. 영어 구문·독해 근거와 수학 개념·조건 해석 중 실제 답안에서 막힌 부분부터 살펴보세요.'),
  ('시간을 쓴 구간 기록','읽기, 풀이, 답안 작성과 검토에 걸린 시간을 나눠 적습니다. 지식 공백과 시간 배분 문제를 구분하고 다음 공부에서 확인할 한 가지를 정하세요.')])
}
GUIDE_CHECKS={
 '초등-영어':('아이의 읽기와 표현을 기준으로 수업을 비교해 보세요.',[
  ('낱말 읽기와 뜻 이해를 어떻게 나누어 보나요?','소리를 읽는 데 도움이 필요한 낱말과 읽어도 뜻을 설명하지 못하는 낱말을 각각 보여 주세요. 상담에서는 두 어려움을 구분해 연습할 내용을 정하는지 확인합니다.'),
  ('따라 쓰기 다음에 무엇을 확인하나요?','예문을 베껴 쓴 자료와 아이가 혼자 바꿔 쓴 문장을 함께 준비하세요. 외운 표현을 새 상황에 사용하는 과정과 틀린 표현을 다시 확인하는 방법을 물어봅니다.'),
  ('복습 분량을 정하는 기준은 무엇인가요?','아이의 집중 시간과 도움 없이 완성한 부분을 전달하세요. 낱말 수만 늘리기 전에 다시 사용할 표현, 확인할 날짜, 보호자가 확인할 기록을 정할 수 있는지 비교합니다.')]),
 '초등-수학':('계산 정확성과 문제 이해를 따로 살피는 기준으로 수업을 비교해 보세요.',[
  ('계산 실수와 문제 이해를 어떻게 구분하나요?','연산장과 문장제 풀이를 함께 보여 주세요. 계산 방법을 몰랐는지, 무엇을 구하는지 읽지 못했는지, 수와 단위를 옮기는 과정에서 실수했는지 답변을 받아 적습니다.'),
  ('정답 외에 어떤 설명을 확인하나요?','아이의 그림·식·말 설명 가운데 서로 연결되지 않는 부분을 질문하세요. 상담에서는 아이가 혼자 설명하는 과정을 볼 수 있는지, 어떤 도움부터 줄지 확인합니다.'),
  ('다음 단원으로 넘어갈 기준은 무엇인가요?','조건이나 수가 달라진 문제를 혼자 풀어 본 자료를 준비하세요. 풀이를 기억한 것과 계산 방법을 선택한 것을 구분하고 복습할 부분을 정하는지 살펴봅니다.')]),
 '중등-영어':('학교 진도와 어휘·문장·답안의 공백을 연결하는 기준으로 수업을 비교해 보세요.',[
  ('본문을 외운 것과 이해한 것을 어떻게 확인하나요?','학교 본문과 표현이 조금 바뀐 문제에서 학생이 설명한 내용을 준비하세요. 어휘, 수식 관계, 글의 흐름 중 놓친 부분을 구분해 말해 주는지 확인합니다.'),
  ('문법과 서술형을 어떤 자료로 점검하나요?','학생이 직접 쓴 답안을 보여 주고 어순·동사 형태·주어진 조건을 따로 확인하는지 질문하세요. 규칙 이름을 아는 것과 조건에 맞게 쓰는 것을 구분해 답변을 남깁니다.'),
  ('학교 평가 범위가 나오면 계획을 어떻게 바꾸나요?','학교에서 안내한 진도와 평가 자료를 전달하세요. 지금 보완할 내용과 평가 전 다시 확인할 표현, 학생이 직접 찾을 답의 근거를 구체적으로 정하는지 비교합니다.')]),
 '중등-수학':('학교 단원과 풀이 과정에서 확인할 공백을 기준으로 수업을 비교해 보세요.',[
  ('풀이를 시작하지 못한 이유를 어떻게 찾나요?','조건을 표시한 문제와 처음 세운 식을 보여 주세요. 개념 선택, 조건 해석, 계산 중 어느 단계에서 도움이 필요한지 설명을 받아 적습니다.'),
  ('서술형 풀이에서 무엇을 확인하나요?','식이 바뀌는 이유를 학생이 직접 적은 답안을 준비하세요. 정답과 별도로 부호·단위·조건, 단계 사이 설명을 확인하는지 질문합니다.'),
  ('오답 이후의 확인 기준은 무엇인가요?','숫자나 조건이 바뀐 문제에서 다시 멈춘 부분을 전달하세요. 다음 단원 전에 보완할 개념, 혼자 다시 풀어 볼 과제와 재확인 시점을 정하는지 비교합니다.')]),
 '고등-영어':('이수 과목과 시험 목표에 맞는 읽기·판단·표현 기준으로 수업을 비교해 보세요.',[
  ('학교 시험 자료와 다른 평가 자료를 어떻게 구분하나요?','교과서·부교재의 현재 범위와 별도 평가 자료를 각각 보여 주세요. 목표에 따라 먼저 보완할 어휘·구문·독해 부분이 어떻게 달라지는지 질문합니다.'),
  ('틀린 선택지의 원인을 어떤 근거로 확인하나요?','학생이 고른 이유와 본문에서 표시한 근거를 함께 준비하세요. 모르는 어휘, 문장 관계, 논리 연결 가운데 놓친 부분을 구체적으로 설명하는지 살펴봅니다.'),
  ('시간 부족과 표현 오류를 어떻게 나누어 보나요?','읽기·판단·작성에 쓴 시간과 직접 쓴 답안을 전달하세요. 제한된 시간 안의 판단과 철자·동사 형태·어순의 수정이 각각 계획에 반영되는지 비교합니다.')]),
 '고등-수학':('현재 이수 과목과 풀이의 공백을 기준으로 수업 상담의 답변을 비교해 보세요.',[
  ('이수 과목과 이번 학습 목표를 어떻게 구분하나요?','현재 배우는 과목과 학교 시험 범위를 먼저 전달하세요. 앞 단원 개념의 보완과 새 단원 학습 중 무엇이 우선인지, 그 판단에 사용한 학생 풀이를 질문합니다.'),
  ('풀이 선택의 이유를 어떻게 확인하나요?','공식과 첫 식을 적은 답안, 문제 조건에 표시한 자료를 보여 주세요. 적용 조건을 놓친 것과 개념을 떠올리지 못한 것을 구분해 설명하는지 비교합니다.'),
  ('시간 배분과 지식 공백을 어떤 기준으로 나누나요?','시간을 정해 푼 답안과 제한 없이 다시 푼 답안을 함께 전달하세요. 멈춘 단계, 검토에 남긴 시간, 다음 확인 단원을 구체적으로 정할 수 있는지 살펴봅니다.')])
}

def pretty(values):
 parts=[]
 for prefix in ['초','중','고']:
  nums=sorted({int(v[1:]) for v in values if re.fullmatch(prefix+r'\d',v)})
  if not nums:continue
  if nums==list(range(nums[0],nums[-1]+1)) and len(nums)>1:parts.append(f'{prefix}{nums[0]}–{prefix}{nums[-1]}')
  else:parts.append('·'.join(prefix+str(n) for n in nums))
 return ' · '.join(parts) or '개설 학년 확인 필요'

AREA_ROWS={}
for r in SUBJECTS:
 if r['subject']=='수학':
  key=norm(r['neighborhood']);assert key not in AREA_ROWS,key;AREA_ROWS[key]={**r,'region':r['path'].strip('/').split('/')[1]}
assert len(AREA_ROWS)==371

def center_path(c):return f'/지점안내/{c["region"]}/{c["routeName"]}/'
def branch_path(r,subject=None,stage=None):
 p=center_path(CENTERS[r['region'],r['center']])+norm(r['neighborhood'])+(subject or r['subject'])+'학원/'
 return p+(stage+'/' if stage else '')

def inventory():
 urls=etree.parse(str(ROOT/'sitemap.xml')).xpath('//*[local-name()="loc"]/text()')
 rows=[]
 for url in urls:
  path=unquote(urlsplit(url).path);parts=path.strip('/').split('/')
  if path in SUB_BY_PATH:
   r=dict(SUB_BY_PATH[path]);r.update(role='enrollment',family='branch-subject',region=parts[1])
  elif path in GRADE_BY_PATH:
   r=dict(GRADE_BY_PATH[path]);r.update(role='enrollment',family='branch-grade')
  elif parts[0]=='전국센터' and len(parts) in [2,3] and norm(parts[1]) in AREA_ROWS:
   r=dict(AREA_ROWS[norm(parts[1])]);r.update(path=path,role='overview' if len(parts)==2 else 'study-guide',family='national-general' if len(parts)==2 else 'national-grade')
   if len(parts)==3:
    match=re.fullmatch('(초등|중등|고등)(영어|수학)학원',parts[2]);assert match,path
    r.update(stage=match[1],subject=match[2])
   else:r.pop('subject',None)
  elif parts[0]=='과목별학원' and len(parts)==3 and parts[1] in CATEGORIES:
   r=dict(AREA_ROWS[norm(parts[2])]);r.update(path=path,role='comparison-guide',family='category',category=parts[1])
   cat=parts[1];r.pop('subject',None)
   if cat in ['수학전문학원','영어전문학원']:r['subject']=cat[:2]
   if cat in ['초등학생학원','중학생학원','고등학생학원']:r['stage']={'초등학생학원':'초등','중학생학원':'중등','고등학생학원':'고등'}[cat]
  else:continue
  r['canonical']=url;r['centerKey']=[r['region'],r['center']]
  c=CENTERS[tuple(r['centerKey'])]
  r['address']=c['address'];r['branchPath']=center_path(c)
  if r.get('subject'):r['enrollmentPath']=branch_path(r,r['subject'],r.get('stage'))
  else:r['enrollmentPath']=center_path(c)
  rows.append(r)
 assert len(rows)==8162,Counter(r['family'] for r in rows)
 assert len({r['path'] for r in rows})==8162
 return rows

def subjects_for(r):
 if r.get('subject'):return [r['subject']]
 return ['영어','수학'] if r.get('category')=='영수전문학원' or r.get('stage') else ['국어','영어','수학','과학','사회']
def grades_for(r,c,subject):
 return [v for v in c['subjects'].get(subject,[]) if not r.get('stage') or v.startswith(r['stage'][0])]
def availability(r,c):return ' / '.join(f'{s} {pretty(grades_for(r,c,s))}' for s in subjects_for(r))
def conflict_note(r,c):
 if c.get('gradeAuthority')=='workbook':return ''
 notes=[]
 for v in CONFLICTS:
  if v['center']!=c['routeName'] or v['region']!=c['region'] or v['subject'] not in subjects_for(r):continue
  a=[g for g in v['csv'] if not r.get('stage') or g.startswith(r['stage'][0])]
  b=[g for g in v['workbook'] if not r.get('stage') or g.startswith(r['stage'][0])]
  if a!=b:notes.append(f'{v["subject"]} 학년 자료가 서로 다릅니다. 센터 안내 CSV: {pretty(a)}, 엑셀: {pretty(b)}. 해당 학년의 현재 개설 여부는 상담으로 확인해 주세요.')
 return ' '.join(notes)
def node(markup):return html.fromstring(markup)
def section(ident,title,body):return node(f'<section id="{ident}" class="cl-section ns-section"><div class="wrap cl-reading"><h2>{E(title)}</h2>{body}</div></section>')
def anchor(path,label):return f'<a class="ns-link" href="{E(U(path))}">{E(label)}</a>'
def paragraph(s):return '<p>'+E(s)+'</p>'
def byid(doc,ident):
 found=doc.xpath('//*[@id=$id]',id=ident);return found[0] if found else None
def replace_section(doc,ident,title,body):
 old=byid(doc,ident)
 if old is None:return
 new=section(ident,title,body)
 for legacy in old.xpath('.//*[@id]/@id'):
  if legacy!=ident and not new.xpath('.//*[@id=$i]',i=legacy):new.append(node(f'<span id="{E(legacy)}" class="cl-legacy-anchor"></span>'))
 old.getparent().replace(old,new)

def quick_facts(r,c):
 branch=r['role']=='enrollment';grades=availability(r,c)
 # Korean labels remain literal and visible, with separate location/coverage facts.
 cells=[('안내 지점',c['displayName']),('실제 주소',c['address']),('센터 자료의 안내 학년',grades)]
 body='<dl class="ns-facts">'+''.join(f'<div><dt>{E(k)}</dt><dd>{E(v)}</dd></div>' for k,v in cells)+'</dl>'
 body+=paragraph(f'{r["neighborhood"]}은 상담 대상 생활권입니다. 실제 수업 장소는 위 주소를 기준으로 확인해 주세요.')
 body+='<div class="ns-actions">'
 if branch:
  body+=anchor('#fees','교육비·수업 구성 확인')+anchor(center_path(c),'지점 전체 정보')
  if r.get('stage'):guide=f'/전국센터/{norm(r["neighborhood"])}/{r["stage"]}{r["subject"]}학원/'
  else:guide=f'/과목별학원/{r["subject"]}전문학원/{norm(r["neighborhood"])}/'
  body+=anchor(guide,'학습 상태·선택 기준 살펴보기')
 else:body+=anchor(r['enrollmentPath'],'수강 학년·주소·교육비 자세히 확인')
 body+='</div>'+paragraph('안내된 학년과 현재 모집 여부는 다를 수 있습니다. 희망 요일·시간과 학생의 현재 진도를 함께 확인해 주세요.')
 if conflict_note(r,c):body+='<div class="ns-source-note">'+paragraph(conflict_note(r,c))+'</div>'
 return section('local-summary','수강·위치 먼저 확인' if branch else '학습 안내에 참고할 지점',body)

def school_context(r,c):
 schools=next((v['schools'] for v in c['schoolAreas'] if norm(v['neighborhood'])==norm(r['neighborhood'])),{})
 kinds=[{'초등':'초등학교','중등':'중학교','고등':'고등학교'}[r['stage']]] if r.get('stage') else list(schools)
 names=list(dict.fromkeys(s for k in kinds for s in schools.get(k,[])))
 if names:
  return f'{r["neighborhood"]} 상담 참고 학교로는 '+', '.join(names[:5])+(' 등이' if len(names)>5 else '가')+' 안내돼 있습니다. 학교 이름만으로 반 편성이나 시험 범위를 판단하지 말고 재학 학교의 현재 자료를 준비하세요.'
 return '학교별 교재와 평가 범위는 상담에서 확인해 주세요. 재학 학교의 진도표와 학생이 직접 푼 자료가 비교의 출발점입니다.'

def study_content(r,c):
 p=PROFILES[r['stage']+'-'+r['subject']]
 intro,checks=GUIDE_CHECKS[r['stage']+'-'+r['subject']]
 body=paragraph(intro)+paragraph(f'{r["neighborhood"]}에서 수업을 비교하기 전에 {p["materials"]}을 모아 보세요. 상담에 참고할 {c["routeName"]}의 안내 학년은 {availability(r,c)}입니다.')
 body+='<div class="ns-check-grid">'+''.join(f'<article><h3>{E(h)}</h3>{paragraph(t)}</article>' for h,t in checks)+'</div>'
 body+=paragraph(school_context(r,c))
 body+='<h3>상담에서 답변을 받아 적을 항목</h3><ul>'+''.join('<li>'+E(t)+'</li>' for t in [f'지금 배우는 {r["subject"]} 진도에서 먼저 보완할 부분과 그 이유',f'{c["routeName"]}에서 희망 학년·과목과 요일·시간을 안내할 수 있는지','수업 뒤 혼자 다시 해 볼 과제와 확인 시점','수업 횟수·시간·포함 과목에 따른 최종 교습비'])+'</ul>'
 body+=paragraph('위 내용은 학습 점검과 수업 비교를 위한 제안입니다. 지점의 실제 수업 방식이나 성적 향상 사례를 뜻하지 않습니다.')
 return body

def category_content(r,c):
 title,focus,materials,checks=CATEGORIES[r['category']]
 body=paragraph(f'{r["neighborhood"]}에서 {r["category"]}을 알아볼 때는 {focus}부터 살펴보세요. {materials}을 준비하면 학생의 설명과 실제 학습 흔적을 함께 비교할 수 있습니다.')
 body+='<div class="ns-check-grid">'+''.join(f'<article><h3>{E(h)}</h3>{paragraph(t)}</article>' for h,t in checks)+'</div>'
 body+='<h3>생활권과 실제 수업 조건 함께 보기</h3>'+paragraph(f'{r["neighborhood"]} 상담에 참고할 지점은 {c["displayName"]}입니다. 실제 주소는 {c["address"]}이며, 안내 학년은 {availability(r,c)}입니다.')
 body+=paragraph(school_context(r,c))
 body+=paragraph('학생의 학교 일정과 실제 이동 시간을 기준으로 희망 수업 시간을 전달하세요. 학교와의 제휴·전용반이나 모든 학년의 수강 가능 여부는 이 안내만으로 판단할 수 없습니다.')
 return body

def faq_content(r,c):
 focus=CATEGORIES[r['category']][1] if r.get('category') else PROFILES[r['stage']+'-'+r['subject']]['focus']
 pairs=[('이 페이지에서 어떤 내용을 확인할 수 있나요?',f'{r["neighborhood"]}에서 수업을 비교할 때 살펴볼 {focus}과 상담 준비 기준을 안내합니다. 실제 수강 조건은 {c["routeName"]}의 지점 안내에서 함께 확인해 주세요.'),
 ('상담 대상 동네와 학원 주소는 같은 뜻인가요?',f'{r["neighborhood"]}은 상담 대상 생활권이며 실제 학원 주소는 {c["address"]}입니다. 학생의 출발 위치에서 이동 시간과 수업 시작 시각을 확인해 주세요.'),
 ('자료에 없는 학년도 바로 수강할 수 있나요?',f'안내 학년은 {availability(r,c)}입니다. 안내되지 않은 학년·과목의 개설 여부와 현재 모집 가능한 자리는 별도 확인이 필요합니다.'),
 ('교육비는 어떤 기준으로 비교하나요?','같은 월 금액이라도 수업 횟수와 시간, 포함 과목이 다를 수 있습니다. 지역 공통 참고 금액과 지점의 확정 교습비를 구분하고 교습비 자료와 상담을 통해 최종 조건을 확인해 주세요.')]
 return ''.join(f'<details><summary>{E(q)}</summary>{paragraph(a)}</details>' for q,a in pairs)

def refresh_faq_schema(doc,data):
 faqs=[]
 for d in doc.xpath('//main//details[summary]'):
  q=d.findtext('summary');answer=' '.join(d.xpath('./p//text()'))
  if q and answer:faqs.append({'@type':'Question','name':q,'acceptedAnswer':{'@type':'Answer','text':answer}})
 for n in data.get('@graph',[]):
  if n.get('@type')=='FAQPage' and faqs:n['mainEntity']=faqs

def descriptions(r,c):
 label=r['neighborhood']+' '+(r.get('stage','')+' ' if r.get('stage') else '')+(r['subject']+'학원' if r.get('subject') else '학원')
 if r['role']=='enrollment':
  title=f'{label} | {c["routeName"]} 수강 학년·위치'
  desc=f'{label} 안내에서 {c["routeName"]}의 수강 학년과 실제 주소, 교습비 확인 경로를 살펴보세요.'
 elif r['role']=='study-guide':
  title=f'{label} | 진도·오답 점검 가이드'
  desc=f'{label} 선택 전 진도·오답 점검 방법과 {c["routeName"]}의 안내 학년을 확인하세요.'
 elif r['role']=='comparison-guide':
  topic=CATEGORIES[r['category']][0];title=f'{r["neighborhood"]} {r["category"]} | {topic} 안내'
  desc=f'{r["neighborhood"]} {r["category"]} 선택 기준과 {c["routeName"]}의 안내 학년·위치 확인 방법을 살펴보세요.'
 else:
  title=f'{r["neighborhood"]} 학원 | {c["routeName"]} 과목·학년·위치'
  desc=f'{r["neighborhood"]} 학원 안내에서 {c["routeName"]}의 과목별 학년과 주소, 학습·수강 안내를 확인하세요.'
 assert len(desc)<=80,(r['path'],len(desc),desc)
 return title,desc

def responsive_assets():
 paths={ROOT/'assets/content-layout/body'/p.name for p in (ROOT/'assets/content-layout/body').glob('*.jpg')}
 out={}
 for p in paths:
  im=Image.open(p);w,h=im.size;variants=[]
  for size in [480,min(768,w),w]:
   if any(v['width']==size for v in variants):continue
   dest=p.with_name(p.stem+f'-{size}.webp')
   if not dest.exists():
    image=im if w==size else im.resize((size,round(h*size/w)),Image.Resampling.LANCZOS)
    image.save(dest,'WEBP',quality=83,method=6)
   variants.append({'src':'/'+dest.relative_to(ROOT).as_posix(),'width':size,'bytes':dest.stat().st_size})
  out['/'+p.relative_to(ROOT).as_posix()]={'width':w,'height':h,'bytes':p.stat().st_size,'variants':variants}
 return out

def protect(doc):
 return {'canonical':doc.xpath('//link[@rel="canonical"]/@href'),
 'h1':doc.xpath('//h1/text()'),
 'index':doc.xpath('//meta[translate(@name,"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz")="robots"]/@content'),
 'media':[(i.get('data-role'),i.get('src')) for i in doc.xpath('//main//img[@data-role]')],
 'contacts':sorted(set(doc.xpath('//a[starts-with(@href,"tel:") or contains(@href,"forms/d/") or contains(@href,"blogsms.net")]/@href')))}

def transform(r,media,config):
 path=ROOT/r['path'].strip('/')/'index.html';before=path.read_text('utf-8')
 doc=html.document_fromstring(before);guard=protect(doc);c=CENTERS[tuple(r['centerKey'])]
 if doc.xpath('//body/@data-neighborhood-seo')==[VERSION]:
  # Recover description config after an interrupted partial run as well.
  entry=config['pages'][r['path'].rstrip('/')];current=doc.xpath('//meta[@name="description"]/@content')[0]
  entry['description']=current;entry['sources']=list(dict.fromkeys(entry.get('sources',[])+[current]))
  return False,0
 assert guard['canonical']==[r['canonical']],r['path']
 main=doc.xpath('//main')[0];head=doc.xpath('//head')[0]
 doc.xpath('//body')[0].set('data-neighborhood-seo',VERSION)
 title,desc=descriptions(r,c);old_desc=doc.xpath('//meta[@name="description"]/@content')[0]
 head.find('title').text=title
 for el in head.xpath('.//meta[@name="description" or @property="og:description" or @name="twitter:description"]'):el.set('content',desc)
 for el in head.xpath('.//meta[@property="og:title" or @name="twitter:title"]'):el.set('content',title)
 head.append(node('<link rel="stylesheet" href="/assets/neighborhood-seo/local.css">'))
 entry=config['pages'][r['path'].rstrip('/')];entry['sources']=list(dict.fromkeys(entry.get('sources',[])+[old_desc,desc]));entry['description']=desc
 for el in doc.xpath('//main/*[contains(@class,"cl-toc")]'):el.getparent().remove(el)
 for el in doc.xpath('//main//*[@aria-label="핵심 키워드"]'):el.getparent().remove(el)
 hero=main[0];lead=hero.xpath('.//p[contains(@class,"bc-lead")]') or hero.xpath('.//h1/following-sibling::p[1]')
 if lead:
  lead[0].text=(f'{c["displayName"]} · {c["address"]}' if r['role']=='enrollment' else f'{r["neighborhood"]}에서 수업을 비교할 때 준비할 자료와 학습 점검 기준을 정리했습니다. 실제 수강 조건은 {c["routeName"]} 안내로 이어서 확인할 수 있습니다.')
  for child in list(lead[0]):lead[0].remove(child)
 # Branch calls to action answer enrollment intent first.
 if r['role']=='enrollment':
  quick_answer=hero.xpath('.//div[contains(@class,"bc-quick-answer")]/p')
  if quick_answer:
   quick_answer[0].text='자료에 안내된 학년: '+availability(r,c)+'. 현재 모집 여부와 희망 수업 시간은 상담으로 확인해 주세요.'
   for child in list(quick_answer[0]):quick_answer[0].remove(child)
  actions=hero.xpath('.//div[contains(@class,"bc-actions")]/a')
  if actions:actions[0].set('href','#local-summary');actions[0].text='수강·위치 먼저 확인'
  if len(actions)>1:actions[1].set('href','#fees');actions[1].text='교육비 확인'
 quick=quick_facts(r,c);main.insert(1,quick)
 main.insert(2,node('<nav class="cl-toc wrap ns-toc" aria-label="핵심 안내 목차">'+anchor('#local-summary','학년·위치')+anchor('#intent-guide' if r['role'] in ['study-guide','comparison-guide'] else '#fees','학습·비교 기준' if r['role'] in ['study-guide','comparison-guide'] else '교육비')+anchor('#page-images','본문·지도')+anchor('#related-intents','다른 안내')+'</nav>'))
 repaired=0
 if r['role']=='enrollment':
  # Real enrollment details precede tall editorial imagery, preserving image order.
  ix=3
  for ident in ['center-info','center-grades','grades','fees','center-schools','schools','child-pages']:
   el=byid(doc,ident)
   if el is not None and el.getparent() is main:main.remove(el);main.insert(ix,el);ix+=1
  for p in doc.xpath('//main//p'):
   text=p.text_content()
   if re.search(r'세\s*가지|3\s*가지',text) and re.search(r'질문|기준|단계',text) and not ('둘째' in text and '셋째' in text):
    p.text='상담에서는 현재 진도에서 막힌 부분, 혼자 다시 풀어 볼 과제, 다음 확인 시점을 각각 질문해 보세요. 학생이 직접 남긴 답안과 풀이 기록을 함께 보여 주면 도움이 필요한 부분을 구체적으로 설명할 수 있습니다.'
    for child in list(p):p.remove(child)
    repaired+=1
 elif r['role'] in ['study-guide','comparison-guide']:
  body=study_content(r,c) if r['role']=='study-guide' else category_content(r,c)
  guide_title=PROFILES[r['stage']+'-'+r['subject']]['focus'] if r['role']=='study-guide' else CATEGORIES[r['category']][0]+'에서 확인할 내용'
  guide=section('intent-guide',guide_title,body);main.insert(3,guide)
  # Keep old section anchors and existing inbound URLs useful while reducing
  # duplicated full enrollment tables on learning/comparison pages.
  for ident in ['center-info','center-grades','fees']:
   replace_section(doc,ident,{'center-info':'실제 수업 장소 확인','center-grades':'과목별 안내 학년 확인','fees':'교습비 확인 경로'}[ident],paragraph({'center-info':f'{c["displayName"]}의 실제 주소는 {c["address"]}입니다.','center-grades':'자료에 안내된 학년: '+availability(r,c)+'. 미확인 학년과 현재 모집 여부는 상담으로 확인해 주세요.','fees':'월 금액과 함께 수업 횟수·시간·포함 과목을 확인하세요. 지점 안내에서 공통 참고 금액과 센터 교습비 자료를 구분해 볼 수 있습니다.'}[ident])+anchor(r['enrollmentPath']+('#fees' if ident=='fees' else ''),'지점 수강 안내에서 자세히 확인'))
  if r['role']=='study-guide':
   replace_section(doc,'learning-plan','준비한 자료로 수업을 비교하는 방법',paragraph(f'{PROFILES[r["stage"]+"-"+r["subject"]]["materials"]}을 기준으로 지금 혼자 할 수 있는 부분과 도움을 받는 부분을 나눠 적어 보세요.')+paragraph(f'{c["routeName"]}에 상담할 때는 {r["neighborhood"]}에서 이동하는 시간, 희망 요일과 학생의 현재 진도를 함께 전달하세요.'))
   replace_section(doc,'learning-steps','학습 뒤 남길 기록',paragraph(PROFILES[r['stage']+'-'+r['subject']]['record'])+paragraph('정답을 기억한 것인지 확인하려면 시간이 지난 뒤 조건이 바뀐 문제나 문장을 다시 살펴보세요. 다음 학습에서 확인할 내용 한 가지를 적습니다.'))
   replace_section(doc,'faq-section','학습 안내와 수강 조건에 관한 질문',faq_content(r,c))
  else:
   # Replace generated anecdotes with explicitly practical, prospective questions.
   replace_section(doc,'reading-2','상담을 준비할 자료',paragraph(CATEGORIES[r['category']][2]) +paragraph('학생이 직접 푼 답안과 설명한 내용을 함께 준비하고, 상담에서 먼저 확인하고 싶은 어려움 한 가지를 적어 주세요.'))
   replace_section(doc,'reading-7','첫 상담에서 비교할 질문',paragraph('현재 자료에서 확인한 어려움을 어떤 순서로 다룰지, 과제 뒤 무엇을 다시 확인할지 질문해 보세요. 수업의 명칭과 별도로 학생이 혼자 해 보는 과정과 피드백의 시점을 살펴봅니다.'))
   replace_section(doc,'reading-9','상담 뒤 계획을 확인하는 방법',paragraph('상담에서 들은 내용을 현재 진도, 복습할 부분, 확인할 날짜로 나누어 적어 보세요. 다음 확인 때에는 과제를 끝낸 양과 혼자 해결한 내용을 각각 비교합니다.')+paragraph('이 안내는 상담을 준비하는 방법이며, 실제 학생의 후기나 수강 결과가 아닙니다.'))
   replace_section(doc,'faq-section','학습 비교와 지점 안내에 관한 질문',faq_content(r,c))
 elif r['role']=='overview':
  ix=3
  for ident in ['center-info','center-grades','fees','center-schools']:
   el=byid(doc,ident)
   if el is not None and el.getparent() is main:main.remove(el);main.insert(ix,el);ix+=1
 # The same existing photographs can be common brand examples, not branch proof.
 if c['photoMode']=='common':
  space=byid(doc,'learning-space')
  if space is not None:
   wrap=space.xpath('./div')[0];wrap.insert(2,node(paragraph('아래 사진은 브랜드 공통 학습 공간 예시입니다. 이 지점의 실제 시설과 동일하다는 의미는 아니므로 방문 전 확인해 주세요.')))
   for i,img in enumerate(space.xpath('.//img'),1):img.set('alt',f'브랜드 공통 학습 공간 예시 {i}')
 for img in doc.xpath('//img[@data-role="body-image"]'):
  m=media[img.get('src')];picture=node('<picture><source type="image/webp"></picture>')
  picture[0].set('srcset',', '.join(v['src']+' '+str(v['width'])+'w' for v in m['variants']))
  picture[0].set('sizes','(max-width: 760px) calc(100vw - 40px), 720px')
  parent=img.getparent();parent.replace(img,picture);picture.append(img)
 if conflict_note(r,c):
  for ident in ['grades','center-grades']:
   block=byid(doc,ident)
   if block is not None and block.xpath('./div'):block.xpath('./div')[0].append(node(paragraph(conflict_note(r,c))))
 # Meaningful cross-links pair parallel intents and expose every grade directly.
 links=[];n=norm(r['neighborhood'])
 if r.get('subject'):
  for stage in ['초등','중등','고등']:
   links.extend([(branch_path(r,r['subject'],stage),stage+' '+r['subject']+' 수강·위치 안내'),(f'/전국센터/{n}/{stage}{r["subject"]}학원/',stage+' '+r['subject']+' 학습 점검')])
  links.append((f'/과목별학원/{r["subject"]}전문학원/{n}/',r['subject']+' 학습 비교 기준'))
 else:
  for subject in ['영어','수학']:
   links.append((branch_path(r,subject),subject+' 수강·위치 안내'))
   for stage in ['초등','중등','고등']:
    if not r.get('stage') or stage==r['stage']:links.append((branch_path(r,subject,stage),stage+' '+subject+' 수강 안내'))
  links.extend((f'/과목별학원/{cat}/{n}/',CATEGORIES[cat][0]+' 안내') for cat in CATEGORIES if cat!=r.get('category'))
 links.append((f'/전국센터/{n}/',r['neighborhood']+' 전체 학원 안내'))
 links=[(p,l) for p,l in links if p!=r['path']]
 for p,l in links:assert (ROOT/p.strip('/')/'index.html').is_file(),(r['path'],p)
 related=section('related-intents','목적에 맞는 안내 이어보기','<div class="ns-link-grid">'+''.join(anchor(p,l) for p,l in links)+'</div>')
 main.insert(4 if r['role'] in ['study-guide','comparison-guide'] else len(main)-1,related)
 for note in doc.xpath('//p[contains(@class,"cl-media-note")]'):
  note.text='본문 이미지의 교육비는 지역별 참고 안내입니다. 이 페이지의 수강·위치 안내와 지점 교습비 자료에서 실제 조건을 함께 확인해 주세요.'
 for p in doc.xpath('//main/p[contains(@class,"cl-revised") or contains(@class,"bc-updated")]'):
  p.text='내용 수정·센터 자료 대조 2026.09.30 · 현재 모집 여부와 최종 수업 구성은 지점에 확인해 주세요.'
  for child in list(p):p.remove(child)
 for script in doc.xpath('//script[@type="application/ld+json"]'):
  data=json.loads(script.text)
  graph=data.get('@graph',[])
  if r['role'] in ['study-guide','comparison-guide'] or (r.get('subject') and not grades_for(r,c,r['subject'])):
   graph[:]=[v for v in graph if v.get('@type')!='Service']
  article_id=next((v.get('@id') for v in graph if v.get('@type')=='Article'),None)
  for v in graph:
   if v.get('@type')=='Service' and conflict_note(r,c):v['description']='과목별 학년 자료에 차이가 있어 현재 개설 학년과 수강 조건은 지점에 확인해야 합니다.'
   if v.get('@type') in ['WebPage','CollectionPage','Article']:
    v['description']=desc;v['dateModified']=DAY
    if v.get('@type')=='Article':
     v['headline']=title
     if 'abstract' in v:v['abstract']=('수강·위치 안내. ' if r['role']=='enrollment' else '학습·비교 안내. ')+availability(r,c)+'. 실제 주소: '+c['address']
     if r['role'] in ['study-guide','comparison-guide']:v['articleSection']='학습 점검과 수업 비교 안내'
    if v.get('@type')=='WebPage' and article_id and r['role'] in ['study-guide','comparison-guide']:v['mainEntity']={'@id':article_id}
  refresh_faq_schema(doc,data)
  script.text=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
 assert protect(doc)==guard,(r['path'],'protected route/media/contact changed')
 out=html.tostring(doc,encoding='unicode',method='html',doctype='<!DOCTYPE html>')+'\n'
 write_page(path,out)
 return True,repaired

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--sample',action='store_true');parser.add_argument('--all',action='store_true');parser.add_argument('--refine-guides',action='store_true');parser.add_argument('--refresh-manifest',action='store_true');args=parser.parse_args()
 REPORT.mkdir(parents=True,exist_ok=True);rows=inventory();dump(DATA/'page-roles.json',rows)
 if args.refine_guides:
  changed=0
  for r in rows:
   if r['role']!='study-guide':continue
   path=ROOT/r['path'].strip('/')/'index.html';before=path.read_text('utf-8');doc=html.document_fromstring(before);guard=protect(doc)
   assert doc.xpath('//body/@data-neighborhood-seo')==[VERSION],r['path']
   c=CENTERS[tuple(r['centerKey'])]
   replace_section(doc,'intent-guide',r['stage']+' '+r['subject']+' 수업을 비교할 때 받아 적을 답변',study_content(r,c))
   assert protect(doc)==guard
   after=html.tostring(doc,encoding='unicode',method='html',doctype='<!DOCTYPE html>')+'\n'
   if after!=before:write_page(path,after);changed+=1
  # Supporting hubs use the same photo provenance and responsive body images.
  media=load(DATA/'responsive-media.json');hub_paths=load(REPORT/'hubs.json')['paths']
  for rel in hub_paths:
   path=ROOT/rel.strip('/')/'index.html';before=path.read_text('utf-8');doc=html.document_fromstring(before);guard=protect(doc)
   parts=rel.strip('/').split('/');c=CENTERS.get((parts[1],parts[2])) if len(parts)==3 and parts[0]=='지점안내' else None
   if c and c['photoMode']=='common':
    space=byid(doc,'learning-space')
    if space is not None and '브랜드 공통 학습 공간 예시' not in space.text_content():
     space.xpath('./div')[0].insert(2,node(paragraph('아래 사진은 브랜드 공통 학습 공간 예시입니다. 이 지점의 실제 시설은 방문 전 확인해 주세요.')))
     for i,img in enumerate(space.xpath('.//img'),1):img.set('alt',f'브랜드 공통 학습 공간 예시 {i}')
   for img in doc.xpath('//img[@data-role="body-image"]'):
    if img.getparent().tag=='picture' or img.get('src') not in media:continue
    picture=node('<picture><source type="image/webp"></picture>')
    picture[0].set('srcset',', '.join(v['src']+' '+str(v['width'])+'w' for v in media[img.get('src')]['variants']))
    picture[0].set('sizes','(max-width: 760px) calc(100vw - 40px), 720px')
    img.getparent().replace(img,picture);picture.append(img)
   for script in doc.xpath('//script[@type="application/ld+json"]'):
    data=json.loads(script.text)
    for n in data.get('@graph',[]):
     if n.get('@type') in ['WebPage','CollectionPage']:n['dateModified']=DAY
    script.text=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
   assert protect(doc)==guard
   after=html.tostring(doc,encoding='unicode',method='html',doctype='<!DOCTYPE html>')+'\n'
   if after!=before:write_page(path,after)
  dump(REPORT/'guide-refinement.json',{'selectedPages':2226,'changedPages':changed,'direction':'diagnostic evidence and comparison questions','deployed':False});print('Refined study-guide bodies',changed);return
 if args.refresh_manifest:
  validation=load(REPORT/'validation.json');assert validation['errors']==[] and validation['improvedPages']==8162
  if any(c.get('gradeAuthority')=='workbook' for c in FACTS['centers']):assert validation.get('phase2Pages')==8162
  manifest=load(ROOT/'release-public-manifest.json')
  names=set(manifest['files'])|{'assets/neighborhood-seo/local.css'}|{p.relative_to(ROOT).as_posix() for p in (ROOT/'assets/content-layout/body').glob('*-*.webp')}
  manifest['files']={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in sorted(names)}
  manifest['textSha256']={n:hashlib.sha256((ROOT/n).read_text('utf-8').replace('\r\n','\n').encode()).hexdigest() for n in sorted(names) if re.search(r'\.(html|css|js|json|xml|txt|svg|webmanifest)$',n,re.I)}
  manifest['createdAt']=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat();dump(ROOT/'release-public-manifest.json',manifest);print('Refreshed reviewed public manifest',len(names));return
 media=responsive_assets();dump(DATA/'responsive-media.json',media)
 config=load(ROOT/'seo-descriptions.json');counts=Counter();repairs=0
 selected=rows
 if args.sample:selected=[r for r in rows if norm(r['neighborhood']) in ['명일동','불당동','구파발','풍덕천동']]
 assert args.all or args.sample,'Choose --sample or --all'
 try:
  for i,r in enumerate(selected,1):
   changed,fixed=transform(r,media,config);counts[r['family']]+=int(changed);repairs+=fixed
   if i%500==0:print('Processed',i,flush=True)
 finally:dump(ROOT/'seo-descriptions.json',config)
 report={'date':DAY,'scope':'sample' if args.sample else 'all','selectedPages':len(selected),'changed':dict(counts),'repairedIncompleteEnumerations':repairs,'roles':dict(Counter(r['role'] for r in rows)),'urlsDeleted':0,'deployed':False}
 dump(REPORT/('sample.json' if args.sample else 'implementation.json'),report);print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
