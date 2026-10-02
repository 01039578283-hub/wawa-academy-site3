"""Publish local review evidence only after the complete build matches hashes."""
from pathlib import Path
import json,csv,shutil,zipfile,hashlib
from lxml import html
import improve_neighborhood_pages as impl
from audit_neighborhood_fees_phase4 import OUT

FOLDER=Path(r'C:\Users\1992k\Desktop\홈페이지 작업 폴더\00_프로젝트 인수인계\코칭학원.com')

def main():
    check=impl.load(OUT/'validation.json');site=impl.load(impl.REPORT/'validation.json');build=impl.load(impl.REPORT/'build-verification.json');responsive=impl.load(OUT/'responsive-checks.json')
    assert check['errors']==site['errors']==build['errors']==[]
    assert check['neighborhoodPages']==8162 and check['centerHubs']==193 and check['changedHtmlPages']==8355
    assert build['reviewedManifestSha256']==hashlib.sha256((impl.ROOT/'release-public-manifest.json').read_bytes()).hexdigest()
    assert build['publicFiles']==10622 and build['htmlPages']==8403
    assert len(responsive)==40 and all(r['scrollWidth']<=r['width'] and not r['overflows'] and r.get('dates') and len(r['pdfLinks'])==1 for r in responsive)
    assert impl.load(OUT/'diff-check.json')['exitCode']==0
    state=impl.load(OUT/'original-source-state.json')
    assert state['head']=='e614c0bac03160ff22a019a3427ff4fbb1590478' and state['statusEntries']==5272 and state['stagedEntries']==0 and state['expandedUntrackedStatusEntries']==9683
    sources=impl.load(OUT/'fee-grid-verified.json');source_files=impl.load(OUT/'fee-pdf-audit.json')
    for name,source in [('all-site-validation.json',impl.REPORT/'validation.json'),('build-verification.json',impl.REPORT/'build-verification.json'),('release-public-manifest.json',impl.ROOT/'release-public-manifest.json')]:shutil.copyfile(source,OUT/name)
    with (OUT/'지점별교습비확인목록.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['지역','지점','원문 파일명','원문 기준일','원문 일반 항목','지점 표시 항목','금액 전재 여부','추가 확인 이유','원문 링크','PDF SHA256'])
        for source in sources['centers']:
            center=impl.CENTERS[source['region'],source['center']];doc=html.document_fromstring((impl.ROOT/impl.center_path(center).strip('/')/'index.html').read_bytes());count=len(impl.byid(doc,'fees').xpath('.//tr[@data-fee-course]'))
            reason='현재 안내 학년과 원문 항목이 일치하지 않아 금액 전재 제외' if source['rows'] and not count else ' / '.join(dict.fromkeys(source['issues']))
            writer.writerow([source['region'],source['center'],source['sourceTitle'],' / '.join(source['sourceDates']),len(source['rows']),count,'원문 기재 금액 표시' if count else '원문 확인 안내',reason,source['feeLink'],source['sourceSha256']])
    text=f'''코칭학원.com — 4차 지점 교습비 원문 안내 개선
상태: 로컬 전체 검증 완료 / 운영 미배포
사용자 지시: 개선을 순차 진행하고 배포는 마지막에 수행합니다.

변경 내용
- 371개 동네의 8,162페이지와 기존 지점 안내 193개, 합계 8,355페이지를 개선했습니다. 기존 URL 삭제·통합·리디렉션·색인 정책 변경 없음.
- 제공된 feeLink 193개에 연결된 PDF 193개 / {sum(f['pdfPages'] for f in source_files['files'])}쪽을 확보하고 SHA256으로 보존했습니다. 연결된 파일 제목에서 지점명 또는 등록 학원명을 확인했습니다. 파일 수정일을 교습비 적용일로 사용하지 않았습니다.
- PDF 텍스트 추출과 표 셀을 각각 대조한 일반 영어·수학 관련 항목 4,162개, 원문 160개 지점. 이 가운데 현재 안내 학년·장소 조건에 맞는 159개 지점에서 금액을 표시했습니다. 반복된 동일 항목은 합치되 서로 다른 원문 기준일·과정명·금액은 구분합니다.
- 일반 항목 미확인·기준일 불일치 33개 지점과 현재 학년 범위에 해당하는 항목이 없는 석사점은 금액을 전재하지 않고 원문·상담 확인 경로를 제공합니다.
- 수강 페이지에는 관련 과목·학년의 과정명, 교습기간, 원문 총 교습시간, 총교습비와 기준일·원문 쪽수를 표시합니다. 동네 종합·학습 점검·비교 페이지에는 기준일과 관련 수강 안내 경로를 제공해 역할을 유지합니다.
- 기존 지역 공통 HTML 금액표를 지점 원문 안내로 교체했습니다. 본문 이미지의 기존 공통 참고 금액은 이미지 설명과 함께 보존했습니다. 안내 금액을 현재 확정 요금으로 선언하지 않으며 Offer/가격 스키마를 새로 만들지 않았습니다.
- 과정명 뒤 숫자를 주당 횟수로 추정하지 않았습니다. 원문 총 교습시간의 단위가 미기재이므로 이를 임의로 분·회당 시간으로 바꾸지 않았습니다. 소수점 값도 원문대로 유지합니다. 실력향상·기초·심화 등의 보조 과정 금액을 전체 수업료로 사용하지 않았습니다.
- 수지점 수학의 별도 수업 장소 W+에는 본점 교습비를 연결하지 않았습니다. 사용자 확정 엑셀의 수강 학년, 침산점 고3 마감 조건, 화성태안점의 확인 안내를 유지했습니다.

검증
- 전체 sitemap 8,403페이지: 오류 0건. 변경 HTML 8,355개 / 나머지 48개 바이트 유지.
- 페이지별 원문 행 20,537회 정확 일치. fees·수정일·관련 확인 문장 외 기존 HTML 바이트 보존. URL·canonical·H1·검색 제목·meta/OG/Twitter 설명·사진 순서·크기·문의 링크 보존.
- 기존 전체 SEO 검사: 오류 0건, H1 중복 0, 끊어진 내부 링크·앵커·홈에서 도달 불가 페이지 0, 설명 최대 80자. 엑셀 192개 센터 재대조 통과.
- 화면 10종 × 320/390/768/1280px = 40조건 검증. 표·본문 가로 넘침 없음. 학년별 표 열기·닫기와 원문 연결 확인. 소수점 시간 자료는 최종 반영 뒤 누락된 4조건을 완료했습니다.
- release-public-build → 기존 wawa-04 통계 삽입 → 설명 후처리 → 전체 원문 바이트 대조 통과. 공개 파일 10,622개 / HTML 8,403개 / 비공개 원본 포함 0개. 기존 통계 코드 삽입 외 모든 바이트가 검토본과 같습니다.
- 검토 manifest SHA256: {build['reviewedManifestSha256']}
- diff --check 종료 코드 0. 원본 작성 폴더 HEAD·5,272개 Git 상태·스테이징 0·확장 미추적 9,683개 상태 유지.
- commit/push/운영 배포 없음. 로컬 검증은 네이버 색인·상위 노출·유입 증가를 확인한 결과가 아닙니다.

다음 개선
- 후속 점검에서 동네 8,162페이지의 교육비 FAQ 답변이 모두 같은 문장이고 원문 기준일 맥락이 없는 것을 확인했습니다. 이번 교습비 본문 개선과 별개로 남은 후속 범위입니다.
- 동네·과목·학년과 페이지 역할에 맞는 FAQ 질문·답변을 정밀하게 다듬고, 이번에 대조한 지점 학년·주소·교습비 자료와 해당 학교 준비 자료를 답변에 연결합니다. 수강 안내, 학습 점검, 비교 안내의 질문을 구분하면서 기존 URL을 유지합니다.
- 자료가 더 필요한 지점의 현재 적용 교습비·실제 사진·화성태안점 학년 기준은 제공된 추가 자료가 확인되는 범위에서 보완합니다. 배포는 사용자 지시대로 마지막 단계에 둡니다.

파일과 재현
- 지점별교습비확인목록.csv: 193개 원문 및 지점별 금액 전재 여부.
- phase3-before-phase4.zip: 변경 전 검토본의 불변 백업. 덮어쓰지 않습니다.
- 검증자료와생성입력.zip: 4차 코드, 전체 원문 PDF, 추출·표 대조 입력, 전체 검증과 화면 증거, 기존 검토 입력과 최신 manifest.
- ZIP의 phase4/를 이 결과 폴더에, tools/를 현재 분리 작업 폴더의 tools/에, inputs/를 tools/data/neighborhood-seo/에 복원합니다. HTML 재현은 기존 3차 검토본에서 tools/improve_neighborhood_phase4.py --all로 수행합니다. 원문 입력·코드는 공개 배포 파일이 아닙니다.
- 이전 1차~3차 생성기·보고서로 현재 본문 또는 과거 증거를 덮어쓰지 않습니다.
'''
    (OUT/'작업결과.txt').write_bytes(text.replace('\n','\r\n').encode('utf-8-sig'))
    section=f'''## 2026-10-01 — 4차 교습비 원문 안내 완료, 운영 미배포

- 사용자 최신 지시: 개선은 순차 진행하며 배포는 마지막에 수행합니다. 지금 commit/push/운영 배포 없음.
- 동네 8,162페이지 + 지점 안내 193개 = 8,355페이지 개선. PDF 193개·701쪽, 원문 표와 일치한 일반 과정 4,162개 대조. 현재 학년·장소 조건에 맞는 159개 지점에 원문 기준 교습비를 표시했고 34개 지점은 원문 확인 안내 유지.
- 원문 과정명·기간·총 교습시간·총교습비·기준일·쪽수 제공. 원문 숫자를 주당 횟수로 해석하거나 시간 단위를 추정하지 않습니다. 현재 적용 요금으로 선언하지 않으며 추가 과정 금액을 전체 수업료로 사용하지 않았습니다. 수지점(W+) 조건과 확정 엑셀 학년 유지.
- 전체 8,403페이지·공개 10,622파일 검사 오류 0건. HTML 8,355변경 / 48바이트 유지. fees·수정일·관련 확인 문장 외 이전 본문 바이트 유지. 반응형 40조건과 표 열기·닫기 확인. 통계·설명 후처리를 포함한 로컬 배포 결과도 검토본과 일치.
- [최신 작업결과](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase4-20261001/작업결과.txt>) / [검증자료와생성입력](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase4-20261001/검증자료와생성입력.zip>) / [변경 전 백업](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase4-20261001/phase3-before-phase4.zip>).
- 최신 manifest SHA256 `{build['reviewedManifestSha256']}`. 원본 작성 폴더 상태 유지. 네이버 수집·색인·순위·유입은 검증하지 않았습니다.
- 다음 개선: 동네·과목·학년과 역할별 FAQ 질문·답변 정밀화 → 확인 필요 자료 보완 → 최종 배포 요청 시 공개 URL 및 수집·노출/클릭 확인. 기존 중복 URL은 보존하고 역할을 구분합니다.
- 4차 입력은 위 결과 폴더의 fee-grid-verified.json와 source-pdfs/. 코드 tools/improve_neighborhood_phase4.py, validate_neighborhood_phase4.py, report_neighborhood_phase4.py. ZIP 복원 경로는 작업결과.txt에 기록했습니다. 이전 생성기로 최신 본문·검증 자료를 되돌리지 않습니다.

'''
    for path in [impl.ROOT/'NEIGHBORHOOD_SEO_HANDOFF.md',FOLDER/'PROJECT_HANDOFF.md']:
        value=path.read_text('utf-8')
        if '## 2026-10-01 — 4차 교습비 원문 안내 완료' in value:continue
        if path.name=='PROJECT_HANDOFF.md':value=value.replace(value.splitlines()[2],'최신 갱신: 2026-10-01. 4차 교습비 원문 안내 개선을 반영했습니다. 사용자 지시대로 배포는 마지막에 수행합니다. 현재는 검증된 로컬 개선본이며 네이버 검색 성과는 별도 확인 대상입니다.',1)
        index=value.find('\n## ');assert index>0
        path.write_text(value[:index]+'\n\n'+section+value[index+1:],'utf-8')
    path=FOLDER/'CHANGELOG.md';value=path.read_text('utf-8')
    if '## 2026-10-01 — 4차 교습비 원문 안내 완료' not in value:path.write_text(value.rstrip()+'\n\n'+section,'utf-8')
    destination=OUT/'검증자료와생성입력.zip'
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED,compresslevel=5) as archive:
        for path in OUT.glob('*'):
            if path.is_file() and path.suffix in ['.json','.csv','.jpg','.png','.txt'] and path.name!='diff-check-output.txt':archive.write(path,'phase4/'+path.name)
        for path in (OUT/'source-pdfs').glob('*.pdf'):archive.write(path,'phase4/source-pdfs/'+path.name)
        for path in impl.DATA.glob('*.json'):archive.write(path,'inputs/'+path.name)
        for path in (impl.ROOT/'tools').glob('*phase4.py'):archive.write(path,'tools/'+path.name)
        for name in ['improve_neighborhood_pages.py','improve_neighborhood_phase2.py','validate_neighborhood_seo.py','verify_neighborhood_build.py']:archive.write(impl.ROOT/'tools'/name,'tools/'+name)
        archive.write(impl.ROOT/'NEIGHBORHOOD_SEO_HANDOFF.md','NEIGHBORHOOD_SEO_HANDOFF.md')
    with zipfile.ZipFile(destination) as archive:assert archive.testzip() is None
    impl.dump(OUT/'archive-verification.json',{'archive':destination.name,'bytes':destination.stat().st_size,'sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),'crcPassed':True,'deployed':False})
    print('Phase 4 complete, verified locally; no deployment',destination.stat().st_size,flush=True)

if __name__=='__main__':main()
