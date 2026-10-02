"""Update only this site's handoff after completed phase-2 verification."""
from pathlib import Path
import improve_neighborhood_pages as impl
from improve_neighborhood_phase2 import OUT

def main():
 v=impl.load(impl.REPORT/'validation.json');b=impl.load(impl.REPORT/'build-verification.json')
 assert not v['errors'] and v['phase2Pages']==8162 and v['phase2CenterHubs']==193
 assert not b['errors'] and (OUT/'작업결과.txt').is_file()
 own=Path(r'C:\Users\1992k\Desktop\홈페이지 작업 폴더\00_프로젝트 인수인계\코칭학원.com')
 section=f'''## 2026-09-30 — 2차 개선 완료, 운영 미배포

- 사용자 확정: **센터 데이터 엑셀을 최신 확정 학년 기준으로 사용**. 정확한 이름이 맞는 192개 센터의 5과목 학년을 엑셀에서 대조·반영했습니다. CSV와 달랐던 14개 센터 38개 항목을 해결했습니다. 주소·등록 정보와 제공 파일 4개의 해시는 유지했습니다. 화성태안점은 XLSX 이름 매칭이 없어 CSV 범위와 확인 안내를 유지합니다.
- 기존 동네 8,162개 페이지를 모두 보존하면서 H1과 본문을 수강·위치 / 진도·오답 점검 / 선택 기준 / 과목·학년 안내로 구분했습니다. 동네 H1 중복은 1,272그룹(2,544페이지)에서 0그룹으로 줄었습니다.
- 서로 다른 역할의 지정 편집 문단 반복은 {v['editorialOverlapBefore']['crossRoleParagraphGroups']}그룹·{v['editorialOverlapBefore']['crossRoleParagraphOccurrences']}회에서 {v['editorialOverlapAfter']['crossRoleParagraphGroups']}그룹·{v['editorialOverlapAfter']['crossRoleParagraphOccurrences']}회로 줄었습니다. 지점·학교 사실 및 공통 안내는 제외한 검사이며 사이트 전체 유사도나 네이버 평가 점수가 아닙니다.
- 실제 센터 안내 193개(동네 상세가 있는 188개 + 기존 센터 정보 안내 5개)에도 최신 학년·운영 참고사항을 반영했습니다. 학년·주소·교습비·운영 조건을 긴 이미지 앞에 제공하고, 4C 설명을 HTML 텍스트와 기존 학습관리 링크로 추가했습니다. 기존 이미지 전체·순서와 연락 경로는 유지했습니다. 특강 홍보 이미지를 실제 지점 사진으로 전용하지 않았습니다.
- 수지점 수학·과학의 별도 수지점(W+) 조건과 침산점 고3 마감 안내를 유지했습니다. 별도 수업 지점의 과정을 해당 안내 지점의 Service로 선언하지 않았고, FAQ·Article 제목 및 안내 내용을 함께 갱신했습니다.
- 전수 검증: 기존 sitemap 8,403개, 동네 8,162개, 센터 안내 193개 검사 오류 0건. URL 및 순서, canonical·색인 정책·이미지 경로와 순서·상담 연락 경로 유지. H1은 페이지 역할에 맞게 의도적으로 변경했습니다. 설명 최대 80자, meta/OG/Twitter/페이지 schema 일치. 제목·설명 중복, 내부 링크·앵커 오류, 홈에서 도달 불가능한 페이지 0개. 모바일 320/390px·태블릿 768px·데스크톱 표본 확인.
- 전체 배포용 빌드: 공개 파일 {b['publicFiles']:,}개, HTML {b['htmlPages']:,}개, 비공개 입력 포함 0개. 기존 방문통계 태그 추가 {b['analyticsTrackerInsertedPages']:,}페이지 외 모든 검토 내용의 바이트 일치. 설명 후처리 추가 변경 0개, 출력 오류 0건.
- 최신 결과: [작업결과.txt](<{OUT.as_posix()}/작업결과.txt>), [최신 검증자료와생성입력.zip](<{OUT.as_posix()}/검증자료와생성입력.zip>), [2차 변경 전 전체 백업](<{OUT.as_posix()}/phase1-before-phase2.zip>). 1차 결과 폴더는 과거 기록이며 최신 입력 복원에는 2차 ZIP을 사용합니다.
- commit/push/운영 배포 없음. 작성용 원본 폴더는 수정하지 않았습니다. 네이버 수집·색인·상위 노출은 아직 검증하지 않았으며, 명시적 배포 요청 후 공개 반영과 검색 실적 확인이 필요합니다.

'''
 handoff=own/'PROJECT_HANDOFF.md';text=handoff.read_text('utf-8')
 assert '## 2026-09-30 — 2차 개선 완료' not in text
 text=text.replace('최신 갱신: 2026-09-30. 9월 28일 인수인계에 전체 동네 페이지의 로컬 개선·검증 완료 기록을 추가했습니다. 아래 9월 25일 배포 기록과 이번 미배포 개선본을 구분합니다. 네이버 검색 성과는 별도 확인 대상입니다.','최신 갱신: 2026-09-30. 2차 로컬 개선과 엑셀 학년 기준 확정을 반영했습니다. 9월 25일 운영 배포와 현재 미배포 개선본을 구분합니다. 네이버 검색 성과는 별도 확인 대상입니다.')
 text=text.replace('## 최신 작업 — 2026-09-30 로컬 개선 완료, 운영 미배포',section+'## 1차 작업 기록 — 2026-09-30 로컬 개선 완료, 운영 미배포')
 handoff.write_text(text,'utf-8')
 log=own/'CHANGELOG.md';text=log.read_text('utf-8');assert '## 2026-09-30 — 2차 개선 완료' not in text
 log.write_text(text.replace('## 다음 작업 기록 양식',section+'## 다음 작업 기록 양식'),'utf-8')
 local=impl.ROOT/'NEIGHBORHOOD_SEO_HANDOFF.md';text=local.read_text('utf-8');assert '## 2026-09-30 — 2차 개선 완료' not in text
 local_section=section+'''2차 전용 도구는 `tools/improve_neighborhood_phase2.py`, `tools/audit_neighborhood_phase2.py`, `tools/report_neighborhood_phase2.py`입니다. 최신 비공개 입력 ZIP의 `inputs/`를 `tools/data/neighborhood-seo/`에 복원합니다. `centers.json`은 확정된 엑셀 학년과 원래 CSV의 `csvSubjects`를 함께 보관합니다. `--prepare`는 1차 백업과 제공 엑셀을 확인하고 사용자 확정 기준을 적용합니다. 이미 완료된 2차 페이지를 `--all`로 원고 재생성하지 않습니다. 추가 편집 뒤 전체 검사와 공개 파일 목록 갱신을 수행합니다.

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

'''
 text=text.replace('## 적용 범위와 페이지 역할',local_section+'## 1차 적용 범위와 페이지 역할',1)
 local.write_text(text,'utf-8')
 print('Updated this site handoff, changelog, and reproduction notes')

if __name__=='__main__':main()
