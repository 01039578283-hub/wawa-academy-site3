"""Preserve complete phase-3 evidence only after source and release validation."""
import csv, hashlib, json, shutil, subprocess, zipfile
from pathlib import Path
import improve_neighborhood_pages as impl
from audit_neighborhood_phase3 import OUT

ORIGINAL=Path(r'C:\Users\1992k\Desktop\홈페이지 작업 폴더\홈페이지 정리\새 홈페이지3')

def handoff():
    folder=Path(r'C:\Users\1992k\Desktop\홈페이지 작업 폴더\00_프로젝트 인수인계\코칭학원.com')
    section='''## 2026-10-01 — 3차 개선 완료, 운영 미배포

- 371개 동네의 기존 8,162페이지 전체 유지. 동네별 정확한 학교 목록 전체와 준비 자료·확정 학년을 긴 이미지 앞에 배치했습니다. 학교는 상담 참고 자료로 표현합니다.
- 학습 점검 2,226페이지의 상세 공통 질문을 기존 `/학습관리/`의 여섯 주제·18개 질문으로 모았습니다. 학생 답안 상황 세 가지와 해당 학교·지점 자료는 동네 페이지에 남겼습니다. 기존 URL 삭제·통합 없음.
- 실제 지점 사진 368장을 원본과 대조하고 96개 지점 허브·관련 동네 페이지에 검토한 설명과 alt를 추가했습니다. 공통 사진 97개 지점은 예시임을 앞부분에도 표시했습니다. 실제 사진 신규 추가·원본 변경 없음.
- 변경 HTML 8,259페이지, 나머지 144페이지 바이트 유지. 전체 sitemap 8,403페이지 및 공개 파일 10,622개 검증 오류 0건. 기존 URL·H1·메타·색인·이미지 순서·문의 경로 유지. 반응형 24조건과 질문 펼치기·앵커 이동 확인.
- 수강 학년은 사용자 확정 엑셀 기준 유지. 화성태안점의 정확한 XLSX 이름 매칭은 미확인으로 기존 범위·확인 안내 유지. 수지점(W+) 장소 조건과 침산점 고3 마감 안내 유지.
- 최신 결과: [작업결과.txt](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase3-20261001/작업결과.txt>), [검증자료와생성입력.zip](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase3-20261001/검증자료와생성입력.zip>), [3차 변경 전 백업](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase3-20261001/phase2-before-phase3.zip>).
- 원본 작성용 폴더·스테이징 상태 보존. commit/push/운영 배포·검색 계정·자동화 작업 없음. 로컬 검증은 네이버 수집·색인·순위·유입의 증거가 아닙니다.
- 다음 순서: 명시적 운영 배포 요청 후 공개 URL·네이버 수집과 노출/클릭 확인 → 지점 확정 교습비 원본의 HTML 안내 → 공통 사진 지점의 실제 사진과 화성태안점 자료 보완.
- 3차 도구는 `tools/improve_neighborhood_phase3.py`, `tools/validate_neighborhood_phase3.py`, `tools/report_neighborhood_phase3.py`. 최신 ZIP의 `inputs/`를 `tools/data/neighborhood-seo/`에, `phase3/photo-audit.json` 등은 위 결과 폴더에 복원합니다. 기존 1차·2차 생성기와 보고서로 최신 본문이나 과거 증거를 덮어쓰지 않습니다.

'''
    for path in [impl.ROOT/'NEIGHBORHOOD_SEO_HANDOFF.md',folder/'PROJECT_HANDOFF.md']:
        value=path.read_text('utf-8')
        if '## 2026-10-01 — 3차 개선 완료' in value:continue
        if path.name=='PROJECT_HANDOFF.md':
            value=value.replace(value.splitlines()[2],'최신 갱신: 2026-10-01. 3차 학교 자료·공통 질문·사진 설명 개선을 반영했습니다. 기존 운영 배포와 현재 미배포 개선본을 구분합니다. 네이버 검색 성과는 별도 확인 대상입니다.',1)
        else:value=value.replace('2026-09-30. 운영 기준','2026-10-01. 운영 기준',1)
        index=value.find('\n## ');assert index>0
        path.write_text(value[:index]+'\n\n'+section+value[index+1:],'utf-8')
    path=folder/'CHANGELOG.md';value=path.read_text('utf-8')
    if '## 2026-10-01 — 3차 개선 완료' not in value:
        path.write_text(value.rstrip()+'\n\n'+section,'utf-8')

def main():
    local=impl.load(OUT/'validation.json')
    global_check=impl.load(impl.REPORT/'validation.json')
    build=impl.load(impl.REPORT/'build-verification.json')
    assert local['errors']==global_check['errors']==build['errors']==[]
    assert local['phase3NeighborhoodPages']==8162 and local['centerHubs']==96 and local['changedHtmlPages']==8259
    assert build['htmlPages']==8403 and build['publicFiles']==10622
    assert build['reviewedManifestSha256']==hashlib.sha256((impl.ROOT/'release-public-manifest.json').read_bytes()).hexdigest()
    diff=subprocess.run(['git','diff','--check'],cwd=impl.ROOT,capture_output=True)
    (OUT/'diff-check-output.txt').write_bytes(diff.stdout+diff.stderr)
    impl.dump(OUT/'diff-check.json',{'exitCode':diff.returncode,'outputBytes':len(diff.stdout+diff.stderr)})
    assert diff.returncode==0, 'Review diff-check-output.txt'
    baseline=impl.load(OUT.parent/'site3-neighborhood-phase2-20260930'/'original-source-state.json')
    def git(*args):return subprocess.check_output(['git','-C',str(ORIGINAL),*args]).decode('utf-8').splitlines()
    status=git('status','--porcelain')
    state={'head':git('rev-parse','HEAD')[0],'statusEntries':len(status),'stagedEntries':sum(bool(line) and line[0] not in [' ','?'] for line in status),'expandedUntrackedStatusEntries':len(git('status','--porcelain','--untracked-files=all'))}
    assert state==baseline, (state,baseline)
    impl.dump(OUT/'original-source-state.json',state)
    shutil.copyfile(impl.REPORT/'validation.json',OUT/'all-site-validation.json')
    shutil.copyfile(impl.REPORT/'build-verification.json',OUT/'build-verification.json')
    for name in ['source-reconciliation.json','hubs.json']:
        if (impl.REPORT/name).exists():shutil.copyfile(impl.REPORT/name,OUT/name)
    implementation=impl.load(OUT/'implementation.json')
    implementation.update(verifiedCompleteNeighborhoodPages=8162,verifiedCompleteCenterHubs=96,verifiedChangedHtmlPages=8259,verifiedSharedGuidePages=1,completeDetailedQuestionOccurrencesRelocated=2226*3,countNote='changedPages/removedRepeatedSchoolParagraphs reflect the last resumed run only; complete coverage is independently verified.')
    impl.dump(OUT/'implementation.json',implementation)
    photos=impl.load(OUT/'photo-audit.json')
    with (OUT/'자료보완목록.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['지역','지점','현재 사진','원본 사진 폴더 존재','제공 이미지 수','다음 보완 자료'])
        for entry in photos['entries']:
            if entry['mode']=='common':writer.writerow([entry['region'],entry['center'],'브랜드 공통 예시',entry['sourceFolderExists'],entry['sourceImageCount'],'현재 지점의 건물·입구·학습 공간 사진과 촬영 시점 확인'])
        writer.writerow(['경기','화성태안점','기존 안내 유지','','','엑셀의 확정 지점명과 5과목 수강 학년 확인'])
    before=impl.load(OUT/'before.json');after=impl.load(OUT/'after.json');ui=impl.load(OUT/'responsive-checks.json')
    assert all(row['scrollWidth']<=row.get('viewport',row['width']) for row in ui)
    report=f'''코칭학원.com 동네 페이지 3차 개선 — 2026.10.01

상태: 로컬 개선·전체 검증·전체 배포용 빌드 완료. 커밋·푸시·운영 배포 없음.
작업 공간: {impl.ROOT}
2차 변경 전 전체 백업: {OUT/'phase2-before-phase3.zip'}

적용 범위
- 371개 동네 8,162페이지 전체 유지: 수강·위치 2,968 / 학습 점검 2,226 / 비교 2,597 / 일반 371.
- 실제 사진이 있는 96개 지점 허브와 기존 /학습관리/ 안내 추가 개선.
- HTML 변경 8,259페이지. 나머지 144페이지의 바이트 보존.
- 기존 sitemap 8,403 URL과 순서, canonical·색인 설정·H1·메타 설명, 이미지 경로·순서·크기·로딩 설정, 상담 연락 경로 유지.

변경 내용
1. 동네별 학교 자료를 정확한 schoolAreas 생활권에서 가져와 전체 학교명을 표시.
   이전 다섯 학교 제한을 없애고 학년 페이지에서는 해당 학교급만 표시.
   준비 자료와 엑셀 기준 과목별 안내 학년을 함께 제공하며 긴 본문 이미지 앞에 배치.
   학교명은 상담 참고 자료이며 전용반·제휴·현재 시험 범위로 표현하지 않음.
2. 학습 점검 2,226페이지의 상세 공통 질문 설명을 기존 /학습관리/에 모음.
   초등·중등·고등 영어·수학 여섯 주제와 원래 질문 18개를 유지.
   동네 페이지에는 실제 안내 지점·학년·해당 학교 자료와 세 가지 학생 답안 상황을 먼저 제공.
   상세 질문 6,678회분은 공통 안내와 정확한 주제 앵커로 연결. URL 삭제 없음.
3. 일반 동네 371페이지의 길고 반복된 상담 설명을 학교 자료 / 실제 과목·지점 확인의 두 경로로 정리.
   다른 본문에서 학교 목록을 다시 나열하던 문단도 학교 자료 링크로 연결.
4. 기존 실제 사진 368장을 제공 원본과 대조하고 96개 지점분 전체를 눈으로 검토.
   건물·입구·책상·자료·기록 등을 구분한 alt와 사진 설명 추가.
   모든 사진을 시설 사진이라고 부르던 제목을 '지점 제공 사진'으로 수정.
   일정·기록·상장 등을 현재 운영 조건이나 학습 성과로 해석하지 않음.
   공통 사진을 쓰는 97개 지점은 동네 페이지 앞부분에도 예시 사진임을 표시.
   실제 사진 추가 0장, 원본 및 기존 공개 이미지 파일 변경 0개.
5. 내용 수정일과 자료 대조일을 구분. 변경된 페이지만 schema dateModified 및 sitemap lastmod 갱신.
   Windows 저장 과정의 중복 줄바꿈 제거 및 기존 단일 파일의 교체 제한을 보호 검사 후 처리.

자료 기준
- 사용자가 확정한 센터 데이터 엑셀 학년 기준 유지; 192개 센터 독립 대조.
- 화성태안점은 엑셀 이름 매칭 미확인으로 CSV 범위와 확인 안내 유지.
- 수지점(W+) 별도 수업 장소, 침산점 고3 마감 조건 유지.
- 제공되지 않은 비용·시간표·수강 성과·후기·시설 정보를 만들지 않음.

검증 결과
- 전체 8,403페이지 검사 오류 0건. 이번 동네 8,162 + 지점 허브 96 + 공통 안내 1 전수 확인.
- 정확한 학교 이름 {local['fullSchoolNameOccurrences']:,}회, 검토한 사진 설명 {local['reviewedCaptionOccurrences']:,}회 배치 확인.
- 표본 반응형 {len(ui)}조건 검사: 320/390/768/1280px, 가로 넘침 없음.
- 공통 질문 링크 이동 및 펼치기 동작 확인, 실제 화면 캡처 보관.
- git diff --check 오류 0건. 작성용 원본 HEAD와 Git 상태 항목 수 유지, 스테이징 0.
- 전체 배포용 결과: 공개 파일 {build['publicFiles']:,}, HTML {build['htmlPages']:,}, 비공개 입력 포함 0개.
  기존 통계 태그 추가 {build['analyticsTrackerInsertedPages']:,}페이지 외 검토한 소스와 바이트 일치.
  검증 manifest SHA256: {build['reviewedManifestSha256']}

반복 문단 측정의 한계
- 지정 편집 영역의 70자 이상 문단, 동네·지점·주소 치환 후 같은 역할 내 반복만 측정.
- 그룹 {before['sameRoleParagraphGroups']:,} → {after['sameRoleParagraphGroups']:,}.
- 출현 {before['sameRoleParagraphOccurrences']:,} → {after['sameRoleParagraphOccurrences']:,}.
- 동일 편집 문단 구성의 그룹 {before['sameRoleEditorialSignatures']:,} → {after['sameRoleEditorialSignatures']:,}, 해당 페이지 {before['sameRoleEditorialSignaturePages']:,} → {after['sameRoleEditorialSignaturePages']:,}.
- 공통 상세 설명을 모으면서 남은 편집 영역의 구성은 더 같아진 경우도 있음. 위 구성 검사는 학교·지점 사실을 제외하므로 동네 정보 전체의 동일 여부를 뜻하지 않음.
- 이 수치는 사이트 전체 중복률이나 네이버 품질 점수가 아님. 공통 수업 조언·확인 안내는 반복될 수 있음.

다음 개선 순서
1. 운영 반영 후 실제 공개 URL과 네이버 수집·색인·노출·클릭 자료 확인.
   현재 개선본은 운영 미배포 상태이며 순위·유입 개선은 아직 측정하지 않음.
   Search Advisor는 웹 검색 관련 노출/클릭 정보만 제공하며 모든 페이지 실적을 직접 제공하는 보고서는 아님.
   공식 안내: https://searchadvisor.naver.com/guide/report-expose-ctr
2. 지점별 교습비 안내 원본을 확인하고 금액·적용 학년·횟수·시간·자료 날짜를 HTML로 정리.
   현재 지역 공통 참고표를 지점 확정 금액으로 전용하지 않음.
3. 공통 사진 97개 지점의 현재 실제 사진 보완 및 화성태안점 학년 자료 확정.
   요청 대상은 자료보완목록.csv 참고. 특강 홍보물을 시설 사진으로 전용하지 않음.
4. 학교별 사용 교재·시험 범위·상담 사례가 실제 자료로 확인되면 해당 동네 안내를 보완.
   지금 없는 자료를 만들거나 같은 조언의 표현만 바꾸어 지역 고유 내용으로 내세우지 않음.

증거 및 재현
- validation.json: 3차 전수 보호/학교/공통 질문/사진 확인.
- all-site-validation.json: 기존 전체 SEO·자료·내부 링크 검사.
- build-verification.json: 최종 공개 출력의 파일 목록과 바이트 보존 확인.
- before.json / after.json: 같은 역할의 반복 문단 측정.
- photo-audit.json 및 photo-review-*.jpg: 사진 원본 대조와 시각 검토.
- 검증자료와생성입력.zip: 최신 비공개 입력·코드·검증 자료.
  inputs/는 tools/data/neighborhood-seo/로, phase3/photo-audit.json 등은 본 결과 폴더에 복원.
  과거 1차·2차 보고서 생성기로 기존 증거를 덮어쓰지 않음.
'''
    (OUT/'작업결과.txt').write_text(report,'utf-8-sig')
    handoff()
    with zipfile.ZipFile(OUT/'phase3-evidence.tmp.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for path in impl.DATA.glob('*.json'):archive.write(path,'inputs/'+path.name)
        for path in impl.REPORT.glob('*.json'):archive.write(path,'reports/'+path.name)
        for path in (impl.ROOT/'tools').glob('*.py'):archive.write(path,'code/tools/'+path.name)
        for path in OUT.iterdir():
            if path.is_file() and path.suffix.lower() in ['.json','.jpg','.csv','.txt']:
                archive.write(path,'phase3/'+path.name)
        archive.write(impl.ROOT/'release-public-manifest.json','reviewed/release-public-manifest.json')
        archive.write(impl.ROOT/'NEIGHBORHOOD_SEO_HANDOFF.md','code/NEIGHBORHOOD_SEO_HANDOFF.md')
    with zipfile.ZipFile(OUT/'phase3-evidence.tmp.zip') as archive:assert archive.testzip() is None
    (OUT/'phase3-evidence.tmp.zip').replace(OUT/'검증자료와생성입력.zip')
    print(json.dumps({'report':str(OUT/'작업결과.txt'),'evidence':str(OUT/'검증자료와생성입력.zip'),'deployed':False},ensure_ascii=False))

if __name__=='__main__':main()
