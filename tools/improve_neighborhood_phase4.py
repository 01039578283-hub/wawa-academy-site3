"""Source-dated tuition facts without new URLs or current price promises.

Edit only existing #fees blocks and explicit revision markers. Keep every byte
outside those bounded regions so earlier reviewed school/media copy is retained.
"""
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import argparse,copy,json,re,hashlib,time
from lxml import html
import improve_neighborhood_pages as impl
import improve_neighborhood_phase2 as phase2
from audit_neighborhood_fees_phase4 import OUT

VERSION='20261001-v4'
REWRITE=False
FEES=re.compile(r'<section\b(?=[^>]*\bid="fees")[^>]*>.*?</section>',re.S)
DATA=impl.load(OUT/'fee-grid-verified.json')
FEES_BY_CENTER={(c['region'],c['center']):c for c in DATA['centers']}
E=impl.E
CSS='''
/* Phase 4: literal, dated branch fee originals. */
body[data-neighborhood-phase4] .ns-fee-source{padding:16px 18px;border-left:4px solid #9a4629;background:#fff5e9;margin:16px 0}
body[data-neighborhood-phase4] .ns-fee-source p{margin:0 0 8px;overflow-wrap:anywhere}
body[data-neighborhood-phase4] .ns-fee-source p:last-child{margin-bottom:0}
body[data-neighborhood-phase4] .ns-fee-table{width:100%;table-layout:fixed;border-collapse:collapse;margin:14px 0 22px;font-size:14px;line-height:1.6}
body[data-neighborhood-phase4] .ns-fee-table caption{text-align:left;font-weight:700;padding:0 0 12px;color:#493c30}
body[data-neighborhood-phase4] .ns-fee-table th,body[data-neighborhood-phase4] .ns-fee-table td{padding:12px 10px;border-bottom:1px solid #d6cbbd;text-align:left;vertical-align:top;overflow-wrap:anywhere}
body[data-neighborhood-phase4] .ns-fee-table thead th{background:#f1ebe2;color:#47392e}
body[data-neighborhood-phase4] .ns-fee-table th:first-child{width:44%}
body[data-neighborhood-phase4] .ns-fee-table th:last-child{width:24%}
body[data-neighborhood-phase4] .ns-fee-table small{display:block;font-size:12px;line-height:1.6;color:#61554b;margin-top:4px}
body[data-neighborhood-phase4] .ns-fee-table td:last-child{font-weight:700}
body[data-neighborhood-phase4] #fees details{padding:14px 0;border-bottom:1px solid #d6cbbd}
body[data-neighborhood-phase4] #fees summary{cursor:pointer;font-weight:700;font-size:18px;line-height:1.6}
body[data-neighborhood-phase4] #fees summary:focus-visible{outline:3px solid #9a4629;outline-offset:4px}
body[data-neighborhood-phase4] #fees .ns-fee-terms{font-size:14px;line-height:1.8;color:#5d5045}
@media(max-width:760px){body[data-neighborhood-phase4] .ns-fee-table{font-size:13px}body[data-neighborhood-phase4] .ns-fee-table th,body[data-neighborhood-phase4] .ns-fee-table td{padding:10px 6px}body[data-neighborhood-phase4] .ns-fee-table th:first-child{width:40%}body[data-neighborhood-phase4] .ns-fee-table th:last-child{width:25%}body[data-neighborhood-phase4] .ns-fee-source{padding:14px}}
'''

def selected_rows(row,center,source):
    wanted=[s for s in impl.subjects_for(row) if s in ['영어','수학']]
    selected=[];seen=set()
    for record in source['rows']:
        if row.get('stage') and record['stage']!=row['stage']:continue
        if not any(s in wanted for s in record['subjects']):continue
        # A combined name is retained whole; do not split its amount into
        # individual subjects or attach a parent venue's price to W+.
        if any(phase2.restricted({**row,'subject':s,'stage':record['stage']},center) for s in record['subjects']):continue
        if not any(any(g.startswith(record['stage'][0]) for g in center['subjects'].get(s,[])) for s in record['subjects'] if s in wanted):continue
        key=(record['courseKey'],record['period'],record['totalTime'],record['totalFee'],record['printedDate'])
        if key in seen:continue
        selected.append(record);seen.add(key)
    return selected

def source_note(source):
    dates=' · '.join(source['sourceDates']) or '기준일 확인 필요'
    return '<div class="ns-fee-source" data-fee-file="'+E(source['fileId'])+'">'+impl.paragraph('제공된 교습비 원문 기준일: '+dates)+impl.paragraph('원문 자료: '+source['sourceTitle'])+impl.paragraph('이 자료의 금액은 게시 당시의 안내입니다. 현재 적용 금액과 모집 여부는 지점 상담에서 확인해 주세요.')+'</div>'

def table(stage,records,opened):
    markup='<details'+(' open' if opened else '')+' data-fee-stage="'+stage+'"><summary>'+stage+' 과정의 원문 기재 항목</summary><table class="ns-fee-table"><caption>교습과목명·기간·총 교습시간은 원문 표기 · 총교습비 단위: 원</caption><thead><tr><th scope="col">교습과목명</th><th scope="col">기간·총 교습시간</th><th scope="col">총교습비</th></tr></thead><tbody>'
    for record in records:
        markup+='<tr data-fee-page="'+str(record['page'])+'" data-fee-course="'+E(record['courseKey'])+'"><th scope="row">'+E(record['course'])+'</th><td>'+E(record['period'])+'<small>총 교습시간 '+E(record['totalTime'])+'<br>원문 표의 시간 단위 미기재</small></td><td>'+format(record['totalFee'],',')+'원<small>'+E(record['printedDate'])+' 기준<br>원문 '+str(record['page'])+'쪽</small></td></tr>'
    return markup+'</tbody></table></details>'

def transform(entry):
    row,center=entry;source=FEES_BY_CENTER[center['region'],center['routeName']]
    name=row['path'].strip('/')+'/index.html';path=impl.ROOT/name
    before=path.read_bytes();text=before.decode('utf-8');doc=html.document_fromstring(before)
    if doc.xpath('//body/@data-neighborhood-phase4')==[VERSION] and not REWRITE:return {'path':row['path'],'role':row['role'],'changed':False}
    old=impl.byid(doc,'fees');assert old is not None and not old.xpath('.//section'),name
    guard=impl.protect(doc);original_links=old.xpath('.//a/@href')
    body=source_note(source);records=[]
    if row['role'] in ['enrollment','center-hub']:
        records=selected_rows(row,center,source)
        if records:
            body+=impl.paragraph('아래는 원문에서 대조한 영어·수학 관련 일반 과정 일부입니다. 현재 안내 학년과 관련된 항목만 표시하며, 원문에 등록된 모든 과정이 현재 모집 중이라는 뜻은 아닙니다.')
            for index,stage in enumerate(s for s in ['초등','중등','고등'] if any(record['stage']==s for record in records)):
                body+=table(stage,[record for record in records if record['stage']==stage],index==0)
            body+='<p class="ns-fee-terms">과정명 뒤의 숫자·기호만으로 주당 횟수를 판단하지 마세요. 총 교습시간과 회당 시간은 다르므로 수업 횟수·회당 시간을 함께 확인해 주세요. 여러 과목이 함께 적힌 과정의 포함 과목과 금액 적용 방식은 상담에서 확인해 주세요. 실력향상·기초·심화 등의 추가 과정과 비용은 원문에서 함께 확인하세요.</p>'
        else:
            body+=impl.paragraph('이 페이지에서 금액을 확정해 안내할 수 있는 일반 과정 항목은 확인이 필요합니다. 원문의 추가 과정 금액을 전체 수업료로 사용하지 않고, 희망 과목·학년의 수업 횟수·회당 시간·최종 금액을 함께 문의해 주세요.')
    elif row['role']=='overview':
        body+=impl.paragraph(center['routeName']+'의 과목별 안내 학년을 먼저 확인한 뒤, 지점 수강 안내에서 원문의 과정명·기간·교습비를 비교해 주세요.')
    elif row['role']=='study-guide':
        body+=impl.paragraph('학생 답안 점검 뒤 수업 조건을 알아볼 때는 '+center['routeName']+' 수강 안내의 원문 기준일과 과정명을 함께 확인해 주세요.')
    else:
        body+=impl.paragraph('수업을 비교할 때는 같은 학년·과목과 기간을 기준으로 원문의 교습시간·총교습비를 확인하세요. 추가 과정이 포함되는지도 따로 질문해 주세요.')
    actions=impl.node('<div class="ns-link-grid"></div>')
    for anchor in old.xpath('.//a'):actions.append(copy.deepcopy(anchor))
    if source['feeLink'] not in original_links:
        actions.append(impl.node('<a class="ns-link" href="'+E(source['feeLink'])+'" target="_blank" rel="noopener noreferrer">'+E(center['routeName'])+' 교습비 원문 PDF 보기</a>'))
    for anchor in actions.xpath('.//a[contains(@href,"drive.google.com/file/")]'):anchor.text=center['routeName']+' 교습비 원문 PDF 보기'
    body+=html.tostring(actions,encoding='unicode')
    new=impl.section('fees',center['routeName']+' 교습비 원문과 확인할 수업 조건',body)
    for ident in old.xpath('.//*[@id]/@id'):
        if not new.xpath('.//*[@id=$id]',id=ident):new.append(impl.node('<span class="cl-legacy-anchor" id="'+E(ident)+'"></span>'))
    assert all(link in new.xpath('.//a/@href') for link in original_links),name
    if row['role']=='center-hub':new.set('data-fee-hub','true')
    section=html.tostring(new,encoding='unicode',method='html')
    matches=list(FEES.finditer(text));assert len(matches)==1,name
    text=text[:matches[0].start()]+section+text[matches[0].end():]
    if 'data-neighborhood-phase4=' not in text:
        text,count=re.subn(r'<body\b([^>]*)>',lambda m:'<body'+m[1]+' data-neighborhood-phase4="'+VERSION+'">',text,count=1);assert count==1
    text=text.replace('공통 참고표의 금액을 지점 확정 교습비로 판단하지 말고 교습비 자료와 상담 답변을 비교합니다.','원문 게시일을 확인하고 자료의 과정명·기간·교습시간과 상담에서 받은 최종 금액을 비교합니다.')
    def date_script(match):
        data=json.loads(match[2]);changed=False
        for node in data.get('@graph',[]):
            if node.get('@type') in ['WebPage','CollectionPage','Article'] and node.get('dateModified')!='2026-10-01':node['dateModified']='2026-10-01';changed=True
        return match[1]+(json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c') if changed else match[2])+match[3]
    text=re.sub(r'(<script\b[^>]*type="application/ld\+json"[^>]*>)(.*?)(</script>)',date_script,text,flags=re.S)
    # Existing visible revision note is kept factual about source dates.
    text=re.sub(r'(<p\b[^>]*class="[^"]*(?:cl-revised|bc-updated)[^"]*"[^>]*>).*?(</p>)',r'\g<1>내용 수정 2026.10.01 · 센터 자료 대조 2026.09.30 · 교습비 원문 확인 2026.10.01 · 현재 모집 여부와 최종 수업 구성은 지점에 확인해 주세요.\g<2>',text,flags=re.S)
    payload=text.encode('utf-8');after=html.document_fromstring(payload);assert impl.protect(after)==guard,name
    pending=path.with_name('index.html.phase4-tmp');fallback=False
    try:
        pending.write_bytes(payload);pending.replace(path)
    except PermissionError:
        assert name=='전국센터/이곡동/초등영어학원/index.html' and (OUT/'phase3-before-phase4.zip').exists()
        with path.open('r+b') as stream:stream.seek(0);stream.write(payload);stream.truncate();stream.flush()
        if pending.exists():pending.unlink()
        fallback=True
    assert path.read_bytes()==payload
    return {'path':row['path'],'role':row['role'],'changed':True,'feeRows':len(records),'sourceFile':source['fileId'],'handleWrite':fallback}

def main():
    global REWRITE
    parser=argparse.ArgumentParser();parser.add_argument('--sample',action='store_true');parser.add_argument('--all',action='store_true');parser.add_argument('--rewrite',action='store_true');args=parser.parse_args();assert args.sample or args.all;REWRITE=args.rewrite
    assert (OUT/'phase3-before-phase4.zip').exists() and DATA['gridValidation']['errors']==[]
    entries=[(r,impl.CENTERS[tuple(r['centerKey'])]) for r in impl.inventory()]
    entries.extend(({'path':impl.center_path(c),'role':'center-hub','neighborhood':c['routeName']},c) for c in impl.FACTS['centers'])
    if args.sample:entries=[entry for entry in entries if entry[1]['routeName'] in ['명일점','내발산점','삼각산점','돈암점','불당점','수지점','침산점']]
    results=[]
    with ThreadPoolExecutor(max_workers=8) as pool:
        for index,result in enumerate(pool.map(transform,entries),1):
            results.append(result)
            if index%1000==0:print('Updated source-dated fee guidance',index,flush=True)
    path=impl.ROOT/'assets/neighborhood-seo/local.css';raw=path.read_bytes()
    if b'/* Phase 4:' not in raw:path.write_bytes(raw+CSS.encode('utf-8'))
    # Phase 3 already uses today's lastmod on locals. Only newly changed
    # center hubs can require an update, without disturbing sitemap order.
    path=impl.ROOT/'sitemap.xml';text=path.read_text('utf-8');changed_paths={r['path'] for r in results}
    def sitemap_block(match):
        block=match[0];loc=re.search(r'<loc>(.*?)</loc>',block)
        if loc and impl.unquote(impl.urlsplit(loc[1]).path) in changed_paths:
            if '<lastmod>' in block:block=re.sub(r'<lastmod>.*?</lastmod>','<lastmod>2026-10-01</lastmod>',block)
            else:block=block.replace('</url>','<lastmod>2026-10-01</lastmod></url>')
        return block
    after=re.sub(r'<url>.*?</url>',sitemap_block,text,flags=re.S)
    if after!=text:path.write_bytes(after.encode('utf-8'))
    result={'version':VERSION,'scope':'all' if args.all else 'sample','pages':results,'roles':dict(Counter(r['role'] for r in results)),'changedPagesThisRun':sum(r['changed'] for r in results),'deployed':False,'urlsDeleted':0}
    impl.dump(OUT/('implementation.json' if args.all else 'sample.json'),result)
    print(json.dumps({k:v for k,v in result.items() if k!='pages'},ensure_ascii=False))

if __name__=='__main__':main()
