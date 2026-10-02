"""Record verified local link results and update only this site's handoff."""
from collections import Counter
from pathlib import Path
import ast,hashlib,json,zipfile
import improve_neighborhood_pages as impl
from audit_neighborhood_phase6 import OUT,PRIOR,BACKUP,dump,state

FOLDER=Path(r'C:\Users\1992k\Desktop\홈페이지 작업 폴더\00_프로젝트 인수인계\코칭학원.com')
TITLE='## 2026-10-01 — 6차 학년 확인 링크 개선 완료, 운영 미배포'

def main():
    check=impl.load(OUT/'validation.json');site=impl.load(OUT/'all-site-validation.json');build=impl.load(OUT/'build-verification.json')
    cases=impl.load(OUT/'responsive-cases.json');responsive=impl.load(OUT/'responsive-checks.json');interactions=impl.load(OUT/'interaction-checks.json')
    assert check['errors']==site['errors']==build['errors']==[]
    assert check['changedHtmlPages']==281 and check['labeledLinks']==1152 and check['labeledTargets']==55 and check['retainedFAQQuestions']==41775
    assert len(cases)==13 and len(responsive)==len({(r['index'],r['requestedWidth']) for r in responsive})==52
    assert Counter(r['index'] for r in responsive)==Counter({i:4 for i in range(13)})
    assert all(r['width']==r['requestedWidth'] and r['scrollWidth']<=r['width'] and r['faqOpen']==5 and r['links'] and all(a['visible'] and a['statusInside'] and a['viewportInside'] and a['height']>=44 for a in r['links']) for r in responsive)
    assert all(interactions[k] for k in ['pointerClicked','keyboardClicked','hoverVerified','viewportReset','previewTabClosed'])
    assert impl.load(OUT/'preview-server-check.json')['stopped']
    assert impl.load(OUT/'diff-check.json')['exitCode']==0
    manifest=impl.ROOT/'release-public-manifest.json';sha=hashlib.sha256(manifest.read_bytes()).hexdigest()
    assert build['reviewedManifestSha256']==sha and build['publicFiles']==10622 and build['htmlPages']==8403 and build['privateSourceFiles']==0
    assert all(r['exitCode']==0 for r in impl.load(OUT/'build-pipeline.json'))
    final_state=state();assert final_state==impl.load(OUT/'original-source-state.json')
    dump(OUT/'original-source-state-final.json',final_state)
    scripts=list((impl.ROOT/'tools').glob('*phase6*.py'))
    for path in scripts:ast.parse(path.read_text('utf-8'))
    text=f'''코칭학원.com — 6차 학년 확인 링크 개선
상태: 로컬 전체 검증 완료 / 운영 미배포
사용자 지시: 기존 URL 보존, 순차 개선, 배포는 마지막에 진행합니다.

변경 내용
- 전체 sitemap 8,403페이지의 모든 링크를 검사했습니다. 제공된 확정 학년 자료가 해당 과목·학년에 비어 있는 수강 안내 페이지는 55개입니다.
- 관련 안내 구역에서 발견했던 545개 링크에 한정하지 않고 FAQ·교습비·지점 안내·학년별 버튼·관련 페이지까지 검사했습니다. 실제 개선은 281페이지의 수강 안내 링크 1,152개입니다.
- 원래 링크 문구 아래에 '자료상 학년 확인 필요'를 표시했습니다. 화면과 보조기술에서 모두 읽을 수 있으며 기존 링크 목적·주소·속성은 유지했습니다. 자료 미확인은 수업 미운영이나 모집 중지라는 의미가 아닙니다.
- 확인된 학년의 수강 링크와 일반 학습 점검·선택 기준 페이지는 확인 필요 대상으로 바꾸지 않았습니다. 현재 위치를 보여 주는 breadcrumb 36개와 페이지 내부 목차·교습비·학교 등 구역 이동 977개는 목적에 맞는 기존 문구를 유지했습니다.
- 링크를 눌러 기존 페이지의 실제 학년 자료·주소·운영 조건·준비 자료를 확인할 수 있습니다. 모든 URL과 기존 페이지를 유지했습니다. 기존 중복 페이지도 삭제·통합하지 않았습니다.
- 센터 데이터 엑셀 기준은 그대로입니다. 화성태안점의 엑셀 이름 미매칭/CSV 안내, 수지점(W+) 별도 장소 조건, 침산점 고3 마감, 석사점 학년 확인 조건을 변경하지 않았습니다.

검증
- 전체 8,403 HTML: 변경 281 / 바이트 유지 8,122. 승인된 링크 안의 표시 외 기존 HTML 바이트가 전부 같습니다. H1·메타 설명·canonical·색인 정책·구조화 데이터·교습비·이미지 및 지도 순서·연락 경로 유지.
- 미확인 수강 대상 55개로 연결되는 선택/안내 링크 1,152개 표시 누락 0건. 확인된 과목·학년 및 학습 가이드에 잘못 붙은 표시 0건. 모든 링크 href와 기존 속성 보존.
- 기존 역할별 FAQ 질문·답변 41,775개와 FAQPage 일치 유지. sitemap과 센터 검토 입력 바이트 보존. 페이지 변경일은 같은 실제 작업일인 2026-10-01로 유지합니다.
- 전체 내부 링크·앵커 오류·도달 불가 페이지·동네 H1 중복·확정 엑셀 불일치 0건. 192개 센터 엑셀 대조 통과. meta/OG/Twitter 설명 최대 80자 유지.
- 13개 화면(다섯 역할·영어/수학·초중고 링크·관련 9개 지점) × 320/390/768/1280px = 52조건 통과. FAQ를 펼쳐 연결 버튼까지 검사했습니다. 확인 문구·버튼 가로 넘침 없고 버튼 높이 44px 이상입니다.
- 마우스 hover 시 문구·배지 대비 유지. 마우스와 키보드 Enter로 기존 수강 페이지 이동 확인. 브라우저 임시 크기 복원, 검증 탭과 로컬 서버 종료.
- 기존 release-public-build → wawa-04 방문통계 → 설명 후처리 → 전체 공개 파일 바이트 대조 통과. 공개 10,622파일 / HTML 8,403 / 비공개 원본 포함 0. 통계 삽입 5,225페이지, 기존 포함 3,178페이지. 설명 후처리 추가 변경 0건.
- 전체 git diff --check 종료 코드 0. 검토 manifest SHA256 {sha}.
- 원본 작성 폴더 HEAD {final_state['head']}, Git 상태 {final_state['statusEntries']:,}, 스테이징 {final_state['stagedEntries']}, 확장 미추적 상태 {final_state['expandedUntrackedStatusEntries']:,} 유지.
- commit/push/운영 배포·검색 계정 작업 없음. 네이버 수집·색인·순위·유입 변화는 이번 로컬 검사로 확인하지 않았습니다.

다음 개선
- 홈·과목별 목록·센터 목록 등 기존 상위 페이지 11개를 읽기 전용으로 점검했습니다. 일곱 분류별 목록은 동네 링크가 주로 키워드 이름으로 표시돼 있습니다. 현재도 지점 예시·상담 안내·FAQ가 있어 빈 페이지로 취급하지 않습니다.
- 다음 단계는 상위 목록에서 수강·위치 안내, 진도·오답 점검, 비교·선택 기준의 목적을 더 분명히 설명하고 학생의 학년·과목에 맞는 기존 동네 페이지로 연결하는 것입니다. 기존 URL과 확인된 자료를 유지합니다. 이번에는 후보 점검만 진행했습니다.
- 확인 필요 지점의 학년·장소·실제 사진은 새로운 확정 자료가 제공될 때 보완합니다. 최종 배포는 사용자 요청 후 수행합니다.

복원과 재현
- phase5-before-phase6.zip는 6차 변경 전 HTML 8,403개·CSS·sitemap·manifest·센터 입력·5차 FAQ 검토 입력을 보존한 불변 백업입니다. 덮어쓰지 않습니다.
- 검증자료와생성입력.zip는 6차 코드·전체 링크 감사·검증·화면·manifest, 현재 센터 입력, 이전 FAQ·교습비 입력과 PDF 원본을 보존합니다. 공개 빌드에 넣지 않습니다.
- 백업의 HTML·CSS·sitemap·manifest를 동일한 분리 작업 폴더에 복원하고, ZIP의 tools/와 inputs/를 각각 tools/와 tools/data/neighborhood-seo/에 복원합니다. phase6/는 본 결과 폴더로, phase5/와 phase4/는 각각 기존 단계 결과 폴더로 복원합니다.
- 링크 입력 incoming-link-audit.json을 검토한 뒤 tools/improve_neighborhood_phase6.py를 실행합니다. 전체 validator와 화면 확인 후 tools/build_neighborhood_phase6.py --freeze --build로 최종 로컬 출력과 대조합니다. 재적용 시 implementation.json의 입력/출력 해시를 확인해 중복 표시를 막습니다.
- 이전 생성기로 최신 HTML·입력·검증 증거를 덮어쓰지 않습니다.
- 전체 검사에서 사용하는 이전 단계의 불변 백업과 결과 폴더도 유지합니다. 이번 ZIP이 작성용 원본이나 전체 저장소·역사적 백업을 대체하지는 않습니다.
'''
    (OUT/'작업결과.txt').write_bytes(text.replace('\n','\r\n').encode('utf-8-sig'))
    section=f'''{TITLE}

- 사용자 지시대로 순차 개선, 배포는 마지막에 진행합니다. commit/push/운영 배포 없음.
- 전체 8,403페이지의 모든 링크를 검사해 281페이지 / 1,152개 수강 링크에 '자료상 학년 확인 필요'를 표시했습니다. 대상 수강 URL 55개. 이전 관련 안내 545개에서 FAQ·교습비·지점·학년별 버튼·관련 링크까지 검사 범위를 확대했습니다.
- 자료 미확인을 미운영으로 단정하지 않습니다. 기존 URL·링크 목적·href·확정 학년·장소·교습비·학교·준비 자료 유지. 현재 위치 breadcrumb와 같은 페이지의 구역 이동, 확정 학년 링크·학습/비교 가이드의 목적은 보존했습니다.
- HTML 281변경 / 8,122바이트 유지. 표시 외 이전 본문·schema·H1·메타·미디어·문의 경로 바이트 보존. 기존 41,775 FAQ 질문과 schema 일치 유지. 전체 내부 링크/앵커/도달성/엑셀 검사 오류 0건.
- 반응형 52조건·hover 가독성·마우스/키보드 이동 확인. 기존 통계/설명 후처리 포함 전체 공개 10,622파일의 바이트 대조 통과. 원본 작성 폴더 상태 유지.
- [작업결과](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase6-20261001/작업결과.txt>) / [검증자료와생성입력](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase6-20261001/검증자료와생성입력.zip>) / [변경 전 백업](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase6-20261001/phase5-before-phase6.zip>).
- 최신 manifest SHA256 `{sha}`. 네이버 수집·색인·순위·유입은 이번 로컬 검사로 검증하지 않았습니다.
- 다음 개선: 홈·과목별 목록 등 기존 상위 안내에서 세 목적(수강·학습 점검·비교)을 명확히 설명하고 학년·과목에 맞는 기존 동네 페이지 연결 강화. 상위 페이지 11개 후보 점검만 수행했습니다.
- tools/audit_neighborhood_phase6.py, improve_neighborhood_phase6.py, validate_neighborhood_phase6.py, build_neighborhood_phase6.py, report_neighborhood_phase6.py 사용. 입력 incoming-link-audit.json와 불변 백업, 복원/재현은 작업결과 참고. 이전 생성기로 최신 검토본을 되돌리지 않습니다.

'''
    for path in [impl.ROOT/'NEIGHBORHOOD_SEO_HANDOFF.md',FOLDER/'PROJECT_HANDOFF.md']:
        value=path.read_text('utf-8')
        if TITLE in value:continue
        if path.name=='PROJECT_HANDOFF.md':value=value.replace(value.splitlines()[2],'최신 갱신: 2026-10-01. 6차 학년 확인 링크 개선을 반영했습니다. 사용자 지시대로 배포는 마지막에 수행합니다. 현재는 전체 검증된 로컬 개선본이며 네이버 검색 성과는 별도 확인 대상입니다.',1)
        index=value.find('\n## ');assert index>0
        path.write_text(value[:index]+'\n\n'+section+value[index+1:],'utf-8')
    path=FOLDER/'CHANGELOG.md';value=path.read_text('utf-8')
    if TITLE not in value:path.write_text(value.rstrip()+'\n\n'+section,'utf-8')
    destination=OUT/'검증자료와생성입력.zip';included={}
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED,compresslevel=5) as archive:
        def add(path,name):
            archive.write(path,name);included[name]=hashlib.sha256(path.read_bytes()).hexdigest()
        for path in OUT.iterdir():
            if path.is_file() and path.suffix in ['.json','.png','.js','.txt','.log'] and path.name not in ['diff-check-output.txt','archive-verification.json']:add(path,'phase6/'+path.name)
        dependencies=['improve_neighborhood_pages.py','improve_neighborhood_phase2.py','audit_neighborhood_phase2.py','audit_neighborhood_phase5.py','build_neighborhood_phase5.py','validate_neighborhood_seo.py','verify_neighborhood_build.py','serve_coaching_preview.py']
        for path in scripts+[impl.ROOT/'tools'/name for name in dependencies]:add(path,'tools/'+path.name)
        for path in impl.DATA.glob('*.json'):add(path,'inputs/'+path.name)
        add(PRIOR/'reviewed-faq.json','phase5/reviewed-faq.json')
        fee=OUT.parent/'site3-neighborhood-phase4-20261001'
        add(fee/'fee-grid-verified.json','phase4/fee-grid-verified.json')
        for path in (fee/'source-pdfs').glob('*.pdf'):add(path,'phase4/source-pdfs/'+path.name)
        add(manifest,'release-public-manifest.json')
        add(impl.ROOT/'NEIGHBORHOOD_SEO_HANDOFF.md','handoff/NEIGHBORHOOD_SEO_HANDOFF.md')
        add(FOLDER/'PROJECT_HANDOFF.md','handoff/PROJECT_HANDOFF.md');add(FOLDER/'CHANGELOG.md','handoff/CHANGELOG.md')
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None and set(archive.namelist())==set(included)
        for name,expected in included.items():assert hashlib.sha256(archive.read(name)).hexdigest()==expected,name
    result={'zip':destination.name,'bytes':destination.stat().st_size,'members':len(included),'sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),'memberHashesVerified':True,'crcVerified':True,'deployed':False}
    dump(OUT/'archive-verification.json',result);print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
