"""Record only verified local FAQ results and this site's handoff."""
from pathlib import Path
from collections import Counter
import ast,hashlib,json,shutil,subprocess,zipfile
import improve_neighborhood_pages as impl
from audit_neighborhood_phase5 import OUT,PRIOR,BACKUP

FOLDER=Path(r'C:\Users\1992k\Desktop\홈페이지 작업 폴더\00_프로젝트 인수인계\코칭학원.com')
AUTHOR=Path(r'C:\Users\1992k\Desktop\홈페이지 작업 폴더\홈페이지 정리\새 홈페이지3')
TITLE='## 2026-10-01 — 5차 역할별 FAQ 개선 완료, 운영 미배포'

def original_state():
    def git(*args):return subprocess.run(['git',*args],cwd=AUTHOR,capture_output=True,check=True).stdout.decode('utf-8')
    status=git('status','--porcelain=v1').splitlines();expanded=git('status','--porcelain=v1','--untracked-files=all').splitlines()
    state={'head':git('rev-parse','HEAD').strip(),'statusEntries':len(status),'stagedEntries':sum(line[0] not in [' ','?'] for line in status),'expandedUntrackedStatusEntries':len(expanded)}
    before=impl.load(OUT/'original-source-state.json');assert state==before
    impl.dump(OUT/'original-source-state-final.json',state)
    return state

def main():
    check=impl.load(OUT/'validation.json');site=impl.load(OUT/'all-site-validation.json');build=impl.load(OUT/'build-verification.json');responsive=impl.load(OUT/'responsive-checks.json');interactions=impl.load(OUT/'interaction-checks.json');next_audit=impl.load(OUT/'next-link-audit.json')
    assert check['errors']==site['errors']==build['errors']==[]
    assert check['changedHtmlPages']==8355 and check['neighborhoodPages']==8162 and check['centerHubs']==193 and check['questions']==41775
    assert check['faqSchemasMatchingVisibleContent']==check['faqBeforeOriginalImages']==check['feeAnswersWithSourceDateContext']==8355
    assert len(responsive)==len({(r['case'],r['width']) for r in responsive})==40
    assert Counter(r['case'] for r in responsive)==Counter({i:4 for i in range(10)})
    assert all(r['openCount']==5 and r['closedOpenCount']==0 and r['scrollWidth']<=r['width'] and not r['overflows'] and r['faqBeforeImages'] for r in responsive)
    assert all(interactions[k] for k in ['pointerOpen','pointerCloseVerified','feeAnchorClicked','viewportReset','previewTabClosed'])
    assert impl.load(OUT/'diff-check.json')['exitCode']==0
    sha=hashlib.sha256((impl.ROOT/'release-public-manifest.json').read_bytes()).hexdigest()
    assert build['reviewedManifestSha256']==sha and build['publicFiles']==10622 and build['htmlPages']==8403 and build['privateSourceFiles']==0
    state=original_state()
    scripts=[p for p in (impl.ROOT/'tools').glob('*phase5.py')]
    for p in scripts:ast.parse(p.read_text('utf-8'))
    text=f'''코칭학원.com — 5차 역할별 FAQ 개선
상태: 로컬 전체 검증 완료 / 운영 미배포
사용자 지시: 기존 URL을 보존하며 순차 개선합니다. 배포는 마지막에 수행합니다.

변경 내용
- 371개 동네의 8,162페이지와 기존 지점 안내 193개, 합계 8,355페이지를 개선했습니다. URL 삭제·통합·리디렉션·색인 정책 변경 없음.
- 각 페이지에 질문 5개를 제공합니다. 수강 안내는 학년·주소·준비 자료·운영 참고 조건·교습비를, 학습 점검은 과목·학년별 답안 점검과 재확인을, 비교 안내는 종류별 선택 기준을 중심으로 구성했습니다. 동네 종합 안내와 지점 안내의 목적도 구분합니다.
- 영어·수학과 초등·중등·고등에 맞는 준비 자료와 답안 점검 내용을 기존 검토 입력에서 사용했습니다. 학습 점검 방법을 해당 지점의 확정 수업 방식이나 수강 성과로 표현하지 않았습니다. 학교별 시험 범위는 학생이 받은 자료를 기준으로 확인합니다.
- 센터 데이터 엑셀의 학년을 기준으로 답변합니다. 엑셀에서 지점명이 정확히 일치하지 않은 화성태안점은 기존 CSV 범위와 추가 확인 안내를 유지합니다. 수지점(W+) 과목 상담과 실제 장소 확인, 침산점 고3 마감, 석사점 세부 학년 확인 조건을 보존했습니다.
- 교습비 FAQ에 해당 지점 원문의 기준일과 PDF 연결을 제공합니다. 여러 날짜가 있는 자료는 과정별 날짜를 구분하도록 안내합니다. 게시 당시의 금액과 현재 적용 금액을 구분하며, 일반 항목을 확인하지 못한 수강 페이지는 확인 필요 안내를 유지합니다.
- FAQ를 긴 원본 이미지 앞에 배치했습니다. 답변에서 학년표·학교 준비 자료·주소/지도·교습비·관련 수강 안내로 이동할 수 있습니다. 기존 대표 이미지, 전체 본문 이미지, 지도와 사진의 순서는 그대로입니다.
- FAQPage 구조화 데이터는 실제 FAQ의 질문·답변과 정확히 일치합니다. 구조화 데이터 추가가 검색 결과의 특별 노출이나 순위를 보장한다고 주장하지 않습니다.

검증
- 전체 sitemap 8,403페이지: 변경 HTML 8,355개 / 나머지 48개 바이트 유지. FAQ 구역·FAQPage·단계 표식 외 기존 본문과 메타데이터 바이트 보존.
- 질문 41,775개 / 본문과 일치한 FAQPage 8,355개 / 원문 기준일 맥락이 있는 교습비 답변 8,355개. 원문 PDF 193개 SHA256 재확인.
- 전체 내부 링크·앵커·홈에서 도달 불가 페이지·H1 중복·확정 엑셀 불일치: 0건. meta/OG/Twitter 설명 최대 80자이며 기존 내용 보존.
- 10종 화면 × 320/390/768/1280px = 40조건 검증. 각 조건에서 답변 5개를 키보드로 펼쳤고, 질문·답변·연결 버튼 가로 넘침 없음. 마우스 열기·닫기와 교습비 바로가기 확인. 검사 뒤 화면 크기 설정 복원 및 정상 검증 탭 종료.
- release-public-build → 기존 wawa-04 통계 삽입 → 설명 후처리 → 전체 파일 바이트 대조 통과. 공개 파일 10,622개 / HTML 8,403개 / 비공개 원본 포함 0개. 기존 통계 코드 삽입 외 모든 바이트가 검토본과 같습니다.
- 최초 manifest 저장 중 메모리 부족으로 중단된 단계는 작업량을 제한하고 JSON을 스트림으로 저장하도록 바꿔 복구했습니다. 홈페이지 수정 없이 이미 완료된 전체 diff 검사 결과를 재사용했습니다. 전체 최종 공개 결과의 바이트 대조가 통과한 뒤에만 완료로 기록합니다.
- 검토 manifest SHA256: {sha}
- diff --check 종료 코드 0. 원본 작성 폴더 HEAD {state['head']}, Git 상태 {state['statusEntries']:,}개, 스테이징 0, 확장 미추적 상태 {state['expandedUntrackedStatusEntries']:,}개 유지.
- commit/push/운영 배포 없음. 네이버 수집·색인·순위·유입 증가는 아직 확인하지 않았습니다.

다음 개선
- 기존 관련 안내에서 학년 자료가 비어 있는 수강 페이지 55개로 연결되는 링크 545개를 확인했습니다. 영향 원본 페이지 233개입니다.
- 다음 단계는 이 링크에 자료상 학년 확인 필요를 표시하고, 실제 안내 학년과 준비 자료로 이어지는 경로를 다듬는 것입니다. 자료 미확인을 수업 미운영으로 바꾸지 않고 기존 URL은 모두 유지합니다. 이번 작업에서는 후보 감사만 수행했습니다.
- 이후 확인이 필요한 지점 자료를 추가 제공 범위에서 보완하고 최종 검수 후 사용자가 배포를 요청할 때 배포합니다.

파일과 재현
- phase4-before-phase5.zip: 5차 변경 전의 8,403 HTML과 검토 입력을 보존한 불변 백업. 덮어쓰지 않습니다.
- 검증자료와생성입력.zip: 5차 코드·FAQ 입력·전체 검증·화면, 현재 manifest와 센터 검토 입력, 4차 교습비 검토 입력/PDF. 비공개 작업 자료입니다.
- 압축의 tools/는 현재 분리 작업 폴더의 tools/에, inputs/는 tools/data/neighborhood-seo/에 복원합니다. phase5/는 이 5차 결과 폴더에, phase4/는 기존 site3-neighborhood-phase4-20261001 결과 폴더에 복원합니다.
- 재현은 불변 4차 백업에서 tools/improve_neighborhood_phase5.py --all을 수행합니다. --prepare는 추가 검토 입력 생성용이며 검증된 reviewed-faq.json을 사용합니다. 전체 검증 뒤 build_neighborhood_phase5.py --freeze --build로 로컬 공개 결과를 대조합니다.
- 이전 단계 생성기로 최신 본문·검토 입력·과거 증거를 덮어쓰지 않습니다.
'''
    (OUT/'작업결과.txt').write_bytes(text.replace('\n','\r\n').encode('utf-8-sig'))
    section=f'''{TITLE}

- 사용자 지시: 배포는 마지막에 수행합니다. 지금 commit/push/운영 배포 없음.
- 동네 371개 / 동네 페이지 8,162개 + 지점 안내 193개 = HTML 8,355개 개선. 페이지별 질문 5개, 총 41,775개. 기존 URL을 유지하고 수강·학습 점검·비교·동네 종합·지점 안내에 맞게 FAQ를 구분했습니다.
- 확정 엑셀 학년·실제 주소·과목별 준비 자료·교습비 원문 기준일과 현재 확인 조건을 답변에 연결했습니다. 화성태안점 CSV/확인, 수지점(W+), 침산점 고3 마감, 석사점 학년 확인 조건 유지. 일반 학습 방법을 확정 지점 서비스나 성과로 표현하지 않습니다.
- FAQ는 긴 이미지 앞에 배치하고 본문 질문·답변과 FAQPage를 일치시켰습니다. 원본 본문·지도·사진 순서·문의 링크·제목·설명·canonical·색인 정책 유지.
- 전체 8,403페이지, 공개 10,622파일 검사 오류 0건. 48 HTML 바이트 유지, FAQ/FAQPage/단계 표식 외 기존 바이트 보존. 반응형 40조건, 키보드 펼침·마우스 열기/닫기·교습비 바로가기 확인. 로컬 배포 결과의 통계·설명 후처리까지 검토본과 일치.
- [최신 작업결과](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase5-20261001/작업결과.txt>) / [검증자료와생성입력](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase5-20261001/검증자료와생성입력.zip>) / [변경 전 백업](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase5-20261001/phase4-before-phase5.zip>).
- 최신 manifest SHA256 `{sha}`. 원본 작성 폴더 상태 유지. 네이버 수집·색인·순위·유입은 검증하지 않았습니다.
- 다음 개선 후보: 학년 자료 미확인 수강 페이지 55개로 연결되는 545개 링크(233개 원본 페이지)의 확인 문구 보완. 운영하지 않는다는 의미로 단정하지 않으며 URL 보존. 다음 후보 감사만 완료, 개선은 후속 단계입니다.
- tools/improve_neighborhood_phase5.py와 reviewed-faq.json 사용. 전체 검증 코드 validate_neighborhood_phase5.py, build_neighborhood_phase5.py, report_neighborhood_phase5.py. 복원/재현은 작업결과.txt 참고. 이전 생성기로 최신 검토본을 되돌리지 않습니다.

'''
    for path in [impl.ROOT/'NEIGHBORHOOD_SEO_HANDOFF.md',FOLDER/'PROJECT_HANDOFF.md']:
        value=path.read_text('utf-8')
        if TITLE in value:continue
        if path.name=='PROJECT_HANDOFF.md':value=value.replace(value.splitlines()[2],'최신 갱신: 2026-10-01. 5차 역할별 FAQ 개선을 반영했습니다. 사용자 지시대로 배포는 마지막에 수행합니다. 현재는 전체 검증된 로컬 개선본이며 네이버 검색 성과는 별도 확인 대상입니다.',1)
        index=value.find('\n## ');assert index>0
        path.write_text(value[:index]+'\n\n'+section+value[index+1:],'utf-8')
    path=FOLDER/'CHANGELOG.md';value=path.read_text('utf-8')
    if TITLE not in value:path.write_text(value.rstrip()+'\n\n'+section,'utf-8')
    destination=OUT/'검증자료와생성입력.zip';included={}
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED,compresslevel=5) as archive:
        def add(path,name):
            archive.write(path,name);included[name]=hashlib.sha256(path.read_bytes()).hexdigest()
        for path in OUT.iterdir():
            if path.is_file() and path.suffix in ['.json','.jpg','.png','.txt','.log'] and path.name not in ['diff-check-output.txt','archive-verification.json']:add(path,'phase5/'+path.name)
        for path in scripts:add(path,'tools/'+path.name)
        for path in impl.DATA.glob('*.json'):add(path,'inputs/'+path.name)
        add(PRIOR/'fee-grid-verified.json','phase4/fee-grid-verified.json')
        for path in (PRIOR/'source-pdfs').glob('*.pdf'):add(path,'phase4/source-pdfs/'+path.name)
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        for name,sha256 in included.items():assert hashlib.sha256(archive.read(name)).hexdigest()==sha256,name
    result={'archiveBytes':destination.stat().st_size,'archiveFiles':len(included),'archiveSha256':hashlib.sha256(destination.read_bytes()).hexdigest(),'crcAndMemberHashesVerified':True,'backupBytes':BACKUP.stat().st_size,'backupSha256':impl.load(OUT/'before-faq-audit.json')['backupSha256'],'deployed':False}
    assert hashlib.sha256(BACKUP.read_bytes()).hexdigest()==result['backupSha256']
    impl.dump(OUT/'archive-verification.json',result);print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
