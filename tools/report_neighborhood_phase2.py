"""Save phase-2 evidence after the complete source and release checks pass."""
import json,shutil,zipfile,hashlib
from pathlib import Path
import improve_neighborhood_pages as impl
from improve_neighborhood_phase2 import OUT,VERSION

def main():
 v=impl.load(impl.REPORT/'validation.json');b=impl.load(impl.REPORT/'build-verification.json')
 assert v['errors']==[] and v['phase2Pages']==8162 and v['phase2CenterHubs']==193 and v['workbookCentersVerified']==192
 assert b['errors']==[] and b['publicFiles']==10622 and b['htmlPages']==8403
 assert b['reviewedManifestSha256']==hashlib.sha256((impl.ROOT/'release-public-manifest.json').read_bytes()).hexdigest()
 assert impl.load(OUT/'diff-check.json')['exitCode']==0
 assert impl.load(OUT/'diff-check.json')['comparisonFolderCheckExitCode']==0
 authority=impl.load(OUT/'workbook-authority.json');before=impl.load(OUT/'before.json')
 assert authority['changedCenters']==14 and authority['changedFields']==38
 implementation=impl.load(OUT/'implementation.json')
 implementation.update(verifiedCompleteNeighborhoodPages=v['phase2Pages'],verifiedCompleteCenterHubs=v['phase2CenterHubs'],countNote='changedPages is the final resumed run only; full coverage is independently verified by validation.json')
 impl.dump(OUT/'implementation.json',implementation)
 for name in ['validation.json','sample-validation.json','build-verification.json','source-reconciliation.json','hubs.json']:
  shutil.copyfile(impl.REPORT/name,OUT/name)
 with zipfile.ZipFile(OUT/'phase2-evidence.tmp.zip','w',zipfile.ZIP_DEFLATED) as z:
  for p in impl.DATA.glob('*.json'):z.write(p,'inputs/'+p.name)
  for p in impl.REPORT.glob('*.json'):z.write(p,'reports/'+p.name)
  for name in ['workbook-authority.json','implementation.json','sample.json','before.json','write-recovery.json','final-refinement.json','comparison-placement.json','diff-check.json','before-backup-verification.json','original-source-state.json']:
   if (OUT/name).is_file():z.write(OUT/name,'phase2/'+name)
 with zipfile.ZipFile(OUT/'phase2-evidence.tmp.zip') as z:assert z.testzip() is None
 (OUT/'phase2-evidence.tmp.zip').replace(OUT/'검증자료와생성입력.zip')
 report=f'''코칭학원.com 동네 페이지 2차 개선 — 2026.09.30

상태: 로컬 개선·전수 검증·전체 배포용 빌드 완료. 커밋·푸시·운영 배포 없음.
작업 공간: {impl.ROOT}
기준 커밋: 3c2b4695e058361a77c81afa065f2758735f22bb
1차 개선본 백업: {OUT/'phase1-before-phase2.zip'}

적용 범위
- 371개 동네의 기존 8,162개 페이지 전체: 수강 안내 2,968 / 학습 점검 2,226 / 비교 가이드 2,597 / 일반 안내 371.
- 실제 센터 안내 193개: 동네 상세 연결이 있는 188개와 기존 센터 정보 안내 5개를 같은 자료 기준으로 정리.
- 기존 8,403개 sitemap URL과 순서 유지. 삭제·리디렉션·noindex·타 페이지 canonical 통합 없음.

변경 내용
1. 같은 키워드의 페이지를 유지하면서 H1과 본문을 목적별로 구분.
   명일동 고등 수학: 지점 페이지는 '수강·위치 안내', 전국센터 페이지는 '진도·오답 점검'.
   과목별 페이지는 '선택 기준', 일반 동네 페이지는 '과목·학년 안내'.
2. 수강 페이지: 실제 안내 학년·지점 주소·학교 자료·일정·교습비를 확인하는 순서.
   학습 가이드: 초등·중등·고등 영어·수학 각각 세 가지 학생 답안 상황과 점검 자료.
   비교 페이지: 분류별 질문 세 가지와 학교 자료·수업 장소·일정 및 교습비 질문 세 가지를 긴 이미지 앞에 제공.
3. 긴 공통 이미지 앞에 4C의 진단·처방·지도·상담을 설명하는 HTML 문장과 기존 학습관리 링크 추가.
   이미지의 후기·평점·결과는 해당 지점의 검증된 후기나 성과 자료로 표시하지 않음.
4. 지점 운영 자료의 평균 오픈 시간·주말 안내와 별도 수강 조건을 표시.
   오픈 시간은 학생 수업 시작 시각과 구분하고, 현재 모집 자리·시간표는 별도 확인.
5. FAQ 질문·답변과 구조화 데이터를 함께 갱신. Article 제목과 실제 H1을 일치.
   수지점 수학·과학의 수지점(W+) 안내와 침산점 고3 마감 조건 유지.
   별도 수업 장소의 과정을 해당 안내 지점의 Service로 선언하지 않음.
6. 기존 본문·지도·학습 공간 사진의 원본 경로와 순서, 상담 연락 경로 유지.
   특강 홍보 이미지 25개 센터분을 실제 시설 사진으로 전용하지 않음. 새로운 실제 지점 사진 추가 없음.

학년 자료 확정
- 사용자 답변: '센터 데이터 엑셀을 최신 확정 기준으로 사용'.
- 제공 엑셀과 정확히 이름이 맞는 192개 센터의 5과목 학년을 엑셀로 반영.
- CSV와 달랐던 14개 센터의 38개 과목 항목을 해결. 원본 CSV·엑셀 4파일 해시 불변.
- 주소·등록 학원명·등록번호 일치 확인. W+는 별도 지점 정체성 유지.
- 화성태안점 1개는 정확한 엑셀 이름 매칭이 없어 CSV 범위와 확인 안내 유지.
- CSV 기존 값은 비공개 입력의 csvSubjects에 보관. 모든 페이지에서 자료 범위와 현재 모집 여부를 구분.

검증 결과
- 기존 sitemap 8,403개 전수 검사 오류 0건. 동네 8,162개와 센터 안내 193개 2차 표시 확인.
- 엑셀 192개 센터의 5과목 학년을 원본 파일에서 독립 대조.
- 동네 H1 중복 그룹 {before['duplicateH1Groups']:,}개 ({before['duplicateH1Pages']:,}페이지) → {v['phase2DuplicateH1Groups']}개.
- 서로 다른 역할의 편집 문단 반복: {v['editorialOverlapBefore']['crossRoleParagraphGroups']}그룹 / {v['editorialOverlapBefore']['crossRoleParagraphOccurrences']}회 → {v['editorialOverlapAfter']['crossRoleParagraphGroups']}그룹 / {v['editorialOverlapAfter']['crossRoleParagraphOccurrences']}회.
  지정된 편집 섹션의 긴 문단을 동네·지점명 정규화 후 비교한 수치이며, 공통 사실·학교 정보·안내 문구는 제외.
  사이트 전체 문장 유사도나 네이버 평가 점수를 뜻하지 않음. before.json의 초기 탐색 수치는 학교 사실 반복도 포함하므로 별도 보관.
- 제목·설명 정확한 중복, JSON-LD 파싱 오류, 내부 링크·앵커 단절, 홈에서 도달 불가능한 페이지 0건.
- 설명 최대 80자, meta/OG/Twitter/페이지 schema 일치. canonical·색인 정책과 보호 항목 유지.
- 모바일 320/390px, 태블릿 768px, 데스크톱 1280px 표본에서 가로 넘침 없음. FAQ·이동 버튼과 별도 지점 안내 확인.
- 배포용 파일 {b['publicFiles']:,}개 / HTML {b['htmlPages']:,}개. 비공개 입력 포함 {b['privateSourceFiles']}개.
- 전체 세 단계 빌드 실행. 기존 방문통계 태그를 없는 {b['analyticsTrackerInsertedPages']:,}페이지에 한 개 삽입한 처리 외에는 검토 소스와 모든 바이트 일치.
- 설명 후처리 추가 변경 0개. 빌드 출력 검사 오류 0건.
- 코드 변경 검사에서 복구한 한 파일의 끝 빈 줄을 정리하고, 이후 변경 9개 페이지 재검사도 통과.
- 비교 가이드 2,597개의 질문을 이미지 앞으로 옮긴 뒤 비교 폴더 코드 검사와 전수 검증 통과.

재현과 보관
- 검증자료와생성입력.zip: 최신 학년 확정 입력, 역할별 경로 목록, 소스·출력 검증과 변경 항목.
- phase1-before-phase2.zip: 2차 변경 전 1차 개선본 전체. 다시 생성하거나 덮어쓰지 않음.
- 재현은 작업 공간의 NEIGHBORHOOD_SEO_HANDOFF.md를 참조. 오래된 원고 생성기를 실행하지 않음.

공개 사이트 및 검색 성과
이 개선은 운영 사이트에 아직 반영되지 않음. 로컬 검증은 네이버 수집·색인·상위 노출의 증거가 아님.
명시적 배포 요청 후 공개 반영을 검증하고, 네이버 수집·노출·클릭을 별도로 확인해야 함.
'''
 (OUT/'작업결과.txt').write_text(report,'utf-8-sig')
 print(str(OUT/'작업결과.txt'))

if __name__=='__main__':main()
