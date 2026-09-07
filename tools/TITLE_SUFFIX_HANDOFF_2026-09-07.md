# 코칭학원.com 본문 기반 타이틀 접미사

## 범위

- 프로젝트: `새 홈페이지3`, 코칭학원.com
- GitHub: `01039578283-hub/wawa-academy-site3`
- Vercel: `wawa-academy-site3` (기존 연결 유지)
- 기준 커밋: `4914e1e366928ccb9ab93e50493270bf14232be8`
- 전국센터 하위 2,616개 + 과목별학원 하위 2,604개 = 5,220개.
- 홈·상담문의·학습관리·전국센터 최상위·과목별학원 최상위는 제외.
- 기존 타이틀 앞부분과 URL, H1, 본문, 이미지, 디자인, 구조화 데이터 유지.
- `<title>`과 기존 `og:title`, `twitter:title` 값만 교체.
- RSS의 해당 항목 제목만 동기화. RSS 내용·날짜와 사이트맵 URL·날짜는 그대로 유지.

## 작성 기준

- 실제 본문에 있는 학생의 어려움, 학습 점검, 소제목에서 근거를 추출한다.
- 첫 학습 답변과 학생 상황을 반복되는 일반 키워드보다 우선한다.
- 수학/영어 단일 과목에는 해당 과목의 근거가 있는 주제를 최소 한 개 포함한다.
- 초등·중등에 수능/모의고사 접미사를 붙이지 않는다.
- 접미사를 모두 다르게 보이도록 무작위 표현을 넣지 않는다. 본문 주제가 같으면 같은 접미사를 사용할 수 있다.
- 디렉터리 페이지는 자신의 소개글과 실제 연결된 지역 목록을 요약한다.
- 원고 생성과 내용 추가는 하지 않는다. 검색 순위나 검색 결과 제목 표시를 보장하지 않는다.

## 유지 관리

- `python -X utf8 tools/personalize_title_suffixes.py`: 적용 전 계획 확인.
- `python -X utf8 tools/personalize_title_suffixes.py --write`: 검증 후 타이틀 반영.
- `python -X utf8 tools/personalize_title_suffixes.py --check`: 재실행 시 결과 동일 여부 확인.
- `python -X utf8 tools/test_title_suffixes.py`: 근거/과목/학년/태그 치환 회귀검사.
- `python -X utf8 tools/verify_title_release.py`: 전 페이지와 RSS·사이트맵·보호 파일 검사.
- `python -X utf8 tools/verify_title_release.py --public`: 실제 운영 URL의 유형별 표본 검사.
- `tools/reports/title-suffix-audit.json`: 페이지별 기존/변경 제목, 근거 문장, 제목 이외 내용의 해시.
- 로컬 원본은 실제 바이트로 비교한다. Git 원본/공개 서버 비교에서는 Windows CRLF와 Linux LF의 줄바꿈 차이만 정규화하며, 본문·태그·공백의 다른 차이는 허용하지 않는다.
- 기존 페이지 생성기를 다시 실행하면 공통 접미사가 복원될 수 있으므로 제목 처리와 검사를 마지막에 실행한다.
- 현재 검사 대상은 5,220개로 고정했다. 향후 페이지 추가 시 범위·개수와 기준 커밋을 새 변경 범위에 맞게 갱신한다.
- 기존 미추적 `PROJECT_HANDOFF.md`, `CHAT_HISTORY_2026-06-25.md`는 수정하거나 커밋하지 않는다.

## 공개 반영 상태

5,220개 로컬 제목·근거·본문 보존 검사 통과. RSS 17개 중 대상 13개 제목 동기화,
사이트맵 5,225개 URL 및 보호 파일 보존 검사 통과. 회귀검사 7개 통과.

실제 배포 결과와 커밋은 로컬의 `tools/reports/title-suffix-release.json`,
공개 URL 검사 결과는 `tools/reports/title-suffix-public-verification.json`에 기록한다.
이 두 결과 파일은 배포 자체를 다시 유발하지 않도록 Git에서 제외한다.
