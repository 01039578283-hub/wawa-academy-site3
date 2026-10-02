# 코칭학원.com 동네 페이지 개선 인수인계

2026-10-01. 운영 기준 커밋 `3c2b4695e058361a77c81afa065f2758735f22bb`에서 분리한 작업 공간입니다. 원본 작성 폴더의 기존 변경분은 보존했습니다. 이 작업에는 GitHub 푸시와 운영 배포가 포함되지 않습니다.










## 2026-10-02 — 11차 전체 URL·수집 설정 로컬 검사 및 배포 후 네이버 확인 범위 준비 완료

- 사용자 순차 개선·배포 마지막 지시 유지. commit/push/배포/외부 계정 작업 미실행.
- 공개 HTML 8,403·전체 파일 10,624·sitemap/RSS 발견·Yeti/기본 수집 허용·canonical·공개 noindex/nofollow·meta refresh·미공개 내부 링크 전수 오류 0. 공개 파일 및 설정 변경 없음.
- @vercel/routing-utils 6.6.0 공식 규칙 변환 + 로컬 HTTP 46,476조건 전부 통과. 전체 파일 GET 내용/MIME·HEAD·쿼리·index.html/슬래시 변형·없는/비공개 경로 확인. 308 자기 대표 주소 이동·최종 404·쿼리 유지.
- 첫 검사 Windows 연결 한도를 도구의 연결 재사용으로 해결하고 전수 재검사 완료. 최종 12연결/46,464회 재사용, 로컬 서버 종료. 첫 시도 증거도 비공개 보관.
- 기존 실제 로컬 빌드 10,624파일 전수 바이트/해시 대조, 원본 작성 폴더 및 사실 자료·본문·날짜·URL·기존 buildCommand/headers/redirects 유지. 공개 변경이 없어 새 빌드나 화면 검증은 반복하지 않음.
- 배포 후 확인 범위 JSON: 전체 8,403 URL/동네 8,162페이지/동네 371/지점 허브 193, 관측값 null/not_checked. 네이버 보고서의 지연·TOP 30·진단 URL 최대 2,000건 범위 반영. 미제공을 0/미색인으로 판단하지 않음.
- tools/audit_neighborhood_phase11.py, check_neighborhood_http.mjs, report_neighborhood_phase11.py, PREDEPLOY_CHECKS.md 추가. 새 도구는 비공개 tools/에 위치하고 공개 manifest에 포함하지 않음.
- 공식 변환+로컬 출력 검사이며 Vercel/CDN 실제 응답 또는 검색 수집·색인·순위·유입 개선 확인은 아님.
- [작업결과](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase11-20261002/작업결과.txt>) / [검증자료와확인범위](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase11-20261002/검증자료와확인범위.zip>) / [변경 전 백업](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase11-20261002/phase10-before-phase11.zip>).
- manifest SHA256 `ac8b06be27ae7e3c8c4e0e130cbf248707ebd966b00239d655beec20433230a7`, HTTP 입력 SHA256 `c5267ed62bbe58a974ce2f3bd8ef82265d2a26dddd988e2ae5d2a788db5998da`.
- 다음 단계는 사용자에게서 마지막 배포 요청을 받은 뒤 검증한 개선본을 배포하고, 실제 전체 URL 응답·운영 alias 및 네이버 수집·색인·노출·클릭·유입을 확인하는 것입니다. 현재는 배포와 계정 작업을 하지 않습니다.

## 2026-10-02 — 10차 본문·RSS·사이트맵 배포 빌드 일치 검사 연결 완료, 운영 미배포

- 사용자 순차 개선 및 배포 마지막 지시 유지. commit/push/운영 배포/외부 계정 작업 없음.
- vercel.json buildCommand 앞뒤에 Node 본문·RSS·사이트맵 검사를 추가. 기존 공개 파일 복사·방문통계·설명 후처리와 outputDirectory·redirects·headers 등 나머지 설정 유지.
- 루트 seo-feed-check.mjs와 비공개 seo-feed-review.json만으로 클라우드 검사 가능. tools/와 Python·추가 패키지는 빌드에 불필요. 두 파일은 공개 manifest에서 제외하며 최종 공개 출력의 비공개 파일 노출도 검사합니다.
- 로컬 review_seo_feeds.py가 XML·전체 canonical/변경일·RSS H1/본문 전체를 대조 후 기록합니다. 배포 빌드는 검토 해시와 실제 전체 파일을 비교하며 본문·날짜를 자동 수정하지 않습니다.
- 오류·정상·줄바꿈·재검토 등 21시험 통과. 공개 manifest만 갱신한 오래된 RSS도 차단하며 실패 시 실제 buildCommand가 공개 출력을 건드리지 않는지 확인.
- 실제 설정 빌드 5단계 및 전체 공개 10,624파일 최종 바이트 검증 통과. 시작/최종 HTML 8,403·sitemap 8,403·RSS 50 각각 오류 0, 비공개 원본 0. 기존 wawa-04 통계 1개씩 유지.
- 기존 공개 10,624파일·RSS·sitemap·manifest·페이지 날짜·센터 자료·원본 작성 폴더 상태 유지. 공개 화면 변경 0. 전체 실제 8,403/50 재검토 시 JSON·검토 시각 바이트 유지도 확인.
- [작업결과](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase10-20261002/작업결과.txt>) / [검증자료와생성입력](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase10-20261002/검증자료와생성입력.zip>) / [변경 전 백업](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase10-20261002/phase9-before-phase10.zip>).
- 변경 없는 공개 manifest SHA256 `ac8b06be27ae7e3c8c4e0e130cbf248707ebd966b00239d655beec20433230a7`. 새 비공개 검토 JSON SHA256 `85cb02d8722d78465df6684fc95176904dd07fc763d531637ac46fbec6d458d5`. 네이버 수집·색인·순위·유입 미측정.
- 도구 review_seo_feeds.py, test_seo_feed_check.py, build/report_neighborhood_phase10.py; 유지보수 tools/SEO_FEED_REVIEW.md 참고. 이전 생성기로 최신 개선본을 덮어쓰지 않습니다.
- 다음 단계는 최종 배포 준비 점검입니다. 전체 URL의 응답·리디렉션·수집 허용 상태 점검 범위와 배포 후 네이버 수집·색인·유입 확인 목록을 정리합니다. 실제 운영 변경은 별도 배포 요청 뒤에 진행합니다.

## 2026-10-01 — 9차 RSS 현재 본문·발행 정보 정비 완료, 운영 미배포

- 사용자 순차 개선 및 배포 마지막 지시 유지. commit/push/배포/외부 계정 작업 없음.
- 기존 RSS 50개(학년별 32 + 과목 전체 18)의 제목·전체 본문을 현재 수강·위치 목적에 정렬. 원래 URL·GUID·발행일·순서를 보존하고 실제 피드 내용 변경 시각만 갱신했습니다.
- FAQ 250답변·교습비 57표·가시 이미지 284개, 링크 1,954개·내부 앵커 878개 검증. 학년 확인 필요·원문 기준일·단위·현재 모집 확인 문구와 센터 입력 보존.
- RSS 리더용 접힘 해제·링크 절대 주소/간격 보완. 숨김 요소 68개 피드 제외, 원래 홈페이지 이미지 구성 유지. RSS 1,142,130바이트.
- 나머지 공개 10,623파일(HTML 8,403 + 기타 2,220개) 바이트 유지; 공개 변경은 RSS 1개. sitemap 8,403 URL 유지. 전체 SEO·자료 대조 및 로컬 공개 10,624파일 빌드 검증 오류 0 / 비공개 원본 0.
- RSS 검토 화면 3곳×3폭=9조건, 생성기 재실행 바이트·시각 유지 확인. 검토 탭/서버 종료·화면 크기 복원·원본 작성 폴더 상태 유지.
- [작업결과](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase9-20261001/작업결과.txt>) / [검증자료와생성입력](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase9-20261001/검증자료와생성입력.zip>) / [변경 전 백업](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase9-20261001/phase8-before-phase9.zip>).
- 최종 manifest SHA256 `ac8b06be27ae7e3c8c4e0e130cbf248707ebd966b00239d655beec20433230a7`. 실제 네이버 수집·색인·순위·유입 미측정. 참고 https://searchadvisor.naver.com/guide/request-feed 및 https://www.rssboard.org/rss-specification .
- 다음 개선: 실제 배포 빌드에 RSS·사이트맵 일치 검사를 연결해, 이후 페이지를 수정할 때 피드 갱신 누락을 자동으로 차단합니다. 이번에는 외부 계정과 배포 설정을 변경하지 않았습니다.
- 도구 improve/build/report_neighborhood_phase9.py와 검토 입력·불변 백업 사용. 기존 release-public-build.mjs의 공개 파일 보호는 유지했습니다. 이전 생성기로 최신 개선본을 덮어쓰지 않습니다.

## 2026-10-01 — 8차 지역·학년 목록 목적별 찾기 개선 완료, 운영 미배포

- 배포 마지막 지시 유지. commit/push/운영 배포 없음.
- 지역 목록 29개 + 학교급/과목 목록 6개 = 35곳에 목적별 동네 찾기 추가. 지역은 원래 목록의 동네만 표시하고 학교급/과목은 해당 값을 기본 선택합니다. 목적과 과목은 바꿀 수 있습니다.
- 두 지역 체계가 각각 전체 371동네를 나누는지 확인. 총 소속 2,968개 검증. 동네 연결 없는 실제 지점 5곳도 기존 목록에 보존했습니다. 기존 URL과 수강·학습·비교 목적 유지.
- 전체 HTML 8,403 중 35변경 / 8,368바이트 유지. 이전 홈·주요 목록 11곳 및 모든 동네·지점 HTML 보존. 공유 JS의 범위 기능·35개 설명/변경일·sitemap만 공개 변경, 총 37파일. 기존 동네 JSON·CSS·센터 입력 보존.
- 같은 지역 두 목적의 설명 중복을 구분해 전체 설명 검사 통과. 비공개 검토 입력도 해당 35개 설명/sources만 변경했고 나머지 항목 독립 대조 통과.
- 전체 링크·앵커·도달성·엑셀·H1·설명 검증 오류 0. 46곳 × 4화면 폭 = 184조건(최종 문장 24조건 재확인), 동작 20개, 마우스/키보드 이동·hover, 데이터 오류 시 원래 목록 유지 3곳 확인.
- 최종 로컬 공개 10,624파일 / HTML 8,403 / 비공개 원본 0 전체 바이트 대조 통과. 검증 화면 크기 복원, 탭/서버 종료, 원본 작성 폴더 상태 유지.
- [작업결과](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase8-20261001/작업결과.txt>) / [검증자료와생성입력](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase8-20261001/검증자료와생성입력.zip>) / [변경 전 백업](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase8-20261001/phase7-before-phase8.zip>).
- 최종 manifest SHA256 `77bd5a42a6454039b26f287c76d2492b13874198e32d04ac80a9b30411cbd792`. 검색 수집·색인·검색 순위·유입 변화 미측정.
- 다음 개선: RSS 50개 항목의 제목·본문·갱신 정보를 현재 페이지 목적과 실제 변경에 맞게 정비. 최초 발행일 차이만으로 오류 판단하지 않으며 전체 본문 공개와 모든 URL의 sitemap 유지 원칙을 검토합니다. 네이버 참고: https://searchadvisor.naver.com/guide/request-feed . 이번에는 읽기 전용 점검만 수행했습니다.
- audit/improve/validate/align/build/report_neighborhood_phase8.py, audit_next_feed_phase8.py 및 검토 입력·불변 백업 사용. 이전 생성기로 최신 결과를 되돌리지 않습니다.

## 2026-10-01 — 7차 홈·상위 목록 목적별 찾기 개선 완료, 운영 미배포

- 순차 개선 및 배포 마지막 지시 유지. commit/push/운영 배포 없음.
- 홈·지점안내·전국센터·과목별학원 및 일곱 분류 목록, 총 11곳에 동네·지역·지점 검색과 목적/과목/학교급 선택 기능 추가. 수강·위치, 진도·오답 점검, 비교·선택을 기존 URL로 연결합니다.
- 동네 371개 / 기존 동네 URL 8,162개 검토. 과목별 목록 2,597개 링크의 실제 목적과 ItemList 이름 정리. 기존 static 목록·동네명·href 유지. 새 페이지 생성·기존 페이지 삭제/통합 없음.
- 확인 필요 수강 대상 55개 표시, 학습·비교 목적 보존. 확정 엑셀 및 W+·마감·CSV 미매칭 조건 유지. 공개 JSON은 공개 이름·검토된 링크 허용 목록이며 원본 센터 메모를 포함하지 않습니다.
- 전체 HTML 8,403 중 11변경 / 8,392바이트 유지. 기존 1,152 학년 확인 표시와 41,775 FAQ 포함 이전 동네·지점 HTML 유지. 메타 설명 11개 ≤80자 및 동일 schema, 실제 변경일 반영.
- 전체 링크·앵커·도달성·엑셀·H1 검증 오류 0. 반응형 44조건·동작 16개·마우스/키보드 이동·hover·JSON 장애 시 기존 목록 유지 확인. 임시 화면 복원 및 검증 탭/서버 종료.
- 비공개 seo-descriptions.json의 해당 11개 검토 설명/sources만 정렬해 후처리 보호 검사 통과. 공개 10,624파일/HTML 8,403 전체 바이트 검증, 최종 diff 검사 통과. 원본 작성 폴더 상태 유지.
- [작업결과](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase7-20261001/작업결과.txt>) / [검증자료와생성입력](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase7-20261001/검증자료와생성입력.zip>) / [변경 전 백업](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase7-20261001/phase6-before-phase7.zip>).
- 최종 manifest SHA256 `8d32981b05f5698f6bda5c67b9ce61ffcf0a43ba5830bfbee019cb3cf82df7d9`. 네이버 수집·색인·검색 순위·유입 변화 미측정.
- 다음 개선: 읽기 전용 점검한 지역별·학년별 목록 35개(지역 29 + 학년/과목 6)에 해당 지역·학년·과목을 미리 선택하는 목적별 찾기 적용. 현재 예시 학년 불일치 0건. 이번에는 후보 점검만 수행했습니다.
- 7차 audit/improve/validate/build/align/report 도구와 검토 입력·불변 백업 사용. 복원 및 재현은 작업결과 참고. 이전 생성기로 최신 검토본을 되돌리지 않습니다.

## 2026-10-01 — 6차 학년 확인 링크 개선 완료, 운영 미배포

- 사용자 지시대로 순차 개선, 배포는 마지막에 진행합니다. commit/push/운영 배포 없음.
- 전체 8,403페이지의 모든 링크를 검사해 281페이지 / 1,152개 수강 링크에 '자료상 학년 확인 필요'를 표시했습니다. 대상 수강 URL 55개. 이전 관련 안내 545개에서 FAQ·교습비·지점·학년별 버튼·관련 링크까지 검사 범위를 확대했습니다.
- 자료 미확인을 미운영으로 단정하지 않습니다. 기존 URL·링크 목적·href·확정 학년·장소·교습비·학교·준비 자료 유지. 현재 위치 breadcrumb와 같은 페이지의 구역 이동, 확정 학년 링크·학습/비교 가이드의 목적은 보존했습니다.
- HTML 281변경 / 8,122바이트 유지. 표시 외 이전 본문·schema·H1·메타·미디어·문의 경로 바이트 보존. 기존 41,775 FAQ 질문과 schema 일치 유지. 전체 내부 링크/앵커/도달성/엑셀 검사 오류 0건.
- 반응형 52조건·hover 가독성·마우스/키보드 이동 확인. 기존 통계/설명 후처리 포함 전체 공개 10,622파일의 바이트 대조 통과. 원본 작성 폴더 상태 유지.
- [작업결과](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase6-20261001/작업결과.txt>) / [검증자료와생성입력](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase6-20261001/검증자료와생성입력.zip>) / [변경 전 백업](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase6-20261001/phase5-before-phase6.zip>).
- 최신 manifest SHA256 `02330914792325d2e063a62bf5872c2200d2ec4e438d2ac88fb0b8c8fc634c39`. 네이버 수집·색인·순위·유입은 이번 로컬 검사로 검증하지 않았습니다.
- 다음 개선: 홈·과목별 목록 등 기존 상위 안내에서 세 목적(수강·학습 점검·비교)을 명확히 설명하고 학년·과목에 맞는 기존 동네 페이지 연결 강화. 상위 페이지 11개 후보 점검만 수행했습니다.
- tools/audit_neighborhood_phase6.py, improve_neighborhood_phase6.py, validate_neighborhood_phase6.py, build_neighborhood_phase6.py, report_neighborhood_phase6.py 사용. 입력 incoming-link-audit.json와 불변 백업, 복원/재현은 작업결과 참고. 이전 생성기로 최신 검토본을 되돌리지 않습니다.

## 2026-10-01 — 5차 역할별 FAQ 개선 완료, 운영 미배포

- 사용자 지시: 배포는 마지막에 수행합니다. 지금 commit/push/운영 배포 없음.
- 동네 371개 / 동네 페이지 8,162개 + 지점 안내 193개 = HTML 8,355개 개선. 페이지별 질문 5개, 총 41,775개. 기존 URL을 유지하고 수강·학습 점검·비교·동네 종합·지점 안내에 맞게 FAQ를 구분했습니다.
- 확정 엑셀 학년·실제 주소·과목별 준비 자료·교습비 원문 기준일과 현재 확인 조건을 답변에 연결했습니다. 화성태안점 CSV/확인, 수지점(W+), 침산점 고3 마감, 석사점 학년 확인 조건 유지. 일반 학습 방법을 확정 지점 서비스나 성과로 표현하지 않습니다.
- FAQ는 긴 이미지 앞에 배치하고 본문 질문·답변과 FAQPage를 일치시켰습니다. 원본 본문·지도·사진 순서·문의 링크·제목·설명·canonical·색인 정책 유지.
- 전체 8,403페이지, 공개 10,622파일 검사 오류 0건. 48 HTML 바이트 유지, FAQ/FAQPage/단계 표식 외 기존 바이트 보존. 반응형 40조건, 키보드 펼침·마우스 열기/닫기·교습비 바로가기 확인. 로컬 배포 결과의 통계·설명 후처리까지 검토본과 일치.
- [최신 작업결과](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase5-20261001/작업결과.txt>) / [검증자료와생성입력](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase5-20261001/검증자료와생성입력.zip>) / [변경 전 백업](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase5-20261001/phase4-before-phase5.zip>).
- 최신 manifest SHA256 `bc4a40d4362767d097c28d48e5dbe2164ee984090858119cfb3e26857fc299d6`. 원본 작성 폴더 상태 유지. 네이버 수집·색인·순위·유입은 검증하지 않았습니다.
- 다음 개선 후보: 학년 자료 미확인 수강 페이지 55개로 연결되는 545개 링크(233개 원본 페이지)의 확인 문구 보완. 운영하지 않는다는 의미로 단정하지 않으며 URL 보존. 다음 후보 감사만 완료, 개선은 후속 단계입니다.
- tools/improve_neighborhood_phase5.py와 reviewed-faq.json 사용. 전체 검증 코드 validate_neighborhood_phase5.py, build_neighborhood_phase5.py, report_neighborhood_phase5.py. 복원/재현은 작업결과.txt 참고. 이전 생성기로 최신 검토본을 되돌리지 않습니다.

## 2026-10-01 — 4차 교습비 원문 안내 완료, 운영 미배포

- 사용자 최신 지시: 개선은 순차 진행하며 배포는 마지막에 수행합니다. 지금 commit/push/운영 배포 없음.
- 동네 8,162페이지 + 지점 안내 193개 = 8,355페이지 개선. PDF 193개·701쪽, 원문 표와 일치한 일반 과정 4,162개 대조. 현재 학년·장소 조건에 맞는 159개 지점에 원문 기준 교습비를 표시했고 34개 지점은 원문 확인 안내 유지.
- 원문 과정명·기간·총 교습시간·총교습비·기준일·쪽수 제공. 원문 숫자를 주당 횟수로 해석하거나 시간 단위를 추정하지 않습니다. 현재 적용 요금으로 선언하지 않으며 추가 과정 금액을 전체 수업료로 사용하지 않았습니다. 수지점(W+) 조건과 확정 엑셀 학년 유지.
- 전체 8,403페이지·공개 10,622파일 검사 오류 0건. HTML 8,355변경 / 48바이트 유지. fees·수정일·관련 확인 문장 외 이전 본문 바이트 유지. 반응형 40조건과 표 열기·닫기 확인. 통계·설명 후처리를 포함한 로컬 배포 결과도 검토본과 일치.
- [최신 작업결과](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase4-20261001/작업결과.txt>) / [검증자료와생성입력](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase4-20261001/검증자료와생성입력.zip>) / [변경 전 백업](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase4-20261001/phase3-before-phase4.zip>).
- 최신 manifest SHA256 `92e13d1c3e21130cada25749c707ca35c5e48f51d2b743f15cd2feaacf238613`. 원본 작성 폴더 상태 유지. 네이버 수집·색인·순위·유입은 검증하지 않았습니다.
- 다음 개선: 동네·과목·학년과 역할별 FAQ 질문·답변 정밀화 → 확인 필요 자료 보완 → 최종 배포 요청 시 공개 URL 및 수집·노출/클릭 확인. 기존 중복 URL은 보존하고 역할을 구분합니다.
- 4차 입력은 위 결과 폴더의 fee-grid-verified.json와 source-pdfs/. 코드 tools/improve_neighborhood_phase4.py, validate_neighborhood_phase4.py, report_neighborhood_phase4.py. ZIP 복원 경로는 작업결과.txt에 기록했습니다. 이전 생성기로 최신 본문·검증 자료를 되돌리지 않습니다.

## 2026-10-01 — 3차 개선 완료, 운영 미배포

- 371개 동네의 기존 8,162페이지 전체 유지. 동네별 정확한 학교 목록 전체와 준비 자료·확정 학년을 긴 이미지 앞에 배치했습니다. 학교는 상담 참고 자료로 표현합니다.
- 학습 점검 2,226페이지의 상세 공통 질문을 기존 `/학습관리/`의 여섯 주제·18개 질문으로 모았습니다. 학생 답안 상황 세 가지와 해당 학교·지점 자료는 동네 페이지에 남겼습니다. 기존 URL 삭제·통합 없음.
- 실제 지점 사진 368장을 원본과 대조하고 96개 지점 허브·관련 동네 페이지에 검토한 설명과 alt를 추가했습니다. 공통 사진 97개 지점은 예시임을 앞부분에도 표시했습니다. 실제 사진 신규 추가·원본 변경 없음.
- 변경 HTML 8,259페이지, 나머지 144페이지 바이트 유지. 전체 sitemap 8,403페이지 및 공개 파일 10,622개 검증 오류 0건. 기존 URL·H1·메타·색인·이미지 순서·문의 경로 유지. 반응형 24조건과 질문 펼치기·앵커 이동 확인.
- 수강 학년은 사용자 확정 엑셀 기준 유지. 화성태안점의 정확한 XLSX 이름 매칭은 미확인으로 기존 범위·확인 안내 유지. 수지점(W+) 장소 조건과 침산점 고3 마감 안내 유지.
- 최신 결과: [작업결과.txt](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase3-20261001/작업결과.txt>), [검증자료와생성입력.zip](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase3-20261001/검증자료와생성입력.zip>), [3차 변경 전 백업](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase3-20261001/phase2-before-phase3.zip>).
- 원본 작성용 폴더·스테이징 상태 보존. commit/push/운영 배포·검색 계정·자동화 작업 없음. 로컬 검증은 네이버 수집·색인·순위·유입의 증거가 아닙니다.
- 다음 순서: 명시적 운영 배포 요청 후 공개 URL·네이버 수집과 노출/클릭 확인 → 지점 확정 교습비 원본의 HTML 안내 → 공통 사진 지점의 실제 사진과 화성태안점 자료 보완.
- 3차 도구는 `tools/improve_neighborhood_phase3.py`, `tools/validate_neighborhood_phase3.py`, `tools/report_neighborhood_phase3.py`. 최신 ZIP의 `inputs/`를 `tools/data/neighborhood-seo/`에, `phase3/photo-audit.json` 등은 위 결과 폴더에 복원합니다. 기존 1차·2차 생성기와 보고서로 최신 본문이나 과거 증거를 덮어쓰지 않습니다.

## 2026-09-30 — 2차 개선 완료, 운영 미배포

- 사용자 확정: **센터 데이터 엑셀을 최신 확정 학년 기준으로 사용**. 정확한 이름이 맞는 192개 센터의 5과목 학년을 엑셀에서 대조·반영했습니다. CSV와 달랐던 14개 센터 38개 항목을 해결했습니다. 주소·등록 정보와 제공 파일 4개의 해시는 유지했습니다. 화성태안점은 XLSX 이름 매칭이 없어 CSV 범위와 확인 안내를 유지합니다.
- 기존 동네 8,162개 페이지를 모두 보존하면서 H1과 본문을 수강·위치 / 진도·오답 점검 / 선택 기준 / 과목·학년 안내로 구분했습니다. 동네 H1 중복은 1,272그룹(2,544페이지)에서 0그룹으로 줄었습니다.
- 서로 다른 역할의 지정 편집 문단 반복은 193그룹·3203회에서 0그룹·0회로 줄었습니다. 지점·학교 사실 및 공통 안내는 제외한 검사이며 사이트 전체 유사도나 네이버 평가 점수가 아닙니다.
- 비교 가이드 2,597개에서는 여섯 질문을 긴 이미지 앞으로 옮겼습니다. 전수 검사에 질문 배치 확인을 추가했고, 비교 폴더 코드 검사와 최종 전체 빌드 출력 검증을 통과했습니다.
- 실제 센터 안내 193개(동네 상세가 있는 188개 + 기존 센터 정보 안내 5개)에도 최신 학년·운영 참고사항을 반영했습니다. 학년·주소·교습비·운영 조건을 긴 이미지 앞에 제공하고, 4C 설명을 HTML 텍스트와 기존 학습관리 링크로 추가했습니다. 기존 이미지 전체·순서와 연락 경로는 유지했습니다. 특강 홍보 이미지를 실제 지점 사진으로 전용하지 않았습니다.
- 수지점 수학·과학의 별도 수지점(W+) 조건과 침산점 고3 마감 안내를 유지했습니다. 별도 수업 지점의 과정을 해당 안내 지점의 Service로 선언하지 않았고, FAQ·Article 제목 및 안내 내용을 함께 갱신했습니다.
- 전수 검증: 기존 sitemap 8,403개, 동네 8,162개, 센터 안내 193개 검사 오류 0건. URL 및 순서, canonical·색인 정책·이미지 경로와 순서·상담 연락 경로 유지. H1은 페이지 역할에 맞게 의도적으로 변경했습니다. 설명 최대 80자, meta/OG/Twitter/페이지 schema 일치. 제목·설명 중복, 내부 링크·앵커 오류, 홈에서 도달 불가능한 페이지 0개. 모바일 320/390px·태블릿 768px·데스크톱 표본 확인.
- 전체 배포용 빌드: 공개 파일 10,622개, HTML 8,403개, 비공개 입력 포함 0개. 기존 방문통계 태그 추가 5,225페이지 외 모든 검토 내용의 바이트 일치. 설명 후처리 추가 변경 0개, 출력 오류 0건.
- 최신 결과: [작업결과.txt](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase2-20260930/작업결과.txt>), [최신 검증자료와생성입력.zip](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase2-20260930/검증자료와생성입력.zip>), [2차 변경 전 전체 백업](<C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-phase2-20260930/phase1-before-phase2.zip>). 1차 결과 폴더는 과거 기록이며 최신 입력 복원에는 2차 ZIP을 사용합니다.
- commit/push/운영 배포 없음. 작성용 원본 폴더는 수정하지 않았습니다. 네이버 수집·색인·상위 노출은 아직 검증하지 않았으며, 명시적 배포 요청 후 공개 반영과 검색 실적 확인이 필요합니다.

2차 전용 도구는 `tools/improve_neighborhood_phase2.py`, `tools/audit_neighborhood_phase2.py`, `tools/report_neighborhood_phase2.py`입니다. 최신 비공개 입력 ZIP의 `inputs/`를 `tools/data/neighborhood-seo/`에 복원합니다. `centers.json`은 확정된 엑셀 학년과 원래 CSV의 `csvSubjects`를 함께 보관합니다. `--prepare`는 1차 백업과 제공 엑셀을 확인하고 사용자 확정 기준을 적용합니다. 이미 완료된 2차 페이지를 `--all`로 원고 재생성하지 않습니다. 추가 편집 뒤 전체 검사와 공개 파일 목록 갱신을 수행합니다.

```powershell
python -X utf8 tools/improve_neighborhood_phase2.py --all
python -X utf8 tools/validate_neighborhood_seo.py
python -X utf8 tools/improve_neighborhood_pages.py --refresh-manifest
node release-public-build.mjs
node wawa-analytics-build.mjs wawa-04 .public-release
node seo-descriptions.mjs --root=.public-release
python -X utf8 tools/verify_neighborhood_build.py
python -X utf8 tools/report_neighborhood_phase2.py
```

아래는 1차 완료 당시의 역사 기록입니다. 'H1 보존'과 '14개 센터 차이 표시'는 1차 상태를 뜻하며, 현재는 위 2차의 H1 역할 구분과 엑셀 확정 기준이 적용됩니다. 아래 1차 보고서 생성 명령을 실행해 최신 결과나 과거 증거를 덮어쓰지 않습니다.

## 1차 적용 범위와 페이지 역할

371개 동네의 기존 8,162개 페이지를 개선했습니다. 삭제, 이동, 리디렉션, noindex 추가와 다른 페이지로 canonical 통합을 하지 않았습니다.

| 페이지 계열 | 페이지 수 | 담당 역할 |
| --- | ---: | --- |
| 전국센터 동네 일반 | 371 | 실제 연결 지점과 과목·학년 안내의 출발점 |
| 전국센터 학년·과목 | 2,226 | 학생 자료를 바탕으로 학습 상태와 수업 비교 질문 확인 |
| 지점안내 동네 과목 | 742 | 실제 지점의 수강 학년·주소·교습비 확인 |
| 지점안내 동네 학년·과목 | 2,226 | 해당 학년·과목의 수강 조건과 위치 확인 |
| 과목별학원 동네 비교 | 2,597 | 일곱 분류별 수업 선택 기준과 상담 준비 |

지점 허브 188개와 최상위 허브 3개에 목적별 연결을 보완했고, 학년·과목 상세 직접 링크 2,226개를 추가했습니다. 제목, 설명, 첫 화면, 본문과 링크를 함께 수정했습니다. 기존 본문 이미지 전체, 지도와 공간 사진의 순서를 유지하며 반응형 WebP를 추가했습니다.

## 사실 확인 기준

`센터정보` 폴더의 CSV·엑셀 네 파일을 현재 통합 데이터와 해시로 대조했습니다. 원본 자료는 수정하지 않았습니다. XLSX와 이름이 매칭된 192개 센터의 주소·등록 정보는 일치했습니다. 14개 센터의 38개 과목 학년 항목은 자료가 달라, 관련 294개 페이지에 두 범위와 확인 필요성을 표시했습니다. 화성태안점은 XLSX 이름 매칭이 없어 CSV 범위를 유지했습니다.

자료에 없는 학년을 개설된 것으로 확대하지 않았습니다. 미확인 과정을 다루는 수강 안내 91개는 URL을 유지하고 Service 선언을 제거했습니다. 교습비 공통표는 지점 확정 금액으로 표현하지 않으며, 현재 수강 여부와 최종 조건은 실제 교습비 자료 및 지점 확인으로 연결합니다. 공통 공간 사진은 실제 지점 사진과 구분해 표시했습니다. 후기처럼 읽히던 생성 예시는 상담 준비 방법으로 수정했습니다.

## 도구와 입력 보관

- `tools/improve_neighborhood_pages.py`: 기존 HTML 보호 항목을 확인하며 표본·전체 변환, 가이드 보완, 검증 후 공개 파일 목록 갱신.
- `tools/improve_neighborhood_hubs.py`: 지점·최상위 허브의 직접 링크 보완.
- `tools/reconcile_neighborhood_sources.py`: 제공 자료의 해시·센터 정보·학년 차이 대조.
- `tools/align_unconfirmed_course_schema.py`: 미확인 수강 안내의 구조화 데이터 보정.
- `tools/validate_neighborhood_seo.py`: 전체 sitemap·본문·메타·구조화 데이터·링크·보호 항목 검사.
- `tools/verify_neighborhood_build.py`: 전체 배포 파이프라인의 파일 목록을 확인하고, 기존 방문통계 태그 한 개를 head에 추가하는 처리 외에는 검토된 소스와 바이트가 같은지 검사.
- `tools/report_neighborhood_improvements.py`: 검증이 모두 통과한 뒤 결과 보고서와 입력 백업 생성.

`tools/data/neighborhood-seo/`는 비공개 작업 입력이며 Git에서 제외됩니다. 재현할 때는 결과 폴더의 `검증자료와생성입력.zip` 안 `inputs/`를 이 디렉터리에 복원해야 합니다. 일반 Python에 패키지가 없으면 Codex 번들 Python을 사용합니다. `centers.json`, `subjects.json`, `grades.json`, 학습 프로필, 과목 학년 차이, 반응형 이미지 정보와 페이지 역할 목록을 함께 보관합니다.

기존의 오래된 생성기는 실행하지 않습니다. 변환 도구는 개선 표시가 있는 페이지를 보존하므로 `--all` 재실행만으로 기존 개선 본문을 다시 쓰지 않습니다. 추가 수정은 해당 구현 경로를 고친 뒤 필요한 변환과 검증을 수행합니다.

## 검증 및 배포용 빌드

전체 8,403개 sitemap 페이지와 8,162개 개선 페이지 검사에서 오류 0건을 확인했습니다. 기존 URL 및 순서, canonical·H1, 이미지 원본 경로와 순서, 상담 연락 경로를 보존했습니다. 정확히 같은 제목·설명, 내부 링크 단절과 홈에서 도달 불가능한 페이지가 없습니다. 설명은 최대 80자이며 meta/OG/Twitter/페이지 schema가 일치합니다. 지점 학년 상세는 홈에서 18개가 두 번, 2,208개가 세 번의 이동으로 도달합니다.

전체 배포 파이프라인과 출력 검증도 완료했습니다. 공개 파일 10,622개, HTML 8,403개이며 비공개 작업 입력은 포함되지 않았습니다. 기존 방문통계 태그가 없는 5,225페이지에 태그 한 개를 추가했고, 이미 있는 3,178페이지는 그대로 유지했습니다. 설명 후처리의 추가 변경은 0건입니다. 이 통계 태그 추가 외에는 검토된 파일 내용과 모든 바이트가 일치하며, 출력 검증 오류는 0건입니다. 모바일 320/390px, 태블릿 768px와 데스크톱 표본도 확인했습니다.

다음 순서로 작업 공간 루트에서 실행합니다. 배포용 빌드의 방문통계 처리와 설명 후처리를 생략하지 않습니다.

```powershell
python -X utf8 tools/validate_neighborhood_seo.py
python -X utf8 tools/improve_neighborhood_pages.py --refresh-manifest
node release-public-build.mjs
node wawa-analytics-build.mjs wawa-04 .public-release
node seo-descriptions.mjs --root=.public-release
python -X utf8 tools/verify_neighborhood_build.py
python -X utf8 tools/report_neighborhood_improvements.py
```

검증 JSON은 `tools/reports/neighborhood-seo/`에 있습니다. 최종 보고서와 비공개 입력 백업은 `C:/Users/1992k/Desktop/CodexData/outputs/site3-neighborhood-improvements-20260930/`에 보관합니다. 로컬 미리보기는 `tools/serve_coaching_preview.py`를 사용하며, 미리보기 응답의 noindex 헤더는 운영 페이지의 색인 설정이 아닙니다.

운영 반영에는 별도 명시적 배포 요청이 필요합니다. 로컬 검사 통과는 네이버 수집·색인·검색 순위 향상을 증명하지 않습니다. 실제 공개 반영 뒤 공개 URL 검사와 Search Advisor의 수집·노출·클릭 추이를 별도로 확인해야 합니다.
