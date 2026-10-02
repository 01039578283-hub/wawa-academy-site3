# RSS·사이트맵 검토와 배포 빌드 검사

`vercel.json`의 빌드는 먼저 `node seo-feed-check.mjs`를 실행합니다. 검사가
통과하면 기존 공개 파일 복사, 방문통계 추가, 페이지 설명 후처리를 진행하고,
마지막에 `node seo-feed-check.mjs --root=.public-release --built-output`으로
최종 출력을 검사합니다. 어느 단계든 실패하면 빌드가 중단됩니다.

검사는 Node 기본 모듈만 사용하며 파일·본문·날짜를 쓰지 않습니다. 배포에
필요한 비공개 검토 입력은 루트의 `seo-feed-review.json`입니다. `tools/`는
Vercel 업로드에서 제외되므로 검사 실행 시 Python이나 tools에 의존하지 않습니다.
검사 도구와 검토 JSON은 공개 manifest에 포함하지 않습니다.

## 페이지나 피드를 수정한 뒤

1. 사실 자료를 확인하고 실제 페이지의 제목·본문·변경일을 정비합니다.
2. RSS에 포함된 페이지를 바꿨다면 제목과 본문 전체도 맞춥니다. 기존 항목의
   URL·GUID·최초 발행일을 보존하고 실제 피드 변경 때만 lastBuildDate를 바꿉니다.
3. sitemap에는 모든 검토 대상 공개 HTML의 canonical을 포함합니다. lastmod는
   페이지 변경일과 맞추고 빌드 날짜로 일괄 갱신하지 않습니다. 원래 수집 제외
   페이지는 공개 manifest에 무조건 추가하지 않습니다.
4. 전체 페이지·자료 검증을 마친 뒤 기존 공개 manifest를 검토·갱신합니다.
5. 로컬에서 `python -X utf8 tools/review_seo_feeds.py`를 실행합니다. 현재 XML,
   전체 canonical·페이지 변경일, RSS의 H1·전체 본문을 lxml로 대조한 뒤 검토
   입력을 저장합니다. 검토 실패 시 기존 JSON은 보존합니다.
6. 실제 buildCommand를 로컬에서 실행하고 전체 공개 출력도 검증합니다.

검토 입력의 해시를 직접 고쳐서 검사를 통과시키지 않습니다. 검토 도구는 피드나
페이지를 자동 생성하거나 고치지 않습니다. 동일한 입력을 다시 검토할 때는
검토 시각과 JSON 바이트도 보존합니다. 기존 RSS 항목의 GUID와 발행일이
달라지면 재검토도 실패합니다.

## 검사 범위와 한계

로컬 검토 도구가 XML 구문, URL·날짜·본문 의미 일치를 확인합니다. 배포 빌드는
그 검토 기록과 실제 전체 HTML·RSS·사이트맵이 그대로 일치하는지 SHA256으로
확인합니다. 검토 이후 변경은 공개 manifest만 갱신해도 통과하지 못합니다.

Windows CRLF와 Linux LF는 동일한 텍스트로 인정합니다. 최종 HTML은 검토한
내용과 기존 wawa-04 통계 스크립트 1개만 허용하며, 다른 후처리 변경은 실패합니다.
최종 출력의 누락·추가 파일 및 비공개 입력 노출도 차단합니다.

이 검사는 네이버 수집·색인·순위·유입을 확인하지 않습니다. 운영 배포와 검색
성과 확인은 별도 작업입니다.

참고: https://searchadvisor.naver.com/guide/request-feed
참고: https://www.sitemaps.org/protocol.html
참고: https://www.rssboard.org/rss-specification
