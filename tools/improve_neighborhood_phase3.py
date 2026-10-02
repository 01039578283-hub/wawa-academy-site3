"""Source-backed school preparation and reviewed branch-picture captions.

Transform the second reviewed release in place. Reusable detailed answer
checks live on the existing learning-management URL. No URLs, image sources,
contact targets, grading policies or enrollment promises are added/removed.
"""
from collections import Counter
import argparse, json, re, zipfile, hashlib
from lxml import html, etree
import improve_neighborhood_pages as impl
import improve_neighborhood_phase2 as phase2
from audit_neighborhood_phase3 import OUT

VERSION='20261001-v3'
DAY='2026-10-01'
KINDS={'초등':'초등학교','중등':'중학교','고등':'고등학교'}
PREP={
    '초등학교':'현재 읽기 자료·연산장, 아이가 혼자 푼 답안',
    '중학교':'학교 진도표·최근 평가와 서술형 답안',
    '고등학교':'현재 이수 과목·학교 교재와 최근 시험지',
}
CAPTION_TYPES={
    'E':'출입문과 안내 표지', 'C':'책상과 가림판이 놓인 학습 공간',
    'B':'지점 간판이 보이는 건물 외관', 'D':'사진에 담긴 학습 기록 자료',
    'L':'책장과 자료 보관 공간', 'F':'안내 데스크와 실내 공간',
    'N':'사진에 담긴 문서·안내 자료', 'T':'안내 기기와 비치 자료',
    'R':'테이블이 놓인 실내 공간', 'H':'복도와 출입문',
    'M':'지점 실내 모습', 'W':'벽면 장식과 게시 자료',
    'P':'책상에서 학습 자료를 살펴보는 모습',
    'V':'비치된 교재와 노트', 'S':'사진에 담긴 비치 물품',
}
# Captions are based on all eight contact sheets, reviewed visually. Describe
# visible objects only: no current timetables, results, awards or capacity claims.
CAPTION_CODES={
    '삼각산점':'HEFN','신방화점':'CCFC','염창점':'CCCC','광장점':'BBNT',
    '금천점':'CCCD','하계점':'ENNN','제기점':'MFCC','마포2호점':'DDDD',
    '상암점':'NT EP'.replace(' ',''),'가좌점':'DNDD','돈암점':'RCFR','종암점':'CFCC',
    '당산점':'DVDV','은평점':'RCDC','마두점':'CCBB','원흥점':'CBCC',
    '탄현점':'EFBC','풍동점':'E','행신점':'L CCT'.replace(' ',''),'철산점':'ENMD',
    '탄벌점':'NNBC','갈매점':'CCMC','산본점':'NBNB','운양점':'CBHD',
    '다산도농점':'BCBC','별내점':'C SFB'.replace(' ',''),'별내중앙점':'LN EH'.replace(' ',''),'퇴계원점':'D PMD'.replace(' ',''),
    '평내점':'FFWW','반달점':'CHNF','범박점':'CFCD','옥길점':'CRCR',
    '단대점':'FBCC','미금점':'ENCB','수진점':'FBBF','야탑점':'BBNP',
    '이매점':'LCCC','영통구청점':'CBBD','천천점':'RCE N'.replace(' ',''),'호매실점':'CPBT',
    '목감점':'CBCC','장곡점':'DEND','옥정점':'CCCS','세교점':'DHBC',
    '오산점':'PD','기흥구청점':'PLCB','보라점':'CCCE','상현점':'TDWC',
    '수지점':'PDHN','신봉점':'CCNH','용인백현점':'TCCC','흥덕점':'BBCF',
    '갈산점':'NMCH','교하점':'EHHR','산내점':'DDCB','운정점':'FCCD',
    '운정호수점':'CCMB','비전점':'FDDC','이충점':'CCCD','미사점':'NNLE',
    '센트럴점':'CCCP','하남풍산점':'DCEN','동탄목동점':'TCHL','동탄호수점':'CEMF',
    '구월점':'B','부평점':'WE RC'.replace(' ',''),'인천삼산점':'ERBD','동춘점':'CCD',
    '웰카운티점':'CBCC','관저점':'ENBP','둔산점':'BNNS','태평점':'BBCH',
    '개신점':'EHHC','복대점':'CCBF','산남점':'BC','칠금점':'CBEH',
    '대구장기점':'ECCC','신월성점':'CRHC','진천점':'BBBH','남외점':'BCCB',
    '동래점':'C','사직점':'CFEB','반여점':'CDDH','좌동점':'CCCD',
    '거제수월점':'BBCC','사동점':'BBBB','상남점':'ERRC','석동점':'ERCF',
    '두호점':'NDCC','첨단점':'CCF','전주혁신점':'RED','노형점':'LHMC',
    '송파위례점':'PCDN','다산지금점':'CCCC','별가람점':'TNCC','위례창곡점':'FENN',
}

def profile_anchor(stage,subject):
    return 'answer-'+{'초등':'elementary','중등':'middle','고등':'high'}[stage]+'-'+{'영어':'english','수학':'math'}[subject]

def write_document(path,doc,guard):
    serialized=html.tostring(doc,encoding='unicode',method='html',doctype='<!DOCTYPE html>')+'\n'
    serialized=re.sub(r'\r+\n','\n',serialized).replace('\r','')
    # lxml serializes Korean href values as percent-encoded URI attributes.
    # Preserve the exact pre-existing canonical representation as well.
    canonical=guard['canonical'][0]
    serialized=re.sub(r'<link\b(?=[^>]*\brel="canonical")[^>]*>', lambda match:re.sub(r'href="[^"]*"',lambda _: 'href="'+impl.E(canonical)+'"',match[0]),serialized)
    assert impl.protect(html.document_fromstring(serialized))==guard
    if path.read_text('utf-8')!=serialized:
        try:impl.write_page(path,serialized)
        except PermissionError:
            # This previously documented Windows file permits writes through
            # an existing handle but rejects replacement. Keep the ACL intact.
            assert path.relative_to(impl.ROOT).as_posix()=='전국센터/이곡동/초등영어학원/index.html'
            before=path.read_bytes();payload=serialized.encode('utf-8')
            assert impl.protect(html.document_fromstring(before))==guard
            if not (OUT/'이곡동-초등영어-변경전.html').exists():
                (OUT/'이곡동-초등영어-변경전.html').write_bytes(before)
            with path.open('r+b') as stream:
                stream.seek(0);stream.write(payload);stream.truncate();stream.flush()
            assert path.read_bytes()==payload
            pending=path.with_name('index.html.neighborhood-tmp')
            assert pending.resolve().is_relative_to(impl.ROOT.resolve())
            if pending.exists():pending.unlink()
            impl.dump(OUT/'write-recovery.json',{'path':path.relative_to(impl.ROOT).as_posix(),'originalSha256':hashlib.sha256(before).hexdigest(),'verifiedSha256':hashlib.sha256(payload).hexdigest(),'protectedFieldsPreserved':True,'ACLUnchanged':True})

def school_rows(row,center):
    match=next((item for item in center['schoolAreas'] if impl.norm(item['neighborhood'])==impl.norm(row['neighborhood'])),None)
    assert match is not None, (row['path'],'No exact neighborhood school source')
    kinds=[KINDS[row['stage']]] if row.get('stage') else list(KINDS.values())
    return [(kind,list(dict.fromkeys(match['schools'].get(kind,[])))) for kind in kinds]

def schools_body(row,center):
    # Keep the full exact school list, rather than the previous five-name cap.
    body=impl.paragraph('센터 안내 자료에 기재된 상담 참고 학교입니다. 학교별 전용반·제휴·현재 시험 범위를 뜻하지 않으므로 재학 학교에서 받은 자료를 준비해 주세요.')
    body+='<div class="ns-school-grid">'
    for kind,names in school_rows(row,center):
        body+='<article data-school-kind="'+kind+'"><h3>'+kind+'</h3>'
        if names:
            body+='<ul class="ns-school-names">'+''.join('<li>'+impl.E(name)+'</li>' for name in names)+'</ul>'
        else: body+=impl.paragraph('이 학교급의 참고 학교는 자료에 기재돼 있지 않습니다. 재학 학교 이름과 현재 진도를 전달해 주세요.')
        body+='<p class="ns-preparation"><strong>준비할 자료</strong> '+impl.E(phase2.materials(row,center) if row.get('stage') and row.get('subject') else PREP[kind])+'</p>'
        stage=next(stage for stage,value in KINDS.items() if value==kind)
        body+='<dl class="ns-school-grades">'
        for subject in impl.subjects_for(row):
            grades=[grade for grade in center['subjects'][subject] if grade.startswith(stage[0])]
            body+='<div data-school-subject="'+subject+'"><dt>'+subject+' 안내 학년</dt><dd>'+impl.E(impl.pretty(grades))+'</dd></div>'
        body+='</dl></article>'
    body+='</div>'+impl.paragraph('안내 학년은 '+phase2.authority(center)+' 기준이며, 현재 모집 자리·반 편성·수업 시간은 별도로 확인합니다.')
    return body

def photo_data():
    audit=impl.load(OUT/'photo-audit.json'); result={}
    for entry in audit['entries']:
        key=(entry['region'],entry['center'])
        if entry['mode']=='center':
            codes=CAPTION_CODES[entry['center']]
            assert len(codes)==len(entry['photos']), (key,len(codes),len(entry['photos']))
            result[key]={photo['src']:{**photo,'caption':entry['center']+' — '+CAPTION_TYPES[code]} for code,photo in zip(codes,entry['photos'])}
        else: result[key]={}
    assert len(CAPTION_CODES)==96
    return result

def caption_photos(doc,center,reviewed):
    block=impl.byid(doc,'learning-space'); assert block is not None
    if center['photoMode']=='common':return 0
    heading=block.xpath('.//h2')[0];heading.text=center['routeName']+' 제공 사진'
    wrapper=heading.getparent()
    if not wrapper.xpath('./p[@class="ns-photo-source"]'):
        p=impl.node(impl.paragraph('지점별로 제공된 사진입니다. 건물·공간·학습 자료를 구분해 설명했으며, 사진 속 일정·기록은 현재 운영 조건이나 성적 향상 결과를 뜻하지 않습니다.'))
        p.set('class','ns-photo-source');wrapper.insert(wrapper.index(heading)+1,p)
    count=0
    for image in block.xpath('.//img[@data-role="space-image"]'):
        value=reviewed[image.get('src')];image.set('alt',value['caption'].replace(' — ',' '))
        figure=image.getparent();assert figure.tag=='figure'
        captions=figure.xpath('./figcaption');assert len(captions)<=1
        caption=captions[0] if captions else etree.SubElement(figure,'figcaption')
        caption.text=value['caption'];caption.set('data-photo-caption','reviewed');count+=1
    return count

def trim_school_repetition(doc,ident,school_id,row):
    block=impl.byid(doc,ident)
    if block is None:return 0
    removed=0
    for p in block.xpath('.//p'):
        if '상담 참고 학교로는' in p.text_content():p.getparent().remove(p);removed+=1
    if removed:
        block.xpath('./div')[0].append(impl.node(impl.anchor('#'+school_id,row['neighborhood']+' 학교 목록·준비 자료 보기')))
    return removed

def shared_guides():
    path=impl.ROOT/'학습관리/index.html';doc=html.document_fromstring(path.read_bytes())
    if doc.xpath('//body/@data-neighborhood-phase3')==[VERSION]:
        with zipfile.ZipFile(OUT/'phase2-before-phase3.zip') as archive:guard=impl.protect(html.document_fromstring(archive.read('학습관리/index.html')))
        current=impl.protect(doc)
        assert {key:value for key,value in current.items() if key!='canonical'}=={key:value for key,value in guard.items() if key!='canonical'}
        doc.xpath('//link[@rel="canonical"]')[0].set('href',guard['canonical'][0])
        write_document(path,doc,guard)
        return False
    guard=impl.protect(doc);main=doc.xpath('//main')[0];body=impl.paragraph('학생이 직접 남긴 답안으로 학습 상태와 상담 답변을 비교하는 점검 방법입니다. 아래 내용은 지점의 실제 수업 방식이나 수강 사례를 뜻하지 않습니다.')
    body+='<nav class="ns-link-grid" aria-label="학년별 답안 점검">'
    for stage,subject in [(stage,subject) for stage in KINDS for subject in ['영어','수학']]:
        body+=impl.anchor('#'+profile_anchor(stage,subject),stage+' '+subject)
    body+='</nav><div class="ns-shared-checks">'
    for stage,subject in [(stage,subject) for stage in KINDS for subject in ['영어','수학']]:
        lead,checks=impl.GUIDE_CHECKS[stage+'-'+subject]
        body+='<details id="'+profile_anchor(stage,subject)+'"><summary>'+stage+' '+subject+' 답안으로 확인할 질문</summary><div class="ns-shared-content">'+impl.paragraph(lead)
        body+=impl.paragraph('준비할 자료: '+impl.PROFILES[stage+'-'+subject]['materials'])
        body+='<div class="ns-check-grid">'+''.join('<article><h3>'+impl.E(title)+'</h3>'+impl.paragraph(text)+'</article>' for title,text in checks)+'</div></div></details>'
    body+='</div>'
    section=impl.section('student-answer-checks','학년·과목별 학생 답안 점검',body)
    main.insert(main.index(impl.byid(doc,'faq')),section)
    doc.xpath('//body')[0].set('data-neighborhood-phase3',VERSION)
    if not doc.xpath('//link[@href="/assets/neighborhood-seo/local.css"]'):
        doc.xpath('//head')[0].append(impl.node('<link rel="stylesheet" href="/assets/neighborhood-seo/local.css">'))
    set_dates(doc)
    assert impl.protect(doc)==guard
    write_document(path,doc,guard)
    return True

def set_dates(doc):
    for note in doc.xpath('//main/p[contains(@class,"cl-revised") or contains(@class,"bc-updated")]'):
        note.text='내용 수정 2026.10.01 · 센터 자료 대조 2026.09.30 · 현재 모집 여부와 최종 수업 구성은 지점에 확인해 주세요.'
        for child in list(note):note.remove(child)
    for script in doc.xpath('//script[@type="application/ld+json"]'):
        data=json.loads(script.text)
        graph=data.get('@graph',[]) if isinstance(data,dict) else []
        for node in graph:
            if node.get('@type') in ['WebPage','CollectionPage','Article']:node['dateModified']=DAY
        script.text=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')

def transform(row,reviewed):
    path=impl.ROOT/row['path'].strip('/')/'index.html';doc=html.document_fromstring(path.read_bytes())
    if doc.xpath('//body/@data-neighborhood-phase3')==[VERSION]:
        before=path.read_text('utf-8');guard=impl.protect(doc)
        center=impl.CENTERS[tuple(row['centerKey'])]
        caption_photos(doc,center,reviewed[tuple(row['centerKey'])])
        after=html.tostring(doc,encoding='unicode',method='html',doctype='<!DOCTYPE html>')+'\n'
        assert impl.protect(doc)==guard
        if before!=after:write_document(path,doc,guard)
        return None
    guard=impl.protect(doc);center=impl.CENTERS[tuple(row['centerKey'])];main=doc.xpath('//main')[0]
    school_id='schools' if impl.byid(doc,'schools') is not None else 'center-schools'
    assert impl.byid(doc,school_id) is not None
    impl.replace_section(doc,school_id,row['neighborhood']+' 학교별 준비 자료와 안내 학년',schools_body(row,center))
    school_block=impl.byid(doc,school_id);image_block=impl.byid(doc,'page-images')
    main.remove(school_block);main.insert(main.index(image_block),school_block)
    removed=sum(trim_school_repetition(doc,ident,school_id,row) for ident in ['subject-learning','grade-learning','consultation-prep','consult-checklist','student-fit'])
    relocated=0
    if row['role']=='study-guide':
        # Full question explanations are retained once on /학습관리/, while
        # the three immediately useful answer scenarios stay on each local URL.
        profile=profile_anchor(row['stage'],row['subject'])
        content=impl.paragraph(row['neighborhood']+' '+row['stage']+' '+row['subject']+' 답안을 아래 세 상황과 비교하고, 학교 자료에서 먼저 확인할 부분을 골라 보세요.')
        content+='<dl class="ns-local-guide-facts"><div><dt>상담에 참고할 안내 지점</dt><dd>'+impl.E(center['displayName'])+'</dd></div><div><dt>'+impl.E(row['subject'])+' 자료의 안내 학년</dt><dd>'+impl.E(impl.pretty(impl.grades_for(row,center,row['subject'])))+'</dd></div></dl>'
        content+='<div class="ns-link-grid">'+impl.anchor('/학습관리/#'+profile,row['stage']+' '+row['subject']+' 질문별 점검 방법')+impl.anchor('#'+school_id,row['neighborhood']+' 학교 자료 확인')+'</div>'
        impl.replace_section(doc,'intent-guide','학생 답안과 학교 자료로 시작하는 점검',content)
        scenarios=impl.byid(doc,'student-fit');main.remove(scenarios);main.insert(main.index(impl.byid(doc,'intent-guide'))+1,scenarios)
        relocated=3
    elif row['role']=='overview':
        impl.replace_section(doc,'consult-checklist','상담 전에 확인할 두 가지', '<div class="ns-check-grid"><article><h3>학교와 현재 교재</h3>'+impl.anchor('#'+school_id,row['neighborhood']+' 참고 학교·준비 자료')+'</article><article><h3>희망 과목과 실제 지점</h3>'+impl.paragraph(center['displayName']+'의 안내 지점 주소는 '+center['address']+'입니다.')+impl.anchor(impl.center_path(center),'과목별 학년·교습비·운영 조건 확인')+'</article></div>')
    captions=caption_photos(doc,center,reviewed[tuple(row['centerKey'])])
    summary=impl.byid(doc,'local-summary');wrap=summary.xpath('./div')[0]
    photo_link=impl.node('<div class="ns-photo-shortcut">'+impl.anchor('#learning-space',center['routeName']+' 제공 사진 보기' if center['photoMode']=='center' else '브랜드 공통 공간 사진 보기')+'</div>')
    if center['photoMode']=='common':photo_link.append(impl.node(impl.paragraph('현재 페이지의 공간 사진은 브랜드 공통 예시입니다. 실제 지점 시설은 방문 전에 확인해 주세요.')))
    wrap.append(photo_link)
    toc=doc.xpath('//main/nav[contains(@class,"ns-toc")]')
    if toc:toc[0].append(impl.node(impl.anchor('#'+school_id,'학교·준비 자료')))
    doc.xpath('//body')[0].set('data-neighborhood-phase3',VERSION);set_dates(doc)
    assert impl.protect(doc)==guard,(row['path'],'Preserved routes/media/contact policy changed')
    write_document(path,doc,guard)
    return {'path':row['path'],'role':row['role'],'schoolNames':sum(len(names) for _,names in school_rows(row,center)), 'removedRepeatedSchoolParagraphs':removed,'relocatedDetailedQuestions':relocated,'photoCaptions':captions}

def hubs(reviewed):
    changed=[]
    for center in impl.FACTS['centers']:
        path=impl.ROOT/impl.center_path(center).strip('/')/'index.html';doc=html.document_fromstring(path.read_bytes())
        if doc.xpath('//body/@data-neighborhood-phase3')==[VERSION]:continue
        guard=impl.protect(doc);captions=caption_photos(doc,center,reviewed[(center['region'],center['routeName'])])
        if not captions:continue
        doc.xpath('//body')[0].set('data-neighborhood-phase3',VERSION);set_dates(doc)
        assert impl.protect(doc)==guard
        write_document(path,doc,guard);changed.append(impl.center_path(center))
    return changed

def update_sitemap(paths):
    tree=etree.parse(str(impl.ROOT/'sitemap.xml'));before=tree.xpath('//*[local-name()="loc"]/text()')
    for entry in tree.getroot():
        loc=entry.find('{*}loc')
        if loc is not None and impl.unquote(impl.urlsplit(loc.text).path) in paths:
            last=entry.find('{*}lastmod')
            if last is None:last=etree.SubElement(entry,'{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod')
            last.text=DAY
    assert tree.xpath('//*[local-name()="loc"]/text()')==before
    tree.write(str(impl.ROOT/'sitemap.xml'),encoding='utf-8',xml_declaration=True,pretty_print=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--sample',action='store_true');parser.add_argument('--all',action='store_true');args=parser.parse_args();assert args.sample or args.all
    assert (OUT/'phase2-before-phase3.zip').exists()
    reviewed=photo_data(); rows=impl.inventory()
    selected=rows if args.all else [row for row in rows if impl.norm(row['neighborhood']) in ['명일동','천호동','삼각산동','불당동','풍덕천동'] or row['center'] in ['침산점','화성태안점']]
    shared=shared_guides();results=[]
    for index,row in enumerate(selected,1):
        result=transform(row,reviewed)
        if result is not None:results.append(result)
        if index%1000==0:print('Phase 3 processed',index,flush=True)
    hub_paths=hubs(reviewed) if args.all else []
    changed_paths={row['path'] for row in rows if html.document_fromstring((impl.ROOT/row['path'].strip('/')/'index.html').read_bytes()).xpath('//body/@data-neighborhood-phase3')==[VERSION]}
    changed_paths.update(impl.center_path(center) for center in impl.FACTS['centers'] if center['photoMode']=='center' and args.all)
    if shared or (impl.byid(html.document_fromstring((impl.ROOT/'학습관리/index.html').read_bytes()),'student-answer-checks') is not None):changed_paths.add('/학습관리/')
    update_sitemap(changed_paths)
    result={'version':VERSION,'scope':'all' if args.all else 'sample','selectedPages':len(selected),'changedPages':len(results),'roles':dict(Counter(row['role'] for row in results)),'changedCenterHubs':len(hub_paths),'sharedGuidesUpdated':shared,'removedRepeatedSchoolParagraphs':sum(row['removedRepeatedSchoolParagraphs'] for row in results),'detailedQuestionOccurrencesRelocated':sum(row['relocatedDetailedQuestions'] for row in results),'sharedDetailedQuestions':18,'newRealPhotosAdded':0,'existingRealPicturesReviewed':368,'urlsDeleted':0,'deployed':False,'pages':results}
    impl.dump(OUT/('implementation.json' if args.all else 'sample.json'),result)
    print(json.dumps({key:value for key,value in result.items() if key!='pages'},ensure_ascii=False))

if __name__=='__main__':main()
