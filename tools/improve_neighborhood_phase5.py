"""Role-specific FAQ, with visible answers and FAQPage from reviewed facts.

Only the FAQ section/FAQPage are changed. The section is placed before the
original long images; original HTML outside these bounded fields stays intact.
"""
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import argparse,hashlib,json,re
from lxml import html
import improve_neighborhood_pages as impl
import improve_neighborhood_phase2 as phase2
from audit_neighborhood_phase5 import OUT,PRIOR,BACKUP,entries,filename

VERSION='20261001-v5'
REWRITE=False
FAQ=re.compile(r'<section\b(?=[^>]*\bid="(?:faq|faq-section)")[^>]*>.*?</section>',re.S)
SCRIPTS=re.compile(r'(<script\b[^>]*type="application/ld\+json"[^>]*>)(.*?)(</script>)',re.S)
FEE_INPUT=impl.load(PRIOR/'fee-grid-verified.json')
FEES={(s['region'],s['center']):s for s in FEE_INPUT['centers']}

COMPARE_QUESTIONS={
 '전문학원':('공부 계획을 자꾸 미룬다면 학습관리 수업에서 무엇을 물어봐야 하나요?','과제 확인 횟수만으로 학습관리를 비교해도 되나요?'),
 '영수전문학원':('영어·수학을 함께 알아볼 때 어느 과목부터 점검하나요?','영어·수학 공부 시간은 어떻게 나누어 비교하나요?'),
 '영어전문학원':('영어학원을 비교하기 전에 읽기에서 무엇을 확인하나요?','영어 문제를 맞힌 것만으로 이해했다고 판단해도 되나요?'),
 '수학전문학원':('수학학원을 비교할 때 정답률 외에 무엇을 보나요?','수학 오답을 상담할 때 어느 풀이 단계를 보여 주나요?'),
 '초등학생학원':('초등학생 수업을 비교할 때 아이의 이해를 어떻게 확인하나요?','초등 수업이면 영어·수학의 시작 학년도 같나요?'),
 '중학생학원':('중학생 수업을 비교하기 전에 학교 진도는 어떻게 정리하나요?','중등 영어·수학의 서술형 답안은 무엇을 비교하나요?'),
 '고등학생학원':('고등학생 수업을 알아볼 때 학년 외에 무엇을 전달하나요?','학교 시험과 별도 평가 준비는 어떻게 나누어 질문하나요?'),
}

def link(path,label):return {'path':path,'label':label}
def pair(kind,q,a,*links):return {'kind':kind,'question':q,'answer':a,'links':list(links)}
def context(r):return (r.get('stage','')+' '+r.get('subject','')).strip()
def materials_for(r,c):
    if r.get('subject') and not r.get('stage') and r['subject'] in ['영어','수학']:
        return impl.CATEGORIES[r['subject']+'전문학원'][2]
    return phase2.materials(r,c)
def grade_answer(r,c):
    answer=c['routeName']+'의 '+phase2.authority(c)+' 기준 안내 학년은 다음과 같습니다. '+impl.availability(r,c)+'. '
    if c.get('gradeAuthority')!='workbook':answer+='센터 데이터 엑셀에서 일치하는 지점명이 확인되지 않아 CSV의 안내 범위를 표시하고 있습니다. 세부 학년은 지점에 다시 확인해 주세요. '
    answer+='안내 학년이 현재 모집 중인 자리나 확정 시간표를 뜻하지는 않습니다.'
    notes=phase2.course_notes(r,c)
    if notes:answer+=' '+' '.join(notes)
    return answer

def venue_answer(r,c):
    answer=c['routeName']+'의 안내 주소는 '+c['address']+'입니다. '
    if r['role']!='center-hub':answer+=r['neighborhood']+'은 상담 대상 생활권이며, 동네 이름이 별도 지점 주소를 뜻하지는 않습니다. '
    if any('수지점(W+)' in n for n in phase2.course_notes(r,c)):
        answer+='수학·과학은 수지점(W+)에서 상담한다는 안내가 있으므로 희망 과목의 실제 수업 장소를 따로 확인해 주세요.'
    else:answer+='학교나 집에서 출발하는 경로와 희망 과목의 실제 수업 장소를 함께 확인해 주세요.'
    return answer

def material_answer(r,c):
    material=materials_for(r,c)
    return material+phase2.eul(material)+' 준비해 주세요. 학생의 현재 학년과 실제 학교 진도, 혼자 해결한 부분과 도움이 필요했던 부분을 함께 전달하면 상담 질문을 구체화할 수 있습니다. 학교별 평가 범위는 학생이 받은 자료를 기준으로 확인합니다.'

def fee_answer(r,c,s,visible_rows):
    dates=' · '.join(s['sourceDates']) or '기준일 확인 필요'
    answer=c['routeName']+' 교습비 원문의 기준일은 '+dates+'입니다. '
    if len(s['sourceDates'])>1:answer+='원문에 여러 기준일이 있어 해당 과정의 날짜를 구분해 확인해야 합니다. '
    if r['role'] in ['enrollment','center-hub']:
        if visible_rows:answer+='이 페이지의 관련 원문 항목에서 과정명·기간·총 교습시간·총교습비를 함께 확인할 수 있습니다. '
        else:answer+='이 페이지에서 금액을 확정해 안내할 수 있는 일반 과정 항목은 확인이 필요합니다. '
    else:answer+='관련 수강 안내에서 같은 학년·과목의 원문 항목을 확인해 주세요. '
    if any('수지점(W+)' in n for n in phase2.course_notes(r,c)) and '수학' in impl.subjects_for(r):
        answer+='수학·과학은 W+ 상담 안내가 있어 실제 수업 장소와 적용 교습비를 별도로 확인해야 합니다. '
    answer+='원문 금액은 게시 당시 안내이며 현재 적용 금액은 지점에 확인해 주세요. 주당 횟수·회당 시간·포함 과목과 추가 비용도 같은 조건으로 질문합니다.'
    return answer

def schedule_answer(c):
    return '센터 자료의 평균 오픈 안내는 '+(c.get('openingReference') or '시간 미기재')+'입니다. 주말 참고 안내: '+(c.get('weekend') or '운영 여부 미기재')+' 오픈 시간은 학생의 수업 시작 시각과 다를 수 있고, 주말 안내가 모든 과목·학년에 적용되는 것은 아닙니다. 학교 종료 시각과 이동 시간, 희망 과목·요일을 전달해 실제 시간표를 확인해 주세요.'

def reviewed_faq(r,c,doc):
    role=r['role'];ctx=context(r);s=FEES[tuple(r['centerKey'])]
    grade_id=next((ident for ident in ['grades','center-grades','courses'] if impl.byid(doc,ident) is not None),None)
    assert grade_id,r['path']
    school_id='schools' if impl.byid(doc,'schools') is not None else 'center-schools'
    source=[link('#fees','교습비 기준일과 관련 항목 보기')]
    if role not in ['enrollment','center-hub']:source.append(link(r['enrollmentPath']+'#fees','관련 수강 안내의 교습비 보기'))
    source.append(link(s['feeLink'],c['routeName']+' 교습비 원문 PDF 보기'))
    fee=pair('fees',ctx+' 교육비는 현재 금액으로 확정된 안내인가요?' if ctx else c['routeName']+' 교습비 자료는 현재 금액인가요?',fee_answer(r,c,s,len(doc.xpath('//section[@id="fees"]//tr[@data-fee-course]'))),*source)
    grade=pair('grades',c['routeName']+'의 '+(ctx+' ' if ctx else '과목별 ')+'안내 학년과 현재 모집 여부는 같나요?',grade_answer(r,c),link('#'+grade_id,'과목별 안내 학년 확인'))
    venue=pair('venue',r['neighborhood']+'에서 알아보는 수업의 실제 주소는 어디인가요?' if role!='center-hub' else c['routeName']+'의 주소와 과목별 수업 장소는 어떻게 확인하나요?',venue_answer(r,c),link('#center-info','주소와 지도 확인'))
    materials=pair('materials',(ctx+' ' if ctx else '')+'상담에서 학교 진도와 오답을 설명하려면 무엇을 준비하나요?',material_answer(r,c),link('#'+school_id,'생활권 학교와 준비 자료 확인'))
    schedule=pair('schedule','오픈 안내 시간에 바로 수업을 시작할 수 있나요?',schedule_answer(c),link('#center-conditions','운영 참고 조건 확인'))
    if role in ['enrollment','center-hub']:
        pairs=[grade,venue,materials,schedule,fee]
        title=(r['neighborhood']+' '+ctx+' 수강 전 확인 질문').replace('  ',' ') if role=='enrollment' else c['routeName']+' 수강·운영 확인 질문'
    elif role=='study-guide':
        profile=impl.PROFILES[r['stage']+'-'+r['subject']];scenario=phase2.SCENARIOS[r['stage']+'-'+r['subject']][0]
        diagnosis=pair('diagnosis',ctx+'에서 '+scenario[0]+'는 무엇부터 점검하나요?',scenario[1]+' 학생 답안을 점검하는 방법이며 해당 지점의 확정 수업 방식이나 수강 성과를 뜻하지는 않습니다.',link('#intent-guide','진도·오답 점검 내용 보기'))
        recall=pair('recheck',ctx+' 오답을 고친 뒤 혼자 이해했는지는 어떻게 확인하나요?',profile['steps'][2][1]+' 기록에는 '+profile['record']+'을 남겨 다음 점검에 활용해 주세요.',link('#learning-steps','학습 뒤 남길 기록 보기'))
        actual=pair('grades-venue',c['routeName']+'에서 '+ctx+' 수강 조건은 어디서 확인하나요?',grade_answer(r,c)+' '+venue_answer(r,c),link(r['enrollmentPath'],'해당 학년·과목 수강 안내 보기'))
        pairs=[diagnosis,recall,materials,actual,fee];title=r['neighborhood']+' '+ctx+' 학습 점검 질문'
    elif role=='comparison-guide':
        questions=COMPARE_QUESTIONS[r['category']];checks=impl.CATEGORIES[r['category']][3]
        first=pair('compare-start',questions[0],r['neighborhood']+'에서 수업을 비교하기 전에 학생이 직접 남긴 자료로 출발점을 정리해 보세요. '+checks[0][1],link('#reading-7','수업 비교 질문과 기준 보기'))
        second=pair('compare-evidence',questions[1],checks[1][1]+' 비교 상담에는 '+phase2.materials(r,c)+phase2.eul(phase2.materials(r,c))+' 준비해 주세요. 이 기준은 비교할 질문이며 지점의 확정 운영 방식으로 단정하지 않습니다.',link('#reading-7','같은 조건으로 비교할 질문 보기'))
        pairs=[first,second,grade,venue,fee];title=r['neighborhood']+' '+impl.CATEGORIES[r['category']][0]+' 질문'
    else:
        routes=pair('navigation',r['neighborhood']+'의 과목·학년 페이지는 어떤 순서로 보면 되나요?',c['routeName']+'의 과목별 안내 학년에서 학생의 학년이 기재돼 있는지 먼저 확인해 주세요. 수강 안내는 학년·주소·일정·교습비를, 학습 점검은 학생 답안의 진도·오답을, 비교 안내는 수업 선택 질문을 살펴보는 데 활용합니다.',link('#center-grades','과목별 안내 학년 보기'),link(r['branchPath'],'지점 수강·위치 안내 보기'),link('#related-intents','과목·학년별 학습·비교 안내 보기'))
        pairs=[routes,grade,materials,venue,fee];title=r['neighborhood']+' 과목·학년 선택 질문'
    return {'path':r['path'],'role':role,'centerKey':r['centerKey'],'faqId':doc.xpath('//section[@id="faq" or @id="faq-section"]/@id')[0],'title':title,'pairs':pairs,'facts':{'gradeAuthority':phase2.authority(c),'subjects':{s:impl.grades_for(r,c,s) for s in impl.subjects_for(r)},'sourceDates':s['sourceDates'],'sourceSha256':s['sourceSha256'],'feeLink':s['feeLink'],'address':c['address']}}

def prepare():
    assert BACKUP.exists()
    rows=entries()
    def review(r):
        raw=(impl.ROOT/filename(r['path'])).read_bytes();doc=html.document_fromstring(raw)
        assert doc.xpath('//body/@data-neighborhood-phase4')==['20261001-v4'],r['path']
        return reviewed_faq(r,impl.CENTERS[tuple(r['centerKey'])],doc)
    with ThreadPoolExecutor(max_workers=8) as pool:pages=list(pool.map(review,rows))
    data={'version':VERSION,'pages':pages,'sourceInputSha256':hashlib.sha256((PRIOR/'fee-grid-verified.json').read_bytes()).hexdigest(),'centerFactsSha256':hashlib.sha256((impl.DATA/'centers.json').read_bytes()).hexdigest(),'deployed':False}
    impl.dump(OUT/'reviewed-faq.json',data)
    print(json.dumps({'reviewedPages':len(pages),'questions':sum(len(p['pairs']) for p in pages),'roles':dict(Counter(p['role'] for p in pages))},ensure_ascii=False))

def render(page,old):
    content=''
    for p in page['pairs']:
        content+='<details data-faq-kind="'+p['kind']+'"><summary>'+impl.E(p['question'])+'</summary>'+impl.paragraph(p['answer'])
        if p['links']:
            content+='<div class="ns-faq-links">'
            for a in p['links']:
                external=a['path'].startswith('https://')
                content+='<a class="ns-link" href="'+impl.E(a['path'] if external else impl.U(a['path']))+'"'+(' target="_blank" rel="noopener noreferrer"' if external else '')+'>'+impl.E(a['label'])+'</a>'
            content+='</div>'
        content+='</details>'
    new=impl.section(page['faqId'],page['title'],content);new.set('data-faq-role',page['role'])
    for ident in old.xpath('.//*[@id]/@id'):
        if not new.xpath('.//*[@id=$id]',id=ident):new.append(impl.node('<span class="cl-legacy-anchor" id="'+impl.E(ident)+'"></span>'))
    return html.tostring(new,encoding='unicode',method='html')

def transform(page):
    path=impl.ROOT/filename(page['path']);before=path.read_bytes();text=before.decode('utf-8');doc=html.document_fromstring(before)
    if doc.xpath('//body/@data-neighborhood-phase5')==[VERSION] and not REWRITE:return {'path':page['path'],'role':page['role'],'changed':False}
    assert doc.xpath('//body/@data-neighborhood-phase4')==['20261001-v4']
    old=impl.byid(doc,page['faqId']);guard=impl.protect(doc);section=render(page,old)
    assert len(list(FAQ.finditer(text)))==1
    text=FAQ.sub('',text,count=1)
    image=re.search(r'<section\b(?=[^>]*\bid="page-images")[^>]*>',text);assert image
    text=text[:image.start()]+section+text[image.start():]
    if 'data-neighborhood-phase5=' not in text:
        text,count=re.subn(r'<body\b([^>]*)>',lambda m:'<body'+m[1]+' data-neighborhood-phase5="'+VERSION+'">',text,count=1);assert count==1
    schema_changes=0
    def schema(match):
        nonlocal schema_changes
        data=json.loads(match[2]);changed=False
        for n in data.get('@graph',[]):
            if n.get('@type')=='FAQPage':
                n['mainEntity']=[{'@type':'Question','name':p['question'],'acceptedAnswer':{'@type':'Answer','text':p['answer']}} for p in page['pairs']];schema_changes+=1;changed=True
        return match[1]+(json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c') if changed else match[2])+match[3]
    text=SCRIPTS.sub(schema,text);assert schema_changes==1
    payload=text.encode('utf-8');assert impl.protect(html.document_fromstring(payload))==guard
    pending=path.with_name('index.html.phase5-tmp');fallback=False
    try:pending.write_bytes(payload);pending.replace(path)
    except PermissionError:
        assert filename(page['path'])=='전국센터/이곡동/초등영어학원/index.html' and BACKUP.exists()
        with path.open('r+b') as stream:stream.seek(0);stream.write(payload);stream.truncate();stream.flush()
        if pending.exists():pending.unlink()
        fallback=True
    assert path.read_bytes()==payload
    return {'path':page['path'],'role':page['role'],'changed':True,'questions':len(page['pairs']),'handleWrite':fallback}

CSS='''
/* Phase 5: readable, linked FAQ answers before long original images. */
body[data-neighborhood-phase5] [data-faq-role] details{border-bottom:1px solid #d6cbbd;padding:15px 0}
body[data-neighborhood-phase5] [data-faq-role] summary{cursor:pointer;font-size:18px;font-weight:700;line-height:1.65;overflow-wrap:anywhere}
body[data-neighborhood-phase5] [data-faq-role] summary:focus-visible{outline:3px solid #9a4629;outline-offset:5px}
body[data-neighborhood-phase5] [data-faq-role] details p{margin:12px 0;line-height:1.85;overflow-wrap:anywhere}
body[data-neighborhood-phase5] .ns-faq-links{display:flex;flex-wrap:wrap;gap:10px;margin-top:12px}
body[data-neighborhood-phase5] .ns-faq-links .ns-link{max-width:100%;min-height:44px;box-sizing:border-box;overflow-wrap:anywhere}
@media(max-width:760px){body[data-neighborhood-phase5] [data-faq-role] summary{font-size:17px}body[data-neighborhood-phase5] .ns-faq-links{display:grid;grid-template-columns:minmax(0,1fr)}}
'''

def main():
    global REWRITE
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true');parser.add_argument('--sample',action='store_true');parser.add_argument('--all',action='store_true');parser.add_argument('--hubs',action='store_true');parser.add_argument('--rewrite',action='store_true');args=parser.parse_args();REWRITE=args.rewrite
    if args.prepare:prepare();return
    assert args.sample or args.all or args.hubs
    data=impl.load(OUT/'reviewed-faq.json');assert data['version']==VERSION and BACKUP.exists()
    assert data['centerFactsSha256']==hashlib.sha256((impl.DATA/'centers.json').read_bytes()).hexdigest()
    pages=data['pages']
    if args.sample:pages=[p for p in pages if p['centerKey'][1] in ['명일점','수지점','침산점','화성태안점','석사점','돈암점','신중동점']]
    if args.hubs:pages=[p for p in pages if p['role']=='center-hub']
    results=[]
    with ThreadPoolExecutor(max_workers=8) as pool:
        for index,r in enumerate(pool.map(transform,pages),1):
            results.append(r)
            if index%1000==0:print('Updated role-specific FAQ',index,flush=True)
    path=impl.ROOT/'assets/neighborhood-seo/local.css';raw=path.read_bytes()
    if b'/* Phase 5:' not in raw:path.write_bytes(raw+CSS.encode('utf-8'))
    result={'version':VERSION,'pages':results,'scope':'all' if args.all else ('hubs' if args.hubs else 'sample'),'changedPagesThisRun':sum(p['changed'] for p in results),'roles':dict(Counter(p['role'] for p in results)),'deployed':False,'urlsDeleted':0}
    impl.dump(OUT/('implementation.json' if args.all else ('hub-link-repair.json' if args.hubs else 'sample.json')),result)
    print(json.dumps({k:v for k,v in result.items() if k!='pages'},ensure_ascii=False))

if __name__=='__main__':main()
