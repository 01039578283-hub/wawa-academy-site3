from __future__ import annotations

import csv
import hashlib
import html
import json
import random
import re
import shutil
import unicodedata
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

import generate_subject_professional_pages as content_engine


ROOT = Path(__file__).resolve().parents[1]
SITE_URL = "https://xn--sp5b72l1taf0p.com"
SITE_NAME = "와와학습코칭학원"
DOMAIN_NAME = "코칭학원.com"
TODAY = "2026-08-11"
SUBJECT_ROOT = ROOT / "과목별학원"
SOURCE_DIR = ROOT.parent / "참고자료" / "사용한 원고" / "코칭학원.com 추가 원고"
COMMON_DIR = ROOT.parent / "참고자료" / "공통자료"
CENTER_CSV = COMMON_DIR / "센터정보 정리.csv"
CONSULT_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdb2oE5Qk5YS0TfYDxyV1w-IOTkhkjOCmmpAKTI9FmqpVj6Yg/viewform"
PHONE = "010-3957-8283"
SMS_URL = "https://blogsms.net/01039578283"

REGION_ORDER = ["서울", "경기", "인천", "충청", "대전", "대구", "울산", "부산", "경상", "광주", "전라", "강원", "제주"]
TARGET_SLUGS = ("영수전문학원", "영어전문학원", "수학전문학원")
EXPECTED_REVIEW_COUNTS = {
    "영수전문학원": 2,
    "영어전문학원": 3,
    "수학전문학원": 3,
}
ENGINE_CONFIGS = {
    str(config["slug"]): dict(config)
    for config in content_engine.CATEGORIES
    if str(config["slug"]) in TARGET_SLUGS
}

CATEGORY_COPY = {
    "영수전문학원": {
        "label": "영수 전문학원",
        "eyebrow": "ENGLISH & MATH SPECIALIST DIRECTORY",
        "lead": "영어와 수학을 같은 분량으로 묶기보다 현재 과목별 차이, 학교 일정, 혼자 복습할 수 있는 시간을 나누어 살펴보도록 371개 동네 안내를 정리했습니다.",
        "summary": "영어는 어휘·문법·독해와 답안 근거를, 수학은 개념·연산·조건 해석과 풀이 과정을 따로 진단한 뒤 주간 계획에서 우선순위를 조정합니다.",
        "tags": ("영어 진단", "수학 진단", "과목별 복습"),
    },
    "영어전문학원": {
        "label": "영어 전문학원",
        "eyebrow": "ENGLISH SPECIALIST ACADEMY DIRECTORY",
        "lead": "단어 암기량만 비교하지 않고 문장 구조를 이해하는 과정, 독해 답의 근거, 서술형 표현과 오답 복습까지 살펴보도록 371개 동네 안내를 정리했습니다.",
        "summary": "최근 영어 시험지와 교재에서 어휘 누적, 문법 적용, 독해 근거, 서술형 표현을 나누고 수업 뒤 다시 확인할 기록까지 비교합니다.",
        "tags": ("어휘 누적", "문법 적용", "독해 근거"),
    },
    "수학전문학원": {
        "label": "수학 전문학원",
        "eyebrow": "MATH SPECIALIST ACADEMY DIRECTORY",
        "lead": "문제 수나 선행 진도만 비교하지 않고 학생이 개념을 설명하고 풀이를 끝까지 이어 가는 과정, 오답을 다시 확인하는 간격까지 살펴보도록 371개 동네 안내를 정리했습니다.",
        "summary": "최근 수학 시험지와 풀이 흔적에서 개념 이해, 계산 과정, 문제 조건 해석, 서술형 표현과 오답 재도전 순서를 구분합니다.",
        "tags": ("개념 진단", "풀이 과정", "오답 재학습"),
    },
}


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def compact_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def normalize(value: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value or "")).strip()


def unique(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = re.sub(r"\s+", " ", value or "").strip(" ,·/")
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def split_values(value: str) -> list[str]:
    return unique(re.split(r"[,/|\n]+", value or ""))


def encoded_url(*parts: str) -> str:
    path = "/".join(quote(str(part), safe="") for part in parts)
    return f"{SITE_URL}/{path}/" if path else SITE_URL + "/"


def root_path(*parts: str) -> str:
    return "/" + "/".join(quote(str(part), safe="") for part in parts) + "/"


def official_region(address: str, fallback: str) -> str:
    checks = (
        ("서울", "서울특별시"), ("경기", "경기도"), ("인천", "인천광역시"),
        ("충북", "충청북도"), ("충남", "충청남도"), ("대전", "대전광역시"),
        ("대구", "대구광역시"), ("울산", "울산광역시"), ("부산", "부산광역시"),
        ("경북", "경상북도"), ("경남", "경상남도"), ("광주", "광주광역시"),
        ("전북", "전북특별자치도"), ("전남", "전라남도"), ("강원", "강원특별자치도"),
        ("제주", "제주특별자치도"), ("세종", "세종특별자치시"),
    )
    compact = (address or "").strip()
    for prefix, value in checks:
        if compact.startswith(prefix):
            return value
    return fallback


def load_rows() -> tuple[list[str], dict[str, dict[str, str]], dict[str, str]]:
    with CENTER_CSV.open(encoding="utf-8-sig", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    if len(csv_rows) != 371:
        raise ValueError(f"센터정보 행 수가 371개가 아닙니다: {len(csv_rows)}")

    existing: dict[str, str] = {}
    for path in (ROOT / "전국센터").iterdir():
        if not path.is_dir() or not (path / "index.html").is_file():
            continue
        if (path / "고등수학학원" / "index.html").is_file():
            existing[normalize(path.name)] = path.name

    aliases = {
        normalize("부천 상동"): "부천상동",
        normalize("당진 읍내동"): "당진읍내동",
        normalize("전주 장동"): "전주장동",
    }
    order: list[str] = []
    rows: dict[str, dict[str, str]] = {}
    center_folders: dict[str, str] = {}
    for row in csv_rows:
        display = str(row.get("근처 수업가능 동네", "")).strip()
        key = normalize(display)
        folder = existing.get(key) or aliases.get(key)
        if not folder or not (ROOT / "전국센터" / folder / "index.html").is_file():
            raise ValueError(f"전국센터 동네 폴더를 찾을 수 없습니다: {display}")
        order.append(folder)
        rows[folder] = {str(k): str(v or "").strip() for k, v in row.items()}
        rows[display] = rows[folder]
        center_folders[folder] = folder
        center_folders[display] = folder
    if len(order) != 371 or len(set(order)) != 371:
        raise ValueError("371개 동네 매핑이 고유하지 않습니다")
    return order, rows, center_folders


ORDER, ROWS, CENTER_FOLDERS = load_rows()
NORMALIZED_LOCAL = {normalize(name): local for local in ORDER for name in (local, str(ROWS[local].get("근처 수업가능 동네", "")))}


def row_for(local: str) -> dict[str, str]:
    actual = NORMALIZED_LOCAL.get(normalize(local), local)
    if actual not in ROWS:
        raise ValueError(f"센터정보를 찾을 수 없습니다: {local}")
    return ROWS[actual]


def actual_local(local: str) -> str:
    value = NORMALIZED_LOCAL.get(normalize(local))
    if not value:
        raise ValueError(f"동네 URL 매핑을 찾을 수 없습니다: {local}")
    return value


def grades_for(row: dict[str, str], focus: str) -> list[str]:
    english = split_values(row.get("가능학년\n(영어)", ""))
    math = split_values(row.get("가능학년\n(수학)", ""))
    if focus == "english":
        return english
    if focus == "math":
        return math
    math_set = set(math)
    return [grade for grade in english if grade in math_set]


def schools_for(row: dict[str, str]) -> list[str]:
    values: list[str] = []
    for key in ("타깃학교\n(초)", "타깃학교\n(중)", "타깃학교\n(고)"):
        values.extend(split_values(row.get(key, "")))
    return [
        value for value in unique(values)
        if not re.search(r"(?:지역\s*내|모든\s*학교|학교\s*가능|학교\s*전체|미기재|없음|상담\s*확인)", value)
    ]


def image_size(path: Path) -> tuple[int, int]:
    try:
        from PIL import Image

        with Image.open(path) as image:
            return image.size
    except Exception:
        return 0, 0


def base_center_data(local: str) -> dict[str, object]:
    local = actual_local(local)
    row = row_for(local)
    reference_page = ROOT / "전국센터" / local / "고등수학학원" / "index.html"
    reference_source = reference_page.read_text(encoding="utf-8")
    image_sources = re.findall(r'<img\b[^>]*\bsrc="([^"]+)"', reference_source, re.IGNORECASE)
    map_source = next((value for value in reversed(image_sources) if "/assets/maps/" in value or "assets/maps/" in value), "")
    if not map_source:
        raise ValueError(f"기존 전국센터 페이지에서 지도 이미지를 찾을 수 없습니다: {local}")
    map_source = "/" + map_source.lstrip("./").replace("../", "")
    if not map_source.startswith("/assets/maps/"):
        map_source = "/assets/maps/" + Path(map_source).name
    map_path = ROOT / map_source.lstrip("/")
    if not map_path.is_file():
        raise ValueError(f"지도 이미지가 없습니다: {local} -> {map_path.name}")
    is_seoul = row.get("지역") == "서울"
    body_name = "seoul-q92.webp" if is_seoul else "local-q92.webp"
    mobile_name = "seoul-mobile.webp" if is_seoul else "local-mobile.webp"
    identifier = row.get("교육지원청 등록번호", "")
    address = row.get("센터 주소", "")
    return {
        "organization_name": row.get("센터명") or f"{SITE_NAME} {local} 안내",
        "telephone": PHONE,
        "address": {
            "@type": "PostalAddress",
            "streetAddress": address,
            "addressCountry": "KR",
            "addressRegion": official_region(address, row.get("지역", "")),
            "addressLocality": row.get("시or구", ""),
        },
        "region": row.get("지역", ""),
        "city": row.get("시or구", ""),
        "street_address": address,
        "opening_hours": [],
        "identifier": ({"@type": "PropertyValue", "propertyID": "교육지원청 등록번호", "value": identifier} if identifier else None),
        "grades": unique(
            split_values(row.get("가능학년\n(국어)", ""))
            + split_values(row.get("가능학년\n(영어)", ""))
            + split_values(row.get("가능학년\n(수학)", ""))
        ),
        "schools": schools_for(row),
        "tuition_url": row.get("센터 교습비", ""),
        "center_url": encoded_url("전국센터", local),
        "body_image": f"/assets/centers/common/{body_name}",
        "body_mobile": f"/assets/centers/common/{mobile_name}",
        "map_image": map_source,
        "map_size": image_size(map_path),
        "source_mentions": [],
    }


def representative_mapping(slug: str) -> dict[str, str]:
    files = sorted((ROOT / "assets" / "representative").glob("*.webp"))
    if len(files) < 371:
        raise ValueError(f"대표이미지가 부족합니다: {len(files)}")
    random.Random(f"{DOMAIN_NAME}-{slug}-20260811").shuffle(files)
    return {local: "/" + path.relative_to(ROOT).as_posix() for local, path in zip(ORDER, files)}


def parse_site_reviews(value: str) -> list[dict[str, str]]:
    """Parse the three supplied review formats without exposing their labels.

    The source sets use a mixture of labelled lines (for example
    ``수업 점검 후기 예시 1:``) and standalone curly-quoted comments.  Every
    non-empty line is one supplied consultation scenario, so extracting the
    quoted body is both more robust and safer than carrying production labels
    into the public page.
    """
    reviews: list[dict[str, str]] = []
    for index, raw_line in enumerate(value.splitlines(), start=1):
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        quoted = re.search(r"[“\"](.+?)[”\"]\s*$", line)
        if quoted:
            content = quoted.group(1).strip()
        else:
            content = re.sub(
                r"^.*?(?:후기(?:형)?\s*예시|후기\s*형식|후기|상담\s*기록)\s*\d*\s*[:：|｜.)-]\s*",
                "",
                line,
            ).strip('“”" ')
        if content:
            reviews.append({"label": f"상담 상황 {index}", "content": content})
    return reviews


UNVERIFIED_OPERATION_RE = re.compile(
    r"(?:입시컨설팅학원|입시컨설팅반|입시합격관리|입시합격전략|입시성공사례|입시자료분석|입시일정관리|"
    r"입시로드맵|입시준비반|입시캠프반|입시캠프|입시실적|입시특강|입시설계|입시컨설팅|"
    r"입시분석|입시평가|입시결과|방학특강|방학캠프|셔틀|주말집중반|주말수업|오전수업|온라인수업|"
    r"화상수업|녹화수업|실시간수업|대면수업|소그룹수업|그룹수업|소수정예수업|일대일수업|"
    r"정원제수업|집중수업|특강수업|성적향상수업|내신보강수업|보충수업|과제관리수업|"
    r"플래너관리수업|토론형수업|수준별수업|밀착관리수업|집중관리수업|학습클리닉반|"
    r"장기관리반|플래너관리반|성적관리반|학습관리반|동기관리반|진도관리반|시험집중관리)"
    r"(?P<particle>이라는|라는|으로|로|은|는|이|가|을|를|과|와)?"
)


def replace_unverified_operation(match: re.Match[str], safe_term: str) -> str:
    particle = match.group("particle") or ""
    normalized = {
        "이라는": "이라는", "라는": "이라는", "으로": "으로", "로": "으로",
        "은": "은", "는": "은", "이": "이", "가": "이", "을": "을", "를": "을",
        "과": "과", "와": "과",
    }.get(particle, particle)
    return safe_term + normalized


def site_polish(value: str, local: str, config: dict[str, object]) -> str:
    """Remove source-authoring language while preserving verified facts."""
    text = re.sub(r"\s+", " ", value or "").strip()
    safe_term = {
        "combined": "과목별 복습 기록",
        "english": "영어 복습 기록",
        "math": "수학 재풀이 기록",
    }[str(config["focus"])]
    replacements = (
        ("학부모에게는 학부모 상담", "학부모 상담"),
        ("학부모에게는 학부모", "학부모에게는"),
        ("지역내 모든 고등학교 가능", "고등학교별 적용 여부 상담 확인 필요"),
        ("지역 내 모든 고등학교 가능", "고등학교별 적용 여부 상담 확인 필요"),
        ("학부모에게는 학원 선택 전에는", "학부모가 학원을 선택하기 전에는"),
        ("확인 센터 안내 기준으로", "확인된 센터 자료 기준으로"),
        ("놓치는 편 학생", "놓치는 학생"),
        ("놓치는 편 아이", "놓치는 아이"),
        ("편 학생", "학생"),
        ("편 아이", "아이"),
        ("것이라는 목표", "것을 목표"),
        ("것을 목표도", "목표도"),
        ("것을 목표에", "목표에"),
        (
            "목표도 이런 작은 기록이 쌓일 때 학부모와 학생 모두가 납득할 수 있습니다",
            "목표는 작은 기록이 쌓일 때 학부모와 학생 모두가 더 구체적으로 확인할 수 있습니다",
        ),
        ("형식의 후기입니다", "상담에서 살펴본 내용입니다"),
        ("내용으로 정리할 수 있습니다", "내용을 확인할 수 있습니다"),
        ("후기형 예시", "상담 상황"),
        ("설정한 학생 유형", "살펴볼 학생 상황"),
        ("수업학교", "수업 가능 학교"),
        ("영어 수학", "영어·수학"),
        ("어휘·문법·독해을", "어휘·문법·독해를"),
        ("개념·계산·문제 해석을", "개념·계산·문제 해석을"),
        ("확인 항목가", "확인 항목이"),
        ("확인 항목는", "확인 항목은"),
        ("확인 항목와", "확인 항목과"),
        ("학생와", "학생과"),
        ("학원라는", "학원이라는"),
        ("이 페이지에서 설정한", "상담에서 먼저 살펴볼"),
        ("이 페이지는", "이 안내는"),
        ("이 페이지에서", "이 안내에서"),
        ("페이지에서는", "상담에서는"),
        ("페이지에는", "안내에는"),
        ("페이지의", "안내의"),
        ("페이지를", "안내를"),
        ("페이지가", "안내가"),
        ("페이지로", "안내로"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    text = UNVERIFIED_OPERATION_RE.sub(
        lambda match: replace_unverified_operation(match, safe_term),
        text,
    )
    text = re.sub(r"(?<=\d)으로(?=\s|[,.]|$)", "로", text)
    text = text.replace("학원 운영 정보", "수업 운영 기준")
    text = text.replace("보강 가능 시간", "복습 가능한 시간")
    text = text.replace(f"{local}{config['label']}", f"{local} {config['label']}")
    text = re.sub(
        r"(?:상담 과정에서는|이때|먼저|실제로|시험을 앞두면|수업을 시작하기 전에는|학습 계획을 세울 때는)\s+"
        r"이 안내에서 설정한 [^,.]{1,60}? 학생 유형은",
        f"{local} 상담에서 먼저 살펴볼 학생은",
        text,
    )
    text = re.sub(
        r"이 안내에서 설정한 [^,.]{1,60}? 학생 유형은",
        f"{local} 상담에서 먼저 살펴볼 학생은",
        text,
    )
    text = re.sub(
        r"[^,.]{1,50}? 본문에서 학교명을 다룰 때는",
        "상담에서 학교 정보를 확인할 때는",
        text,
    )
    text = text.replace(
        "알 수 있었다는 점을 남길 수 있습니다",
        "집에서도 확인할 기준이 분명해졌습니다",
    )
    text = re.sub(
        r"([^.!?]{1,80}?)다는 점을 남길 수 있습니다",
        r"\1다는 점을 확인할 수 있었습니다",
        text,
    )
    text = text.replace("해당 영어 관리 방식 수업은", "영어 수업은")
    text = text.replace("해당 영어 관리 방식에서", "영어 수업에서는")
    text = text.replace("해당 영어 관리 방식 상담", "영어 상담")
    text = text.replace("지역별 영어 학습 기준 수업", "영어 수업")
    text = text.replace("이 영어 학습 과정 중등 과정", "영어 중등 과정")
    text = text.replace("지역별 영어 학습 기준 고등 과정", "영어 고등 과정")
    if config["focus"] == "english":
        text = text.replace("영어·수학 보완 순서", "영어 보완 순서")
    elif config["focus"] == "math":
        text = text.replace("영어·수학 보완 순서", "수학 보완 순서")
    text = re.sub(
        r"[^.!?]*SEO\s*검색에도 도움이 되고,?\s*AEO[·/ ]*GEO\s*환경에서도 학부모의 의도를 바로 설명할 수 있습니다\.?",
        " 학생의 현재 기록을 상담 질문으로 바꾸면 다음 복습 순서를 더 분명하게 확인할 수 있습니다.",
        text,
    )
    text = re.sub(r"\b(?:SEO|AEO|GEO)\b", "학습 안내", text)
    text = re.sub(r"(?<![가-힣])원고(?:에서는|에서|에는|에|의|를|로|가|는)?(?![가-힣])", "안내", text)
    text = re.sub(r"(?<![가-힣])키워드(?![가-힣])", "확인 항목", text)
    text = re.sub(r"(?<![가-힣])페이지(?![가-힣])", "안내", text)
    text = re.sub(
        r"학원\s*(?:실\s*시간\s*수업|온라인\s*수업|화상\s*수업|대면\s*수업|차량|주차|시설|방역(?:관리)?|"
        r"예약(?:관리)?|결제(?:시스템|관리)?|출결(?:앱|관리)?|전자계약|온라인등록|알림톡|관리시스템|고객관리|"
        r"수강생관리|직원|원장|강사|매니저|보강|특강|주말수업|소수정예(?:수업)?|일대일(?:수업)?|집중반|"
        r"상담실|자습실|스터디룸|강의실|휴게실|사물함)",
        "수업 운영 방식",
        text,
    )
    text = text.replace(
        "자료에 없는 학교를 임의로 추가하지 않는 것이 신뢰를 지키는 방법입니다.",
        "실제 학교와 시험 범위는 상담에서 최신 자료로 다시 확인합니다.",
    )
    text = text.replace(
        "학교명을 임의로 추가하지 않는 것이 신뢰를 지키는 방법입니다.",
        "실제 학교와 시험 범위는 상담에서 최신 자료로 다시 확인합니다.",
    )
    text = text.replace(";", ".")
    text = re.sub(r"\s+([,.!?])", r"\1", text)
    text = re.sub(r"([.!?]){2,}", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def polish_manuscript(
    manuscript: dict[str, object],
    local: str,
    config: dict[str, object],
    center: dict[str, object],
) -> dict[str, object]:
    verified_grades = [str(item) for item in center.get("verified_grades", [])]
    schools = [str(item) for item in center.get("schools", [])]

    def clean(value: object) -> str:
        first = site_polish(str(value or ""), local, config)
        grammar = content_engine.final_polish(first, local, config, verified_grades, schools)
        return site_polish(grammar, local, config)

    manuscript["meta"] = clean(manuscript.get("meta"))
    manuscript["intro"] = [clean(item) for item in manuscript.get("intro", [])]
    manuscript["sections"] = [
        (clean(heading), [clean(paragraph) for paragraph in paragraphs])
        for heading, paragraphs in manuscript.get("sections", [])
    ]
    manuscript["faqs"] = [
        {"question": clean(item["question"]), "answer": clean(item["answer"])}
        for item in manuscript.get("faqs", [])
    ]
    manuscript["reviews"] = [
        {"label": clean(item.get("label") or f"{local} 상담 상황 {index}"), "content": clean(item["content"])}
        for index, item in enumerate(manuscript.get("reviews", []), start=1)
    ]
    manuscript["summary"] = clean(manuscript.get("summary"))
    manuscript["answer_heading"] = clean(manuscript.get("answer_heading"))
    manuscript["answer_text"] = clean(manuscript.get("answer_text"))
    manuscript["answer_tags"] = [clean(item) for item in manuscript.get("answer_tags", [])]
    return manuscript


def validate_manuscript(slug: str, local: str, manuscript: dict[str, object]) -> None:
    meta = str(manuscript.get("meta", ""))
    if not 70 <= len(meta) <= 100:
        raise ValueError(f"{slug}/{local}: 메타 길이 {len(meta)}자")
    if len(manuscript.get("reviews", [])) != EXPECTED_REVIEW_COUNTS[slug]:
        raise ValueError(
            f"{slug}/{local}: 상담 상황 {len(manuscript.get('reviews', []))}개, "
            f"기대 {EXPECTED_REVIEW_COUNTS[slug]}개"
        )
    if len(manuscript.get("faqs", [])) < 4:
        raise ValueError(f"{slug}/{local}: FAQ가 4개 미만입니다")
    visible = " ".join(
        [meta, *[str(item) for item in manuscript.get("intro", [])]]
        + [str(value) for pair in manuscript.get("sections", []) for value in (pair[0], *pair[1])]
        + [str(value) for item in manuscript.get("faqs", []) for value in (item["question"], item["answer"])]
        + [str(value) for item in manuscript.get("reviews", []) for value in (item["label"], item["content"])]
        + [str(manuscript.get("summary", "")), str(manuscript.get("answer_heading", "")), str(manuscript.get("answer_text", ""))]
    )
    forbidden = re.compile(
        r"(?:\bSEO\b|\bAEO\b|\bGEO\b|(?<![가-힣])원고(?![가-힣])|(?<![가-힣])키워드(?![가-힣])|"
        r"후기형\s*예시|설정한\s*학생\s*유형|놓치는\s*편\s*학생|것이라는\s*목표|"
        r"형식의\s*후기|수업학교|확인\s*항목[가는와]|학생와|학원라는|편\s*(?:학생|아이)|"
        r"학원\s*(?:실\s*시간|온라인|화상|대면)\s*수업|이\s*안내에서\s*설정한|"
        r"남길\s*수\s*있습니다|목표도\s*이런|(?<![가-힣])본문에서(?![가-힣]))"
    )
    match = forbidden.search(visible)
    if match:
        raise ValueError(f"{slug}/{local}: 공개용 문장 금지 표현 {match.group(0)!r}")
    operation = UNVERIFIED_OPERATION_RE.search(visible)
    if operation:
        raise ValueError(f"{slug}/{local}: 검증되지 않은 운영 표현 {operation.group(0)!r}")
    awkward = re.search(r"(?:학부모에게는\s*학부모|\d{2,4}으로(?:\s|[,.])|지역\s*내\s*모든\s*고등학교)", visible)
    if awkward:
        raise ValueError(f"{slug}/{local}: 문장 또는 사실 표현 오류 {awkward.group(0)!r}")


def prepare_manuscripts(config: dict[str, object]) -> tuple[dict[str, dict[str, object]], object]:
    content_engine.ROOT = ROOT
    content_engine.SITE_URL = SITE_URL
    content_engine.SITE_NAME = SITE_NAME
    content_engine.TODAY = TODAY
    content_engine.CENTER_INFO_PATH = CENTER_CSV
    content_engine.CENTER_ROWS = {**ROWS, **{name: row_for(name) for name in ORDER}}
    content_engine.shared.ROOT = ROOT
    content_engine.shared.SITE_URL = SITE_URL
    content_engine.shared.TODAY = TODAY

    namespace = content_engine.shared.transformed_namespace(config)
    namespace.update(
        {
            "ROOT": ROOT,
            "SITE_URL": SITE_URL,
            "SITE_NAME": SITE_NAME,
            "TODAY": TODAY,
            "SOURCE_DIR": SOURCE_DIR,
            "ZIP_PATH": SOURCE_DIR / str(config["zip"]),
            "ENGLISH_ROOT": SUBJECT_ROOT / str(config["slug"]),
            "MATH_ROOT": ROOT / "전국센터",
            "extract_center_data": base_center_data,
            "ordered_locals_and_directory": lambda: (ORDER, ""),
            "select_representatives": lambda _order: representative_mapping(str(config["slug"])),
            "update_subject_hub": lambda: None,
            "update_sitemap": lambda _order: None,
        }
    )
    content_engine.configure_namespace(namespace, config)
    namespace["parse_reviews"] = parse_site_reviews
    values = namespace["load_manuscripts"]()
    mapped: dict[str, dict[str, object]] = {}
    for source_local, manuscript in values.items():
        local = actual_local(str(source_local))
        if local in mapped:
            raise ValueError(f"원고 동네가 중복 매핑되었습니다: {local}")
        manuscript["title"] = f"{local} {config['label']}"
        center = namespace["extract_center_data"](local)
        polish_manuscript(manuscript, local, config, center)
        validate_manuscript(str(config["slug"]), local, manuscript)
        mapped[local] = manuscript
    missing = set(ORDER) - set(mapped)
    extra = set(mapped) - set(ORDER)
    if len(mapped) != 371 or missing or extra:
        raise ValueError(f"{config['slug']} 원고 매핑 오류: pages={len(mapped)} missing={sorted(missing)[:5]} extra={sorted(extra)[:5]}")
    return mapped, namespace


def navigation(home: str, active: str) -> str:
    links = (
        ("홈", ""),
        ("학습관리", "학습관리/"),
        ("과목별학원", "과목별학원/"),
        ("전국센터", "전국센터/"),
        ("상담문의", "상담문의/"),
    )
    rendered = "".join(
        f'<a{" class=\"active\" aria-current=\"page\"" if label == active else ""} href="{esc(home + suffix)}">{label}</a>'
        for label, suffix in links
    )
    return f'''<header class="site-header">
    <nav class="nav wrap" aria-label="주요 메뉴">
      <a class="brand" href="{esc(home)}"><span class="brand-mark">W</span><span><small>STUDY COACHING</small>{SITE_NAME}</span></a>
      <div class="nav-links">{rendered}</div>
      <a class="nav-cta" href="{CONSULT_URL}" target="_blank" rel="noopener">상담 신청</a>
    </nav>
  </header>'''


def footer(home: str) -> str:
    return f'''<footer class="site-footer" id="contact"><div class="wrap footer-inner"><div><a class="brand footer-brand" href="{esc(home)}"><span class="brand-mark">W</span><span><small>STUDY COACHING</small>{SITE_NAME}</span></a><p>초중고 영어수학 학습코칭 · 진단상담 · 플래너 관리</p></div><div class="footer-links"><a href="{esc(home)}학습관리/">학습관리</a><a href="{esc(home)}과목별학원/">과목별학원</a><a href="{esc(home)}전국센터/">전국센터</a><a href="tel:{PHONE}">{PHONE}</a></div></div></footer>
  <nav class="floating-actions" aria-label="빠른 상담 메뉴"><a class="fab-call" href="tel:{PHONE}">전화문의</a><a class="fab-sms" href="{SMS_URL}" target="_blank" rel="noopener">문자문의</a><a class="fab-consult" href="{CONSULT_URL}" target="_blank" rel="noopener">상담신청</a></nav>'''


def head(title: str, description: str, canonical: str, image: str, schema: dict[str, object], depth: int, page_type: str) -> str:
    home = "../" * depth
    return f'''<!doctype html>
<html lang="ko"><head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title><meta name="description" content="{esc(description)}"><meta name="robots" content="index, follow">
  <link rel="canonical" href="{esc(canonical)}"><link rel="alternate" type="application/rss+xml" title="{SITE_NAME} RSS" href="{SITE_URL}/rss.xml">
  <meta property="og:type" content="{page_type}"><meta property="og:url" content="{esc(canonical)}"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:image" content="{esc(image)}">
  <meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{esc(title)}"><meta name="twitter:description" content="{esc(description)}"><meta name="twitter:image" content="{esc(image)}">
  <link rel="icon" type="image/png" href="{home}assets/favicon.png"><link rel="apple-touch-icon" href="{home}assets/favicon.png"><link rel="stylesheet" href="{home}assets/site.css">
  <script type="application/ld+json">{compact_json(schema)}</script>
</head>'''


def subject_root_schema() -> dict[str, object]:
    url = encoded_url("과목별학원")
    items = [
        {"@type": "ListItem", "position": index, "name": CATEGORY_COPY[slug]["label"], "url": encoded_url("과목별학원", slug)}
        for index, slug in enumerate(TARGET_SLUGS, 1)
    ]
    faqs = subject_root_faqs()
    return {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "CollectionPage", "@id": url + "#webpage", "url": url, "name": f"과목별학원 | {DOMAIN_NAME}", "description": "영수·영어·수학 전문학원 안내를 371개 동네별로 찾고 현재 학습 상태, 센터 정보와 상담 준비 기준을 확인할 수 있습니다.", "inLanguage": "ko-KR", "isPartOf": {"@id": SITE_URL + "/#website"}, "breadcrumb": {"@id": url + "#breadcrumb"}, "mainEntity": {"@id": url + "#directory"}, "dateModified": TODAY},
            {"@type": "BreadcrumbList", "@id": url + "#breadcrumb", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "홈", "item": SITE_URL + "/"}, {"@type": "ListItem", "position": 2, "name": "과목별학원", "item": url}]},
            {"@type": "ItemList", "@id": url + "#directory", "name": "전문학원 분류", "numberOfItems": len(items), "itemListElement": items},
            {"@type": "FAQPage", "@id": url + "#faq", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]},
        ],
    }


def subject_root_faqs() -> list[tuple[str, str]]:
    return [
        ("과목별학원 페이지는 전국센터와 무엇이 다른가요?", "전국센터는 동네와 센터를 먼저 선택하는 구조이고, 과목별학원은 영수·영어·수학 전문학원 분류를 먼저 고른 뒤 해당 동네의 학습 안내를 확인하는 구조입니다."),
        ("전문학원 상담 전에는 어떤 자료를 준비하면 좋나요?", "최근 시험지와 현재 교재, 틀린 문제의 답안·풀이 기록, 학교 시험 범위와 일주일 공부 시간을 준비하면 현재 상태를 더 구체적으로 나눌 수 있습니다."),
        ("동네 페이지에 표시된 센터 정보는 어떻게 확인하나요?", "제공된 센터정보 자료의 센터명, 주소, 교육지원청 등록번호, 가능 학년과 학교 정보를 사용하며 실제 개설 여부와 시간표는 상담에서 다시 확인합니다."),
    ]


def render_subject_root() -> str:
    canonical = encoded_url("과목별학원")
    description = "영수·영어·수학 전문학원 안내를 371개 동네별로 찾고 현재 학습 상태, 센터 정보와 상담 준비 기준을 확인할 수 있습니다."
    cards = "".join(
        f'''<a class="home-link-card{' is-primary' if index == 0 else ''}" href="./{slug}/"><span>{esc(CATEGORY_COPY[slug]['eyebrow'])}</span><strong>{esc(CATEGORY_COPY[slug]['label'])}</strong><p>{esc(CATEGORY_COPY[slug]['lead'])}</p></a>'''
        for index, slug in enumerate(TARGET_SLUGS)
    )
    faq = "".join(f'<details{" open" if index == 0 else ""}><summary>{esc(q)}</summary><p>{esc(a)}</p></details>' for index, (q, a) in enumerate(subject_root_faqs()))
    return f'''{head(f"과목별학원 | {DOMAIN_NAME}", description, canonical, SITE_URL + "/assets/generated/site3-hero.webp", subject_root_schema(), 1, "website")}
<body class="center-page subject-page"><a class="skip-link" href="#main">본문 바로가기</a>{navigation("../", "과목별학원")}
  <main id="main">
    <section class="center-hero"><div class="wrap"><div class="crumbs"><span><a href="../">홈</a></span><span>과목별학원</span></div><div class="center-hero-card"><div class="center-hero-inner"><div><p class="eyebrow">SUBJECT ACADEMY DIRECTORY</p><h1>과목별학원</h1><p>{description}</p><div class="local-actions"><a class="btn btn-primary" href="#subject-categories">분류 선택</a><a class="btn btn-ghost" href="../전국센터/">전국센터 보기</a></div></div><aside class="hero-mini-panel"><span>전문학원 분류</span><strong>3개</strong><span>각 371개 동네 안내</span></aside></div></div></div></section>
    <section id="subject-categories" class="local-section"><div class="wrap"><article class="home-link-hub"><p class="eyebrow">CHOOSE A SUBJECT</p><h2>학생의 현재 과목 상황부터 선택하세요</h2><p>두 과목의 균형이 필요하면 영수 전문학원, 한 과목의 진단과 복습을 깊게 보고 싶다면 영어 또는 수학 전문학원 안내를 선택할 수 있습니다.</p><div class="home-link-grid">{cards}</div></article></div></section>
    <section class="local-section"><div class="wrap local-grid"><article class="local-card"><p class="eyebrow">HOW TO USE</p><h2>동네 페이지 확인 순서</h2><ol class="process-list"><li><strong>1. 분류 선택</strong>영수·영어·수학 가운데 현재 우선순위를 고릅니다.</li><li><strong>2. 동네 검색</strong>허브에서 동네명 또는 광역지역을 선택합니다.</li><li><strong>3. 자료 확인</strong>최근 교재·시험지, 센터 정보와 가능 학년을 함께 봅니다.</li><li><strong>4. 상담 질문</strong>진단·과제·오답 재확인 과정을 실제 시간표와 대조합니다.</li></ol></article><article class="local-card"><p class="eyebrow">FACT CHECK</p><h2>안내 정보의 기준</h2><p>센터명·주소·교육지원청 등록번호·가능 학년·참고 학교는 제공된 센터정보 자료를 사용합니다. 자료가 비어 있는 항목은 임의로 만들지 않으며 상담 확인이 필요하다고 표시합니다.</p><p class="verified-note">자료 기준: 센터정보 정리 자료 · 최종 검수 {TODAY}</p></article></div></section>
    <section id="faq-section" class="local-section"><div class="wrap faq-local"><p class="eyebrow">FAQ</p><h2>과목별학원 이용 전 확인사항</h2>{faq}</div></section>
  </main>{footer("../")}
</body></html>'''


def hub_faqs(slug: str) -> list[tuple[str, str]]:
    label = str(CATEGORY_COPY[slug]["label"])
    if slug == "영수전문학원":
        first = "영어와 수학의 최근 시험지·교재를 따로 놓고 취약 영역, 과목별 오답, 학교 일정과 주간 학습시간을 비교할 수 있습니다."
    elif slug == "영어전문학원":
        first = "최근 영어 시험지와 교재에서 어휘 누적, 문법 적용, 독해 근거와 서술형 표현을 나누어 확인할 수 있습니다."
    else:
        first = "최근 수학 시험지와 풀이에서 개념 이해, 계산 과정, 문제 조건 해석, 서술형 표현과 오답 재도전을 나누어 확인할 수 있습니다."
    return [
        (f"동네별 {label} 페이지에서는 무엇을 확인할 수 있나요?", first + " 센터 자료가 있는 경우 주소·가능 학년·학교 정보도 함께 안내합니다."),
        (f"{label} 상담 전 어떤 자료를 준비하면 좋나요?", "최근 시험지와 현재 교재, 틀린 문제의 답안 또는 풀이 흔적, 학교 시험 범위와 일주일 공부 시간을 준비하면 진단과 계획을 더 구체적으로 살펴볼 수 있습니다."),
        (f"{label} 선택에서 진도보다 먼저 볼 기준은 무엇인가요?", "학생이 막힌 지점을 어떻게 진단하고, 수업 뒤 어떤 기록을 남기며, 일정 기간이 지난 뒤 오답을 다시 확인하는지부터 비교하는 편이 좋습니다."),
    ]


def hub_schema(slug: str) -> dict[str, object]:
    copy = CATEGORY_COPY[slug]
    url = encoded_url("과목별학원", slug)
    items = [
        {"@type": "ListItem", "position": index, "name": f"{local} {copy['label']}", "url": encoded_url("과목별학원", slug, local)}
        for index, local in enumerate(ORDER, 1)
    ]
    faqs = hub_faqs(slug)
    return {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "CollectionPage", "@id": url + "#webpage", "url": url, "name": f"{copy['label']} 지역 안내 | {DOMAIN_NAME}", "description": copy["lead"], "inLanguage": "ko-KR", "isPartOf": {"@id": SITE_URL + "/#website"}, "breadcrumb": {"@id": url + "#breadcrumb"}, "mainEntity": {"@id": url + "#directory"}, "about": [{"@type": "Thing", "name": copy["label"]}], "dateModified": TODAY},
            {"@type": "BreadcrumbList", "@id": url + "#breadcrumb", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "홈", "item": SITE_URL + "/"}, {"@type": "ListItem", "position": 2, "name": "과목별학원", "item": encoded_url("과목별학원")}, {"@type": "ListItem", "position": 3, "name": f"{copy['label']} 지역 안내", "item": url}]},
            {"@type": "ItemList", "@id": url + "#directory", "name": f"동네별 {copy['label']} 안내", "numberOfItems": 371, "itemListElement": items},
            {"@type": "FAQPage", "@id": url + "#faq", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]},
        ],
    }


def directory_markup(slug: str) -> str:
    grouped: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for local in ORDER:
        row = row_for(local)
        grouped[row.get("지역", "기타")][row.get("시or구", "지역 안내")].append(local)
    sections: list[str] = []
    for region in REGION_ORDER:
        districts = grouped.get(region, {})
        if not districts:
            continue
        district_markup: list[str] = []
        for district in sorted(districts):
            locals_here = sorted(districts[district])
            links = "".join(
                f'<a class="hub-link subject-locality-link" href="./{quote(local, safe="")}/" data-local="{esc(local)}"><strong>{esc(local)}</strong><small>{esc(CATEGORY_COPY[slug]["label"])}</small></a>'
                for local in locals_here
            )
            district_markup.append(f'<details class="category-district" open><summary>{esc(district)} <small>{len(locals_here)}개 동네</small></summary><div class="hub-links">{links}</div></details>')
        sections.append(f'<section class="category-region-panel" data-region="{esc(region)}"><h2>{esc(region)} {esc(CATEGORY_COPY[slug]["label"])}</h2><div class="category-district-list">{"".join(district_markup)}</div></section>')
    return "".join(sections)


def render_hub(slug: str) -> str:
    copy = CATEGORY_COPY[slug]
    canonical = encoded_url("과목별학원", slug)
    title = f"{copy['label']} 지역 안내 | {DOMAIN_NAME}"
    faqs = hub_faqs(slug)
    faq = "".join(f'<details{" open" if index == 0 else ""}><summary>{esc(q)}</summary><p>{esc(a)}</p></details>' for index, (q, a) in enumerate(faqs))
    tags = "".join(f"<span>{esc(tag)}</span>" for tag in copy["tags"])
    return f'''{head(title, str(copy['lead']), canonical, SITE_URL + "/assets/generated/site3-hero.webp", hub_schema(slug), 2, "website")}
<body class="center-page subject-page"><a class="skip-link" href="#main">본문 바로가기</a>{navigation("../../", "과목별학원")}
  <main id="main">
    <section class="center-hero"><div class="wrap"><div class="crumbs"><span><a href="../../">홈</a></span><span><a href="../">과목별학원</a></span><span>{esc(copy['label'])} 지역 안내</span></div><div class="center-hero-card"><div class="center-hero-inner"><div><p class="eyebrow">{esc(copy['eyebrow'])}</p><h1>동네별 {esc(copy['label'])} 안내</h1><p>{esc(copy['lead'])}</p><div class="keyword-row local-keywords">{tags}</div></div><aside class="hero-mini-panel"><span>지역 상세 안내</span><strong>371개</strong><span>검색 · 광역지역 · 시군구</span></aside></div></div></div></section>
    <section class="local-section"><div class="wrap local-grid"><article class="local-card"><p class="eyebrow">상담 핵심 답변</p><h2>{esc(copy['label'])}, 무엇부터 확인할까요?</h2><p>{esc(copy['summary'])}</p></article><article class="local-card"><p class="eyebrow">CONSULTATION CHECK</p><h2>상담 전 준비할 기록</h2><ul class="summary-list"><li>최근 시험지와 현재 교재</li><li>틀린 문제의 답안 또는 풀이 흔적</li><li>학교 시험 범위와 수행 일정</li><li>일주일 공부 시간과 과제 기록</li></ul></article></div></section>
    <section class="local-section"><div class="wrap"><article class="center-search-card"><div class="center-search-head"><div><p class="eyebrow">LOCAL DIRECTORY</p><h2>동네명으로 {esc(copy['label'])} 찾기</h2><p>검색하거나 광역지역·시군구를 차례로 펼쳐 원하는 동네 안내로 이동할 수 있습니다.</p></div><form class="center-search-form" id="subjectSearch"><label for="subjectSearchInput">동네 이름으로 찾기</label><input id="subjectSearchInput" type="search" placeholder="예: 명일동, 불당동, 가경동" autocomplete="off"><button type="submit">첫 결과로 이동</button></form></div><div class="center-search-meta"><span>전체 371개 동네</span><span id="subjectSearchStatus" aria-live="polite">동네 이름을 입력해 주세요.</span></div></article><div class="category-directory-tools"><div class="category-region-tabs" role="group" aria-label="광역지역 선택"><button class="category-region-tab" type="button" data-region="all" aria-pressed="true">전체</button>{''.join(f'<button class="category-region-tab" type="button" data-region="{esc(region)}" aria-pressed="false">{esc(region)}</button>' for region in REGION_ORDER)}</div></div>{directory_markup(slug)}</div></section>
    <section id="faq-section" class="local-section"><div class="wrap faq-local"><p class="eyebrow">FAQ</p><h2>{esc(copy['label'])} 안내 이용 전 확인사항</h2>{faq}</div></section>
  </main>{footer("../../")}
  <script>(()=>{{const input=document.getElementById('subjectSearchInput');const form=document.getElementById('subjectSearch');const status=document.getElementById('subjectSearchStatus');const links=[...document.querySelectorAll('.subject-locality-link')];const panels=[...document.querySelectorAll('.category-region-panel')];const tabs=[...document.querySelectorAll('.category-region-tab')];let region='all';function apply(){{const q=input.value.trim().toLowerCase();let visible=0;links.forEach(link=>{{const inRegion=region==='all'||link.closest('.category-region-panel').dataset.region===region;const match=!q||link.dataset.local.toLowerCase().includes(q);link.hidden=!(inRegion&&match);if(!link.hidden)visible++;}});document.querySelectorAll('.category-district').forEach(group=>{{const show=[...group.querySelectorAll('.subject-locality-link')].some(link=>!link.hidden);group.hidden=!show;if(q&&show)group.open=true;}});panels.forEach(panel=>panel.hidden=![...panel.querySelectorAll('.subject-locality-link')].some(link=>!link.hidden));status.textContent=q||region!=='all'?visible+'개 동네가 검색되었습니다.':'동네 이름을 입력해 주세요.';}}input.addEventListener('input',apply);tabs.forEach(tab=>tab.addEventListener('click',()=>{{region=tab.dataset.region;tabs.forEach(item=>item.setAttribute('aria-pressed',String(item===tab)));apply();}}));form.addEventListener('submit',event=>{{event.preventDefault();const first=links.find(link=>!link.hidden);if(first)location.href=first.href;else status.textContent='일치하는 동네가 없습니다.';}});}})();</script>
</body></html>'''


def detail_schema(slug: str, local: str, manuscript: dict[str, object], center: dict[str, object], representative: str, links: list[dict[str, str]]) -> dict[str, object]:
    config = ENGINE_CONFIGS[slug]
    title = str(manuscript["title"])
    description = str(manuscript["meta"])
    summary = str(manuscript.get("summary") or description)
    url = encoded_url("과목별학원", slug, local)
    center_url = encoded_url("전국센터", local)
    center_id = center_url + "#organization"
    image_url = SITE_URL + representative
    headings = [str(heading) for heading, _ in manuscript.get("sections", [])]
    schools = [str(value) for value in center.get("schools", [])]
    grades = [str(value) for value in center.get("verified_grades", [])]
    mentions = [{"@type": "Place", "name": local}, {"@type": "Thing", "name": config["label"]}, *[{"@type": "Organization", "name": school} for school in schools]]
    offer = None
    if grades and center.get("tuition_url"):
        offer = {"@type": "Offer", "url": center["tuition_url"], "category": "교습비 안내", "description": "교습비와 현재 수업 가능 여부는 연결된 공개 자료와 상담에서 확인합니다."}
    organization: dict[str, object] = {
        "@type": ["EducationalOrganization", "LocalBusiness"], "@id": center_id,
        "name": center["organization_name"], "url": center_url, "telephone": PHONE,
        "address": center["address"], "areaServed": {"@type": "Place", "name": f"{center['region']} {center['city']} {local}"},
    }
    if center.get("identifier"):
        organization["identifier"] = center["identifier"]
    if grades:
        organization["educationalLevel"] = grades
        organization["teaches"] = list(config["subjects"])
    if offer:
        organization["makesOffer"] = [offer]
    service: dict[str, object] = {
        "@type": "Service", "@id": url + "#service", "name": f"{title} 학습관리",
        "serviceType": str(config["label"]) if grades else f"{config['label']} 수업 가능 여부 상담",
        "description": summary, "provider": {"@id": center_id}, "areaServed": {"@type": "Place", "name": local},
        "about": [{"@type": "Thing", "name": topic} for topic in config["topics"]],
    }
    if grades:
        service["audience"] = {"@type": "EducationalAudience", "educationalRole": "student", "audienceType": " · ".join(grades)}
    if offer:
        service["offers"] = offer
    faqs = [{"@type": "Question", "name": item["question"], "acceptedAnswer": {"@type": "Answer", "text": item["answer"]}} for item in manuscript["faqs"]]
    related = [{"@type": "ListItem", "position": index, "name": item["name"], "url": item["url"]} for index, item in enumerate(links, 1)]
    parts = [{"@type": "WebPageElement", "name": heading, "url": url + f"#section-{index}"} for index, heading in enumerate(headings, 1)]
    provenance_id = url + "#source"
    graph: list[dict[str, object]] = [
        {"@type": "WebPage", "@id": url + "#webpage", "url": url, "name": f"{title} | {DOMAIN_NAME}", "description": description, "inLanguage": "ko-KR", "isPartOf": {"@id": SITE_URL + "/#website"}, "about": [{"@type": "Thing", "name": config["label"]}], "mentions": mentions, "breadcrumb": {"@id": url + "#breadcrumb"}, "mainEntity": {"@id": url + "#service"}, "primaryImageOfPage": {"@id": url + "#primaryimage"}, "dateModified": TODAY},
        {"@type": "ImageObject", "@id": url + "#primaryimage", "contentUrl": image_url, "url": image_url, "caption": f"{title} {DOMAIN_NAME} 대표", "inLanguage": "ko-KR"},
        organization,
        {"@type": "BreadcrumbList", "@id": url + "#breadcrumb", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "홈", "item": SITE_URL + "/"}, {"@type": "ListItem", "position": 2, "name": "과목별학원", "item": encoded_url("과목별학원")}, {"@type": "ListItem", "position": 3, "name": config["label"], "item": encoded_url("과목별학원", slug)}, {"@type": "ListItem", "position": 4, "name": title, "item": url}]},
        {"@type": "Article", "@id": url + "#article", "headline": title, "description": summary, "inLanguage": "ko-KR", "mainEntityOfPage": {"@id": url + "#webpage"}, "author": {"@id": center_id}, "publisher": {"@id": center_id}, "about": [{"@type": "Thing", "name": config["label"]}], "mentions": mentions, "hasPart": parts, "articleSection": [config["label"], center["region"], center["city"], local, *headings], "image": {"@id": url + "#primaryimage"}, "isBasedOn": {"@id": provenance_id}, "dateModified": TODAY},
        service,
        {"@type": "FAQPage", "@id": url + "#faq", "mainEntity": faqs},
        {"@type": "ItemList", "@id": url + "#related", "name": f"{title} 관련 안내", "itemListElement": related},
        {"@type": "CreativeWork", "@id": provenance_id, "name": "센터정보 정리 자료", "dateModified": TODAY, "description": "센터명·주소·교육지원청 등록번호·가능 학년·학교 자료를 확인한 내부 기준 자료입니다."},
    ]
    return {"@context": "https://schema.org", "@graph": graph}


def related_links(slug: str, local: str, index: int) -> list[dict[str, str]]:
    links = [
        {"name": f"{local} {CATEGORY_COPY[other]['label']}", "url": encoded_url("과목별학원", other, local)}
        for other in TARGET_SLUGS if other != slug
    ]
    links.extend(
        [
            {"name": f"{local} 전국센터 안내", "url": encoded_url("전국센터", local)},
            {"name": f"{CATEGORY_COPY[slug]['label']} 전체 지역", "url": encoded_url("과목별학원", slug)},
            {"name": "과목별학원 전체 안내", "url": encoded_url("과목별학원")},
            {"name": "학습관리 안내", "url": encoded_url("학습관리")},
            {"name": f"이전 지역 · {ORDER[index - 1] if index else ORDER[-1]}", "url": encoded_url("과목별학원", slug, ORDER[index - 1] if index else ORDER[-1])},
            {"name": f"다음 지역 · {ORDER[index + 1] if index + 1 < len(ORDER) else ORDER[0]}", "url": encoded_url("과목별학원", slug, ORDER[index + 1] if index + 1 < len(ORDER) else ORDER[0])},
        ]
    )
    return links


def render_detail(slug: str, local: str, index: int, manuscript: dict[str, object], center: dict[str, object], representative: str) -> str:
    config = ENGINE_CONFIGS[slug]
    title = str(manuscript["title"])
    description = str(manuscript["meta"])
    summary = str(manuscript.get("summary") or description)
    canonical = encoded_url("과목별학원", slug, local)
    links = related_links(slug, local, index)
    schema = detail_schema(slug, local, manuscript, center, representative, links)
    grades = [str(value) for value in center.get("verified_grades", [])]
    grade_html = "".join(f"<span>{esc(value)}</span>" for value in grades) if grades else "<span>상담 확인 필요</span>"
    schools = [str(value) for value in center.get("schools", [])]
    school_html = "".join(f"<span>{esc(value)}</span>" for value in schools)
    sections = "".join(
        f'<section class="subject-prose-section" id="section-{section_index}"><p class="subject-section-index">{section_index:02d}</p><h2>{esc(heading)}</h2>{"".join(f"<p>{esc(paragraph)}</p>" for paragraph in paragraphs)}</section>'
        for section_index, (heading, paragraphs) in enumerate(manuscript.get("sections", []), 1)
    )
    intro = "".join(f"<p>{esc(paragraph)}</p>" for paragraph in manuscript.get("intro", []))
    faqs = "".join(f'<details{" open" if faq_index == 0 else ""}><summary>{esc(item["question"])}</summary><p>{esc(item["answer"])}</p></details>' for faq_index, item in enumerate(manuscript["faqs"]))
    cases = "".join(f'<article class="review-card"><strong>{esc(review.get("label", f"상담 상황 {case_index}"))}</strong><p>{esc(review["content"])}</p></article>' for case_index, review in enumerate(manuscript.get("reviews", []), 1))
    link_html = "".join(f'<a href="{esc(item["url"])}">{esc(item["name"])}</a>' for item in links)
    map_width, map_height = center.get("map_size", (0, 0))
    map_dimensions = f' width="{map_width}" height="{map_height}"' if map_width and map_height else ""
    body_mobile = str(center.get("body_mobile", ""))
    body_image = str(center["body_image"])
    info_rows = [
        ("센터명", center["organization_name"]),
        ("센터 주소", center["street_address"]),
        (f"{config['label']} 가능 학년", " · ".join(grades) if grades else "제공 자료에 공통 가능 학년 정보가 없어 상담 확인이 필요합니다."),
    ]
    if center.get("identifier"):
        info_rows.append(("교육지원청 등록번호", center["identifier"].get("value", "")))
    data_rows = "".join(f"<div><dt>{esc(label)}</dt><dd>{esc(value)}</dd></div>" for label, value in info_rows)
    tuition = f'<a class="text-link" href="{esc(center["tuition_url"])}" target="_blank" rel="noopener noreferrer">센터별 교습비 자료 확인 ↗</a>' if center.get("tuition_url") else ""
    return f'''{head(f"{title} | {DOMAIN_NAME}", description, canonical, SITE_URL + representative, schema, 3, "article")}
<body class="local-page child-page subject-page"><a class="skip-link" href="#main">본문 바로가기</a>{navigation("../../../", "과목별학원")}
  <main id="main">
    <section class="local-hero"><div class="wrap"><div class="crumbs"><span><a href="../../../">홈</a></span><span><a href="../../">과목별학원</a></span><span><a href="../">{esc(config['label'])}</a></span><span>{esc(title)}</span></div><div class="local-hero-card"><div class="local-hero-inner"><div><p class="eyebrow">{esc(config['eyebrow'])}</p><h1>{esc(title)}</h1><p>{esc(description)}</p><div class="hero-center-fact"><span>확인된 상담 장소</span><strong>{esc(center['organization_name'])}</strong><small>{esc(center['street_address'])} · {esc(local)} 센터 안내</small></div><div class="local-actions"><a class="btn btn-primary" href="{CONSULT_URL}" target="_blank" rel="noopener">상담 신청</a><a class="btn btn-ghost" href="tel:{PHONE}">전화 문의</a></div></div><aside class="hero-mini-panel"><span>{esc(center['region'])} · {esc(center['city'])}</span><strong>{esc(local)}</strong><span>{esc(config['label'])}<br>진단 · 계획 · 오답 재학습</span></aside></div></div></div></section>
    <section class="local-section subject-media-section"><div class="wrap local-image-pair"><img src="{esc(representative)}" alt="{esc(title)} {DOMAIN_NAME} 대표" style="display:none;"><picture class="local-responsive-picture"><source media="(max-width: 640px)" srcset="{esc(body_mobile)}"><img src="{esc(body_image)}" alt="{esc(title)} 본문 {SITE_NAME}" loading="lazy" decoding="async"></picture><figure class="location-card"><img src="{esc(center['map_image'])}" alt="{esc(title)} 지도 {SITE_NAME}" loading="lazy" decoding="async"{map_dimensions}><figcaption>{esc(center['region'])} {esc(center['city'])} {esc(local)} 상담 장소와 이동 동선을 확인할 때 참고하는 위치 안내입니다.</figcaption></figure></div></section>
    <section class="local-section"><div class="wrap geo-summary-panel"><p class="eyebrow">30초 핵심 안내</p><h2>{esc(title)} 상담에서 먼저 확인할 내용</h2><p>{esc(summary)}</p><div class="geo-fact-grid"><article class="geo-fact-card"><span>학습 범위</span><strong>{esc(' · '.join(config['subjects']))}</strong><p>현재 교재와 최근 시험 기록에서 과목별 시작점을 구분합니다.</p></article><article class="geo-fact-card"><span>수업 가능 학년</span><strong>{esc(' · '.join(grades) if grades else '상담 확인 필요')}</strong><p>자료가 없는 항목은 임의로 확정하지 않습니다.</p></article><article class="geo-fact-card"><span>상담 기준</span><strong>진단 · 실행 · 재확인</strong><p>진도보다 수업 뒤 남는 기록과 오답 재도전 과정을 확인합니다.</p></article></div></div></section>
    <section id="verified-center" class="local-section"><div class="wrap verified-center-grid"><article class="verified-center-card"><p class="eyebrow">VERIFIED CENTER DATA</p><h2>확인된 센터 정보</h2><dl class="verified-data-list">{data_rows}</dl>{f'<div class="verified-school-list">{school_html}</div>' if school_html else '<p class="verified-note">제공 자료에 학교 목록이 없어 특정 학교 진도를 임의로 단정하지 않습니다.</p>'}{tuition}<p class="verified-note">자료 기준: 센터정보 정리 자료 · 최종 검수 {TODAY}</p></article><article class="local-card subject-answer-card"><p class="eyebrow">상담 핵심 답변</p><h2>{esc(manuscript.get('answer_heading') or f'{local} 상담 판단 기준')}</h2><p>{esc(manuscript.get('answer_text') or summary)}</p><div class="pill-list">{"".join(f'<span>{esc(tag)}</span>' for tag in manuscript.get('answer_tags', []))}</div></article></div></section>
    <section class="local-section"><article class="wrap local-card subject-article"><div class="subject-article-intro">{intro}</div>{sections}</article></section>
    <section id="faq-section" class="local-section"><div class="wrap faq-local"><p class="eyebrow">FAQ</p><h2>{esc(title)} 자주 묻는 질문</h2>{faqs}</div></section>
    <section class="local-section"><div class="wrap"><article class="local-card"><p class="eyebrow">PARENT CONSULTATION SCENARIOS</p><h2>{esc(local)} 상담 상황 예시</h2><div class="review-grid">{cases}</div><p class="verified-note">※ 실제 수강 후기나 특정 성적 결과가 아니라, 상담에서 점검할 수 있는 학생 상황을 재구성한 예시입니다.</p></article></div></section>
    <section id="internal-links" class="local-section"><div class="wrap local-card"><p class="eyebrow">RELATED PAGES</p><h2>{esc(local)} 관련 학습 페이지</h2><nav class="neighbor-links" aria-label="관련 학습 페이지">{link_html}</nav></div></section>
  </main>{footer("../../../")}
</body></html>'''


def update_navigation() -> int:
    changed = 0
    for path in sorted(ROOT.rglob("index.html")):
        relative = path.relative_to(ROOT)
        depth = len(relative.parent.parts)
        home = "../" * depth if depth else "./"
        active = relative.parts[0] if depth else "홈"
        if active not in {"학습관리", "과목별학원", "전국센터", "상담문의"}:
            active = "홈"
        source = path.read_text(encoding="utf-8")
        nav_match = re.search(r'<div class="nav-links">.*?</div>', source, re.DOTALL)
        if not nav_match:
            raise ValueError(f"상단 메뉴를 찾을 수 없습니다: {path}")
        links = (
            ("홈", ""), ("학습관리", "학습관리/"), ("과목별학원", "과목별학원/"),
            ("전국센터", "전국센터/"), ("상담문의", "상담문의/"),
        )
        replacement = '<div class="nav-links">\n' + "".join(
            f'        <a{" class=\"active\" aria-current=\"page\"" if label == active else ""} href="{home + suffix}">{label}</a>\n'
            for label, suffix in links
        ) + "      </div>"
        updated = source[:nav_match.start()] + replacement + source[nav_match.end():]
        footer_match = re.search(r'<div class="footer-links">.*?</div>', updated, re.DOTALL)
        if footer_match:
            footer_links = f'<div class="footer-links"><a href="{home}학습관리/">학습관리</a><a href="{home}과목별학원/">과목별학원</a><a href="{home}전국센터/">전국센터</a><a href="tel:{PHONE}">{PHONE}</a></div>'
            updated = updated[:footer_match.start()] + footer_links + updated[footer_match.end():]
        if updated != source:
            path.write_text(updated, encoding="utf-8", newline="\n")
            changed += 1
    return changed


def update_home_discovery() -> None:
    path = ROOT / "index.html"
    source = path.read_text(encoding="utf-8")
    if 'class="home-link-card" href="과목별학원/"' not in source:
        marker = '<a class="home-link-card is-primary" href="전국센터/">'
        position = source.find(marker)
        if position >= 0:
            card = '<a class="home-link-card" href="과목별학원/"><span>SUBJECT DIRECTORY</span><strong>과목별학원 3개 분류</strong><p>영수·영어·수학 전문학원 안내를 371개 동네별로 확인합니다.</p></a>\n          '
            source = source[:position] + card + source[position:]
    path.write_text(source, encoding="utf-8", newline="\n")


def update_llms() -> None:
    path = ROOT / "llms.txt"
    source = path.read_text(encoding="utf-8")
    block = f'''\n## 과목별학원\n\n- 과목별학원: {encoded_url('과목별학원')}\n- 영수 전문학원: {encoded_url('과목별학원', '영수전문학원')}\n- 영어 전문학원: {encoded_url('과목별학원', '영어전문학원')}\n- 수학 전문학원: {encoded_url('과목별학원', '수학전문학원')}\n'''
    if "## 과목별학원" not in source:
        source = source.rstrip() + "\n" + block
    else:
        source = re.sub(r"\n## 과목별학원\n.*?(?=\n## |\Z)", "\n" + block.strip() + "\n", source, flags=re.DOTALL)
    path.write_text(source, encoding="utf-8", newline="\n")


def main() -> None:
    if set(ENGINE_CONFIGS) != set(TARGET_SLUGS):
        raise ValueError(f"콘텐츠 엔진 카테고리 누락: {set(TARGET_SLUGS) - set(ENGINE_CONFIGS)}")
    SUBJECT_ROOT.mkdir(parents=True, exist_ok=True)
    generated = 0
    for slug in TARGET_SLUGS:
        config = ENGINE_CONFIGS[slug]
        manuscripts, namespace = prepare_manuscripts(config)
        representatives = representative_mapping(slug)
        category_root = SUBJECT_ROOT / slug
        if category_root.exists():
            shutil.rmtree(category_root)
        category_root.mkdir(parents=True)
        for index, local in enumerate(ORDER):
            center = namespace["extract_center_data"](local)
            target = category_root / local
            target.mkdir(parents=True)
            target.joinpath("index.html").write_text(
                render_detail(slug, local, index, manuscripts[local], center, representatives[local]),
                encoding="utf-8", newline="\n",
            )
            generated += 1
        category_root.joinpath("index.html").write_text(render_hub(slug), encoding="utf-8", newline="\n")
        print(f"{slug}: detail=371 hub=1")
    SUBJECT_ROOT.joinpath("index.html").write_text(render_subject_root(), encoding="utf-8", newline="\n")
    update_home_discovery()
    nav_changed = update_navigation()
    update_llms()
    print(f"generated_details={generated} subject_hubs=4 navigation_pages={nav_changed}")


if __name__ == "__main__":
    main()
