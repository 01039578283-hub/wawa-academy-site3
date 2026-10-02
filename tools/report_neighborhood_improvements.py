"""Create a reviewable local report only after whole-site and build validation."""
from pathlib import Path
import json,shutil,zipfile
from urllib.parse import quote
import improve_neighborhood_pages as impl

def main():
 validation=impl.load(impl.REPORT/'validation.json');assert validation['errors']==[] and validation['improvedPages']==8162
 build=impl.load(impl.REPORT/'build-verification.json');assert build['errors']==[]
 hubs=impl.load(impl.REPORT/'hubs.json');sources=impl.load(impl.REPORT/'source-reconciliation.json')
 out=Path(r'C:\Users\1992k\Desktop\CodexData\outputs\site3-neighborhood-improvements-20260930');out.mkdir(parents=True,exist_ok=True)
 for name in ['validation.json','source-reconciliation.json','hubs.json','implementation.json','sample.json','guide-refinement.json','unconfirmed-course-schema.json','build-verification.json']:
  shutil.copyfile(impl.REPORT/name,out/name)
 shutil.copyfile(impl.DATA/'page-roles.json',out/'page-roles.json')
 # Ignored private source snapshots are preserved separately for regeneration.
 with zipfile.ZipFile(out/'검증자료와생성입력.zip','w',zipfile.ZIP_DEFLATED) as z:
  for p in impl.DATA.glob('*.json'):z.write(p,'inputs/'+p.name)
  for p in impl.REPORT.glob('*.json'):z.write(p,'reports/'+p.name)
 report=f'''코칭학원.com 동네 페이지 개선 — 2026.09.30

상태: 별도 작업 공간에서 로컬 개선·검증 완료. GitHub 푸시·운영 배포는 실행하지 않음.
작업 공간: {impl.ROOT}
기준 커밋: 3c2b4695e058361a77c81afa065f2758735f22bb

적용 범위
- 전체 371개 생활권의 동네 페이지 8,162개
- 전국센터 일반 안내 371개
- 전국센터 초등·중등·고등 영어·수학 학습 가이드 2,226개
- 지점안내 영어·수학 수강 안내 742개
- 지점안내 초등·중등·고등 영어·수학 수강 안내 2,226개
- 과목·학교급 비교 가이드 2,597개
- 지점 및 최상위 허브 {hubs['changedHubs']}개, 학년·과목 직접 링크 {hubs['directGradeLinksAdded']:,}개 추가

실제 변경
1. 동일한 키워드를 다루는 URL 모두 보존. 지점 안내는 수강·위치·교습비,
   전국센터 상세는 학습 점검, 과목별 페이지는 수업 비교 기준으로 구성.
2. 실제 주소·과목별 학년과 교습비 확인 경로를 긴 본문 이미지 앞에 배치.
3. 제목·첫 설명·본문·상호 링크를 페이지 목적에 맞게 수정.
4. 모든 동네 설명을 80자 이내 완결된 문장으로 작성하고 meta/OG/Twitter/페이지 schema에 동기화.
5. 단문 추출로 끊긴 질문을 완결된 내용으로 수정. 실제 후기처럼 읽힐 수 있는
   생성 예시는 상담 준비 방법으로 다시 작성. 공통 공간 사진은 공통 예시로 표시.
6. 기존 본문 이미지 전체와 지도·사진 순서를 유지하고 480/768/918px WebP 적용.
7. 지점·동네·학습 가이드 사이 직접 이동과 실제 변경 페이지의 sitemap lastmod 갱신.
8. 수강 학년 미확인 안내 91개는 주소를 유지하고 Service 선언을 제거.

자료 대조
- 제공된 CSV·엑셀 4개 파일의 해시 일치 확인, 371개 동네-센터 연결 대조.
- 엑셀과 이름이 매칭된 192개 센터의 주소·등록 정보 충돌 없음.
- {sources['differentGradeCenters']}개 센터, {sources['differentGradeFields']}개 과목 학년 항목에서 CSV와 엑셀 차이 확인.
  해당 페이지 {validation['sourceDisagreementLabeledPages']}개에 두 자료의 범위와 별도 확인 필요성을 표시.
- 화성태안점은 엑셀 이름 매칭이 없어 CSV 안내를 바탕으로 유지. 현재 개설 조건 확인 필요.
- 자료에 없는 학년은 수강 가능으로 확대하지 않음. 현재 모집 여부와 최종 교습비는 별도 확인 대상.

검증
- sitemap 8,403개 기존 URL 및 순서 보존, 삭제·이동·리디렉션·noindex 추가 없음.
- 동네 8,162개 개선 상태 및 전체 8,403개 페이지 검사 오류 0건.
- canonical·H1·이미지 출처와 순서·상담 연락 경로 보존 확인.
- 메타/페이지 schema 설명 일치, 제목·설명 중복 없음, JSON-LD 파싱 오류 없음.
- 내부 페이지 연결 및 새 목차 앵커 정상, 홈에서 도달 불가능한 페이지 없음.
- 지점 학년 상세의 홈에서 이동 거리: {json.dumps(validation['branchGradeDistance'],ensure_ascii=False)}
- 기존 배포용 빌드의 공개 파일 복사·방문통계 처리·설명 후처리 전체 실행 및 출력 검증 완료.
- 공개 파일 {build['publicFiles']:,}개와 HTML {build['htmlPages']:,}개 확인, 작업용 비공개 입력 포함 없음.
- 모바일 320/390px, 태블릿 768px 및 데스크톱 표본에서 가로 넘침·버튼·구조 확인.

명일동 고등 수학 예시
- 지점 페이지: '명일동 고등 수학학원 | 명일점 수강 학년·위치'
  명일점 실제 주소, 수학 고1–고2, 교습비 경로를 먼저 제공.
- 전국센터 페이지: '명일동 고등 수학학원 | 진도·오답 점검 가이드'
  이수 과목·조건 적용·재풀이 기록과 학교 자료를 기준으로 수업을 비교.
- 두 기존 URL은 서로 연결된 별도 페이지로 계속 유지.
- 모바일 첫 화면: 같은 폴더의 명일동-수강안내-모바일.png에서 확인.

공개 사이트 상태
이 작업은 아직 운영 사이트에 반영하지 않음. 로컬 검증은 네이버 수집·색인·검색 순위의
개선을 증명하지 않으며, 공개 반영 후 검색 실적과 수집 상태를 별도로 확인해야 함.
'''
 (out/'작업결과.txt').write_text(report,'utf-8-sig')
 print(str(out/'작업결과.txt'))
if __name__=='__main__':main()
