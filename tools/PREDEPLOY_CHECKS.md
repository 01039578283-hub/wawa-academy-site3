# 코칭학원.com 배포 전 검사와 배포 후 확인

현재 사용자 지시는 **배포를 마지막에 수행**하는 것입니다. 아래 도구와
확인표를 준비했지만 commit/push/운영 배포/서치어드바이저 계정 작업은
실행하지 않았습니다. 순차 개선본은 기존 분리 작업 공간에 보존합니다.

## 현재 로컬 점검 결과

- 공개 HTML 8,403개, 공개 파일 총 10,624개를 대상으로 합니다.
- sitemap과 canonical, RSS 발견 링크, Yeti 수집 허용, 공개 페이지의
  noindex/nofollow·meta refresh 및 미공개 내부 링크를 전수 대조했습니다.
- `@vercel/routing-utils@6.6.0`으로 현재 vercel.json 규칙을 변환했습니다.
- 공개 파일 GET, 페이지 HEAD, 쿼리 유지, index.html 주소 및 슬래시 변형,
  존재하지 않는 주소와 비공개 경로를 합쳐 46,476조건을 검사했습니다.
- 12개 연결을 재사용한 최종 로컬 HTTP 검사는 모두 통과했습니다.
  첫 실행은 Windows 연결 한도에 걸렸고 비공개 결과 폴더에 기록을 보관했습니다.
- 공개 본문·URL·날짜·robots.txt·RSS·sitemap·배포 설정은 변경하지 않았습니다.
  공식 도구의 규칙 변환과 로컬 파일 응답 검사이며 Vercel 배포 관측은 아닙니다.

로컬 서버는 `.public-release`의 공개 허용 목록만 읽고 127.0.0.1에만
바인딩합니다. 임시 포트를 사용하고 검사 종료 시 닫습니다. 미리보기
응답에는 `noindex, nofollow`와 `no-store`를 추가합니다. 이 값은
vercel.json 또는 운영 HTML에 기록하지 않습니다.

## 재검사

전체 내용 검토와 실제 배포 빌드 검사 방법은 `SEO_FEED_REVIEW.md`를
따릅니다. 기존 단계별 생성기로 최신 개선본을 덮어쓰지 않습니다.

```powershell
python -X utf8 tools/audit_neighborhood_phase11.py
node tools/check_neighborhood_http.mjs --mode=local --inputs="C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase11-20261002/http-inputs.json" --out="C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase11-20261002" --routing-utils="C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase11-20261002/routing-runtime/node_modules/@vercel/routing-utils"
```

이 단계의 감사 도구는 현재 검증본의 manifest를 고정합니다. 공개 내용이
바뀌면 기존 보고서를 최신 결과로 재사용하지 말고 새 작업 범위·백업과
전체 내용/빌드 검증을 완료한 뒤 감사 입력을 갱신합니다. 미래 릴리스는
이전 단계의 날짜·해시 고정을 느슨하게 해서 통과시키지 않습니다.

## 마지막 배포를 요청받은 뒤

1. 현재 개선 작업 공간의 변경 범위와 검증 기록을 검토합니다. dirty 원본
   작성 폴더를 덮어쓰지 않고, 검증한 개선본만 릴리스에 포함합니다.
2. 실제 대상 프로젝트·운영 도메인·commit SHA를 확인합니다. 실제 설정된
   전체 빌드의 시작/종료 검사를 통과한 개선본을 배포하고 READY와 운영
   alias가 같은 배포를 가리키는지 확인합니다.
3. 실제 도메인에서 전체 페이지·파일·리디렉션 응답을 다시 검사합니다.
   HTTP→HTTPS, www/기본 vercel.app 호스트 처리, TLS·DNS·대시보드 라우팅
   및 봇 차단은 로컬 코드만으로 확인되지 않으므로 별도로 확인합니다.
4. 로컬 미리보기의 noindex가 운영 응답에 없고, robots.txt는 text/plain,
   RSS·sitemap은 XML이며 모두 정상 응답인지 확인합니다. index.html과
   슬래시 변형은 308로 자기 페이지 대표 주소에 도착해야 합니다.
   없는 페이지는 최종 404여야 하며 홈페이지 200으로 대체하지 않습니다.
5. 모바일·PC에서 개선된 페이지 목적, 확인 필요 학년 표시, 교육비 자료,
   문의 동작을 확인합니다. 서로 다른 목적의 동네 페이지를 유지합니다.

실제 배포 후 전체 HTTP 재검사 명령은 다음과 같습니다. **현재는 실행하지
않았습니다.** 약 46,476회의 읽기 전용 GET/HEAD를 수행하며 배포·계정
작업·페이지 수정은 하지 않습니다. 프로덕션만을 대상으로 합니다.

```powershell
node tools/check_neighborhood_http.mjs --mode=public --base=https://xn--sp5b72l1taf0p.com --inputs="C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase11-20261002/http-inputs.json" --out="C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase11-20261002/postdeployment"
```

운영 전용 헤더와 MIME, 정확한 파일 내용도 대조합니다. Windows CRLF와
Linux LF만 동일한 텍스트로 허용하며, 서로 다른 본문은 통과하지 않습니다.
별도 호스트의 리디렉션 또는 방화벽·대시보드 정책은 위 CLI가 검사하는
대표 HTTPS 호스트와 구분하여 기록합니다.

## 네이버 성과 확인

실제 검색 성과는 로컬 검사로 채우지 않습니다. 비공개 결과 폴더의
`naver-followup-scope.json`은 전체 8,403 URL과 동네 페이지 8,162개의
확인 범위를 보관합니다. 관측하지 않은 값은 null이고 확인 상태는
`not_checked`입니다. 페이지의 과목/학년 주제는 운영 학년의 추가 확정이
아니며, 엑셀·확인 필요 표시는 그대로 유지합니다.

- 배포 후 계정 작업이 허용된 범위에서 소유 확인 사이트의 sitemap/RSS,
  robots 수집 상태와 수집 현황·사이트 진단을 확인합니다. 수집제한,
  색인제외, SEO 문제에 실제 제공된 URL을 기존 페이지 목록과 대조합니다.
- 노출·클릭 리포트의 실제 업데이트 기준일과 관측 기간을 기록합니다.
  공식 안내상 약 1주 지연, 최근 90일, 키워드·웹문서 TOP 30 범위가
  있으므로 그 목록에 없는 URL을 노출/클릭 0 또는 미색인으로 단정하지
  않습니다. 사이트 진단의 다운로드 URL 역시 최대 2,000건 범위입니다.
- 광고·블로그 영역은 웹 검색 리포트와 구분합니다. 제공되는 URL/키워드
  노출·클릭과 방문통계의 네이버 유입을 같은 기간으로 맞춰 대조합니다.
  검색어가 제공되지 않은 방문에서 검색 키워드를 추정하여 채우지 않습니다.
- 371개 동네와 과목·학년·페이지 목적별로 수집 및 실제 성과를 분리합니다.
  노출 없음은 수집/색인부터, 노출 있으나 클릭 적음은 검색어와 제목/설명,
  유입 있으나 문의 적음은 상담 경로를 근거로 다음 개선을 선택합니다.
- 검색 결과를 직접 확인할 때는 검색어·날짜·PC/모바일·검색 영역과 실제
  노출 URL을 함께 남깁니다. site: 검색 결과의 수만으로 전체 URL의 색인
  여부나 특정 키워드 순위를 확정하지 않습니다.

참고:
- https://searchadvisor.naver.com/guide/seo-basic-http
- https://searchadvisor.naver.com/guide/seo-basic-robots
- https://searchadvisor.naver.com/guide/report-crawl-refine
- https://searchadvisor.naver.com/guide/report-diagnosis
- https://searchadvisor.naver.com/guide/report-expose-ctr
- https://vercel.com/docs/routing/redirects/configuration-redirects
- https://vercel.com/docs/routing/redirects
