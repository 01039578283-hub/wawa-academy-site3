"""Record complete local URL checks and prepare an unobserved Naver follow-up scope."""
from collections import Counter
from pathlib import Path
from urllib.parse import unquote
import ast, hashlib, json, subprocess, zipfile
import improve_neighborhood_pages as impl
from audit_neighborhood_phase6 import dump, state
from audit_neighborhood_phase11 import OUT, BASE_SHA

FOLDER = Path(r'C:\Users\1992k\Desktop\홈페이지 작업 폴더\00_프로젝트 인수인계\코칭학원.com')
TITLE = '2026-10-02 — 11차 전체 URL·수집 설정 로컬 검사 및 배포 후 네이버 확인 범위 준비 완료'
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    crawl = impl.load(OUT / 'crawl-audit.json'); routes = impl.load(OUT / 'configured-route-audit.json')
    checks = impl.load(OUT / 'http-verification.json'); build = impl.load(OUT / 'build-verification.json')
    inputs = impl.load(OUT / 'http-inputs.json')
    assert crawl['errors'] == build['errors'] == routes['errors'] == []
    assert checks['errorCount'] == 0 and checks['failures'] == [] and checks['mode'] == 'local' and checks['localServerClosed']
    assert checks['expectedCases'] == checks['completedCases'] == checks['successfulRequests'] == routes['cases'] == 46476
    assert checks['localConnections'] == 12 and checks['reusedConnections'] == 46464
    assert checks['inputsSha256'] == digest(OUT / 'http-inputs.json')
    assert checks['manifestSha256'] == inputs['manifestSha256'] == digest(impl.ROOT / 'release-public-manifest.json') == BASE_SHA
    assert inputs['configSha256'] == digest(impl.ROOT / 'vercel.json')
    assert checks['byKind'] == {'public-file-get': 10624, 'canonical-head': 8403, 'query-head': 8403, 'index-alias': 8403, 'without-slash': 8402, 'file-with-slash': 2221, 'missing-or-private': 17, 'missing-path-normalization': 2, 'missing-index-alias': 1}
    assert crawl['htmlPages'] == build['htmlPages'] == 8403 and crawl['publicFiles'] == build['publicFiles'] == 10624
    protected = impl.load(OUT / 'protected-input-hashes.json')
    assert all(digest(impl.ROOT / name) == value for name, value in protected.items())
    authoring = state(); assert authoring == impl.load(OUT / 'original-source-state.json')
    dump(OUT / 'original-source-state-after.json', authoring)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=impl.ROOT).decode().strip()
    assert head == '3c2b4695e058361a77c81afa065f2758735f22bb'
    rows = {row['path']: row for row in impl.inventory()}
    hubs = {impl.center_path(c) for c in impl.FACTS['centers']}
    observations = []
    for page in inputs['pages']:
        source = rows.get(unquote(page['path']))
        observations.append({'canonical': page['canonical'], 'pageHeading': page['h1'], 'role': source['role'] if source else 'center-hub' if unquote(page['path']) in hubs else 'other', 'neighborhood': source.get('neighborhood') if source else None, 'region': source.get('region') if source else None, 'center': source.get('center') if source else None, 'pageSubject': source.get('subject') if source else None, 'pageStage': source.get('stage') if source else None, 'observationStatus': 'not_checked', 'observedSearchQuery': None, 'reportCoverage': None, 'reportUpdatedThrough': None, 'periodStart': None, 'periodEnd': None, 'naverCollected': None, 'naverIndexed': None, 'impressions': None, 'clicks': None, 'naverVisits': None, 'evidence': None})
    counts = Counter(r['role'] for r in observations)
    assert counts == {'comparison-guide': 2597, 'enrollment': 2968, 'overview': 371, 'study-guide': 2226, 'center-hub': 193, 'other': 48}
    assert len({r['neighborhood'] for r in observations if r['neighborhood']}) == 371
    dump(OUT / 'naver-followup-scope.json', {'scope': 'All reviewed public URLs; observation placeholders only, not search results', 'htmlPages': 8403, 'neighborhoodPages': 8162, 'neighborhoods': 371, 'byRole': dict(counts), 'gradeMeaning': 'Page topic only; current supplied Excel and confirmation labels remain authoritative', 'dataLimits': {'exposureClickReport': 'Official guide: about one week lag, recent 90 days, top 30 keyword/URL records', 'diagnosisDownloads': 'Official guide: up to 2000 URLs per diagnosis category', 'absentRows': 'Unobserved or outside report coverage is not zero and not proof of exclusion'}, 'observations': observations, 'deployed': False})
    dump(OUT / 'scope-validation.json', {'publicFiles': 10624, 'htmlPages': 8403, 'changedPublicFiles': 0, 'changedVercelSettings': False, 'changedFactsOrDates': False, 'publicManifestSha256': BASE_SHA, 'existingBuildControlsUnchanged': True, 'authoringStatePreserved': True, 'worktreeHead': head, 'newPrivateRepoFiles': ['tools/audit_neighborhood_phase11.py', 'tools/check_neighborhood_http.mjs', 'tools/report_neighborhood_phase11.py', 'tools/PREDEPLOY_CHECKS.md'], 'publicHttpChecksPerformed': False, 'searchAccountAccessed': False, 'deployed': False})
    next_text = '다음 단계는 사용자에게서 마지막 배포 요청을 받은 뒤 검증한 개선본을 배포하고, 실제 전체 URL 응답·운영 alias 및 네이버 수집·색인·노출·클릭·유입을 확인하는 것입니다. 현재는 배포와 계정 작업을 하지 않습니다.'
    report = f'''코칭학원.com 11차 개선 완료 — 배포 전 전수 점검, 운영 미배포
2026-10-02 / 배포는 마지막에 수행한다는 사용자 지시 유지

이번 단계의 결과
- 공개 HTML 8,403개와 파일 총 10,624개를 대상으로 URL·수집 설정을 전수 검사했습니다.
- 발견된 공개 URL·수집 설정 오류는 0건입니다. 기존 페이지·주소·목적·본문·날짜·배포 설정을 그대로 유지했습니다.
- 새 비공개 도구로 반복 가능한 전수 HTTP 검사와 배포 후 네이버 확인 범위를 준비했습니다.

검사 내용과 결과
- sitemap 8,403 URL과 실제 canonical·공개 HTML이 모두 일치합니다. 기존 두 canonical의 한글 표기와 동일 주소의 URI 인코딩을 구분하여 URL을 보존했습니다.
- RSS 발견 링크 8,403곳, Yeti/기본 검색로봇 수집 허용, 공개 noindex/nofollow 및 meta refresh 0곳, 미공개 내부 링크 0건.
- @vercel/routing-utils 6.6.0의 공식 변환 도구로 현재 vercel.json 규칙을 변환했습니다. 오류 0건.
- 전체 로컬 HTTP 46,476조건 완료/통과: 공개 파일 GET 10,624, 페이지 HEAD 8,403, 쿼리 포함 HEAD 8,403, index.html 주소 8,403, 끝 슬래시 없는 주소 8,402, 파일 뒤 슬래시 2,221, 없는/비공개 경로 20.
- 공개 GET 파일 내용의 SHA256·Content-Type과 nosniff, HEAD 빈 본문을 대조했습니다. index.html·슬래시 변형은 자기 대표 주소로 308 이동하며 쿼리를 보존하고 목적지에서 끝납니다. 없는 페이지는 최종 404입니다.
- 처음에는 검사 서버의 연결 종료로 Windows 로컬 연결 한도에 걸렸습니다. 검사 서버의 빈 응답 길이·연결 재사용을 조정한 뒤 전수 재검사했습니다. 최종 12연결/46,464회 재사용/누락·오류 0건. 첫 시도 기록도 비공개 결과 폴더에 보관했습니다.
- 검사 서버는 공개 허용 목록만 읽고 127.0.0.1 임시 포트를 사용한 뒤 종료했습니다. 로컬 noindex/no-store는 운영 설정에 추가하지 않았습니다.
- 기존 검증된 .public-release의 전체 바이트를 다시 대조했습니다. 기존 통계 스크립트 추가 외 변경 0, 비공개 원본 포함 0. 전체 공개 원본 해시와 최종 HTML 검토 해시도 전수 확인했습니다.
- 이번에 공개 변경이 없어 배포 빌드를 새로 생성하거나 화면 검증을 반복하지 않았습니다. 기존 로컬 빌드 출력 및 현재 시작/종료 피드 검사는 통과했습니다.

배포 후 확인 범위
- naver-followup-scope.json: 전체 공개 URL 8,403 / 동네 페이지 8,162 / 동네 371 / 지점 허브 193. 수집·색인·검색어·노출·클릭·유입 관측값은 null, 상태는 not_checked입니다.
- URL마다 학습 안내·학원 선택 안내·지점 수강 안내 등 기존 목적을 구분합니다. 페이지 학년은 운영 학년을 새로 확정한 값이 아닙니다.
- 네이버 공식 안내에 있는 데이터 지연과 TOP 30 키워드/URL 범위, 사이트 진단 URL 다운로드 최대 2,000건을 반영했습니다. 목록에 없는 페이지를 유입 0 또는 미색인으로 단정하지 않습니다.
- 실제 도메인의 HTTP→HTTPS·추가 호스트 처리·TLS/DNS·대시보드/봇 정책, READY/운영 alias/commit 일치도 마지막 배포 이후에 확인합니다.
- 자세한 확인 순서와 실제 전체 HTTP 재검사 명령: tools/PREDEPLOY_CHECKS.md.

범위와 한계
- 공식 도구로 변환한 설정과 로컬 HTTP 출력의 검사입니다. 실제 Vercel/CDN 응답이나 네이버 수집·색인·순위·유입 증가를 관측한 결과는 아닙니다.
- 원본 작성 폴더의 HEAD 및 Git 상태, 현재 작업 공간 HEAD, 공개 10,624파일·manifest·수강 사실 자료·RSS/사이트맵·기존 빌드 설정 모두 유지했습니다.
- Git commit/push/배포/서치어드바이저·GSC/외부 계정 작업 미실행.
- {next_text}

증거 자료
- crawl-audit.json / configured-route-audit.json / http-verification.json / url-response-results.json
- http-inputs.json / naver-followup-scope.json / build-verification.json / scope-validation.json
- phase10-before-phase11.zip / 검증자료와확인범위.zip
- 공개 manifest SHA256: {BASE_SHA}
- HTTP 검토 입력 SHA256: {checks['inputsSha256']}

공식 참고
https://searchadvisor.naver.com/guide/seo-basic-http
https://searchadvisor.naver.com/guide/seo-basic-robots
https://searchadvisor.naver.com/guide/report-diagnosis
https://searchadvisor.naver.com/guide/report-expose-ctr
https://vercel.com/docs/routing/redirects/configuration-redirects
'''
    (OUT / '작업결과.txt').write_bytes(report.replace('\n', '\r\n').encode('utf-8-sig'))
    url = OUT.as_posix()
    section = f'''## {TITLE}

- 사용자 순차 개선·배포 마지막 지시 유지. commit/push/배포/외부 계정 작업 미실행.
- 공개 HTML 8,403·전체 파일 10,624·sitemap/RSS 발견·Yeti/기본 수집 허용·canonical·공개 noindex/nofollow·meta refresh·미공개 내부 링크 전수 오류 0. 공개 파일 및 설정 변경 없음.
- @vercel/routing-utils 6.6.0 공식 규칙 변환 + 로컬 HTTP 46,476조건 전부 통과. 전체 파일 GET 내용/MIME·HEAD·쿼리·index.html/슬래시 변형·없는/비공개 경로 확인. 308 자기 대표 주소 이동·최종 404·쿼리 유지.
- 첫 검사 Windows 연결 한도를 도구의 연결 재사용으로 해결하고 전수 재검사 완료. 최종 12연결/46,464회 재사용, 로컬 서버 종료. 첫 시도 증거도 비공개 보관.
- 기존 실제 로컬 빌드 10,624파일 전수 바이트/해시 대조, 원본 작성 폴더 및 사실 자료·본문·날짜·URL·기존 buildCommand/headers/redirects 유지. 공개 변경이 없어 새 빌드나 화면 검증은 반복하지 않음.
- 배포 후 확인 범위 JSON: 전체 8,403 URL/동네 8,162페이지/동네 371/지점 허브 193, 관측값 null/not_checked. 네이버 보고서의 지연·TOP 30·진단 URL 최대 2,000건 범위 반영. 미제공을 0/미색인으로 판단하지 않음.
- tools/audit_neighborhood_phase11.py, check_neighborhood_http.mjs, report_neighborhood_phase11.py, PREDEPLOY_CHECKS.md 추가. 새 도구는 비공개 tools/에 위치하고 공개 manifest에 포함하지 않음.
- 공식 변환+로컬 출력 검사이며 Vercel/CDN 실제 응답 또는 검색 수집·색인·순위·유입 개선 확인은 아님.
- [작업결과](<{url}/작업결과.txt>) / [검증자료와확인범위](<{url}/검증자료와확인범위.zip>) / [변경 전 백업](<{url}/phase10-before-phase11.zip>).
- manifest SHA256 `{BASE_SHA}`, HTTP 입력 SHA256 `{checks['inputsSha256']}`.
- {next_text}

'''
    handoffs = [impl.ROOT / 'NEIGHBORHOOD_SEO_HANDOFF.md', FOLDER / 'PROJECT_HANDOFF.md', FOLDER / 'CHANGELOG.md']
    for file in handoffs:
        text = file.read_text('utf-8')
        if TITLE in text: continue
        if file.name == 'PROJECT_HANDOFF.md':
            text = text.replace(text.splitlines()[2], '최신 갱신: 2026-10-02. 11차 전체 URL·수집 설정 전수 점검과 마지막 배포 후 네이버 확인 범위를 준비했습니다. 기존 개선본은 로컬에 보존하며 배포·계정 작업은 마지막 요청 뒤에 진행합니다.', 1)
        if file.name == 'CHANGELOG.md': text = text.rstrip() + '\n\n' + section
        else:
            index = text.find('\n## '); assert index > 0
            text = text[:index] + '\n\n' + section + text[index + 1:]
        file.write_text(text, 'utf-8')
    diff = subprocess.run(['git', '-c', 'core.safecrlf=false', 'diff', '--check'], cwd=impl.ROOT, capture_output=True)
    (OUT / 'diff-check-output.txt').write_bytes(diff.stdout + diff.stderr)
    assert diff.returncode == 0
    dump(OUT / 'diff-check.json', {'exitCode': 0, 'outputBytes': len(diff.stdout) + len(diff.stderr), 'scope': 'Entire existing worktree'})
    scripts = [impl.ROOT / 'tools' / name for name in ['audit_neighborhood_phase11.py', 'report_neighborhood_phase11.py']]
    pending = scripts[:]; dependencies = {}
    while pending:
        file = pending.pop()
        if file.name in dependencies: continue
        dependencies[file.name] = file
        for node in ast.walk(ast.parse(file.read_text('utf-8'))):
            imports = [node.module] if isinstance(node, ast.ImportFrom) else [a.name for a in node.names] if isinstance(node, ast.Import) else []
            for name in imports:
                if name:
                    local = impl.ROOT / 'tools' / (name.split('.')[0] + '.py')
                    if local.exists(): pending.append(local)
    archive_path = OUT / '검증자료와확인범위.zip'; included = {}
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=5) as archive:
        def add(file, name):
            assert name not in included
            archive.write(file, name); included[name] = digest(file)
        for file in sorted(OUT.iterdir()):
            if file.is_file() and file.suffix in {'.json', '.log', '.txt', '.py', '.zip'} and file.name not in {archive_path.name, 'archive-verification.json', 'diff-check-output.txt'}:
                add(file, 'phase11/' + file.name)
        for file in sorted(dependencies.values()): add(file, 'tools/' + file.name)
        for name in ['check_neighborhood_http.mjs', 'PREDEPLOY_CHECKS.md', 'SEO_FEED_REVIEW.md']: add(impl.ROOT / 'tools' / name, 'tools/' + name)
        for file in handoffs: add(file, 'handoff/' + file.name)
        # Preserve the exact small routing runtime used, including lock and licenses.
        runtime = OUT / 'routing-runtime'
        for file in sorted(runtime.rglob('*')):
            if file.is_file(): add(file, 'routing-runtime/' + file.relative_to(runtime).as_posix())
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None and set(archive.namelist()) == set(included)
        for name, expected in included.items(): assert hashlib.sha256(archive.read(name)).hexdigest() == expected, name
    dump(OUT / 'archive-verification.json', {'file': archive_path.name, 'members': len(included), 'bytes': archive_path.stat().st_size, 'sha256': digest(archive_path), 'crcVerified': True, 'allMemberHashesVerified': True, 'deployed': False})
    assert digest(impl.ROOT / 'release-public-manifest.json') == BASE_SHA and state() == authoring
    print(json.dumps({'report': str(OUT / '작업결과.txt'), 'archiveMembers': len(included), 'publicFiles': 10624, 'httpCasesPassed': 46476, 'searchObservations': 'not_checked', 'deployed': False}, ensure_ascii=False), flush=True)

if __name__ == '__main__': main()
