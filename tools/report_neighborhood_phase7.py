"""Package verified local finder changes without publishing or changing public bytes."""
from collections import Counter
from pathlib import Path
import ast
import hashlib
import json
import zipfile

import improve_neighborhood_pages as impl
from audit_neighborhood_phase7 import OUT, PRIOR, BACKUP
from audit_neighborhood_phase6 import dump, state

FOLDER = Path(r'C:\Users\1992k\Desktop\홈페이지 작업 폴더\00_프로젝트 인수인계\코칭학원.com')
TITLE = '## 2026-10-01 — 7차 홈·상위 목록 목적별 찾기 개선 완료, 운영 미배포'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    check = impl.load(OUT / 'validation.json')
    site = impl.load(OUT / 'all-site-validation.json')
    build = impl.load(OUT / 'build-verification.json')
    inputs = impl.load(OUT / 'final-input-validation.json')
    responsive = impl.load(OUT / 'responsive-checks.json')
    functional = impl.load(OUT / 'functional-checks.json')
    interactions = impl.load(OUT / 'interaction-checks.json')
    fallback = impl.load(OUT / 'failure-fallback-check.json')
    next_audit = impl.load(OUT / 'next-regional-audit.json')
    assert check['errors'] == site['errors'] == build['errors'] == inputs['errors'] == []
    assert check['sitemapPages'] == 8403 and check['changedHtmlPages'] == 11 and check['unchangedHtmlPages'] == 8392
    assert check['directoryLabels'] == check['matchingItemListLabels'] == 2597
    assert check['areas'] == 371 and check['reviewedRoutes'] == 8162 and check['confirmationTargets'] == 55
    assert all(check[k] for k in ['originalHTMLOutsideApprovedFieldsByteExact', 'existingURLsAndOrderPreserved', 'centerInputsByteExact', 'whitelistOnly'])
    assert site['workbookCentersVerified'] == 192 and site['unreachablePages'] == site['phase2DuplicateH1Groups'] == site['legacyFragmentIssues'] == 0
    assert site['descriptionsMax'] <= 80
    assert len(responsive) == len({(r['index'], r['requestedWidth']) for r in responsive}) == 44
    assert Counter(r['index'] for r in responsive) == Counter({i: 4 for i in range(11)})
    assert {r['requestedWidth'] for r in responsive} == {320, 390, 768, 1280}
    assert all(r['width'] == r['requestedWidth'] and r['scrollWidth'] <= r['width'] and not r['captionOverflow'] and r['links'] and not r['resultHidden'] and all(c['height'] >= 44 and c['left'] >= 0 and c['right'] <= r['width'] for c in r['controls']) for r in responsive)
    assert len(functional) == len({r['name'] for r in functional}) == 16
    assert all(interactions[k] for k in ['pointerPassed', 'keyboardPassed', 'hoverVerified', 'viewportReset', 'previewTabClosed'])
    assert fallback['formHidden'] and fallback['resultHidden'] and fallback['originalDirectoryLinks'] == 371 and fallback['purposeLinks'] == 3
    assert '수지점(W+)' in impl.load(OUT / 'W-plus-destination-check.json')['note']
    assert impl.load(OUT / 'preview-server-check.json')['stopped']
    assert inputs['changedEditorialEntries'] == 11 and inputs['allOtherEditorialEntriesUnchanged'] and inputs['diffExitCode'] == 0
    assert next_audit['remainingIndexHubs'] == 35 and next_audit['regionalHubs'] == 29 and next_audit['gradeSubjectHubs'] == 6 and not next_audit['exampleGradeConflicts'] and next_audit['currentPhaseHubConflicts'] == 0 and next_audit['readOnly']
    manifest = impl.ROOT / 'release-public-manifest.json'
    sha = digest(manifest)
    assert sha == inputs['manifestSha256'] == build['reviewedManifestSha256'] == impl.load(OUT / 'reviewed-release-state.json')['manifestSha256']
    assert build['publicFiles'] == 10624 and build['htmlPages'] == 8403 and build['privateSourceFiles'] == 0
    assert build['analyticsTrackerInsertedPages'] == 5225 and build['analyticsAlreadyPresentPages'] == 3178
    assert [r['step'] for r in impl.load(OUT / 'build-pipeline.json')] == [1, 2, 3, 4]
    assert all(r['exitCode'] == 0 for r in impl.load(OUT / 'build-pipeline.json'))
    assert digest(BACKUP) == impl.load(OUT / 'backup-verification.json')['sha256']
    final_state = state()
    assert final_state == impl.load(OUT / 'original-source-state.json')
    dump(OUT / 'original-source-state-final.json', final_state)
    scripts = sorted((impl.ROOT / 'tools').glob('*phase7*.py'))
    for path in scripts:
        ast.parse(path.read_text('utf-8'))

    text = f'''코칭학원.com — 7차 홈·상위 목록 목적별 찾기 개선
상태: 로컬 전체 검증 완료 / 운영 미배포
사용자 지시: 기존 페이지와 URL 유지, 센터 데이터 엑셀을 확정 학년 기준으로 사용, 배포는 마지막에 진행합니다.

변경 내용
- 홈·지점안내·전국센터·과목별학원과 일곱 과목/학교급 분류 목록, 총 11페이지를 개선했습니다.
- 수강·위치 안내, 진도·오답 점검, 비교·선택 기준의 세 목적을 설명하고 선택한 동네·과목·학교급에 맞는 기존 페이지로 연결하는 찾기 기능을 추가했습니다.
- 371개 동네와 기존 동네 URL 8,162개를 검토한 공개 입력으로 사용합니다. 동네·지역·지점 이름을 검색할 수 있고 띄어쓰기를 정규화합니다. 전체 학년을 고른 학습 점검은 초등·중등·고등 안내 3개를 보여 줍니다.
- 과목별 분류 목록의 동네 링크 2,597개에 연결 대상의 실제 비교·선택 목적을 표시했습니다. ItemList 이름도 같은 문구로 맞췄습니다. 동네 이름과 href는 유지했습니다.
- 새 기능은 기존 HTML 지역·분류 목록과 함께 제공됩니다. 자바스크립트 또는 찾기 데이터가 없으면 원래 목록으로 안내합니다. 기존 페이지가 삭제·통합되거나 새 키워드 URL이 생성되지 않았습니다.
- 자료에서 해당 과목·학년이 비어 있는 수강 대상 55개는 '자료상 학년 확인 필요'로 표시합니다. 자료 미확인은 수업 미운영이나 모집 중지가 아닙니다. 학습 방법·비교 기준을 모집 사실로 표현하지 않습니다.
- 공개 데이터는 기존 동네·지역·구·공개 지점명·검토된 주소와 링크를 허용 목록으로 구성했습니다. 원본 센터 객체나 엑셀 영업 메모를 공개하지 않았습니다.
- 실제 주소·안내 학년·현재 모집 여부는 기존 수강 안내에서 확인하도록 연결했습니다. 화성태안점 CSV/확인, 수지점(W+) 별도 장소, 침산점 고3 마감, 석사점 학년 확인 조건을 유지했습니다.
- 설명 11개는 80자 이내 완전한 문장으로 고치고 meta/OG/Twitter/페이지 schema를 일치시켰습니다. 11페이지의 변경일과 sitemap lastmod만 실제 작업일 2026-10-01로 반영했습니다.

검증
- sitemap HTML 8,403개 전체 대조: 변경 11 / 바이트 유지 8,392. 허용한 찾기 영역·목록 캡션·설명·변경일 외 원래 HTML 바이트가 모두 같습니다. 모든 기존 URL·sitemap 순서·H1·canonical·색인 정책·FAQ·연락 경로·본문 이미지와 지도/사진 순서 보존.
- 기존 6차 학년 확인 링크 1,152개와 5차 FAQ 질문·답변 41,775개를 포함한 동네·지점 페이지는 바이트 그대로입니다. 센터 검토 입력도 바이트 그대로입니다.
- 전체 내부 링크·앵커·도달 불가·동네 H1 중복·확정 엑셀 불일치 오류 0건. 센터 엑셀 192개 대조, 설명 최대 80자 통과.
- 11페이지 × 320/390/768/1280px = 44조건 통과. 표시된 입력·선택·결과 버튼 높이 44px 이상, 화면 및 목록 캡션 가로 넘침 0건.
- 과목·목적·학교급 전환, 확인 필요 표시의 추가/해제, 전체 학습 학년 3개, 일곱 비교 주제, 띄어쓰기 검색, 결과 없는 검색, Enter, CSV 미매칭 지점, W+ 연결을 포함한 16개 동작을 확인했습니다.
- 명일동 고등 수학 링크를 마우스로, 명일동 수학 비교 기준을 키보드로 눌러 실제 기존 URL 이동을 확인했습니다. 새 결과 링크 hover와 표시 범위 확인. 수지점 목적지에서 W+ 장소 안내 확인.
- 찾기 JSON만 의도적으로 503 응답하도록 만든 별도 로컬 서버에서 오류 안내, 원래 동네 링크 371개와 목적 목록 링크 3개 유지 확인. 검증 탭 종료, 임시 화면 크기 복원, 소유한 로컬 서버 2개 종료.
- 초기 설명 후처리는 비공개 검토 입력 seo-descriptions.json에 이전 설명이 남아 있어 거절했습니다. 해당 11개 설명 및 sources만 새 검토 문구로 맞췄으며 나머지 입력은 그대로입니다. 검토 보호 검사를 유지하고 전체 8,403페이지 후처리와 바이트 검증을 다시 수행했습니다. 이미 통과한 공개 복사/통계 단계는 같은 manifest에서 유지했습니다.
- 최종 release-public-build → wawa-04 통계 → 설명 후처리 → 전체 공개 파일 검증 통과. 공개 10,624파일 / HTML 8,403 / 비공개 원본 포함 0. 통계 삽입 5,225, 기존 포함 3,178. 설명 후처리 추가 변경 0건. 최종 공개 파일은 검토된 HTML·자산에 기존 통계 삽입만 반영합니다.
- 전체 git diff --check 종료 코드 0. 검토 manifest SHA256 {sha}.
- 원본 작성 폴더 HEAD {final_state['head']}, Git 상태 {final_state['statusEntries']:,}, 스테이징 {final_state['stagedEntries']}, 확장 미추적 상태 {final_state['expandedUntrackedStatusEntries']:,} 유지.
- commit/push/운영 배포·검색 계정 작업 없음. 네이버 수집·색인·검색 순위·유입 변화는 이번 로컬 작업으로 측정하지 않았습니다.

다음 개선
- 기존 지역별·학년별 목록 35개를 읽기 전용으로 점검했습니다. 지역 목록 29개와 초등/중등/고등 영어·수학 목록 6개입니다. 아직 새 찾기 기능을 적용하지 않았습니다.
- 다음 단계는 이 35개 목록에서도 해당 지역 또는 학년·과목을 미리 선택해 목적에 맞는 동네 안내로 연결하는 것입니다. 기존 지역별 소속·목록·URL·확정 자료를 유지합니다. 예시 카드의 학년 자료를 점검했고 현재 불일치 0건입니다.
- 새로운 지점별 확정 자료가 제공되면 확인 필요 정보와 실제 사진을 보완합니다. 운영 배포는 사용자의 별도 요청 후 진행합니다.

복원과 재현
- phase6-before-phase7.zip은 변경 전 전체 HTML 8,403개·CSS·sitemap·manifest·센터 입력·6차 도구의 불변 백업입니다. 기존 파일에 덮어쓰지 않습니다. 변경 전 seo-descriptions.json은 seo-descriptions-before-phase7.json에 별도로 보존했습니다.
- 검증자료와생성입력.zip은 7차 도구·검토 입력·화면·최종 manifest·현재 공개 자산과 비공개 설명 입력·이전 FAQ/교습비 입력/PDF·인수인계 기록입니다. 검증 자료와 원본 센터 데이터는 공개 출력에 넣지 않습니다.
- 백업 HTML·CSS·sitemap·manifest를 같은 분리 작업 폴더에 복원하고 ZIP tools/를 tools/로, inputs/를 tools/data/neighborhood-seo/로, public-assets/를 프로젝트 루트로 복원합니다. editorial/seo-descriptions.json은 루트의 비공개 검토 파일입니다. phase7/는 본 결과 폴더로, phase6/·phase5/·phase4/는 해당 기존 단계 폴더로 복원합니다.
- 적용할 때 public-assets의 두 새 find-guide 자산은 유지하고 CSS는 변경 전 백업을 먼저 사용합니다. 검토한 reviewed-pages.json, reviewed-finder-data.json, hub-audit.json과 7차 improve 도구로 11페이지·CSS·sitemap을 재현합니다. description 입력은 현재 검토본을 유지합니다. 입력/출력 해시가 다른 기존 파일을 임의로 덮어쓰지 않습니다.
- 전체 validator와 화면 확인 후 build_neighborhood_phase7.py --freeze --build로 로컬 출력과 대조합니다. 완성된 manifest에서 --build만 수행하면 빌드만 재검증합니다. 이전 단계 생성기로 최신 HTML·자료·검증 결과를 되돌리지 않습니다.
- 전체 검사에 필요한 이전 단계의 불변 백업 및 결과 폴더를 함께 유지합니다. 이번 ZIP은 전체 저장소나 모든 역사적 백업을 대체하지 않습니다.
'''
    (OUT / '작업결과.txt').write_bytes(text.replace('\n', '\r\n').encode('utf-8-sig'))
    section = f'''{TITLE}

- 순차 개선 및 배포 마지막 지시 유지. commit/push/운영 배포 없음.
- 홈·지점안내·전국센터·과목별학원 및 일곱 분류 목록, 총 11곳에 동네·지역·지점 검색과 목적/과목/학교급 선택 기능 추가. 수강·위치, 진도·오답 점검, 비교·선택을 기존 URL로 연결합니다.
- 동네 371개 / 기존 동네 URL 8,162개 검토. 과목별 목록 2,597개 링크의 실제 목적과 ItemList 이름 정리. 기존 static 목록·동네명·href 유지. 새 페이지 생성·기존 페이지 삭제/통합 없음.
- 확인 필요 수강 대상 55개 표시, 학습·비교 목적 보존. 확정 엑셀 및 W+·마감·CSV 미매칭 조건 유지. 공개 JSON은 공개 이름·검토된 링크 허용 목록이며 원본 센터 메모를 포함하지 않습니다.
- 전체 HTML 8,403 중 11변경 / 8,392바이트 유지. 기존 1,152 학년 확인 표시와 41,775 FAQ 포함 이전 동네·지점 HTML 유지. 메타 설명 11개 ≤80자 및 동일 schema, 실제 변경일 반영.
- 전체 링크·앵커·도달성·엑셀·H1 검증 오류 0. 반응형 44조건·동작 16개·마우스/키보드 이동·hover·JSON 장애 시 기존 목록 유지 확인. 임시 화면 복원 및 검증 탭/서버 종료.
- 비공개 seo-descriptions.json의 해당 11개 검토 설명/sources만 정렬해 후처리 보호 검사 통과. 공개 10,624파일/HTML 8,403 전체 바이트 검증, 최종 diff 검사 통과. 원본 작성 폴더 상태 유지.
- [작업결과](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase7-20261001/작업결과.txt>) / [검증자료와생성입력](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase7-20261001/검증자료와생성입력.zip>) / [변경 전 백업](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase7-20261001/phase6-before-phase7.zip>).
- 최종 manifest SHA256 `{sha}`. 네이버 수집·색인·검색 순위·유입 변화 미측정.
- 다음 개선: 읽기 전용 점검한 지역별·학년별 목록 35개(지역 29 + 학년/과목 6)에 해당 지역·학년·과목을 미리 선택하는 목적별 찾기 적용. 현재 예시 학년 불일치 0건. 이번에는 후보 점검만 수행했습니다.
- 7차 audit/improve/validate/build/align/report 도구와 검토 입력·불변 백업 사용. 복원 및 재현은 작업결과 참고. 이전 생성기로 최신 검토본을 되돌리지 않습니다.

'''
    for path in [impl.ROOT / 'NEIGHBORHOOD_SEO_HANDOFF.md', FOLDER / 'PROJECT_HANDOFF.md']:
        value = path.read_text('utf-8')
        if TITLE in value:
            continue
        if path.name == 'PROJECT_HANDOFF.md':
            value = value.replace(value.splitlines()[2], '최신 갱신: 2026-10-01. 7차 홈·상위 목록 목적별 찾기 개선을 반영했습니다. 사용자 지시대로 배포는 마지막에 수행합니다. 현재는 전체 검증된 로컬 개선본이며 네이버 검색 성과는 별도 확인 대상입니다.', 1)
        index = value.find('\n## ')
        assert index > 0
        path.write_text(value[:index] + '\n\n' + section + value[index + 1:], 'utf-8')
    changelog = FOLDER / 'CHANGELOG.md'
    value = changelog.read_text('utf-8')
    if TITLE not in value:
        changelog.write_text(value.rstrip() + '\n\n' + section, 'utf-8')

    destination = OUT / '검증자료와생성입력.zip'
    included = {}
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, compresslevel=5) as archive:
        def add(path, name):
            assert name not in included, name
            archive.write(path, name)
            included[name] = digest(path)
        excluded = {'diff-check-output.txt', 'diff-check-final-output.txt', 'archive-verification.json'}
        for path in sorted(OUT.iterdir()):
            if path.is_file() and path.suffix in {'.json', '.png', '.js', '.txt', '.log'} and path.name not in excluded:
                add(path, 'phase7/' + path.name)
        dependencies = ['improve_neighborhood_pages.py', 'improve_neighborhood_phase2.py', 'audit_neighborhood_phase2.py', 'audit_neighborhood_phase5.py', 'build_neighborhood_phase5.py', 'audit_neighborhood_phase6.py', 'validate_neighborhood_seo.py', 'verify_neighborhood_build.py', 'serve_coaching_preview.py']
        for path in scripts + [impl.ROOT / 'tools' / name for name in dependencies]:
            add(path, 'tools/' + path.name)
        for path in sorted(impl.DATA.glob('*.json')):
            add(path, 'inputs/' + path.name)
        for name in ['assets/neighborhood-seo/find-guide.js', 'assets/neighborhood-seo/find-guide.json', 'assets/neighborhood-seo/local.css']:
            add(impl.ROOT / name, 'public-assets/' + name)
        add(impl.ROOT / 'seo-descriptions.json', 'editorial/seo-descriptions.json')
        add(PRIOR / 'validation.json', 'phase6/validation.json')
        add(PRIOR / 'incoming-link-audit.json', 'phase6/incoming-link-audit.json')
        phase5 = OUT.parent / 'site3-neighborhood-phase5-20261001'
        add(phase5 / 'reviewed-faq.json', 'phase5/reviewed-faq.json')
        fee = OUT.parent / 'site3-neighborhood-phase4-20261001'
        add(fee / 'fee-grid-verified.json', 'phase4/fee-grid-verified.json')
        for path in sorted((fee / 'source-pdfs').glob('*.pdf')):
            add(path, 'phase4/source-pdfs/' + path.name)
        add(manifest, 'release-public-manifest.json')
        for path in [impl.ROOT / 'NEIGHBORHOOD_SEO_HANDOFF.md', FOLDER / 'PROJECT_HANDOFF.md', FOLDER / 'CHANGELOG.md']:
            add(path, 'handoff/' + path.name)
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None and set(archive.namelist()) == set(included)
        for name, expected in included.items():
            h = hashlib.sha256()
            with archive.open(name) as member:
                for block in iter(lambda: member.read(1024 * 1024), b''):
                    h.update(block)
            assert h.hexdigest() == expected, name
    result = {'zip': destination.name, 'bytes': destination.stat().st_size, 'members': len(included), 'sha256': digest(destination), 'memberHashesVerified': True, 'crcVerified': True, 'deployed': False}
    dump(OUT / 'archive-verification.json', result)
    print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
