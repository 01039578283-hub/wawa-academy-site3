"""Record only fully verified phase-9 local delivery and archive its evidence."""
import ast, hashlib, json, subprocess, zipfile
from pathlib import Path
import improve_neighborhood_pages as impl
from improve_neighborhood_phase9 import OUT, BACKUP, BASE_SHA, digest
from audit_neighborhood_phase6 import dump, state

FOLDER = Path(r'C:\Users\1992k\Desktop\홈페이지 작업 폴더\00_프로젝트 인수인계\코칭학원.com')
TITLE = '2026-10-01 — 9차 RSS 현재 본문·발행 정보 정비 완료, 운영 미배포'

def main():
    feed = impl.load(OUT / 'validation.json'); output_feed = impl.load(OUT / 'output-feed-validation.json')
    site = impl.load(OUT / 'all-site-validation.json'); build = impl.load(OUT / 'build-verification.json')
    release = impl.load(OUT / 'reviewed-release-state.json'); review = impl.load(OUT / 'reviewed-feed.json')
    pipeline = impl.load(OUT / 'build-pipeline.json'); ui = impl.load(OUT / 'rss-preview-checks.json')
    assert feed['errors'] == output_feed['errors'] == site['errors'] == build['errors'] == []
    assert feed['items'] == output_feed['items'] == 50 and site['sitemapPages'] == build['htmlPages'] == 8403
    assert build['publicFiles'] == 10624 and build['privateSourceFiles'] == 0
    assert len(pipeline) == 4 and all(r['exitCode'] == 0 for r in pipeline)
    assert {(r['index'], r['width']) for r in ui} == {(i, w) for i in [1, 33, 50] for w in [320, 390, 1280]}
    assert all(r['width'] >= r['scrollWidth'] and r['linksSeparated'] and not r['closedAccordions'] and len(r['strongQuestions']) == 5 and all(im['complete'] and im['width'] for im in r['images']) for r in ui)
    assert impl.load(OUT / 'browser-cleanup.json')['viewportReset'] and impl.load(OUT / 'preview-cleanup.json')['ownedServersStopped']
    assert impl.load(OUT / 'diff-check.json')['exitCode'] == 0
    manifest_path = impl.ROOT / 'release-public-manifest.json'
    assert digest(manifest_path.read_bytes()) == release['manifestSha256'] == build['reviewedManifestSha256']
    assert release['changedFiles'] == ['rss.xml'] and release['unchangedHtmlPages'] == 8403
    original = state(); assert original == impl.load(OUT / 'original-source-state.json')
    dump(OUT / 'original-source-state-after.json', original)
    untouched_inputs = impl.load(OUT / 'input-hashes.json')
    assert all(digest((impl.ROOT / name).read_bytes()) == expected for name, expected in untouched_inputs.items())
    before = (impl.ROOT / 'rss.xml').read_bytes(); before_manifest = manifest_path.read_bytes()
    # Re-running the accepted generator must not fake freshness on each build.
    result = subprocess.run([__import__('sys').executable, '-X', 'utf8', 'tools/improve_neighborhood_phase9.py', 'apply'], cwd=impl.ROOT, capture_output=True)
    assert result.returncode == 0 and (impl.ROOT / 'rss.xml').read_bytes() == before and manifest_path.read_bytes() == before_manifest
    dump(OUT / 'idempotence.json', {'rssBytesUnchanged': True, 'manifestBytesUnchanged': True, 'publicationDatesUnchanged': True, 'lastBuildDateUnchanged': True, 'exitCode': result.returncode})
    next_text = '다음 개선: 실제 배포 빌드에 RSS·사이트맵 일치 검사를 연결해, 이후 페이지를 수정할 때 피드 갱신 누락을 자동으로 차단합니다. 이번에는 외부 계정과 배포 설정을 변경하지 않았습니다.'
    report = f'''코칭학원.com 9차 개선 완료 — 로컬 검증본, 운영 미배포
2026-10-01 / 사용자의 순차 개선·배포 마지막 요청

변경 내용
- 기존 RSS 50개 항목의 제목을 현재 H1에 맞추고, 현재 main 본문 전체를 description에 반영했습니다. 영어·수학, 학년별 32개와 과목 전체 18개 항목입니다.
- 수강·위치 안내, 엑셀 기준 학년, 확인 필요 문구, 운영 참고 조건과 교습비 원문의 기준일·단위를 그대로 보존했습니다.
- FAQ 답변 {feed['faqAnswersPreserved']}개 / 교습비 표 {feed['feeTablesPreserved']}개 / 본문 이미지 {feed['checkedVisibleImages']}개를 대조했습니다.
- 숨김 대표 이미지와 빈 숨김 앵커 68개는 피드 본문에서 제외했습니다. 홈페이지의 기존 숨김 대표 이미지 구성은 변경하지 않았습니다.
- RSS 리더에서 모든 FAQ·교습비를 읽을 수 있도록 접힘 UI를 펼친 본문으로 변환하고 링크 간격을 추가했습니다. 링크·이미지 URL을 절대 주소로 변환했습니다.
- 기존 50개 URL·GUID·발행일·순서 유지. 채널 이름·설명과 실제 RSS 변경 시각(lastBuildDate)을 정비했습니다. 페이지 작성일·변경일·sitemap lastmod는 변경하지 않았습니다.

최종 검증
- RSS XML 정상 / 50개 본문 전체 대조 / 링크 {feed['internalAndOriginalExternalLinks']}개와 내부 앵커 {feed['checkedInternalFragments']}개 검사 / 최종 오류 0.
- RSS {feed['rssBytes']:,}바이트, 네이버 10MB 제한 이내. sitemap의 전체 8,403 URL 유지.
- 전체 HTML 8,403의 canonical·H1·설명·스키마·링크·도달성·학년 자료 검사 오류 0. 엑셀 기준 센터 192곳 대조 통과.
- 전 단계 공개 파일 10,624개와 대조: RSS 1파일만 변경, 나머지 10,623파일(HTML 8,403 + 기타 2,220개) 바이트 유지. 검토 manifest 별도 갱신.
- 로컬 공개 빌드 4단계 통과 / 전체 공개 파일 10,624개 바이트 대조 통과 / 비공개 원본 포함 0.
- 비공개 RSS 본문 검토 화면 3곳 × 320/390/1280px = 9조건 통과. 이는 검토용 화면이며 RSS 리더별 표시 디자인은 다를 수 있습니다.
- 생성기 재실행 시 RSS·발행일·갱신 시각·manifest 바이트 유지. 원본 작성 폴더의 HEAD·Git 상태 유지. 검토용 탭·서버 종료, 화면 크기 복원.

작업 범위와 후속
- Git commit/push/운영 배포/서치어드바이저 제출/색인 요청 미실행.
- 네이버 수집·색인·검색 순위·유입 변화는 이번 로컬 검증으로 확인하지 않았습니다.
- {next_text}
- 이전 생성기로 최신 개선본을 덮어쓰지 않습니다. 이번 RSS 생성기는 검토한 50개 원본 페이지가 달라지면 다시 검토해야 합니다.

최종 manifest SHA256: {release['manifestSha256']}
RSS SHA256: {digest(before)}
검토 입력: reviewed-feed.json / 원본 상태: original-source-state*.json
변경 전 백업: phase8-before-phase9.zip
검증 자료와 생성 입력: 검증자료와생성입력.zip
도구: tools/improve_neighborhood_phase9.py, build_neighborhood_phase9.py, report_neighborhood_phase9.py
참고: https://searchadvisor.naver.com/guide/request-feed
참고: https://www.rssboard.org/rss-specification
'''
    (OUT / '작업결과.txt').write_bytes(report.replace('\n', '\r\n').encode('utf-8-sig'))
    url = OUT.as_posix()
    section = f'''## {TITLE}

- 사용자 순차 개선 및 배포 마지막 지시 유지. commit/push/배포/외부 계정 작업 없음.
- 기존 RSS 50개(학년별 32 + 과목 전체 18)의 제목·전체 본문을 현재 수강·위치 목적에 정렬. 원래 URL·GUID·발행일·순서를 보존하고 실제 피드 내용 변경 시각만 갱신했습니다.
- FAQ 250답변·교습비 57표·가시 이미지 284개, 링크 1,954개·내부 앵커 878개 검증. 학년 확인 필요·원문 기준일·단위·현재 모집 확인 문구와 센터 입력 보존.
- RSS 리더용 접힘 해제·링크 절대 주소/간격 보완. 숨김 요소 68개 피드 제외, 원래 홈페이지 이미지 구성 유지. RSS {feed['rssBytes']:,}바이트.
- 나머지 공개 10,623파일(HTML 8,403 + 기타 2,220개) 바이트 유지; 공개 변경은 RSS 1개. sitemap 8,403 URL 유지. 전체 SEO·자료 대조 및 로컬 공개 10,624파일 빌드 검증 오류 0 / 비공개 원본 0.
- RSS 검토 화면 3곳×3폭=9조건, 생성기 재실행 바이트·시각 유지 확인. 검토 탭/서버 종료·화면 크기 복원·원본 작성 폴더 상태 유지.
- [작업결과](<{url}/작업결과.txt>) / [검증자료와생성입력](<{url}/검증자료와생성입력.zip>) / [변경 전 백업](<{url}/phase8-before-phase9.zip>).
- 최종 manifest SHA256 `{release['manifestSha256']}`. 실제 네이버 수집·색인·순위·유입 미측정. 참고 https://searchadvisor.naver.com/guide/request-feed 및 https://www.rssboard.org/rss-specification .
- {next_text}
- 도구 improve/build/report_neighborhood_phase9.py와 검토 입력·불변 백업 사용. 기존 release-public-build.mjs의 공개 파일 보호는 유지했습니다. 이전 생성기로 최신 개선본을 덮어쓰지 않습니다.

'''
    handoffs = [impl.ROOT / 'NEIGHBORHOOD_SEO_HANDOFF.md', FOLDER / 'PROJECT_HANDOFF.md', FOLDER / 'CHANGELOG.md']
    for path in handoffs:
        text = path.read_text('utf-8')
        if TITLE in text:
            continue
        if path.name == 'PROJECT_HANDOFF.md':
            text = text.replace(text.splitlines()[2], '최신 갱신: 2026-10-01. 9차 RSS 현재 본문·발행 정보 개선을 반영했습니다. 배포는 마지막에 수행합니다. 현재는 전체 검증된 로컬 개선본이며 네이버 검색 성과는 별도 확인 대상입니다.', 1)
        if path.name == 'CHANGELOG.md':
            text = text.rstrip() + '\n\n' + section
        else:
            index = text.find('\n## '); assert index > 0
            text = text[:index] + '\n\n' + section + text[index + 1:]
        path.write_text(text, 'utf-8')
    dependencies = {}; pending = [impl.ROOT / 'tools' / n for n in ['improve_neighborhood_phase9.py', 'build_neighborhood_phase9.py', 'report_neighborhood_phase9.py', 'verify_neighborhood_build.py']]
    while pending:
        path = pending.pop()
        if path.name in dependencies:
            continue
        dependencies[path.name] = path
        for node in ast.walk(ast.parse(path.read_text('utf-8'))):
            imports = [node.module] if isinstance(node, ast.ImportFrom) else [a.name for a in node.names] if isinstance(node, ast.Import) else []
            for name in imports:
                if name:
                    local = impl.ROOT / 'tools' / (name.split('.')[0] + '.py')
                    if local.exists():
                        pending.append(local)
    destination = OUT / '검증자료와생성입력.zip'; included = {}
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, compresslevel=5) as archive:
        def add(path, name):
            assert name not in included
            archive.write(path, name); included[name] = digest(path.read_bytes())
        for path in sorted(OUT.rglob('*')):
            if path.is_file() and path.suffix in {'.json', '.txt', '.log', '.html', '.png'} and path.name not in ['archive-verification.json', 'diff-check-output.txt']:
                add(path, 'phase9/' + path.relative_to(OUT).as_posix())
        add(BACKUP, 'phase9/' + BACKUP.name)
        for path in sorted(dependencies.values()):
            add(path, 'tools/' + path.name)
        for name in ['release-public-build.mjs', 'wawa-analytics-build.mjs', 'seo-descriptions.mjs', 'vercel.json', 'seo-descriptions.json']:
            add(impl.ROOT / name, 'build-inputs/' + name)
        add(impl.ROOT / 'rss.xml', 'reviewed-public/rss.xml')
        add(manifest_path, 'reviewed-public/release-public-manifest.json')
        for path in sorted(impl.DATA.glob('*.json')):
            add(path, 'fact-inputs/' + path.name)
        for path in handoffs:
            add(path, 'handoff/' + path.name)
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None and set(archive.namelist()) == set(included)
        for name, expected in included.items():
            assert digest(archive.read(name)) == expected, name
    dump(OUT / 'archive-verification.json', {'file': destination.name, 'members': len(included), 'bytes': destination.stat().st_size, 'sha256': digest(destination.read_bytes()), 'crcVerified': True, 'allMemberHashesVerified': True, 'deployed': False})
    assert digest(manifest_path.read_bytes()) == release['manifestSha256']
    print(json.dumps({'report': str(OUT / '작업결과.txt'), 'archiveMembers': len(included), 'publicFiles': 10624, 'rssItems': 50, 'deployed': False}, ensure_ascii=False), flush=True)

if __name__ == '__main__':
    main()
