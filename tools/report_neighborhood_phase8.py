"""Record and package the verified local regional/grade finder release."""
from collections import Counter
from pathlib import Path
import ast, copy, hashlib, json, zipfile
import improve_neighborhood_pages as impl
from audit_neighborhood_phase8 import OUT, PRIOR, BACKUP
from audit_neighborhood_phase6 import dump, state

FOLDER = Path(r'C:\Users\1992k\Desktop\홈페이지 작업 폴더\00_프로젝트 인수인계\코칭학원.com')
TITLE = '## 2026-10-01 — 8차 지역·학년 목록 목적별 찾기 개선 완료, 운영 미배포'

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def main():
    check = impl.load(OUT / 'validation.json'); site = impl.load(OUT / 'all-site-validation.json'); build = impl.load(OUT / 'build-verification.json')
    responsive = impl.load(OUT / 'responsive-checks.json'); functional = impl.load(OUT / 'functional-checks.json'); interaction = impl.load(OUT / 'interaction-checks.json')
    configs = impl.load(OUT / 'reviewed-configs.json'); pages = impl.load(OUT / 'reviewed-pages.json')
    assert check['errors'] == site['errors'] == build['errors'] == []
    assert check['sitemapPages'] == 8403 and check['changedHtmlPages'] == 35 and check['unchangedHtmlPages'] == 8368
    assert check['regionalHubs'] == 29 and check['gradeSubjectHubs'] == 6 and check['scopedMemberships'] == 2968 and check['branchesWithoutNeighborhood'] == 5
    assert all(check[k] for k in ['originalHTMLBytePreservedOutsideApprovedFields', 'originalDirectoriesUnchanged', 'existingURLsAndOrderPreserved', 'finderDataAndCenterInputsByteExact', 'previous11HubHTMLByteExact'])
    assert site['workbookCentersVerified'] == 192 and site['phase2DuplicateH1Groups'] == site['unreachablePages'] == site['legacyFragmentIssues'] == 0 and site['descriptionsMax'] <= 80
    assert len(responsive) == len({(r['index'], r['requestedWidth']) for r in responsive}) == 184
    assert Counter(r['index'] for r in responsive) == Counter({i: 4 for i in range(46)})
    assert all(r['width'] == r['requestedWidth'] and r['scrollWidth'] <= r['width'] and not r['hidden'] and r['links'] and all(c['height'] >= 44 and c['left'] >= 0 and c['right'] <= r['width'] for c in r['controls']) for r in responsive)
    assert sum(bool(r.get('copyRechecked')) for r in responsive) == 24
    assert len(functional) == len({r['name'] for r in functional}) == 20
    fallback = impl.load(OUT / 'failure-fallback-checks.json')
    assert len(fallback) == 3 and all(r['formHidden'] and r['resultHidden'] and r['directoryLinks'] == r['expectedOriginalLinks'] and r['purposeLinks'] == 3 for r in fallback)
    assert sorted(r['directoryLinks'] for r in fallback) == [17, 23, 371]
    assert all(interaction[k] for k in ['pointerPassed', 'keyboardPassed', 'failureTabClosed', 'viewportReset', 'previewTabClosed', 'hoverVerified'])
    assert impl.load(OUT / 'hover-check.json')['hovered'] and impl.load(OUT / 'preview-server-check.json')['stopped']
    assert impl.load(OUT / 'diff-check.json')['exitCode'] == 0
    manifest = impl.ROOT / 'release-public-manifest.json'; sha = digest(manifest)
    assert sha == build['reviewedManifestSha256'] == impl.load(OUT / 'reviewed-release-state.json')['manifestSha256']
    assert build['publicFiles'] == 10624 and build['htmlPages'] == 8403 and build['privateSourceFiles'] == 0
    assert build['analyticsTrackerInsertedPages'] == 5225 and build['analyticsAlreadyPresentPages'] == 3178
    assert len(impl.load(OUT / 'build-pipeline.json')) == 4 and all(r['exitCode'] == 0 for r in impl.load(OUT / 'build-pipeline.json'))
    # Independently reconstruct every allowed editorial-input change.
    before = impl.load(OUT / 'seo-descriptions-before-phase8.json'); expected = copy.deepcopy(before)
    for page in pages:
        entry = expected['pages'][page['path'].rstrip('/')]
        assert entry['description'] == page['oldDescription']
        new = configs[page['path']]['description']
        entry['sources'] = list(dict.fromkeys(entry.get('sources', []) + [page['oldDescription'], new])); entry['description'] = new
    assert impl.load(impl.ROOT / 'seo-descriptions.json') == expected
    dump(OUT / 'final-input-validation.json', {'changedEditorialEntries': 35, 'allOtherEditorialEntriesUnchanged': True, 'configSha256': digest(impl.ROOT / 'seo-descriptions.json'), 'manifestSha256': sha, 'errors': [], 'deployed': False})
    assert digest(BACKUP) == impl.load(OUT / 'backup-verification.json')['sha256']
    final_state = state(); assert final_state == impl.load(OUT / 'original-source-state.json')
    dump(OUT / 'original-source-state-final.json', final_state)
    scripts = sorted((impl.ROOT / 'tools').glob('*phase8*.py'))
    for path in scripts:
        ast.parse(path.read_text('utf-8'))

    result_text = f'''코칭학원.com — 8차 지역·학년 목록 목적별 찾기 개선
상태: 로컬 전체 검증 완료 / 운영 미배포
사용자 지시: 기존 페이지와 URL 유지, 센터 데이터 엑셀을 확정 학년 기준으로 사용, 배포는 마지막에 진행합니다.

변경 내용
- 지역 목록 29개와 초등·중등·고등 영어·수학 목록 6개, 총 35페이지에 목적별 동네 찾기를 적용했습니다. 앞서 개선한 홈·상위 목록 11곳과 함께 총 46곳에서 사용할 수 있습니다.
- 지역 목록의 검색·선택에는 원래 목록에 연결된 동네만 표시합니다. 두 지역 목록 체계가 각각 전체 371개 동네를 중복 없이 나누는지 확인했습니다. 경상은 경남·경북, 충청은 충남·충북·세종, 전라는 원래 전라 목록의 동네 범위를 유지합니다.
- 학교급·과목 목록은 해당 과목과 초등/중등/고등을 기본 선택합니다. 목적이나 과목을 바꿔도 학생의 학교급 선택을 유지하고, 다른 학교급을 직접 선택할 수 있습니다.
- 지점 목록의 첫 목적은 수강·위치 안내, 전국센터의 첫 목적은 진도·오답 점검입니다. 비교·선택 기준으로도 전환할 수 있으며 모든 목적지는 기존 URL입니다.
- 동네 연결이 없는 실제 지점 5개(다산지금점·별가람점·옥길스타점·위례창곡점·송파위례점)는 원래 지점 목록에 그대로 남겼습니다. 해당 지역에 동네 찾기에 없는 지점을 아래 목록에서 확인할 수 있다고 안내했습니다. 동네나 가짜 신규 지점을 만들지 않았습니다.
- 각 지역의 수강 목록과 학습 목록 설명은 서로 다른 목적을 전달하도록 나눴습니다. 35개 설명을 80자 이내 완전한 문장으로 만들고 meta/OG/Twitter/페이지 schema와 비공개 seo-descriptions.json 검토 입력을 맞췄습니다.
- 공유 find-guide.js에는 각 페이지의 검토된 동네 ID로 범위를 제한하는 기능만 추가했습니다. 잘못된 범위 입력은 전체 동네로 확대하지 않고 기존 목록으로 안내합니다. 기존 공개 동네 JSON·CSS와 센터 입력은 바이트 그대로입니다.
- 실제 변경일과 sitemap lastmod는 변경한 35페이지에만 반영했습니다. 기존 URL·목록·지역 소속·FAQ·지점 연락 경로·사진/지도 순서를 유지했습니다.

검증
- 전체 HTML 8,403개 대조: 변경 35 / 바이트 유지 8,368. 추가 찾기 영역·검토 설명·변경일 외 원래 HTML 바이트가 모두 같습니다. 이전 홈/상위 11곳도 바이트 그대로입니다.
- 동네·지점 페이지의 확정 학년·교습비 원문·운영 조건·FAQ 41,775개 및 자료상 학년 확인 표시 1,152개 유지. 화성태안 CSV/확인·수지점(W+) 별도 장소·침산점 고3 마감·석사점 학년 확인 조건 유지.
- 두 지역 체계 각 371개 및 여섯 학교급/과목 각 371개, 총 2,968개 목록 소속 검증. 원래 목록 및 확정 지점 자료와 일치합니다. 기존 지점 193개와 동네에 연결된 지점 188개의 차이를 없애지 않았습니다.
- 전체 내부 링크·앵커·도달 불가·동네 H1 중복·설명 중복·확정 엑셀 불일치 오류 0건. 센터 엑셀 192개 대조 통과, 설명 최대 80자 유지.
- 처음 전체 설명 검사에서 같은 지역의 두 목록 설명이 중복된 10쌍을 발견해 수강과 학습 점검 목적에 맞게 구분했습니다. 재검사 오류 0건입니다. HTML 설명과 검토 입력 35개만 변경됐고 나머지 입력은 독립 대조로 보존을 확인했습니다.
- 새 목록 35 + 기존 목록 11 = 46곳 × 320/390/768/1280px = 184조건 통과. 실제 지역 소속 및 기본 목적·학교급·과목·결과 링크·버튼 높이 44px 이상·가로 넘침 없음 확인. 최종 문장 수정 후 여섯 학교급 목록 24조건을 다시 확인했습니다.
- 지역 밖 검색 결과 없음/검색 초기화, 자료상 미확인 수강 표시와 과목 전환, 일반 학습 안내, 세 학교급 안내, 일곱 비교 주제, Enter, 경상·충청·전라 범위, 고등 영어 기본값 및 목적·과목 전환 등 20개 동작 통과.
- 새 고등 영어 목록에서 마우스로 명일동 고등 영어 학습 안내 이동, 서울 목록에서 키보드 Enter로 명일동 고등 수학 수강 안내 이동 확인. 새 버튼 hover와 화면 범위 확인.
- JSON만 503 오류를 내는 로컬 서버에서 서울 지점 목록 23개(동네 미연결 지점 포함), 경상 동네 목록 17개, 고등 영어 목록 371개와 세 목적 링크가 유지됩니다. 폼/결과는 숨기고 원래 목록으로 안내합니다.
- 검증 연결 중단 시 저장된 조건을 이어서 검사했습니다. 검증 화면의 임시 크기 복원·소유한 탭 종료·두 로컬 서버 종료 완료. 최종 문장 수정 전 중단된 빌드는 최종 결과로 사용하지 않았습니다.
- release-public-build → wawa-04 방문통계 → 설명 후처리 → 전체 공개 파일 바이트 대조 통과. 공개 10,624파일 / HTML 8,403 / 비공개 원본 포함 0. 통계 삽입 5,225, 기존 포함 3,178. 설명 후처리 추가 변경 0건. 공개 변경은 HTML 35 + 공유 JS 1 + sitemap 1 = 37파일입니다.
- 전체 git diff --check 종료 코드 0. 최종 manifest SHA256 {sha}.
- 원본 작성 폴더 HEAD {final_state['head']}, Git 상태 {final_state['statusEntries']:,}, 스테이징 {final_state['stagedEntries']}, 확장 미추적 상태 {final_state['expandedUntrackedStatusEntries']:,} 유지.
- commit/push/운영 배포·검색 계정 작업 없음. 네이버 수집·색인·검색 순위·유입 변화는 이번 로컬 작업으로 측정하지 않았습니다.

다음 개선
- RSS 50개 항목을 읽기 전용으로 현재 목적지와 대조했습니다. 기존 RSS 제목이 현재 H1과 다른 항목 50개, HTML 본문을 포함한 항목 32개, 페이지 schema의 실제 변경일보다 최초 pubDate가 이전인 항목 50개입니다. 더 짧은 제목이나 원래 발행일 자체를 오류로 단정하지 않습니다.
- 다음 단계는 RSS의 제목·본문을 현재 페이지 목적과 확정 자료에 맞추고 갱신 정보를 실제 내용 변경에 맞게 정비하는 것입니다. 원래 발행일을 임의로 새 날짜로 바꾸지 않으며 모든 동네 범위는 기존 8,403 URL sitemap으로 계속 안내합니다.
- 네이버 공식 안내는 RSS 항목의 전체 본문 공개를 권장하며 많은 URL은 sitemap 활용을 권장합니다. RSS를 짧은 메타 설명만으로 바꾸지 않고 본문 범위·내부 링크·용량도 함께 점검합니다. 참고: https://searchadvisor.naver.com/guide/request-feed
- 이번에는 RSS/robots/llms 본문을 수정하거나 계정에 제출하지 않았습니다. 최종 배포는 사용자의 별도 요청 후 진행합니다.

복원과 재현
- phase7-before-phase8.zip은 8차 변경 전 전체 HTML 8,403개·sitemap·manifest·공개 찾기 JS/JSON/CSS·센터 입력을 보존한 불변 백업입니다. 변경 전 비공개 설명 입력은 seo-descriptions-before-phase8.json에 별도로 보존했습니다.
- 검증자료와생성입력.zip은 8차 코드·검토 입력·전체 검증·화면·최종 manifest·공개 찾기 자산·현재 비공개 설명 입력·이전 단계 FAQ/교습비 입력/PDF·인수인계 기록을 보존합니다. 원본 센터 입력과 검증 폴더를 공개 출력에 넣지 않습니다.
- 백업 HTML·sitemap·manifest·자산을 같은 분리 작업 폴더에 복원합니다. ZIP tools/는 tools/로, inputs/는 tools/data/neighborhood-seo/로, editorial/seo-descriptions.json은 루트의 비공개 입력으로, phase8/는 본 결과 폴더로 복원합니다. 이전 단계 결과/불변 백업도 함께 유지합니다.
- 백업 상태에서 reviewed-pages.json과 reviewed-configs.json을 검토한 뒤 improve_neighborhood_phase8.py로 35페이지와 공유 JS를 재현합니다. 입력/출력 해시가 다른 파일을 임의로 덮어쓰지 않습니다. CSS·동네 JSON과 원래 디렉터리는 변경하지 않습니다.
- 공개 자산 완성본만 확인하려면 ZIP public-assets/를 프로젝트 루트 경로에 대조합니다. 재현 도구를 실행할 때 공유 JS는 먼저 백업 상태를 사용해야 합니다.
- 전체 validator 및 화면 검사 후 build_neighborhood_phase8.py --freeze --build로 최종 로컬 출력과 대조합니다. 완성된 manifest에서 --build는 빌드만 검사합니다. 이전 단계 생성기로 최신 검토본을 되돌리지 않습니다.
- 이번 ZIP은 전체 Git 저장소나 모든 역사적 백업을 대체하지 않습니다.
'''
    (OUT / '작업결과.txt').write_bytes(result_text.replace('\n', '\r\n').encode('utf-8-sig'))
    section = f'''{TITLE}

- 배포 마지막 지시 유지. commit/push/운영 배포 없음.
- 지역 목록 29개 + 학교급/과목 목록 6개 = 35곳에 목적별 동네 찾기 추가. 지역은 원래 목록의 동네만 표시하고 학교급/과목은 해당 값을 기본 선택합니다. 목적과 과목은 바꿀 수 있습니다.
- 두 지역 체계가 각각 전체 371동네를 나누는지 확인. 총 소속 2,968개 검증. 동네 연결 없는 실제 지점 5곳도 기존 목록에 보존했습니다. 기존 URL과 수강·학습·비교 목적 유지.
- 전체 HTML 8,403 중 35변경 / 8,368바이트 유지. 이전 홈·주요 목록 11곳 및 모든 동네·지점 HTML 보존. 공유 JS의 범위 기능·35개 설명/변경일·sitemap만 공개 변경, 총 37파일. 기존 동네 JSON·CSS·센터 입력 보존.
- 같은 지역 두 목적의 설명 중복을 구분해 전체 설명 검사 통과. 비공개 검토 입력도 해당 35개 설명/sources만 변경했고 나머지 항목 독립 대조 통과.
- 전체 링크·앵커·도달성·엑셀·H1·설명 검증 오류 0. 46곳 × 4화면 폭 = 184조건(최종 문장 24조건 재확인), 동작 20개, 마우스/키보드 이동·hover, 데이터 오류 시 원래 목록 유지 3곳 확인.
- 최종 로컬 공개 10,624파일 / HTML 8,403 / 비공개 원본 0 전체 바이트 대조 통과. 검증 화면 크기 복원, 탭/서버 종료, 원본 작성 폴더 상태 유지.
- [작업결과](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase8-20261001/작업결과.txt>) / [검증자료와생성입력](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase8-20261001/검증자료와생성입력.zip>) / [변경 전 백업](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase8-20261001/phase7-before-phase8.zip>).
- 최종 manifest SHA256 `{sha}`. 검색 수집·색인·검색 순위·유입 변화 미측정.
- 다음 개선: RSS 50개 항목의 제목·본문·갱신 정보를 현재 페이지 목적과 실제 변경에 맞게 정비. 최초 발행일 차이만으로 오류 판단하지 않으며 전체 본문 공개와 모든 URL의 sitemap 유지 원칙을 검토합니다. 네이버 참고: https://searchadvisor.naver.com/guide/request-feed . 이번에는 읽기 전용 점검만 수행했습니다.
- audit/improve/validate/align/build/report_neighborhood_phase8.py, audit_next_feed_phase8.py 및 검토 입력·불변 백업 사용. 이전 생성기로 최신 결과를 되돌리지 않습니다.

'''
    for path in [impl.ROOT / 'NEIGHBORHOOD_SEO_HANDOFF.md', FOLDER / 'PROJECT_HANDOFF.md']:
        value = path.read_text('utf-8')
        if TITLE in value:
            continue
        if path.name == 'PROJECT_HANDOFF.md':
            value = value.replace(value.splitlines()[2], '최신 갱신: 2026-10-01. 8차 지역·학년 목록 목적별 찾기 개선을 반영했습니다. 사용자 지시대로 배포는 마지막에 수행합니다. 현재는 전체 검증된 로컬 개선본이며 네이버 검색 성과는 별도 확인 대상입니다.', 1)
        index = value.find('\n## '); assert index > 0
        path.write_text(value[:index] + '\n\n' + section + value[index + 1:], 'utf-8')
    changelog = FOLDER / 'CHANGELOG.md'; value = changelog.read_text('utf-8')
    if TITLE not in value:
        changelog.write_text(value.rstrip() + '\n\n' + section, 'utf-8')
    # Include local Python dependencies by module name, keeping repository paths.
    queue = scripts + [impl.ROOT / 'tools' / n for n in ['validate_neighborhood_seo.py', 'verify_neighborhood_build.py', 'serve_coaching_preview.py']]
    dependencies = {}
    while queue:
        path = queue.pop()
        if path.name in dependencies:
            continue
        dependencies[path.name] = path
        for node in ast.walk(ast.parse(path.read_text('utf-8'))):
            names = [node.module] if isinstance(node, ast.ImportFrom) else [a.name for a in node.names] if isinstance(node, ast.Import) else []
            for name in names:
                if not name:
                    continue
                local = impl.ROOT / 'tools' / (name.split('.')[0] + '.py')
                if local.exists():
                    queue.append(local)
    destination = OUT / '검증자료와생성입력.zip'; included = {}
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, compresslevel=5) as archive:
        def add(path, name):
            assert name not in included
            archive.write(path, name); included[name] = digest(path)
        for path in sorted(OUT.iterdir()):
            if path.is_file() and path.suffix in {'.json', '.png', '.js', '.txt', '.log'} and path.name not in ['archive-verification.json', 'diff-check-output.txt']:
                add(path, 'phase8/' + path.name)
        for path in sorted(dependencies.values()):
            add(path, 'tools/' + path.name)
        for path in sorted(impl.DATA.glob('*.json')):
            add(path, 'inputs/' + path.name)
        for name in ['find-guide.js', 'find-guide.json', 'local.css']:
            add(impl.ROOT / 'assets' / 'neighborhood-seo' / name, 'public-assets/assets/neighborhood-seo/' + name)
        add(impl.ROOT / 'seo-descriptions.json', 'editorial/seo-descriptions.json')
        for name in ['reviewed-pages.json', 'reviewed-finder-data.json', 'validation.json']:
            add(PRIOR / name, 'phase7/' + name)
        phase5 = OUT.parent / 'site3-neighborhood-phase5-20261001'; add(phase5 / 'reviewed-faq.json', 'phase5/reviewed-faq.json')
        fee = OUT.parent / 'site3-neighborhood-phase4-20261001'; add(fee / 'fee-grid-verified.json', 'phase4/fee-grid-verified.json')
        for path in sorted((fee / 'source-pdfs').glob('*.pdf')):
            add(path, 'phase4/source-pdfs/' + path.name)
        add(manifest, 'release-public-manifest.json')
        for path in [impl.ROOT / 'NEIGHBORHOOD_SEO_HANDOFF.md', FOLDER / 'PROJECT_HANDOFF.md', FOLDER / 'CHANGELOG.md']:
            add(path, 'handoff/' + path.name)
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None and set(archive.namelist()) == set(included)
        for name, expected_hash in included.items():
            h = hashlib.sha256()
            with archive.open(name) as member:
                for block in iter(lambda: member.read(1024 * 1024), b''):
                    h.update(block)
            assert h.hexdigest() == expected_hash, name
    value = {'zip': destination.name, 'bytes': destination.stat().st_size, 'members': len(included), 'sha256': digest(destination), 'memberHashesVerified': True, 'crcVerified': True, 'deployed': False}
    dump(OUT / 'archive-verification.json', value); print(json.dumps(value, ensure_ascii=False), flush=True)

if __name__ == '__main__':
    main()
