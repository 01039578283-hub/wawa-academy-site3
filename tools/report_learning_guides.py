"""Archive verified local guides and update only this project's handoffs."""
import hashlib,json,re,zipfile,subprocess
from pathlib import Path
from build_learning_guides import ROOT,OUT,DOMAIN,CATEGORIES,articles,dump,digest

def load(name):return json.loads((OUT/name).read_text('utf-8-sig'))

def main():
    validation=load('validation.json');http=load('http/http-verification.json');responsive=load('responsive-guides.json');tops=load('responsive-existing-hubs.json');source=load('source-preservation.json');idem=load('idempotence.json');download=load('download-verification.json')
    manifest_sha=digest((ROOT/'release-public-manifest.json').read_bytes())
    assert validation['errors']==[] and http['errorCount']==0 and http['completedCases']==46851
    assert http['manifestSha256']==manifest_sha and http['inputsSha256']==digest((OUT/'http-inputs.json').read_bytes())
    assert responsive['errors']==[] and responsive['views']==165 and tops['errors']==[] and tops['views']==24
    assert source['same'] and idem['checks']['release-public-manifest.json']==manifest_sha and download['filesystemVerificationPassed']
    assert subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,check=True,capture_output=True,text=True).stdout.strip()==source['worktreeHead']
    log=(OUT/'configured-build.log').read_text('utf-8')
    final=json.loads(log.strip().splitlines()[-1]);assert final['ok'] and final['mode']=='built-output' and final['errorCount']==0
    rows=articles()
    result='코칭학원.com 학습가이드 생성 결과 — 2026-10-02\n\n'
    result+='완료: 독립 원고 48개, 주제별 목록 6개, 전체 목록 1개, 빈 기록표 48개.\n'
    result+='인터넷의 교육부·EBS·학교알리미·고교학점제 자료와 IES·EEF 연구 안내를 확인했습니다.\n'
    result+='참고 사이트의 구성과 질문 범위만 참고하고 글·예시·기록표는 새로 작성했습니다.\n'
    result+='학교별 출제·평가 및 센터의 개설 과목·학년·비용·수업 형태·성과는 추측해 추가하지 않았습니다.\n'
    result+='요청에 따라 공개 페이지에 편집 원칙·정책 언급은 넣지 않았습니다.\n\n'
    result+='기능: 검색·대상/주제 필터·목차·FAQ·관련 글·빈 TXT 다운로드·기록 작성/저장·인쇄.\n'
    result+='기록표의 입력은 서버 전송·자동 저장 없이 해당 페이지에만 유지됩니다.\n'
    result+='다운로드된 한글 TXT 파일의 네 항목과 줄바꿈을 실제 파일로 확인했습니다.\n'
    result+='인쇄 명령은 호출했습니다. 네이티브 인쇄창 때문에 자동 화면 검증이 중단되어 검증 탭을 닫았으며 실제 종이/PDF 출력은 확인하지 않았습니다.\n\n'
    result+='검증: 공개 파일 10,729개 전체 비교, HTML/사이트맵 8,458개, RSS 98개 일치.\n'
    result+='기존 8,403개 URL과 RSS 50개 발행 정보·상대 순서·본문 보존. 변경한 기존 주요 페이지 6개는 본문 보존 후 메뉴·가이드 연결만 추가했습니다.\n'
    result+='새 페이지 55개 내부 링크 1,721개·앵커 494개·메타/구조화 데이터·예시·기록표 전수 통과.\n'
    result+='새 페이지 55개 × 320/390/1280px = 165화면, 기존 주요 메뉴 6개 × 4크기 = 24화면 오류 0.\n'
    result+='공식 Vercel 라우팅 규칙을 사용한 로컬 HTTP 46,851조건 오류 0. 실제 운영/CDN 응답 검사는 아닙니다.\n'
    result+='vercel.json의 전체 5단계 빌드와 재생성 동일성 확인. 기존 본문·날짜·사실 자료 보존.\n\n'
    result+='운영 상태: 이번 학습가이드 변경의 commit/push/배포/검색 계정 작업은 하지 않았습니다.\n'
    result+='이전 동네 SEO 운영 배포는 2e9e200c745ec7a91eeb9d03cae55faaaa6082d3 / dpl_Bte45zAYrWT5b4W2cD8c6PC4jc4h입니다. 이번에는 그 이후의 로컬 변경만 있습니다.\n'
    result+='미리보기: http://127.0.0.1:8863/학습가이드/\n작업 공간: '+str(ROOT)+'\n'
    result+='manifest SHA256: '+manifest_sha+'\n\n'
    for key,(_,name,_) in CATEGORIES.items():
        result+=name+' — 8개\n'
        for r in [r for r in rows if r['category']==key]:result+='  '+r['title']+'\n    예정 경로: /학습가이드/'+r['slug']+'/\n'
        result+='\n'
    result+='재현: tools/data/learning-guides는 비공개·Git 제외 입력입니다. 검증자료 ZIP의 inputs/learning-guides를 같은 위치에 복원하세요.\n'
    result+='생성기는 이 작업의 48개 원고와 기준 백업을 전제로 합니다. 이후 범위가 바뀌면 원고·검증 범위·검토 해시를 함께 갱신해야 합니다.\n'
    result+='순서: build_learning_guides.py → review_seo_feeds.py → vercel.json의 전체 buildCommand → audit_learning_guides.py → 전체 로컬 HTTP·화면 검증. 옛 고정 8,403페이지 도구로 현재 결과를 덮어쓰지 않습니다.\n'
    (OUT/'작업결과.txt').write_text(result,'utf-8')
    handoff='## 2026-10-02 — 학습가이드 48개 신규 생성, 로컬 완료·운영 미배포\n\n'
    handoff+='- 사용자 요청: 전국수업.com/학습가이드와 daezang.co.kr/guides 구성을 참고해 코칭학원.com에 학생·학부모 가이드 생성. 공개 페이지에는 편집 원칙 언급 제외.\n'
    handoff+='- 전체 목록 1 + 주제 목록 6 + 독립 글 48 = 새 HTML 55. 시험·전환/수학/영어/국어·사회·과학·발표/공부 습관/학부모 상담·선택 각 8개. 각 글에 답·점검·4단계·연습 예시/표·서로 다른 기록표·FAQ·관련 글·1차 출처.\n'
    handoff+='- 검색·대상/주제 필터, 빈 TXT 48개, 작성 내용 TXT 저장·초기화·인쇄 기능. 입력 서버 전송·자동 저장 없음. 실제 다운로드·한글 네 항목 확인. 인쇄창 호출만 확인하고 실제 출력 미확인.\n'
    handoff+='- 기존 주요 메뉴 6곳에 링크·안내 추가. 기존 8,403 URL, RSS 50개 발행 정보·본문·순서, 동네/센터 사실 및 원본 작성 폴더 상태 보존. 학교 평가/센터 개설 과목·비용·성과 추측 없음.\n'
    handoff+='- 공개 10,729파일/HTML·sitemap 8,458/RSS 98 전수 비교·일치. 내부 링크 1,721/앵커 494, 새 55페이지 165화면 + 기존 6곳 24화면, 공식 라우팅 기반 로컬 HTTP 46,851조건 오류 0. 전체 5단계 빌드·재생성 동일성 통과.\n'
    handoff+='- 작업 공간 '+str(ROOT)+'. HEAD `'+source['worktreeHead']+'`. 이번 요청의 commit/push/배포/검색 계정 작업 없음. 이전 운영 배포 `dpl_Bte45zAYrWT5b4W2cD8c6PC4jc4h` 기록 유지. 새 가이드는 운영 반영 전이며 별도 배포 요청이 필요합니다.\n'
    handoff+='- 결과 '+str(OUT/'작업결과.txt')+' / 검증자료 '+str(OUT/'학습가이드-원고와검증자료.zip')+'. 미리보기 http://127.0.0.1:8863/학습가이드/ (loopback·noindex/no-store).\n'
    handoff+='- 도구 build_learning_guides.py, seo_feed_content.py, audit_learning_guides.py, preview_learning_guides.py, report_learning_guides.py. tools/data/learning-guides는 Git 제외 입력으로 ZIP에서 복원합니다. 기존 고정 8,403페이지 생성기/검사기를 그대로 재실행하지 않습니다. 현재 생성기는 48개와 이번 기준 백업을 전제로 합니다.\n'
    handoff+='- 공개 반영 후 실제 도메인 검사와 네이버 검색 성과 관측은 별도입니다. 로컬 검사만으로 수집·순위·유입 개선을 확인했다고 말하지 않습니다.\n\n'
    own=Path(r'C:\Users\1992k\Desktop\홈페이지 작업 폴더\00_프로젝트 인수인계\코칭학원.com')
    for destination in [ROOT/'NEIGHBORHOOD_SEO_HANDOFF.md',own/'PROJECT_HANDOFF.md']:
        text=destination.read_text('utf-8-sig')
        if handoff.splitlines()[0] not in text:
            if text.startswith('# '):
                first,rest=text.split('\n',1);text=first+'\n\n'+handoff+rest.lstrip('\n')
            else:text=handoff+text
            if destination.name=='PROJECT_HANDOFF.md':text=re.sub(r'^최신 갱신:.*$', '최신 갱신: 2026-10-02. 동네 SEO 운영 배포 이후, 새 학습가이드 48개와 목록·기록표의 로컬 생성·검증을 완료했습니다. 이번 새 가이드 변경은 아직 운영 미배포입니다.',text,flags=re.M)
            destination.write_text(text,'utf-8')
    change=own/'CHANGELOG.md';text=change.read_text('utf-8-sig')
    if handoff.splitlines()[0] not in text:change.write_text(text.rstrip()+'\n\n'+handoff,'utf-8')
    archive=OUT/'학습가이드-원고와검증자료.zip'
    inputs=list((ROOT/'tools/data/learning-guides').glob('*.json'))
    tools=[ROOT/'tools'/n for n in ['build_learning_guides.py','seo_feed_content.py','audit_learning_guides.py','preview_learning_guides.py','report_learning_guides.py','review_seo_feeds.py','check_neighborhood_http.mjs']]
    public_new=[ROOT/n for n in load('implementation.json')['newPublicFiles']]
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=5) as z:
        for path in inputs:z.write(path,'inputs/learning-guides/'+path.name)
        for path in tools:z.write(path,'tools/'+path.name)
        for path in public_new:z.write(path,'public/'+path.relative_to(ROOT).as_posix())
        for name in ['index.html','학습관리/index.html','전국센터/index.html','과목별학원/index.html','지점안내/index.html','상담문의/index.html','sitemap.xml','rss.xml','release-public-manifest.json','seo-descriptions.json','seo-feed-review.json','NEIGHBORHOOD_SEO_HANDOFF.md']:
            z.write(ROOT/name,'current/'+name)
        for path in sorted(OUT.rglob('*')):
            if path.is_file() and path!=archive and path.name!='archive-verification.json':z.write(path,'evidence/'+path.relative_to(OUT).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for path in inputs:assert z.read('inputs/learning-guides/'+path.name)==path.read_bytes()
        members=len(z.namelist())
    dump(OUT/'archive-verification.json',{'archive':str(archive),'bytes':archive.stat().st_size,'sha256':digest(archive.read_bytes()),'members':members,'crcVerified':True,'authoredInputsVerified':True,'deployed':False})
    print(json.dumps({'report':str(OUT/'작업결과.txt'),'archive':str(archive),'members':members,'crcVerified':True,'deployed':False},ensure_ascii=False))

if __name__=='__main__':main()
