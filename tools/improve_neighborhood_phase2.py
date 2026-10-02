"""Differentiate page purposes and apply the user's confirmed workbook authority.

Transforms the reviewed first local release; never regenerates old manuscripts.
Existing routes, indexing, original images and contact destinations are protected.
"""
from pathlib import Path
from collections import Counter
import argparse,copy,hashlib,json,re
from lxml import html,etree
from openpyxl import load_workbook
import improve_neighborhood_pages as impl

VERSION='20260930-v2'
OUT=Path(r'C:\Users\1992k\Desktop\CodexData\outputs\site3-neighborhood-phase2-20260930')
SOURCE=Path(r'C:\Users\1992k\Desktop\홈페이지 작업 폴더\센터정보')

SCENARIOS={
 '초등-영어':[
  ('소리는 읽지만 뜻을 고르기 어려울 때','아이에게 익숙한 낱말과 짧은 문장을 따로 보여 주세요. 읽은 낱말을 그림이나 상황과 연결하는지 기록하고, 소리 읽기와 의미 이해 중 먼저 연습할 부분을 나눕니다.'),
  ('따라 쓴 문장은 맞지만 혼자 쓰기 어려울 때','예문과 아이가 혼자 쓴 문장을 나란히 둡니다. 낱말 선택, 철자, 어순 가운데 도움을 받은 위치를 표시해 다음 연습에서 한 부분씩 확인합니다.'),
  ('며칠 뒤 같은 표현을 떠올리기 어려울 때','처음 배운 날의 답안과 다시 사용한 날의 답안을 남깁니다. 외운 낱말 수보다 문장 안에서 다시 사용한 표현을 기준으로 복습할 내용을 정합니다.')],
 '초등-수학':[
  ('연산은 맞지만 문장제의 첫 식을 못 세울 때','문제에서 주어진 수와 구할 값을 다른 표시로 나눕니다. 그림으로 나타낸 뒤 식을 적어 보고, 문제를 읽는 어려움과 계산 방법의 어려움을 구분합니다.'),
  ('계산 중 자릿수나 단위를 놓칠 때','틀린 답 아래에 정답만 쓰지 말고 처음 달라진 줄에 표시합니다. 수를 옮긴 위치, 계산 순서, 답의 단위를 각각 확인해 다시 풀 문제를 고릅니다.'),
  ('설명을 들으면 풀지만 혼자 다시 시작하지 못할 때','도움을 받은 단계와 혼자 해결한 단계를 나누어 적습니다. 숫자가 달라진 문제를 다시 풀고 어떤 그림이나 식부터 만들었는지 설명해 봅니다.')],
 '중등-영어':[
  ('본문은 외웠지만 바뀐 문장에서 틀릴 때','학교 본문과 표현이 달라진 문제를 함께 둡니다. 어휘의 뜻, 수식 관계, 문장 사이 연결 중 무엇을 놓쳤는지 근거 문장에 표시합니다.'),
  ('문법 문제는 맞지만 서술형에서 틀릴 때','직접 쓴 문장에서 동사 형태, 어순, 주어진 조건을 각각 확인합니다. 규칙을 말하는 것과 그 규칙으로 문장을 완성하는 것을 별도로 점검합니다.'),
  ('평가 범위가 넓어지면 복습 순서를 못 정할 때','학교 진도표 옆에 헷갈린 표현과 틀린 문제를 적습니다. 이미 혼자 설명할 수 있는 부분과 다시 확인할 부분을 나누어 다음 복습의 범위를 정합니다.')],
 '중등-수학':[
  ('개념 이름은 알지만 문제의 첫 식이 막힐 때','문제 조건에 표시하고 사용할 개념을 적습니다. 정의를 모르는지, 조건과 개념을 연결하지 못했는지 구분한 뒤 첫 식의 이유를 말해 봅니다.'),
  ('정답은 맞지만 서술형 설명이 빠질 때','식이 바뀌는 줄마다 사용한 성질이나 조건을 적습니다. 부호와 단위뿐 아니라 앞 단계에서 다음 단계로 넘어가는 설명이 있는지 확인합니다.'),
  ('해설을 본 오답을 다음 단원에서 다시 틀릴 때','틀린 문제의 개념과 다음 단원에서 쓰인 개념을 연결해 적습니다. 조건이 달라진 문제를 혼자 풀어 보고 재확인할 개념과 날짜를 정합니다.')],
 '고등-영어':[
  ('학교 자료는 익숙하지만 처음 보는 글이 어려울 때','교과서·부교재와 별도 평가 지문을 구분합니다. 모르는 어휘, 길어진 수식 관계, 문단 연결 중 읽기를 멈춘 지점을 각각 남깁니다.'),
  ('선택지 두 개 사이에서 근거 없이 고를 때','고른 이유와 본문 근거를 함께 적습니다. 선택지의 표현이 본문의 어느 범위까지 설명하는지 비교하고, 판단을 바꾼 근거를 기록합니다.'),
  ('제한 시간이 있으면 읽기나 답안 작성이 흔들릴 때','읽기·판단·작성에 쓴 시간을 나눠 봅니다. 제한 없이 다시 푼 결과와 비교해 지식의 공백, 검토 시간, 표현 오류를 따로 정리합니다.')],
 '고등-수학':[
  ('앞 단원은 배웠지만 현재 과목의 조건 적용이 막힐 때','현재 이수 과목과 학교 진도를 적고 최근 오답의 조건을 표시합니다. 앞 단원의 개념이 필요한 부분과 새로운 조건을 해석해야 하는 부분을 구분합니다.'),
  ('풀이를 따라가지만 혼자 방법을 고르지 못할 때','공식의 적용 조건과 첫 식을 선택한 이유를 적습니다. 다른 풀이와 비교할 때 단계 수보다 조건의 누락과 검토할 부분을 먼저 확인합니다.'),
  ('시간을 정해 풀면 아는 문제도 끝내지 못할 때','시간을 정해 푼 답안과 제한 없이 다시 푼 답안을 함께 둡니다. 멈춘 단계, 계산과 검토에 쓴 시간을 나누어 개념 보완과 시간 배분을 따로 계획합니다.')]
}

def guard(doc):
 result=impl.protect(doc);result.pop('h1');return result

def heading(r):
 base=r['neighborhood']+' '+(r.get('stage','')+' ' if r.get('stage') else '')+(r['subject']+'학원' if r.get('subject') else '학원')
 if r['role']=='enrollment':return base+' 수강·위치 안내'
 if r['role']=='study-guide':return base+' 진도·오답 점검'
 if r['role']=='comparison-guide':return r['neighborhood']+' '+r['category']+' 선택 기준'
 return r['neighborhood']+' 학원 과목·학년 안내'

def authority(c):
 return '센터 데이터 엑셀' if c.get('gradeAuthority')=='workbook' else '센터 안내 CSV'

def prepare():
 assert (OUT/'phase1-before-phase2.zip').exists(),'Preserve the first local release before changing inputs'
 for entry in impl.FACTS['sources']:
  assert hashlib.sha256((SOURCE/entry['file']).read_bytes()).hexdigest()==entry['sha256'],entry['file']
 wb=load_workbook(SOURCE/'코칭센터_데이터_.xlsx',read_only=True,data_only=True)
 rows=list(wb.active.values);wb.close();by_name={str(v[0]).strip():(i,v) for i,v in enumerate(rows,1) if v[0]}
 changed=[];matched=0;missing=[]
 for c in impl.FACTS['centers']:
  if c['sourceName'] not in by_name:missing.append(c['routeName']);continue
  index,row=by_name[c['sourceName']];matched+=1
  for field,column in [('address',11),('registeredName',6),('registrationNumber',7)]:
   assert impl.norm(c[field])==impl.norm(str(row[column] or '')),(c['routeName'],field)
  c.setdefault('csvSubjects',copy.deepcopy(c['subjects']))
  latest={s:re.findall(r'[초중고][1-6]',str(row[col] or '')) for s,col in zip(['국어','영어','수학','과학','사회'],range(16,21))}
  for subject,values in latest.items():
   if c['csvSubjects'][subject]!=values:changed.append({'center':c['routeName'],'region':c['region'],'subject':subject,'before':c['csvSubjects'][subject],'after':values,'workbookRow':index})
  c['subjects']=latest;c['gradeAuthority']='workbook';c['gradeAuthorityRow']=index
 impl.dump(impl.DATA/'centers.json',impl.FACTS)
 result={'authority':'User confirmed center workbook as latest definitive grade source','matchedCenters':matched,'changedCenters':len({v['center'] for v in changed}),'changedFields':len(changed),'changes':changed,'unmatchedCenters':missing,'identityConflicts':[],'sourceFilesUnchanged':True}
 impl.dump(OUT/'workbook-authority.json',result);print(json.dumps({k:v for k,v in result.items() if k!='changes'},ensure_ascii=False))

def course_notes(r,c):
 notes=[]
 for raw in c.get('courseNotes',[]):
  for sentence in re.split(r'(?<=\.)\s+',raw):
   # Old CSV/table disagreements are resolved by the user's workbook decision.
   if c.get('gradeAuthority')=='workbook' and any(t in sentence for t in ['별도 안내가 달라','별도 안내와 차이','수강 학년 표와','별도 안내가 있어','표와 별도']):continue
   if '수강 가능 학년은' in sentence:continue
   notes.append(sentence)
 return notes

def restricted(r,c):
 notes=' '.join(course_notes(r,c))
 return ('수지점(W+)' in notes and r.get('subject') in ['수학','과학']) or (r.get('stage')=='고등' and '고3 수업 마감' in notes and impl.grades_for(r,c,r.get('subject',''))==['고3'])

def grade_body(r,c):
 body=impl.paragraph(f'수강 학년은 {authority(c)}에 기재된 범위를 기준으로 안내합니다. 실제 모집 가능한 자리와 시간표는 별도로 확인해 주세요.')
 body+='<div class="ns-check-grid">'
 for s in impl.subjects_for(r):
  values=impl.grades_for(r,c,s)
  body+='<article data-grade-subject="'+s+'"><h3>'+s+'</h3>'+impl.paragraph(impl.pretty(values))+'</article>'
 body+='</div>'
 for note in course_notes(r,c):body+=impl.paragraph(note)
 return body

def conditions(r,c):
 entries=[('자료의 평균 오픈 시간',c.get('openingReference') or '자료에 시간 기재 없음'),('자료의 주말 운영 안내',c.get('weekend') or '자료에 주말 운영 기재 없음')]
 body='<dl class="ns-facts ns-conditions">'+''.join('<div><dt>'+impl.E(k)+'</dt><dd>'+impl.E(v)+'</dd></div>' for k,v in entries)+'</dl>'
 body+=impl.paragraph('오픈 시간은 학생의 수업 시작 시각과 다를 수 있습니다. 주말 안내도 모든 과목·학년에 동일하게 적용되는 것은 아니므로 희망 과목과 시간을 함께 확인해 주세요.')
 for note in course_notes(r,c):body+=impl.paragraph(note)
 body+=impl.paragraph('수강 학년 기준: '+authority(c)+'. 운영 시간과 별도 수강 조건은 제공된 센터 자료의 참고 안내입니다.')
 return body

def materials(r,c):
 stage=r.get('stage');subject=r.get('subject')
 if stage and subject:return impl.PROFILES[stage+'-'+subject]['materials']
 if r.get('category'):return impl.CATEGORIES[r['category']][2]
 return '현재 교재, 학교 진도표와 최근 학생 답안'

def eul(value):
 last=value[-1];return '을' if '\uac00'<=last<='\ud7a3' and (ord(last)-0xac00)%28 else '를'

def enrollment_documents(r,c):
 body=impl.paragraph(f'{c["routeName"]}에 수강을 문의할 때 학생의 학년, 희망 과목과 아래 자료를 함께 전달해 주세요. '+materials(r,c)+eul(materials(r,c))+' 준비하면 현재 진도를 구체적으로 설명할 수 있습니다.')
 body+='<ul>'+''.join('<li>'+impl.E(v)+'</li>' for v in [f'학생의 현재 학년과 {authority(c)}의 안내 범위: {impl.availability(r,c)}','재학 학교에서 실제로 사용하는 교재와 안내된 평가 범위','학생이 혼자 풀고 어려운 곳에 표시한 최근 답안','학교 종료 시각, 출발 위치와 희망 등원 요일'])+'</ul>'
 body+=impl.paragraph(impl.school_context(r,c))
 if r.get('stage'):guide=f'/전국센터/{impl.norm(r["neighborhood"])}/{r["stage"]}{r["subject"]}학원/'
 else:guide=f'/과목별학원/{r["subject"]}전문학원/{impl.norm(r["neighborhood"])}/'
 body+=impl.anchor(guide,'학생 답안의 학습 점검 기준 보기')
 return body

def enrollment_order(r,c):
 steps=[('학년·과목과 수업 장소 확인',f'{c["routeName"]}의 안내 범위는 {impl.availability(r,c)}입니다. 실제 주소는 {c["address"]}입니다. 안내되지 않은 학년과 별도 수업 지점이 있는 과목은 신청 전에 확인해 주세요.'),('학교 일정과 희망 시간 전달',f'{r["neighborhood"]}의 출발 위치와 학교 종료 시각을 기준으로 이동 시간을 확인하세요. 자료의 오픈 안내는 {c.get("openingReference") or "시간 미기재"}이며, 학생의 수업 시작 시각은 별도 확인 대상입니다.'),('교습비와 포함 항목 확인','수업 횟수·회당 시간·포함 과목과 추가 프로그램을 함께 받아 적으세요. 공통 참고표의 금액을 지점 확정 교습비로 판단하지 말고 교습비 자료와 상담 답변을 비교합니다.')]
 if restricted(r,c):
  steps[0]=(steps[0][0],steps[0][1].replace('실제 주소는 '+c['address']+'입니다.','안내 지점 주소는 '+c['address']+'입니다. 이 과목의 실제 수업 장소는 별도 지점 안내를 기준으로 확인해 주세요.'))
 return '<div class="ns-check-grid">'+''.join('<article><h3>'+impl.E(h)+'</h3>'+impl.paragraph(t)+'</article>' for h,t in steps)+'</div>'+impl.anchor('#fees','교육비 확인 경로로 이동')

def clarify_venue(doc,r,c):
 if not restricted(r,c):return False
 changed=False
 for p in doc.xpath('//main//p'):
  if p.text and '실제 수업 장소는 위 주소를 기준으로 확인해 주세요.' in p.text:
   p.text=p.text.replace('실제 수업 장소는 위 주소를 기준으로 확인해 주세요.','위 주소는 안내 지점 주소이며, 이 과목의 실제 수업 장소는 별도 지점 안내를 기준으로 확인해 주세요.');changed=True
  if p.text and '실제 주소는 '+c['address'] in p.text:
   p.text=p.text.replace('실제 주소는 '+c['address'],'안내 지점 주소는 '+c['address'])
   if '별도 지점 안내' not in p.text:p.text+=' 이 과목의 실제 수업 장소는 별도 지점 안내를 기준으로 확인해 주세요.'
   changed=True
 for script in doc.xpath('//script[@type="application/ld+json"]'):
  data=json.loads(script.text);updated=False
  for n in data.get('@graph',[]):
   if n.get('@type')=='Article' and '실제 주소:' in n.get('abstract',''):
    n['abstract']=n['abstract'].replace('실제 주소:','안내 지점 주소:');updated=True
  if updated:script.text=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c');changed=True
 return changed

def refine_venues():
 count=0
 for r in impl.inventory():
  c=impl.CENTERS[tuple(r['centerKey'])]
  if not restricted(r,c):continue
  path=impl.ROOT/r['path'].strip('/')/'index.html';doc=html.document_fromstring(path.read_text('utf-8'));protected=impl.protect(doc)
  if clarify_venue(doc,r,c):
   assert impl.protect(doc)==protected
   impl.write_page(path,html.tostring(doc,encoding='unicode',method='html',doctype='<!DOCTYPE html>')+'\n');count+=1
 return count

def scenarios(r,c):
 values=SCENARIOS[r['stage']+'-'+r['subject']]
 return impl.paragraph('학생이 실제로 남긴 답안에서 가까운 상황을 골라 보세요. 아래는 공부 상태를 구분하는 방법이며 수강 사례나 성적 향상 결과가 아닙니다.')+'<div class="ns-check-grid">'+''.join('<article><h3>'+impl.E(h)+'</h3>'+impl.paragraph(t)+'</article>' for h,t in values)+'</div>'

def category_matrix(r,c):
 _,focus,_,checks=impl.CATEGORIES[r['category']]
 body=impl.paragraph(f'{r["neighborhood"]}에서 수업을 비교할 때 {focus}에 관한 답변과 실제 수강 조건을 나누어 기록하세요.')
 entries=[(h,t) for h,t in checks]+[('학교 자료를 기준으로 범위 확인',impl.school_context(r,c)),('과목별 학년과 수업 지점 확인',f'{c["routeName"]}의 안내 학년은 {impl.availability(r,c)}입니다. 실제 주소 {c["address"]}와 희망 과목의 수업 장소가 일치하는지 확인하세요.'),('일정·교습비 답변의 기준 확인',f'자료의 평균 오픈 안내는 {c.get("openingReference") or "시간 미기재"}입니다. 수업 요일·횟수·회당 시간과 최종 교습비를 같은 조건으로 받아 적어 비교합니다.')]
 body+='<div class="ns-comparison-list">'+''.join('<article id="section-'+str(i)+'"><h3>'+impl.E(h)+'</h3>'+impl.paragraph(t)+'</article>' for i,(h,t) in enumerate(entries,1))+'</div>'
 return body

def move_comparison_questions(doc):
 main=doc.xpath('//main')[0];questions=impl.byid(doc,'reading-7');image=impl.byid(doc,'page-images')
 assert questions is not None and image is not None
 assert len(questions.xpath('.//div[@class="ns-comparison-list"]/article'))==6
 if main.index(questions)<main.index(image):return False
 main.remove(questions);main.insert(main.index(image),questions);return True

def place_comparison_questions():
 count=0
 rows=[r for r in impl.inventory() if r['role']=='comparison-guide']
 for i,r in enumerate(rows,1):
  path=impl.ROOT/r['path'].strip('/')/'index.html';doc=html.document_fromstring(path.read_text('utf-8'));protected=impl.protect(doc)
  assert doc.xpath('//body/@data-neighborhood-phase2')==[VERSION]
  if move_comparison_questions(doc):
   assert impl.protect(doc)==protected
   impl.write_page(path,html.tostring(doc,encoding='unicode',method='html',doctype='<!DOCTYPE html>')+'\n');count+=1
  if i%1000==0:print('Placed comparison questions',i,flush=True)
 impl.dump(OUT/'comparison-placement.json',{'checkedPages':len(rows),'changedPages':count,'imageOrderPreserved':True,'deployed':False})
 return count

def faq(r,c):
 first=('어떤 학년의 수강을 확인할 수 있나요?',f'{authority(c)} 기준 안내 학년은 {impl.availability(r,c)}입니다. 현재 모집 자리와 과목별 수업 조건은 {c["routeName"]}에 확인해 주세요.') if r['role']=='enrollment' else ('이 페이지는 어떤 목적으로 활용하나요?',f'{r["neighborhood"]}에서 학생의 자료로 학습 상태와 수업 선택 기준을 살펴보는 안내입니다. 실제 수강 조건은 {c["routeName"]}의 수강·위치 안내에서 확인해 주세요.')
 pairs=[first,('실제 수업 장소는 어디인가요?',f'안내 지점의 주소는 {c["address"]}입니다. '+(' '.join(course_notes(r,c)) if restricted(r,c) else '학생의 출발 위치에서 이동 시간을 확인하고 희망 과목의 실제 수업 장소를 함께 문의해 주세요.')),('상담에는 어떤 자료를 준비하나요?',materials(r,c)+eul(materials(r,c))+' 준비하고 학생의 현재 학년, 학교 진도와 희망 요일을 함께 전달해 주세요.'),('교육비와 수업 시간을 어떻게 확인하나요?','월 금액뿐 아니라 주당 횟수·회당 시간·포함 과목과 추가 비용을 함께 확인합니다. 지점의 교습비 안내 자료와 상담에서 최종 조건을 확인해 주세요.')]
 return ''.join('<details><summary>'+impl.E(q)+'</summary>'+impl.paragraph(a)+'</details>' for q,a in pairs)

def update_schema(doc,r,c):
 for script in doc.xpath('//script[@type="application/ld+json"]'):
  data=json.loads(script.text);graph=data.get('@graph',[])
  has_course=r['role']=='enrollment' and r.get('subject') and impl.grades_for(r,c,r['subject']) and not restricted(r,c)
  if not has_course:graph[:]=[n for n in graph if n.get('@type')!='Service']
  elif not any(n.get('@type')=='Service' for n in graph):
   graph.append({'@type':'Service','@id':r['canonical']+'#service','name':heading(r),'serviceType':r.get('stage','')+' '+r['subject']+' 수강 안내','provider':{'@id':impl.DOMAIN+impl.U(impl.center_path(c))+'#center'},'areaServed':{'@type':'Place','name':r['neighborhood']}})
  article_id=next((n.get('@id') for n in graph if n.get('@type')=='Article'),None)
  for n in graph:
   if n.get('@type')=='Service':n['description']=f'{authority(c)} 기준 {impl.availability(r,c)} 안내입니다. 현재 모집 여부와 시간표는 별도 확인해 주세요.'
   if n.get('@type')=='WebPage' and article_id:n['mainEntity']={'@id':article_id}
   if n.get('@type')=='Article':
    n['headline']=heading(r);n['abstract']=f'{authority(c)} 기준 {impl.availability(r,c)}. 실제 주소: {c["address"]}. '+('수강 조건을 확인하는 안내입니다.' if r['role']=='enrollment' else '학습 자료와 수업을 비교하는 안내입니다.')
    n['articleSection']={'enrollment':'수강 학년·위치·일정 확인','study-guide':'학생 답안과 진도·오답 점검','comparison-guide':'과목·학교급별 수업 비교 기준','overview':'동네별 과목·학년 안내'}[r['role']]
    if isinstance(n.get('about'),dict) and str(n['about'].get('@id','')).endswith('#service') and not has_course:n['about']={'@id':impl.DOMAIN+impl.U(impl.center_path(c))+'#center'}
    if 'hasPart' in n:
     n['hasPart']=[{'@type':'WebPageElement','name':el.text_content().strip(),'url':r['canonical']+'#'+el.getparent().get('id')} for el in doc.xpath('//main//*[@id]/h3') if el.getparent().get('id','').startswith('section-')]
   if n.get('@type') in ['WebPage','CollectionPage','Article']:n['dateModified']=impl.DAY
  impl.refresh_faq_schema(doc,data);script.text=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')

def image_explanation(doc):
 media=impl.byid(doc,'page-images')
 if media is None:return
 wrap=media.xpath('./div')[0]
 if not wrap.xpath('.//*[@class="ns-image-summary"]'):
  content=impl.node('<div class="ns-image-summary">'+impl.paragraph('공통 브랜드 소개 이미지의 4C는 맞춤 진단(Check), 맞춤 처방(Curriculum), 맞춤 지도(Coaching), 맞춤 상담(Consulting)을 설명합니다. 학생의 현재 상태를 살피고 학습 내용을 정한 뒤 지도와 상담으로 다음 계획을 조정하는 과정입니다.')+impl.anchor('/학습관리/#four-c','학습관리 과정을 텍스트로 읽기')+'</div>')
  container=wrap.xpath('./div[contains(@class,"cl-media")]')[0];wrap.insert(wrap.index(container),content)
 for note in media.xpath('.//p[contains(@class,"cl-media-note")]'):
  note.text='이 이미지는 브랜드 공통 소개 자료입니다. 이미지 속 후기·평점·결과 예시는 이 지점의 실제 후기나 수강 성과를 확인한 자료가 아닙니다. 교육비는 지역 공통 참고 안내이며, 지점 교습비와 현재 수업 구성은 별도로 확인해 주세요.'

def transform(r):
 path=impl.ROOT/r['path'].strip('/')/'index.html';before=path.read_text('utf-8');doc=html.document_fromstring(before);protected=guard(doc);c=impl.CENTERS[tuple(r['centerKey'])]
 assert doc.xpath('//body/@data-neighborhood-seo')==[impl.VERSION]
 if doc.xpath('//body/@data-neighborhood-phase2')==[VERSION]:return False
 doc.xpath('//body')[0].set('data-neighborhood-phase2',VERSION);h=doc.xpath('//h1')[0];h.text=heading(r)
 for child in list(h):h.remove(child)
 main=doc.xpath('//main')[0];old=impl.byid(doc,'local-summary');main.replace(old,impl.quick_facts(r,c))
 summary=impl.byid(doc,'local-summary');summary.xpath('./div')[0].append(impl.node(impl.paragraph('수강 학년 기준: '+authority(c)+'.')))
 if restricted(r,c):
  for dt in summary.xpath('.//dt[text()="실제 주소"]'):dt.text='안내 지점 주소'
  summary.xpath('./div')[0].append(impl.node('<div class="ns-source-note">'+''.join(impl.paragraph(v) for v in course_notes(r,c))+'</div>'))
 for ident in ['center-grades','grades']:
  if impl.byid(doc,ident) is not None:impl.replace_section(doc,ident,c['routeName']+' 안내 학년 확인',grade_body(r,c))
 if r['role'] in ['enrollment','overview']:
  block=impl.section('center-conditions',c['routeName']+' 운영 자료와 수강 조건',conditions(r,c));images=impl.byid(doc,'page-images');main.insert(main.index(images),block)
 else:
  for ident in ['center-grades']:
   impl.replace_section(doc,ident,'학습 자료에 맞는 안내 학년 확인',impl.paragraph(authority(c)+' 기준 '+impl.availability(r,c)+'.')+impl.anchor(r['enrollmentPath']+'#center-conditions','운영 시간·수강 조건 자세히 확인'))
 if r['role']=='enrollment':
  hero=main[0]
  for p in hero.xpath('.//div[contains(@class,"bc-quick-answer")]/p'):p.text='안내 학년: '+impl.availability(r,c)+'. '+(' '.join(course_notes(r,c)) if restricted(r,c) else '현재 모집 여부와 희망 수업 시간은 지점에 확인해 주세요.')
  for ident in ['grade-learning','subject-learning']:impl.replace_section(doc,ident,'수강 상담에 전달할 학생 자료',enrollment_documents(r,c))
  for ident in ['learning-routine','learning-plan']:impl.replace_section(doc,ident,'수강 전에 확인할 순서',enrollment_order(r,c))
  impl.replace_section(doc,'consultation-prep','상담에서 확정할 수업 조건',impl.paragraph(f'{c["routeName"]}에 전달한 학년·과목과 희망 일정이 실제 수업 조건에 맞는지 확인하세요. 가능한 요일, 회당 시간, 포함 과목과 교습비를 함께 받아 적어 주세요.')+impl.anchor('#center-conditions','지점 운영 자료 다시 확인'))
 elif r['role']=='study-guide':
  impl.replace_section(doc,'intent-guide',r['stage']+' '+r['subject']+' 수업을 비교할 때 받아 적을 답변',impl.study_content(r,c))
  impl.replace_section(doc,'student-fit','학생 답안에서 구분할 세 가지 상황',scenarios(r,c))
  impl.replace_section(doc,'consult-checklist','재학 학교 자료와 답안 묶기',impl.paragraph(impl.school_context(r,c))+impl.paragraph(materials(r,c)+eul(materials(r,c))+' 학교 진도 순서로 묶고 도움이 필요한 부분에 표시하세요. 학교별 제휴나 전용반을 전제로 하지 않고 실제로 받은 자료를 기준으로 비교합니다.'))
 elif r['role']=='comparison-guide':
  _,focus,docs,_=impl.CATEGORIES[r['category']]
  impl.replace_section(doc,'intent-guide',impl.CATEGORIES[r['category']][0]+'의 출발점',impl.paragraph(f'{r["neighborhood"]}에서 수업을 비교할 때 먼저 살펴볼 내용은 {focus}입니다. '+docs+eul(docs)+' 준비하고 아래 질문별로 답변을 받아 적어 보세요.')+impl.paragraph(f'상담에 참고할 {c["routeName"]}의 안내 학년은 {impl.availability(r,c)}입니다.'))
  impl.replace_section(doc,'reading-7','수업을 비교할 여섯 가지 질문',category_matrix(r,c))
  impl.replace_section(doc,'reading-2','비교에 사용할 학생 자료',impl.paragraph(docs+eul(docs)+' 준비하고 최근 자료와 이전 자료를 나누어 주세요. 어려운 지점이 어느 자료에서 반복되는지 표시하면 상담 답변을 비교하기 쉽습니다.'))
  impl.replace_section(doc,'reading-9','답변을 받은 뒤 비교할 조건',impl.paragraph(f'{r["category"]} 상담에서 '+focus+eul(focus)+' 어떻게 확인하는지 받은 답변을 학생의 실제 자료와 대조하세요.')+impl.paragraph('그다음 안내 학년, 수업 지점, 가능한 요일·시간과 교습비가 학생의 조건에 맞는지 확인합니다. 설명이 불분명한 항목은 추가로 질문하고 확인된 내용만 계획에 반영하세요.'))
 else:
  impl.replace_section(doc,'learning-plan','생활권과 실제 지점 구분',impl.paragraph(f'{r["neighborhood"]} 안내의 연결 지점은 {c["displayName"]}이며 실제 주소는 {c["address"]}입니다. 같은 지점에 연결된 동네 안내는 별도 학원이 있다는 뜻이 아닙니다.')+impl.paragraph('주소·과목별 학년·교습비는 수강 안내에서, 학생 답안의 점검은 학년별 가이드에서 확인해 주세요.'))
  impl.replace_section(doc,'learning-steps','필요한 안내를 고르는 순서',impl.paragraph('먼저 학생의 학년과 희망 과목으로 안내 범위를 확인하세요. 다음으로 실제 수업 장소와 시간 조건을 확인하고, 학생이 준비한 교재와 답안으로 학습 점검 가이드를 살펴봅니다.'))
  impl.replace_section(doc,'student-fit','학교와 과목에 맞게 자료 준비',impl.paragraph(impl.school_context(r,c))+impl.paragraph('재학 학교, 현재 교재와 학생의 직접 답안을 기준으로 필요한 도움을 구분하세요. 학교 목록에 없는 학교도 수강 여부를 임의로 판단하지 말고 지점에 확인해 주세요.'))
 for ident in ['faq','faq-section']:impl.replace_section(doc,ident,'수강·위치 확인 질문' if r['role']=='enrollment' else '학습·비교 안내 확인 질문',faq(r,c))
 if r['role']=='comparison-guide':move_comparison_questions(doc)
 image_explanation(doc);update_schema(doc,r,c);clarify_venue(doc,r,c)
 assert guard(doc)==protected,(r['path'],'protected route/media/contact changed')
 impl.write_page(path,html.tostring(doc,encoding='unicode',method='html',doctype='<!DOCTYPE html>')+'\n');return True

def hubs():
 changed=0
 for c in impl.FACTS['centers']:
  path=impl.ROOT/impl.center_path(c).strip('/')/'index.html'
  if not path.exists():continue
  before=path.read_text('utf-8');doc=html.document_fromstring(before);protected=impl.protect(doc)
  if doc.xpath('//body/@data-neighborhood-phase2')==[VERSION]:continue
  r={'role':'enrollment','neighborhood':c['routeName'],'centerKey':[c['region'],c['routeName']]}
  impl.replace_section(doc,'courses','과목별 안내 학년과 수강 조건',grade_body(r,c))
  main=doc.xpath('//main')[0]
  for ident in ['center-info','courses','fees']:
   block=impl.byid(doc,ident);image=impl.byid(doc,'page-images')
   if block is not None and image is not None:main.remove(block);main.insert(main.index(image),block)
  image=impl.byid(doc,'page-images')
  if image is not None:main.insert(main.index(image),impl.section('center-conditions','운영 자료와 상담 전 확인',conditions(r,c)))
  impl.replace_section(doc,'faq','지점 수강 조건 확인 질문',faq(r,c));image_explanation(doc)
  for script in doc.xpath('//script[@type="application/ld+json"]'):
   data=json.loads(script.text);graph=data.get('@graph',[])
   for n in graph:
    if n.get('@type')=='Service':
     subject=next((s for s in c['subjects'] if s in n.get('name','')),None)
     if subject:n['description']=f'{authority(c)} 기준 {subject} {impl.pretty(c["subjects"][subject])} 안내입니다. 현재 모집 여부와 시간표는 확인이 필요합니다.'
   graph[:]=[n for n in graph if n.get('@type')!='Service' or any(s in n.get('name','') and c['subjects'][s] and not restricted({**r,'subject':s},c) for s in c['subjects'])]
   impl.refresh_faq_schema(doc,data);script.text=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
  doc.xpath('//body')[0].set('data-neighborhood-phase2',VERSION)
  assert impl.protect(doc)==protected
  impl.write_page(path,html.tostring(doc,encoding='unicode',method='html',doctype='<!DOCTYPE html>')+'\n');changed+=1
 finish_hubs()
 return changed

def finish_hubs():
 # Five existing center pages have no neighborhood routes, but their grades
 # still need the same confirmed authority and public styling.
 paths=set()
 for c in impl.FACTS['centers']:
  rel=impl.center_path(c);path=impl.ROOT/rel.strip('/')/'index.html'
  if not path.exists():continue
  doc=html.document_fromstring(path.read_text('utf-8'));protected=impl.protect(doc)
  if doc.xpath('//body/@data-neighborhood-phase2')!=[VERSION]:continue
  paths.add(rel);changed=False
  if not doc.xpath('//link[@href="/assets/neighborhood-seo/local.css"]'):
   doc.xpath('//head')[0].append(impl.node('<link rel="stylesheet" href="/assets/neighborhood-seo/local.css">'));changed=True
  for script in doc.xpath('//script[@type="application/ld+json"]'):
   data=json.loads(script.text);updated=False
   for n in data.get('@graph',[]):
    if n.get('@type') in ['WebPage','CollectionPage'] and n.get('dateModified')!=impl.DAY:n['dateModified']=impl.DAY;updated=True
   if updated:script.text=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c');changed=True
  if changed:
   assert impl.protect(doc)==protected
   impl.write_page(path,html.tostring(doc,encoding='unicode',method='html',doctype='<!DOCTYPE html>')+'\n')
 sitemap=etree.parse(str(impl.ROOT/'sitemap.xml'));before=sitemap.xpath('//*[local-name()="loc"]/text()')
 for entry in sitemap.getroot():
  url=entry.find('{*}loc')
  if url is not None and impl.unquote(impl.urlsplit(url.text).path) in paths:
   last=entry.find('{*}lastmod')
   if last is None:last=etree.SubElement(entry,'{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod')
   last.text=impl.DAY
 assert sitemap.xpath('//*[local-name()="loc"]/text()')==before
 sitemap.write(str(impl.ROOT/'sitemap.xml'),encoding='utf-8',xml_declaration=True,pretty_print=True)

def main():
 p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--sample',action='store_true');p.add_argument('--all',action='store_true');p.add_argument('--place-comparison',action='store_true');args=p.parse_args()
 if args.prepare:prepare();return
 if args.place_comparison:print('Comparison pages moved',place_comparison_questions());return
 assert args.sample or args.all
 rows=impl.inventory();selected=rows if args.all else [r for r in rows if impl.norm(r['neighborhood']) in ['명일동','불당동','구파발','풍덕천동'] or r['center'] in ['침산점','소하점','범박점']]
 counts=Counter()
 for i,r in enumerate(selected,1):
  counts[r['family']]+=int(transform(r))
  if i%1000==0:print('Phase 2 processed',i,flush=True)
 hub_count=hubs() if args.all else 0
 venue_count=refine_venues() if args.all else 0
 if args.all:place_comparison_questions()
 result={'version':VERSION,'scope':'all' if args.all else 'sample','selectedPages':len(selected),'changedPages':sum(counts.values()),'changedFamilies':dict(counts),'changedCenterHubs':hub_count,'separateVenuePagesRefined':venue_count,'urlsDeleted':0,'deployed':False}
 impl.dump(OUT/('implementation.json' if args.all else 'sample.json'),result);print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
