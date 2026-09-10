# 코칭학원.com 본사 자료 기반 업그레이드

작업일: 2026-09-11. 아래 내용은 로컬 수정·검증 완료 시점의 기록입니다.
이후 사용자가 공개 배포를 승인했습니다. 실제 배포 결과는 바탕화면 작업 기록과 tools/reports/brand-upgrade/release-verification.json에서 확인합니다.

## 범위

- 대상 저장소: C:\Users\1992k\Desktop\홈페이지 정리\새 홈페이지3
- 메인 / 와 학습관리 /학습관리/ 두 페이지 보강.
- 전국센터·과목별학원·동네별 페이지 본문/주소/이미지는 변경하지 않음.
- 기존 전화, 문자, 상담 신청 링크와 검색 소유확인 태그 유지.
- 기존 CHAT_HISTORY_2026-06-25.md, PROJECT_HANDOFF.md는 수정하지 않음.
- Git 커밋·푸시·Vercel 배포는 진행하지 않음.

## 반영 내용

- 메인: 브랜드 일러스트, 학습 공간 안내, 학습코칭 소개, 본사 영상 3개, AI 과목별 바로가기.
- 학습관리: Check·Curriculum·Coaching·Consulting 4C 안내, 플랜·학습·생활관리 사진 및 설명, AI 영어·수학·국어·독서 설명.
- 프로그램 대상 학년은 본사 기준: 영어/수학 초1~고3, 국어 중1~고3, 독서 초1~중2. 실제 개설·이용 가능 여부는 지점 상담 확인으로 구분.
- 과장된 성적 보장 및 지점 공통 운영을 새로 단정하지 않음. 이미지·영상은 본사 예시/개별 사례로 표시.
- PNG 원본 11개와 영상 썸네일 JPG 3개를 로컬 자산으로 저장(총 2,189,868바이트). 사진 편집·재압축 없음. 이미지 원본 비율과 전체 영역 유지.
- 영상은 클릭할 때만 iframe 생성. 초기 iframe 0개, 자동재생 없음. 닫기로 제거·포스터 복원, 별도 YouTube 링크 제공. 외부 라이브러리·폰트·분석 코드 추가 없음.
- FAQ는 JavaScript가 없어도 동작하는 details/summary로 구성. 본문 설명은 접지 않음.
- 공통 site.css는 그대로 두고 두 페이지에만 brand-upgrade-v1.css 적용.
- canonical 유지, 설명/OG/JSON-LD를 본문과 동기화. Service의 makesOffer를 offers로 정리. 없는 영상 업로드일 등을 만들어 VideoObject를 추가하지 않음.
- 사이트맵의 기존 5,225개 URL 유지. 수정한 2개 URL의 lastmod 및 RSS 항목만 갱신.

## 자료 출처 / 내부 확인용

- https://www.wawacenter.com/brand/wawacenter
- https://www.wawacenter.com/intro/coachingSystem
- https://www.wawacenter.com/intro/AISystem
- 본사 페이지에 실제 연결된 영상 ID: avpJfW7eIV0 / f_skFu40U04 / UIXUaBZdNXU
- 본사 페이지의 영상 설명과 실제 YouTube 제목이 일부 달라 oEmbed 메타데이터로 대조 후 중립적인 카드 제목 사용.
- 자료 스냅샷과 수집 메타데이터: tools/data/brand-upgrade/ (Git 제외).
- 원본 Main_CD_wawa.png → brand-learning.png; system_03/04/05.png → learning-space/teacher-coaching/four-c.png.
- 원본 system_06_01/07_01.png → learning-planner/learning-materials.png.
- 원본 ais_step02/ais_math_content02/ais_kor_content03/ais_read_portfolio/ais01.png → ai-english/ai-math/ai-korean/ai-reading/ai-guide.png.

## 검증

- python -X utf8 tools/audit_brand_upgrade.py: PASS.
- 두 페이지 H1 각 1개, 메타·canonical·OG·JSON-LD 파싱 및 FAQ 본문 일치(4개/6개), 내부 자산·링크·앵커 80건, 이미지 선언 해상도·원본 바이트·디코딩 확인.
- node --check assets/brand-upgrade-v1.js / git diff --check: PASS.
- 인앱 브라우저 320/390/768/1280px × 2페이지: 가로 넘침 0, 블록 글씨 잘림 0, 메뉴 44px/상담 버튼 46px.
- PC 메인/학습관리, 모바일 메인/AI 수학 화면 시각 확인. 홈↔학습관리 이동, 내용 목차, AI 과목 앵커 정상 확인.
- 학습관리 FAQ 클릭 열기 및 Enter 닫기 확인. 보이는 이미지 깨짐 0.
- 영상 3개의 ID별 iframe 생성·닫기·포스터 복원 및 YouTube 링크 확인. 인앱의 iframe 내부 영상 화면은 검증 중 빈 화면으로 나타나 실제 재생은 확인하지 못함. 실제 휴대폰/일반 브라우저의 재생은 별도 확인 항목이며, 직접 YouTube 열기를 항상 제공함.
- 정적 감사 보고서: tools/reports/brand-upgrade/static-audit.json
- 반응형 검사 보고서: tools/reports/brand-upgrade/browser-responsive.json

## 로컬 확인

- http://127.0.0.1:8794/
- http://127.0.0.1:8794/학습관리/
- 서버가 꺼지면 저장소에서 python -m http.server 8794 --bind 127.0.0.1 실행.
- 향후 배포 승인 시 두 페이지와 전용 자산, sitemap.xml/rss.xml을 함께 배포하고 정식 도메인 및 영상 재생을 추가 점검할 것.
