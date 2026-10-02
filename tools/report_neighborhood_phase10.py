"""Archive verified build integration and update this site's handoffs only."""
import ast, hashlib, json, subprocess, zipfile
from pathlib import Path
import improve_neighborhood_pages as impl
from audit_neighborhood_phase6 import dump, state
from build_neighborhood_phase10 import OUT, BASE_SHA, STEPS

FOLDER = Path(r'C:\Users\1992k\Desktop\홈페이지 작업 폴더\00_프로젝트 인수인계\코칭학원.com')
TITLE = '2026-10-02 — 10차 본문·RSS·사이트맵 배포 빌드 일치 검사 연결 완료, 운영 미배포'
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    scope = impl.load(OUT / 'scope-validation.json'); integration = impl.load(OUT / 'integration-validation.json')
    tests = impl.load(OUT / 'failure-tests.json'); pipeline = impl.load(OUT / 'build-pipeline.json')
    source = impl.load(OUT / 'source-feed-check.json'); output = impl.load(OUT / 'output-feed-check.json'); build = impl.load(OUT / 'build-verification.json')
    assert tests['scenarios'] == tests['passed'] == 21 and tests['failed'] == 0
    assert len(pipeline) == 5 and [r['command'] for r in pipeline] == STEPS and all(r['exitCode'] == 0 for r in pipeline)
    assert source['ok'] and output['ok'] and source['errorCount'] == output['errorCount'] == 0
    assert source['htmlPages'] == output['htmlPages'] == build['htmlPages'] == 8403 and source['rssItems'] == output['rssItems'] == 50
    assert scope['errors'] == integration['errors'] == build['errors'] == [] and scope['changedPublicFiles'] == 0
    assert build['publicFiles'] == 10624 and build['privateSourceFiles'] == 0 and build['reviewedManifestSha256'] == BASE_SHA
    assert build['analyticsTrackerInsertedPages'] == 5225 and build['analyticsAlreadyPresentPages'] == 3178
    assert integration['fullReviewRefreshByteStable'] and integration['reviewTimestampPreserved']
    assert digest(impl.ROOT / 'seo-feed-review.json') == integration['ledgerSha256']
    assert digest(impl.ROOT / 'release-public-manifest.json') == BASE_SHA
    for name, expected in impl.load(OUT / 'protected-input-hashes.json').items():
        assert digest(impl.ROOT / name) == expected, name
    authoring = state(); assert authoring == impl.load(OUT / 'original-source-state.json')
    dump(OUT / 'original-source-state-after.json', authoring)
    with (OUT / 'diff-check-output.txt').open('wb') as log:
        result = subprocess.run(['git', '-c', 'core.safecrlf=false', 'diff', '--check'], cwd=impl.ROOT, stdout=log, stderr=subprocess.STDOUT)
    assert result.returncode == 0
    dump(OUT / 'diff-check.json', {'exitCode': result.returncode, 'scope': 'Entire existing worktree', 'outputBytes': (OUT / 'diff-check-output.txt').stat().st_size})
    ledger = impl.load(impl.ROOT / 'seo-feed-review.json')
    assert set(ledger['pages']) == {name for name in impl.load(impl.ROOT / 'release-public-manifest.json')['files'] if name.endswith('.html')}
    next_text = '다음 단계는 최종 배포 준비 점검입니다. 전체 URL의 응답·리디렉션·수집 허용 상태 점검 범위와 배포 후 네이버 수집·색인·유입 확인 목록을 정리합니다. 실제 운영 변경은 별도 배포 요청 뒤에 진행합니다.'
    report = f'''코칭학원.com 10차 개선 완료 — 로컬 검증본, 운영 미배포
2026-10-02 / 순차 개선·배포 마지막 지시 유지

변경 내용
- vercel.json의 buildCommand 앞뒤에 본문·RSS·사이트맵 일치 검사를 연결했습니다.
- 앞 검사 통과 → 기존 공개 파일 복사 → 기존 wawa-04 방문통계 → 기존 설명 후처리 → 최종 출력 검사 순서입니다.
- Node 기본 모듈만 사용합니다. 배포 환경에서 제외되는 tools/ 폴더나 Python, 추가 npm 패키지에 의존하지 않습니다.
- 비공개 seo-feed-review.json에는 전체 HTML 8,403개와 RSS 50개를 함께 검토한 기록을 저장했습니다. 검사 도구와 JSON은 공개 manifest에서 제외됩니다.
- tools/review_seo_feeds.py는 현재 XML 구문, 전체 canonical·페이지/사이트맵 변경일, RSS 제목·본문 전체를 lxml로 대조합니다. 검토가 성공할 때만 비공개 입력을 저장합니다.
- 실제 배포 빌드는 해당 검토 기록과 실제 파일을 SHA256으로 대조합니다. 공개 manifest만 갱신해도 미검토 본문·피드 변경은 통과하지 못합니다.
- 검사 중 본문·피드·사이트맵·날짜를 자동 수정하지 않습니다. 기존 RSS 항목의 최초 발행일·GUID·동일 항목 순서도 재검토 시 보존합니다.
- Windows CRLF와 Linux LF를 지원하며, 동일한 내용 재검토 시 검토 JSON 바이트와 검토 시각을 보존합니다.

검증 결과
- 격리된 검증용 사본에서 21조건 통과: 정상 빌드, 오래된 RSS, 제목·본문 축약·발행일·GUID·도메인 불일치, XML 오류, sitemap 누락·중복·잘못된 날짜, 누락 파일, 비공개 입력 노출, 후처리 변경, 경로 이탈, 줄바꿈 호환, 재검토 안정성.
- 오류가 있으면 실제 설정된 buildCommand가 공개 출력 파일을 건드리기 전에 멈추는 것을 확인했습니다.
- 현재 실제 사이트의 빌드 5단계 통과. 시작/최종 검사 각각 HTML 8,403 / sitemap 8,403 / RSS 50 / 오류 0.
- 전체 공개 10,624파일의 최종 바이트 검증 통과. 기존 통계 스크립트가 필요한 5,225곳에 정확히 하나 추가되었고, 기존 3,178곳은 유지되었습니다. 기타 후처리 변경·비공개 원본 포함 0.
- 공개 원본 10,624파일과 기존 공개 manifest는 바이트 유지했습니다. RSS·sitemap·페이지 날짜 및 센터 자료·URL·페이지 목적은 변경하지 않았습니다.
- 공개 화면을 변경하지 않아 별도의 화면 재검증은 반복하지 않았습니다. 9차에서 확인한 공개 HTML과 모든 자산을 전수 바이트 대조했습니다.
- Vercel 업로드 제외 규칙과 확인: 루트의 검사 코드·검토 JSON은 제외되지 않으며 tools/는 제외됩니다. 공개 출력 whitelist와 마지막 검사로 비공개 입력 노출을 막습니다.
- 원본 작성 폴더의 HEAD·Git 상태 유지. 실패 시험의 사본은 비공개 결과 폴더에 보관했으며 원본 페이지를 변경하지 않았습니다.

작업 범위와 후속
- 이번 변경은 빌드 설정·검사 코드·비공개 검토 입력·로컬 검토/시험 도구입니다. 공개 웹페이지 변경은 0개입니다.
- Git commit/push/운영 배포/외부 계정·서치어드바이저·GSC 작업 미실행.
- 네이버 검색 수집·색인·순위·유입 개선을 이번 빌드 검증으로 확인한 것은 아닙니다.
- {next_text}

유지보수 설명: tools/SEO_FEED_REVIEW.md
실제 buildCommand: {impl.load(impl.ROOT / 'vercel.json')['buildCommand']}
변경 전 백업: phase9-before-phase10.zip
검증 자료와 생성 입력: 검증자료와생성입력.zip
공개 manifest SHA256(변경 없음): {BASE_SHA}
비공개 검토 JSON SHA256: {integration['ledgerSha256']}
참고: https://searchadvisor.naver.com/guide/request-feed
참고: https://www.sitemaps.org/protocol.html
참고: https://www.rssboard.org/rss-specification
'''
    (OUT / '작업결과.txt').write_bytes(report.replace('\n', '\r\n').encode('utf-8-sig'))
    url = OUT.as_posix()
    section = f'''## {TITLE}

- 사용자 순차 개선 및 배포 마지막 지시 유지. commit/push/운영 배포/외부 계정 작업 없음.
- vercel.json buildCommand 앞뒤에 Node 본문·RSS·사이트맵 검사를 추가. 기존 공개 파일 복사·방문통계·설명 후처리와 outputDirectory·redirects·headers 등 나머지 설정 유지.
- 루트 seo-feed-check.mjs와 비공개 seo-feed-review.json만으로 클라우드 검사 가능. tools/와 Python·추가 패키지는 빌드에 불필요. 두 파일은 공개 manifest에서 제외하며 최종 공개 출력의 비공개 파일 노출도 검사합니다.
- 로컬 review_seo_feeds.py가 XML·전체 canonical/변경일·RSS H1/본문 전체를 대조 후 기록합니다. 배포 빌드는 검토 해시와 실제 전체 파일을 비교하며 본문·날짜를 자동 수정하지 않습니다.
- 오류·정상·줄바꿈·재검토 등 21시험 통과. 공개 manifest만 갱신한 오래된 RSS도 차단하며 실패 시 실제 buildCommand가 공개 출력을 건드리지 않는지 확인.
- 실제 설정 빌드 5단계 및 전체 공개 10,624파일 최종 바이트 검증 통과. 시작/최종 HTML 8,403·sitemap 8,403·RSS 50 각각 오류 0, 비공개 원본 0. 기존 wawa-04 통계 1개씩 유지.
- 기존 공개 10,624파일·RSS·sitemap·manifest·페이지 날짜·센터 자료·원본 작성 폴더 상태 유지. 공개 화면 변경 0. 전체 실제 8,403/50 재검토 시 JSON·검토 시각 바이트 유지도 확인.
- [작업결과](<{url}/작업결과.txt>) / [검증자료와생성입력](<{url}/검증자료와생성입력.zip>) / [변경 전 백업](<{url}/phase9-before-phase10.zip>).
- 변경 없는 공개 manifest SHA256 `{BASE_SHA}`. 새 비공개 검토 JSON SHA256 `{integration['ledgerSha256']}`. 네이버 수집·색인·순위·유입 미측정.
- 도구 review_seo_feeds.py, test_seo_feed_check.py, build/report_neighborhood_phase10.py; 유지보수 tools/SEO_FEED_REVIEW.md 참고. 이전 생성기로 최신 개선본을 덮어쓰지 않습니다.
- {next_text}

'''
    handoffs = [impl.ROOT / 'NEIGHBORHOOD_SEO_HANDOFF.md', FOLDER / 'PROJECT_HANDOFF.md', FOLDER / 'CHANGELOG.md']
    for file in handoffs:
        text = file.read_text('utf-8')
        if TITLE in text: continue
        if file.name == 'PROJECT_HANDOFF.md':
            text = text.replace(text.splitlines()[2], '최신 갱신: 2026-10-02. 10차 본문·RSS·사이트맵 일치 검사를 실제 배포 빌드에 연결했습니다. 배포는 마지막에 수행합니다. 현재는 전체 검증된 로컬 개선본이며 네이버 검색 성과는 별도 확인 대상입니다.', 1)
        if file.name == 'CHANGELOG.md': text = text.rstrip() + '\n\n' + section
        else:
            index = text.find('\n## '); assert index > 0
            text = text[:index] + '\n\n' + section + text[index + 1:]
        file.write_text(text, 'utf-8')
    scripts = [impl.ROOT / 'tools' / name for name in ['review_seo_feeds.py', 'test_seo_feed_check.py', 'build_neighborhood_phase10.py', 'report_neighborhood_phase10.py', 'verify_neighborhood_build.py']]
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
    archive_path = OUT / '검증자료와생성입력.zip'; included = {}
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=5) as archive:
        def add(file, name):
            assert name not in included
            archive.write(file, name); included[name] = digest(file)
        for file in sorted(OUT.iterdir()):
            if file.is_file() and file.suffix in {'.json', '.log', '.txt'} and file.name not in ['diff-check-output.txt', 'archive-verification.json']:
                add(file, 'phase10/' + file.name)
        add(OUT / 'phase9-before-phase10.zip', 'phase10/phase9-before-phase10.zip')
        for file in sorted(dependencies.values()): add(file, 'tools/' + file.name)
        add(impl.ROOT / 'tools/SEO_FEED_REVIEW.md', 'tools/SEO_FEED_REVIEW.md')
        for name in ['seo-feed-check.mjs', 'seo-feed-review.json', 'vercel.json', 'release-public-build.mjs', 'wawa-analytics-build.mjs', 'seo-descriptions.mjs', 'seo-descriptions.json', 'release-public-manifest.json']:
            add(impl.ROOT / name, 'build-inputs/' + name)
        for file in sorted(impl.DATA.glob('*.json')): add(file, 'fact-inputs/' + file.name)
        fixture = Path(tests['fixtureDirectory']) / 'baseline'
        assert fixture.resolve().is_relative_to(OUT.resolve())
        for file in sorted(fixture.rglob('*')):
            if file.is_file() and '.public-release' not in file.parts:
                add(file, 'test-baseline/' + file.relative_to(fixture).as_posix())
        for file in handoffs: add(file, 'handoff/' + file.name)
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None and set(archive.namelist()) == set(included)
        for name, expected in included.items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == expected, name
    dump(OUT / 'archive-verification.json', {'file': archive_path.name, 'members': len(included), 'bytes': archive_path.stat().st_size, 'sha256': digest(archive_path), 'crcVerified': True, 'allMemberHashesVerified': True, 'deployed': False})
    assert digest(impl.ROOT / 'release-public-manifest.json') == BASE_SHA
    print(json.dumps({'report': str(OUT / '작업결과.txt'), 'archiveMembers': len(included), 'htmlPages': 8403, 'rssItems': 50, 'failureScenariosPassed': 21, 'deployed': False}, ensure_ascii=False), flush=True)

if __name__ == '__main__': main()
