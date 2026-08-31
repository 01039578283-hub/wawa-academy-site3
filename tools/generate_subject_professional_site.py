from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import random
import re
import shutil
import unicodedata
import zipfile
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

import generate_subject_professional_pages as content_engine


ROOT = Path(__file__).resolve().parents[1]
SITE_URL = "https://xn--sp5b72l1taf0p.com"
SITE_NAME = "와와학습코칭학원"
DOMAIN_NAME = "코칭학원.com"
TODAY = "2026-09-01"
SUBJECT_ROOT = ROOT / "과목별학원"
SOURCE_DIR = ROOT.parent / "참고자료" / "사용한 원고" / "코칭학원.com 추가 원고"
COMMON_DIR = ROOT.parent / "참고자료" / "공통자료"
CENTER_CSV = COMMON_DIR / "센터정보 정리.csv"
CONSULT_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdb2oE5Qk5YS0TfYDxyV1w-IOTkhkjOCmmpAKTI9FmqpVj6Yg/viewform"
PHONE = "010-3957-8283"
SMS_URL = "https://blogsms.net/01039578283"

REGION_ORDER = ["서울", "경기", "인천", "충청", "대전", "대구", "울산", "부산", "경상", "광주", "전라", "강원", "제주"]
LEGACY_SLUGS = ("영수전문학원", "영어전문학원", "수학전문학원", "전문학원")
TARGET_SLUGS = (*LEGACY_SLUGS, "초등학생학원", "중학생학원", "고등학생학원")
EXPECTED_REVIEW_COUNTS = {
    "전문학원": 1,
    "영수전문학원": 2,
    "영어전문학원": 3,
    "수학전문학원": 3,
    "초등학생학원": 1,
    "중학생학원": 1,
    "고등학생학원": 1,
}
ENGINE_CONFIGS = {
    str(config["slug"]): dict(config)
    for config in content_engine.CATEGORIES
    if str(config["slug"]) in TARGET_SLUGS
}
GENERAL_CONFIG = dict(ENGINE_CONFIGS["영수전문학원"])
GENERAL_CONFIG.update(
    {
        "slug": "전문학원",
        "label": "전문학원",
        "zip": "전문학원.zip",
        "eyebrow": "LOCAL ACADEMY LEARNING MANAGEMENT GUIDE",
        "directory": "LOCAL ACADEMY DIRECTORY",
        "card_id": "academy-management",
        "card_number": "11",
        "card_small": "ACADEMY LEARNING MANAGEMENT",
        "card_copy": "확인된 수업 가능 범위와 학생 유형, 학교 일정, 숙제·오답·질문 기록이 이어지는 관리 방식을 살펴봅니다.",
        "topics": (
            "현재 학습 상태 진단",
            "학년·학교 일정 확인",
            "숙제·오답·질문 기록",
            "주간 학습 실행",
            "상담 후 재확인 기준",
        ),
        "hero_copy": "과목 이름만 비교하지 않고 확인된 수업 가능 범위, 학생의 현재 기록, 학교 일정과 복습 실행 과정을 함께 살펴봅니다.",
        "hero_tags": (
            ("학생 유형", "학교 일정", "학습 기록"),
            ("현재 교재", "숙제 점검", "오답 재확인"),
            ("질문 기록", "주간 계획", "실행 점검"),
            ("가능 학년", "상담 기준", "다음 계획"),
        ),
        "hub_lead": "특정 과목의 심화 방식보다 학생의 현재 상태, 학년과 학교 일정, 숙제·오답·질문 기록이 수업 뒤 어떻게 이어지는지 살펴보도록 371개 동네 안내를 정리했습니다.",
    }
)
ENGINE_CONFIGS["전문학원"] = GENERAL_CONFIG

ELEMENTARY_STUDENT_CONFIG = dict(
    next(config for config in content_engine.CATEGORIES if str(config["slug"]) == "초등전문학원")
)
ELEMENTARY_STUDENT_CONFIG.update(
    {
        "slug": "초등학생학원",
        "label": "초등학생학원",
        "zip": "초등학생학원.zip",
        "eyebrow": "ELEMENTARY SCHOOL ACADEMY GUIDE",
        "directory": "ELEMENTARY SCHOOL ACADEMY DIRECTORY",
        "card_id": "elementary-school-academy",
        "card_number": "17",
        "card_small": "ELEMENTARY SCHOOL ACADEMY",
        "representative_seed": "coaching-elementary-school-academy-v1",
        "card_copy": "초등 영어 읽기·어휘와 수학 개념·연산을 현재 교재, 과제 습관, 설명 과정과 짧은 복습 기록으로 살펴봅니다.",
        "related_pages": (
            ("영수전문학원", "영수 전문학원"),
            ("영어전문학원", "영어 전문학원"),
            ("수학전문학원", "수학 전문학원"),
            ("전문학원", "전문학원"),
        ),
        "base_page": ("영수전문학원", "영수 전문학원"),
        "hero_copy": "최근 초등 영어·수학 교재와 과제 기록을 바탕으로 읽기·어휘, 개념·연산, 질문 습관과 짧은 복습 순서를 점검합니다.",
        "hub_lead": "초등학생의 영어·수학을 문제 수나 선행 진도로만 비교하지 않고 읽기·어휘, 개념·연산, 과제 습관과 짧은 복습의 연결 과정을 살펴보도록 371개 동네 안내를 정리했습니다.",
    }
)
ENGINE_CONFIGS["초등학생학원"] = ELEMENTARY_STUDENT_CONFIG

MIDDLE_STUDENT_CONFIG = dict(
    next(config for config in content_engine.CATEGORIES if str(config["slug"]) == "중등전문학원")
)
MIDDLE_STUDENT_CONFIG.update(
    {
        "slug": "중학생학원",
        "label": "중학생학원",
        "zip": "중학생학원.zip",
        "eyebrow": "MIDDLE SCHOOL ACADEMY GUIDE",
        "directory": "MIDDLE SCHOOL ACADEMY DIRECTORY",
        "card_id": "middle-school-academy",
        "card_number": "16",
        "card_small": "MIDDLE SCHOOL ACADEMY",
        "representative_seed": "coaching-middle-school-academy-v1",
        "card_copy": "중등 영어·수학의 학교 진도와 지필·수행평가 준비, 과제 실행과 오답 복습 기준을 함께 살펴봅니다.",
        "related_pages": (
            ("영수전문학원", "영수 전문학원"),
            ("영어전문학원", "영어 전문학원"),
            ("수학전문학원", "수학 전문학원"),
            ("전문학원", "전문학원"),
        ),
        "base_page": ("영수전문학원", "영수 전문학원"),
        "hero_copy": "최근 중등 영어·수학 학습 자료를 바탕으로 학교 진도, 지필·수행평가 준비, 과제 실행과 오답 복습 순서를 점검합니다.",
        "hub_lead": "중학생의 영어·수학을 단순 선행 진도로 비교하지 않고 학교 진도, 지필·수행평가 준비, 과제 실행과 오답 복습의 연결 과정을 살펴보도록 371개 동네 안내를 정리했습니다.",
    }
)
ENGINE_CONFIGS["중학생학원"] = MIDDLE_STUDENT_CONFIG

HIGH_STUDENT_CONFIG = dict(
    next(config for config in content_engine.CATEGORIES if str(config["slug"]) == "고등전문학원")
)
HIGH_STUDENT_CONFIG.update(
    {
        "slug": "고등학생학원",
        "label": "고등학생학원",
        "zip": "고등학생학원.zip",
        "eyebrow": "HIGH SCHOOL ACADEMY GUIDE",
        "directory": "HIGH SCHOOL ACADEMY DIRECTORY",
        "card_id": "high-school-academy",
        "card_number": "15",
        "card_small": "HIGH SCHOOL ACADEMY",
        "representative_seed": "coaching-high-school-academy-v1",
        "card_copy": "고등 영어·수학의 학교 시험 범위와 모의고사, 과목별 시간 배분과 오답 재확인 기준을 함께 살펴봅니다.",
        "related_pages": (
            ("영수전문학원", "영수 전문학원"),
            ("영어전문학원", "영어 전문학원"),
            ("수학전문학원", "수학 전문학원"),
            ("전문학원", "전문학원"),
        ),
        "base_page": ("영수전문학원", "영수 전문학원"),
        "hero_copy": "최근 고등 영어·수학 시험지와 교재를 바탕으로 학교 시험 범위, 모의고사 학습, 과목별 시간 배분과 오답 재확인 순서를 점검합니다.",
        "hub_lead": "고등학생의 영어·수학을 같은 진도표로 묶지 않고 학교 시험 범위, 모의고사 학습, 과목별 시간 배분과 오답 재확인 기준을 나누어 보도록 371개 동네 안내를 정리했습니다.",
    }
)
ENGINE_CONFIGS["고등학생학원"] = HIGH_STUDENT_CONFIG

CATEGORY_COPY = {
    "전문학원": {
        "label": "전문학원",
        "eyebrow": "ACADEMY LEARNING MANAGEMENT DIRECTORY",
        "lead": "특정 과목의 진도보다 확인된 수업 가능 범위, 학생 유형, 학교 일정과 숙제·오답·질문 기록이 어떻게 이어지는지 살펴보도록 371개 동네 안내를 정리했습니다.",
        "summary": "센터 자료에서 확인된 수업 가능 과목과 학년을 먼저 보고, 현재 교재·시험 기록·주간 일정·복습 실행 과정을 상담 기준으로 나눕니다.",
        "tags": ("학생 유형", "주간 일정", "학습 기록"),
    },
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
    "초등학생학원": {
        "label": "초등학생학원",
        "eyebrow": "ELEMENTARY SCHOOL ACADEMY DIRECTORY",
        "lead": "초등학생의 영어·수학을 문제 수나 선행 진도로만 비교하지 않고 읽기·어휘, 개념·연산, 과제 습관과 짧은 복습의 연결 과정을 살펴보도록 371개 동네 안내를 정리했습니다.",
        "summary": "최근 초등 영어·수학 교재와 과제 기록에서 읽기·어휘, 개념·연산, 질문 습관과 짧은 복습 순서를 구분합니다.",
        "tags": ("읽기·어휘", "개념·연산", "과제·짧은 복습"),
    },
    "중학생학원": {
        "label": "중학생학원",
        "eyebrow": "MIDDLE SCHOOL ACADEMY DIRECTORY",
        "lead": "중학생의 영어·수학을 단순 선행 진도로 비교하지 않고 학교 진도, 지필·수행평가 준비, 과제 실행과 오답 복습의 연결 과정을 살펴보도록 371개 동네 안내를 정리했습니다.",
        "summary": "최근 중등 영어·수학 학습 자료에서 학교 진도, 지필·수행평가 준비, 과제 실행과 오답 복습 순서를 구분합니다.",
        "tags": ("중등 내신", "지필·수행평가", "과제·오답 복습"),
    },
    "고등학생학원": {
        "label": "고등학생학원",
        "eyebrow": "HIGH SCHOOL ACADEMY DIRECTORY",
        "lead": "고등학생의 영어·수학을 같은 진도표로 묶지 않고 학교별 시험 범위, 모의고사 학습, 과목별 시간 배분과 오답 재확인 기준을 나누어 보도록 371개 동네 안내를 정리했습니다.",
        "summary": "최근 고등 영어·수학 시험지와 교재에서 학교 시험 범위, 모의고사 학습, 과목별 시간 배분과 오답 재확인 순서를 구분합니다.",
        "tags": ("고등 내신", "모의고사", "과목별 시간 배분"),
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


def public_school_names(values: list[str]) -> list[str]:
    """Expand only unambiguous source separators for reader-facing copy.

    The verified centre card and organization facts continue to use the CSV
    strings verbatim.  Public prose may split dot- or space-delimited school
    lists, but it must never infer a boundary inside an ordinary school name
    such as ``성남중앙초``.
    """
    result: list[str] = []
    school = r"[가-힣A-Za-z0-9]+?(?:초등학교|중학교|고등학교|초|중|고)"
    for raw in values:
        dot_parts = [part.strip() for part in re.split(r"[.,;；/|·]+", raw) if part.strip()]
        for part in dot_parts:
            spaced = [item for item in re.split(r"\s+", part) if item]
            if len(spaced) > 1 and all(re.fullmatch(school, item) for item in spaced):
                result.extend(spaced)
            else:
                result.append(part)
    return unique(result)


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
    public_region = row.get("지역", "")
    public_city = row.get("시or구", "")
    # The source rows for 다정동/새롬동 store a road name in the city field.
    # Keep the verified street address untouched, but use the actual public
    # administrative locality for areaServed, captions and reader copy.
    if official_region(address, public_region) == "세종특별자치시":
        public_region = "세종"
        if public_city.endswith(("로", "길")):
            public_city = "세종시"

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
        "region": public_region,
        "city": public_city,
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
        "body_size": image_size(ROOT / "assets" / "centers" / "common" / body_name),
        "map_image": map_source,
        "map_size": image_size(map_path),
        "source_mentions": [],
    }


def category_center_data(local: str, config: dict[str, object]) -> dict[str, object]:
    """Project verified centre facts to the requested category scope.

    Grade-specific collections must not expose another school level merely
    because the values share the same centre row.
    """
    center = dict(base_center_data(local))
    prefix = str(config.get("grade_prefix", ""))
    grade_ranges = {"초": "1-6", "중": "1-3", "고": "1-3"}
    school_suffixes = {
        "초": r"(?:초등학교|초)$",
        "중": r"(?:중학교|중)$",
        "고": r"(?:고등학교|고)$",
    }
    if prefix not in grade_ranges:
        return center

    row = row_for(local)
    focus = str(config.get("focus", "combined"))
    center["grades"] = [
        grade for grade in grades_for(row, focus)
        if re.fullmatch(rf"{re.escape(prefix)}[{grade_ranges[prefix]}]", str(grade))
    ]
    school_suffix = school_suffixes[prefix]
    center["schools"] = [
        school for school in public_school_names([str(value) for value in center.get("schools", [])])
        if re.search(school_suffix, school) and school != "오현초호매실중"
    ]
    return center


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
        if line.startswith("※"):
            continue
        if re.search(r"실제\s*수강생의?\s*후기|실제\s*(?:수강\s*)?후기가\s*아니", line):
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
        ("지역내 모든 고등학교 가능", "학교별 적용 여부는 상담에서 확인해야 합니다"),
        ("지역 내 모든 고등학교 가능", "학교별 적용 여부는 상담에서 확인해야 합니다"),
        ("학부모에게는 학원 선택 전에는", "학부모가 학원을 선택하기 전에는"),
        ("확인 센터 안내 기준으로", "확인된 센터 자료 기준으로"),
        ("확인된 센터 자료 기준으로", "확인된 정보상"),
        ("센터 자료에 나온 학교는", "확인된 학교 정보에는"),
        ("특정 학교명을 임의로 만들지 않습니다", "자녀 학교의 최신 자료로 수업 범위를 확인해야 합니다"),
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
        ("수업 설계은", "수업 설계는"),
        ("피드백 구조은", "피드백 구조는"),
        ("선택 전 확인할 확인 항목", "선택 전 점검할 항목"),
        ("선택 전 확인할 선택 기준", "선택 전 확인할 기준"),
        ("자료에 적힌", "확인된"),
        ("자료에 제시된", "확인된"),
        ("제공된 주소 정보", "확인된 센터 주소"),
        ("학습 운영 기준 같은 운영 정보는", "학습 운영 기준은"),
        ("학습 운영 기준 같은 환경 정보와", "학습 운영 기준과"),
        ("학습 운영 기준 관련 학습 환경 확인", "학습 운영 기준 확인"),
        ("학습 운영 기준까지 함께 살펴보는 학습 환경", "학습 운영 기준과 가정 복습 흐름"),
        (
            "자료에 함께 제시된 추가 확인 항목은 학습 운영 기준입니다",
            "학습 운영 기준은 상담에서 실제 적용 방식을 확인해야 합니다",
        ),
        ("이 항목을 단순 시설명으로만 보지 말고", "이 기준을 이름만 보고 판단하지 말고"),
        ("수학 풀이이", "수학 풀이가"),
        ("영어 답안과 수학 풀이와", "영어 답안·수학 풀이와"),
        ("학생이 받은 학교에서 받은 자료", "학교에서 받은 자료"),
        ("학생이 가져온 제공된 학교 자료", "학생이 가져온 학교 자료"),
        ("과정이 필요한 과정입니다", "과정이 필요합니다"),
        ("보는 지도가 확인할 필요가 있습니다", "보는 지도가 필요합니다"),
        ("최근 교재 활용과 교재", "최근 교재와 학습 기록"),
        ("학습학습", "학습"),
        ("시험학습 성과", "시험 대비 과정"),
        (
            "학생이 설명한 두 과목 내용을 학생의 설명과 나란히 놓으면",
            "학생이 설명한 두 과목 내용을 실제 답안과 나란히 놓으면",
        ),
        ("제공 자료에서는", "확인된 자료에는"),
        ("제공된 센터 자료", "확인된 센터 정보"),
        ("학습 운영 기준 관련 안내를 확인할 때", "학습 운영 기준을 확인할 때"),
        ("학습 운영 기준 같은 항목을 체크리스트로", "학습 운영 기준을 체크리스트로"),
        ("학습 운영 기준 관련 내용", "학습 운영 기준"),
        ("학습 운영 기준 항목은", "학습 운영 기준은"),
        ("상담 첫 상담", "첫 상담"),
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
    text = text.replace("중등학교", "중학교")
    text = re.sub(
        r"((?:(?:초등|중등|중|고등)(?:학교)?\s*[1-6]\s*학년)|해당\s*학년)\s+중\s+"
        r"(?=[^,.]{2,120}?학생)",
        r"\1이면서 ",
        text,
    )
    text = re.sub(
        r"주소\s*정보는\s*(.{5,180}?)\s*기준으로\s*제공되어\s*있습니다",
        r"확인된 센터 주소는 \1입니다",
        text,
    )
    text = re.sub(
        r"([초중고][1-6](?:·[초중고][1-6])+?)이\s+확인된\s+수업\s+가능\s+학년입니다",
        r"확인된 수업 가능 학년은 \1입니다",
        text,
    )
    text = re.sub(
        r"확인된\s+센터\s+정보에는\s+([초중고][1-6](?:·[초중고][1-6])+?)이\s+"
        r"전문학원\s+상담\s+가능\s+학년으로\s+확인됩니다",
        r"확인된 센터 정보에서 전문학원 상담 가능 학년은 \1입니다",
        text,
    )
    text = re.sub(
        rf"같은\s+([^,.]{{0,50}}{re.escape(local)})\s+학생이라도",
        r"\1 학생이라도",
        text,
    )
    object_particles = {
        "루틴": "루틴을",
        "장치": "장치를",
        "구조": "구조를",
        "절차": "절차를",
        "관리": "관리를",
    }
    text = re.sub(
        r"(루틴|장치|구조|절차|관리)(?:가|이)\s+확인할\s+필요가\s+있습니다",
        lambda match: f"{object_particles[match.group(1)]} 확인할 필요가 있습니다",
        text,
    )
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
    # This wrapper performs several context substitutions after the shared
    # engine's grammar pass.  Run the deterministic language guard once more
    # so a replacement prefix cannot leave a doubled particle (for example
    # ``해당 ... 방식에서는`` becoming ``수업에서는는``).
    text = content_engine.polish_known_language_defects(text)
    text = re.sub(
        r"(?:영어·수학\s+학습\s+과정|해당\s+영수\s+관리\s+방식|지역별\s+영수\s+학습\s+기준)"
        r"\s+(상담|수업)",
        r"영수 \1",
        text,
    )
    text = text.replace(";", ".")
    text = re.sub(r"\s+([,.!?])", r"\1", text)
    text = re.sub(r"([.!?]){2,}", r"\1", text)
    text = text.replace("으입니다", "입니다")
    text = re.sub(r"\s+", " ", text).strip()
    return text


MALFORMED_LANGUAGE_RE = re.compile(
    r"집에서도\s+무엇을\s+봐야\s+하는지\s+집에서도|"
    r"(?:에서는는|에게는는|으로으로|에서에서|에는에는)|"
    r"영수\s+전문학원\s+일반적인\s+안내처럼|"
    r"(?<![가-힣])원고라(?=\s|[,.!?]|$)|"
    r"학생이\s+받은\s+제공된|자녀\s+제공된|"
    r"가장\s+가장|기준\s+기준|수학\s+풀이으로|"
    r"다음\s+첫\s+상담|이\s+영수\s+학습\s+과정|"
    r"(?<![가-힣])(?P<repeat>학생|학부모|상담|관리|확인|자료|학습|수업|학교|"
    r"기준|과정|결과|계획|기록|답안|풀이|교재|영역|오답|복습|진단|설명|단원|학년)"
    r"\s+(?P=repeat)(?=(?:에서|으로|은|는|이|가|을|를|과|와|의|에|도|만|부터|까지)?(?:\s|[,.!?]|$))|"
    r"기준는|기준를|기준와|기록라는|학습관리은|예비고이|점검와|결과과|날짜과|과정를|기록를|피드백와|분위기을|"
    r"일정와|기록와|과정는|학습량와|계획와|재확인가|배분와|적용와|구조을|설계을|"
    r"교정와|해석와|대비이|과정와|준비이|누적와|정리이|분류이|복습와|연계이|테스트이|"
    r"피드백는|공유이|활용를|점검는|기록가|기록는|학습를|구성를|자기주도반를|점검가|"
    r"동선를|계획는|시간를|환경를|누적가|단기집중반를|(?:신창지구|첨단지구|청라)과|"
    r"예비해당\s*학년|나누는지부터\s+나누어\s+보면|설명하는\s+데\s+실제\s+계획을\s+세우는\s+데|"
    r"을\s+함께\s+서술형\s+풀이|학교\s+학생에게|오답노트를\s+학생에게|"
    r"영어\s+답안과\s+수학\s+풀이를\s+과목별\s+오답과\s+복습\s+일정을\s+나누면|"
    r"필요한\s+학생에게\s+필요한|확인\s+내용을\s+확인|학생\s+설명과\s+풀이\s+흔적과|교재\s+진도와\s+이해도와"
    r"|[가-힣]+(?:는지|인지)부터\s+나누어\s+보면|서술형\s+답안의\s+식과\s+설명과\s+서술형\s+풀이의\s+근거를|"
    r"문제집\s+학생에게|시험분석|이\s+행의|학교\s+칸|해당\s+학년\s+(?:이|에게)(?=\s)|"
    r"(?<![가-힣])페이지(?:이지만|는|를|가|에서)?(?![가-힣])"
    r"|이\s+문장은|이\s+목록|목록\s+안에서만\s+언급|[,，]상담에서"
    r"|센터\s+등록\s+자료에서|학교\s+참고\s+범위로|자료에\s+없는\s+학교명|제공된\s+학교\s+범위|"
    r"주소가\s+.{1,250}?으로\s+제공된\s+.{1,80}?학습\s+과정을\s+방문한다면"
    r"|(?:학교\s+)?항목에\s+기재된"
    r"|학생처럼\s+약점이\s+뚜렷한\s+학생|상담을\s+상담할\s+때|"
    r"(?:이\s+과정에서|상담\s+과정에서는)\s+영어\s+학습\s+과정에서|"
    r"확인(?:이|하는지가)\s+핵심\s+확인사항|확인하는\s+방식이\s+확인할\s+필요가\s+있습니다|"
    r"학습량\s+조정(?:은\s+학습량\s+조정에|을\s+학습량\s+조정과|과\s+학습량\s+조정을)|"
    r"학생에게는\s+학생별\s+계획은|학습\s+과정을\s+(?:알아보는|찾는)\s+과정(?:에서는|에서)|"
    r"수업을\s+시작하기\s+전에는\s+수업\s+위치는|"
    r"현재\s+학년에게|등록\s+자료에|특정\s+학교명을\s+임의로|"
    r"센터\s+자료(?:\s+기준|에\s+나온)|"
    r"(?:(?:영어|수학)\s+학습\s+과정|해당\s+(?:영어|수학)\s+관리\s+방식|"
    r"지역별\s+(?:영어|수학)\s+학습\s+기준|영어·수학\s+학습\s+과정|"
    r"해당\s+영수\s+관리\s+방식|지역별\s+영수\s+학습\s+기준)"
    r"\s+(?:상담|수업|선택|기준)|"
    r"살펴보기을|점검을\s+점검|등록\s+전\s+확인하면|"
    r"것이\s+확인할\s+필요가\s+있습니다|,(?=확인된)|"
    r"학습\s+계획을\s+세울\s+때는\s+확인된\s+수업\s+위치는|"
    r"까지\s+무엇을\s+남길지까지|예비현재\s+학년|현재\s+학년(?:맞춤|과정)|"
    r"현재\s+학년의\s+학생의|(?:이)?라는\s+표현은|’\s+표현은\s+결과를\s+약속|"
    r"상담\s+때[^.!?]{0,100}?상담에서|"
    r"학습\s+운영\s+기준\s+이\s+기준|"
    r"(?:하면|보면|살펴보면|맞춰\s+보면|대조하면|정리하면|나란히\s+놓으면|넣으면|"
    r"바꾸면|이어\s+보면|구체화하면|연결하면|배열하면|바뀌면|찾으면|나누면),\s*"
    r"[^,.!?]{5,110}?(?:하면|보면|살펴보면|맞춰\s+보면|대조하면|정리하면|"
    r"나란히\s+놓으면|넣으면|바꾸면|이어\s+보면|구체화하면|연결하면|배열하면|"
    r"바뀌면|찾으면|나누면),"
)

PUBLIC_COPY_RESIDUE_RE = re.compile(
    r"‘[^’]{1,45}’\s*(?:학습\s*)?항목|"
    r"[가-힣·0-9]+\s+단계의\s+[^,.!?]{1,50}생활권의|"
    r"\b(?:서울|부산|대구|인천|광주|대전|울산|세종)\s+[가-힣]+(?:시|군|구)\s+"
    r"(?:서울|부산|대구|인천|광주|대전|울산|세종)\s+|"
    r"\b(?:경기|강원|충청|전라|경상|제주)\s+(?P<city>[가-힣]+)시\s+(?P=city)\s+|"
    r"제공된\s+학교\s+범위|이\s+행의|학교\s+칸|해당\s+학년|현재\s+학년\s+진단|"
    r"학생에게는[^,.!?]{0,70}학생(?:에게는|이라면|은|이)|"
    r"예비고가라도|[가-힣A-Za-z0-9·]+가라는|"
    r"학원을\s+고르는\s+과정은[^.!?]{0,100}학습\s+흐름을\s+찾는\s+과정|"
    r"가정에서\s+가장\s+먼저\s+묻는\s+질문은\s+'여기\s+다니면\s+성적이\s+오르나요'이지만|"
    r"(?:해당\s+영수\s+관리\s+방식|영어·수학\s+학습\s+과정|지역별\s+영수\s+학습\s+기준)\s+수업\s+전후로|"
    r"문장\s+구조를\s+읽는\s+힘과\s+시험\s+조건을\s+해석하는\s+힘이\s+같이|"
    r"학부모에게는[^.!?]{0,100}목표는|"
    r"(?:영어\s+학습\s+과정|해당\s+영어\s+관리\s+방식|영어\s+전문\s+수업|"
    r"지역별\s+영어\s+학습\s+기준|지역\s+영어\s+상담·수업)\s+(?:초등|중등|고등)\s+과정은|"
    r"생활권의\s+(?:(?:초등|중등|고등)(?:학교)?\s*[1-6]학년|예비(?:중|고)1?|"
    r"초[1-6]|중[1-3]|고[1-3])[^,.!?]{5,100}?학생에게는|"
    r"진단\s+내용을\s+다시\s+묻는\s+것이\s+(?:확인할\s+필요|먼저\s+마련)|"
    r"시험\s+전후의\s+변화를\s+시험\s+전후로|"
    r"확인(?:하는\s+시간|되는\s+루틴|하는\s+절차)을?\s+확인할\s+필요|"
    r"제공되지\s+않은\s+학교명을\s+만들지\s+않는\s+것이|"
    r"학부모에게\s+비교\s+기준|학부모\s+관점에서는\s+가정에서|"
    r"확인된\s+자료에는[^.!?]{1,180}?등을\s+확인할\s+수\s+있습니다|"
    r"지역별\s+영수\s+학습\s+기준\s+상담\s+기준에서는|"
    r"(?:영어\s+학습\s+과정|해당\s+영어\s+관리\s+방식)\s+수업에서는|"
    r"영어\s+상담\s+수업에서는|"
    r"이\s+행에는\s+수업\s+가능\s+학교명|제공\s+자료에\s+학교명이|등록\s+자료\s+기준|"
    r"주소\s+항목에는[^.!?]{0,180}?정보가\s+제공|수업\s+위치는\s+자료에\s+기재된|"
    r"학생에게는\s+내신\s+대비는|상담\s+과정에서\s+상담에서|"
    r"(?:수학\s+학습\s+과정|해당\s+수학\s+관리\s+방식|[가-힣 ]+\s+수학\s+상담)\s+수업을\s+검토할\s+때|"
    r"정확히\s+다루는\s+순서로\s+상담\s+질문으로|"
    r"(?:상담\s+과정에서는|이\s+과정에서|학습\s+계획을\s+세울\s+때는|수업을\s+시작하기\s+전에는)"
    r"[^.!?]{0,100}?영어\s+수업에서는|확인하는\s+시간이\s+필요한\s+과정입니다|"
    r"현재\s+학년에게|등록\s+자료에|특정\s+학교명을\s+임의로|"
    r"센터\s+자료(?:\s+기준|에\s+나온)|"
    r"(?:(?:영어|수학)\s+학습\s+과정|해당\s+(?:영어|수학)\s+관리\s+방식|"
    r"지역별\s+(?:영어|수학)\s+학습\s+기준|영어·수학\s+학습\s+과정|"
    r"해당\s+영수\s+관리\s+방식|지역별\s+영수\s+학습\s+기준)"
    r"\s+(?:상담|수업|선택|기준)|"
    r"[가-힣 ]+\s+영어\s+(?:상담|수업)\s+(?:초등|중등|고등)\s+과정은|"
    r"(?:이)?라는\s+표현은|’\s+표현은\s+결과를\s+약속|"
    r"추가\s+확인\s+항목|두\s+과목의\s+주간\s+계획을\s+주간\s+계획과|"
    r"어휘·문법·독해의\s+차이를\s+어휘·문법·독해로|"
    r"학생이\s+(?:문장을|말로)\s+설명한\s+내용을\s+학생의\s+설명과|"
    r"나눠\s+보는\s+것이\s+(?:필요한\s+과정|먼저\s+마련)|"
    r"현재\s+단원과\s+누적\s+빈틈과|확인\s+가능한지|"
    r"과목별\s+오답과\s+복습\s+일정이\s+수업\s+후\s+일정으로|확인된\s+자료에는|"
    r"진단\s+내용을\s+다시\s+묻는\s+것이\s+필요한\s+과정입니다|"
    r"(?:시험\s+범위와\s+남은\s+기간|숙제\s+수행과\s+오답)과|내신진도|"
    r"주소가\s+.{3,220}?로\s+제공되어\s+있으니|주소는\s+.{3,220}?로\s+제공되어\s+있습니다|"
    r"주소가\s+.{3,220}?로\s+제공된\s+.{1,80}?을\s+방문한다면|"
    r"수업\s+시작\s+전에는\s+위치를\s+자료에\s+기재된|제공된\s+학교\s+자료가\s+있다면|"
    r"주간\s+계획을\s+계획에\s+반영하는\s+순서|(?:영어\s+답안과\s+독해\s+근거|수학\s+답안과\s+풀이\s+과정)과|"
    r",\s+또한\s+|"
    r"(?:수업을\s+시작하기\s+전에는|학습\s+계획을\s+세울\s+때는)"
    r"[^.!?]{1,160}?영어[^.!?]{0,80}?찾는\s+가정은|"
    r"현재\s+학년(?!\s+확인이\s+필요한\s+자녀)|필요한\s+과정입니다|"
    r"(?:해당\s+(?:영수|영어|수학)\s+관리\s+방식|지역별\s+(?:영수|영어|수학)\s+학습\s+기준)|"
    r"상담에서\s+살펴본\s+내용입니다|내용을\s+확인할\s+수\s+있습니다|흐름이\s+자연스럽습니다|"
    r"관련\s+안내를\s+학습\s+관리\s+질문|"
    r"확인된\s+학교\s+정보에는[^.!?]{1,180}?등을\s+확인할\s+수\s+있습니다|"
    r"이\s+보완\s+과정은\s+학원과\s+가정이|"
    r"설명받는지가\s+놓치지\s+말아야\s+할\s+대목|"
    r"문법\s+문제를\s+감으로\s+찍는\s+횟수가\s+많은\s+부분이\s+보여|"
    r"학생이\s+혼자\s+다시\s+해낸\s+기록도\s+비교\s+기준입니다\.\s+"
    r"학생이\s+혼자\s+다시\s+해낸\s+기록도\s+함께\s+남겨\s+두세요|"
    r"학부모\s+관점에서는\s+(?:질문|수업\s+운영\s+기준|광고)(?:은|는|이|가|에는)|"
    r"비교\s+기준\s+비교|가정\s+점검\s+내용을\s+점검|"
    r"학생\s+중\s+(?:수학|영어|초등|고등학교|개념|집에서는|성실하지만)\s+학생을\s+위한\s+접근|"
    r"(?:수학|영어|초등|고등학교|개념|집에서는|성실하지만)\s+학생을\s+위한\s+접근|"
    r"(?:오답을|학년이|방학에는|기초가|영어)\s+학생의\s+주간\s+계획\s+예시|"
    r"과정이\s+우선\s+살펴볼\s+기준|합니다입니다|다음\s+수업에서\s+상담에서|"
    r"(?:학습설계|학습노트|입시준비|시험성적|학습목표설정|학습프로그램|학습반복|"
    r"학습자율성|학습\s+성과\s+점검반|학습오답\s+관리|밀착학습관리|학습문제관리|내신과제관리)|"
    r"(?:집중|자기주도|학습|입시|방학)\s*캠프|내신\s+과제\s+점검가|"
    r"학년\s+확인이\s+필요한\s+학생|예비학년|학생학생|"
    r"학생(?:학습|시험|학교|집|쉬운|수학|문제|풀이|상황|맞춤|과정)|"
    r"(?:있는|분명한|이어지는|보는|작동하는)(?:가|이)입니다|으입니다|"
    r"수업의\s+수업\s+내용을|(?:학습암기|학습심화|학습몰입도|학습부진|오답\s+반복)을?\s+잘\s+활용하려면|"
    r"고등학교\s+1학년\s+학생에게\s+학습\s+성적이\s+필요하다면|"
    r"(?:학습예습|학습실전|학습성장력|학습응용|학습암기|학습연습|학습복습|시험오답|학습정리|학습향상|학습이해|학습부진|학습심화|학습자립도|학습달성률|학습약점|학습요약|학습완성도|학습자극|학습보완)|"
    r"영어\s+답안과\s+수학\s+풀이를\s+과목별\s+오답과\s+복습\s+일정을|"
    r"서술형\s+교정과\s+가정\s+복습을\s+가정\s+복습과|"
    r"영어\s+(?:수업|상담|학습\s+기준|학습\s+과정)\s+행에는\s+학교명이|"
    r"학교명이\s+별도로\s+제공되지\s+않은|꾸며\s+쓰는\s+것이\s+아니라|"
    r"차이를\s+구체적으로\s+설명하는\s+데\s+비교\s+기준을\s+세우기\s+수월합니다|"
    r"(?:자녀|학생)의\s+두\s+과목의\s+최근\s+시험지|"
    r"먼저\s+[^.!?]{1,90}?\s+먼저\s+정리하고|주소\s+항목에는|"
    r"같은\s+운영\s+요소가\s+학습\s+지속성에\s+어떤\s+도움을|"
    r"작은\s+항목처럼\s+보여도[^.!?]{0,120}?꾸준히\s+다닐\s+수\s+있는지|"
    r"잘\s+활용하려면\s+강의\s+내용,\s*과제,\s*재확인\s+문제가|"
    r"학생에게\s+[^.!?]{1,55}?(?:이|가)\s+필요하다면\s+먼저\s+최근\s+시험지"
    r"|영어\s+학습\s+기준\s+(?:초등|중등|고등)\s+과정|영어\s+학습\s+기준\s+행|"
    r"(?:영어|수학)\s+학습\s+기준\s+커리큘럼|수학\s+학습\s+기준\s+등록\s+전(?:에는)?|"
    r"생활권의\s+(?:초등학교\s*[1-6]학년|중학교\s*[1-3]학년|고등학교\s*[1-3]학년|"
    r"초[1-6]|중[1-3]|고[1-3]|예비[초중고])[^.!?]{3,150}?학생|"
    r"기준으로\s+상담\s+질문으로|오답을\s+맞힌\s+문제처럼|문제집\s+안내\s+수|"
    r"함께\s+살펴보는[^.!?]{0,100}?(?:한\s+번에|연결하는\s+방식)|"
    r"별도\s+수업\s+가능\s+학교\s+정보가\s+제공되지\s+않았으므로|"
    r"영어\s+(?:전문학원|전문\s+수업)\s+행에는\s+학교명이|"
    r"[^.!?]{2,70}?(?:을|를)\s+먼저\s+안정시키는\s+접근|"
    r"[^.!?]{2,75}?(?:을|를)\s+현재\s+수준을\s+판단하는\s+기준으로\s+삼으면|"
    r"영어와\s+수학의\s+차이를\s+영어·수학으로\s+구분하면|"
    r"어휘·문법·독해와\s+답의\s+근거와\s+서술형\s+교정|"
    r"답의\s+근거를\s+설명하지\s+못하는\s+지점을\s+설명하고|"
    r"학부모\s+관점에서\s+보면|학생에게는\s+[^,.!?]{0,80}?(?:질문은|영어·수학은|"
    r"광고에는|등록\s+전에는|학습\s+공간은|이\s+보완은|상담\s+때는|상담\s+후에는|평일에는)"
    r"|[^.!?]{1,100}?(?:이|가)\s+제공되는지보다\s+중요한\s+점은|"
    r"학생이라는\s+가설을\s+세우고|목표는\s+작은\s+기록이\s+쌓일\s+때|"
    r"(?:영어|수학)\s+학습\s+(?:과정|기준)을\s+찾는|학생의\s+시험을\s+준비할\s+때|"
    r"학습\s+변화\s+확인을\s+보장한다는\s+표현|수학\s+(?:수업|상담|전문학원)의\s+확인된\s+주소|"
    r"수학\s+학습\s+(?:과정|기준)\s+커리큘럼|커리큘럼은\s+빠른\s+선행표보다|"
    r"먼저\s+[^.!?]{1,90}?\s+먼저\s+정리|다음\s+(?:영어|수학)\s+수업\s+전\s+실행\s+계획을\s+다음\s+점검|"
    r"다음\s+계획을\s+다음\s+(?:학습|점검)|풀이\s+과정을\s+설명하게\s+해\s+보는\s+과정|"
    r"영어\s+학생에게\s+맞는|영어\s+학습\s+(?:과정|기준)\s+안내에서|"
    r"필요한\s+부분부터\s+살펴볼\s+부분은|최근\s+학교\s+교재\s+활용과\s+교재를|"
    r"관리까지\s+확인하는\s+관리\s+포인트|수업의\s+수업\s+가능|수업에서\s+수업\s+가능한|"
    r"서술형\s+답안의\s+식과\s+설명을\s+함께[^.!?]{2,100}?하는지를\s+점검|"
    r"살펴볼\s+학생은|(?:에서는|으로는)\s+이\s+보완은|훈련이\s+비교\s+기준을\s+세우기|"
    r"부분(?:이\s+생기는|에서\s+막히는)\s+부분은|영수\s+상담의\s+상담\s+기준|"
    r"차이를\s+구체적으로\s+설명하는\s+데\s+비교\s+기준을\s+세우기\s+수월합니다|"
    r"상담\s+자리에서\s+먼저\s+상담에서|"
    r"문제\s+조건을\s+표시한\s+흔적에서\s+문제\s+조건을|"
    r"(?:과목별|영어|수학)\s+현재\s+차이를\s+바탕으로\s+현재\s+수준|"
    r"학교\s+일정과\s+함께\s+살펴보면,\s*학교\s+일정과|"
    r"상담\s+과정에서는[^.!?]{1,160}?(?:확인된\s+수업\s+위치는|"
    r"확인된\s+수업\s+가능\s+학교\s+정보에는|영어\s+전문\s+수업의\s+기본은)|"
    r"학생에게는[^.!?]{0,110}?(?:시험\s+기간\s+수업은|영어·수학\s+학습은|"
    r"문제집(?:\s+선택)?은|학생일수록)|"
    r"함께\s+챙겨야\s+하는\s+준비\s+과정을\s+함께\s+겪는|"
    r"함께\s+계산해야\s+하는\s+상황도\s+함께\s+고려|"
    r"충청\s+새롬중앙로\s+(?:다정동|새롬동)|"
    r"등록된\s+학교\s+정보가\s+없는\s+경우에는\s+최근\s+학교|"
    r"어휘\s+누적\s+기록과\s+단어\s+시험을\s+시험\s+전후\s+기록으로|"
    r"상담\s+과정에서는[^.!?]{1,160}?학생은|"
    r"(?<![가-힣A-Za-z0-9])·능실중"
)


def polish_manuscript(
    manuscript: dict[str, object],
    local: str,
    config: dict[str, object],
    center: dict[str, object],
) -> dict[str, object]:
    verified_grades = [str(item) for item in center.get("verified_grades", [])]
    schools = public_school_names([str(item) for item in center.get("schools", [])])

    source_reference = ""
    if str(config["slug"]) == "전문학원":
        candidates = (
            [str(item) for item in manuscript.get("intro", [])]
            + [str(value) for pair in manuscript.get("sections", []) for value in (pair[0], *pair[1])]
            + [str(value) for item in manuscript.get("faqs", []) for value in (item["question"], item["answer"])]
            + [str(value) for item in manuscript.get("reviews", []) for value in (item.get("label", ""), item["content"])]
            + [str(manuscript.get("summary", ""))]
        )
        for candidate in candidates:
            match = re.fullmatch(r".+?\s+통학\s+동선과\s+(.+?)\s+점검", candidate)
            if not match:
                match = re.fullmatch(r"학습\s+지속성을\s+높이는\s+(.+?)\s+확인법", candidate)
            if not match:
                match = re.search(
                    r"(?:참고\s*키워드|추가\s*확인\s*항목)(?:은|는)\s*([^.!?]{1,40}?)입니다",
                    candidate,
                )
            if not match:
                match = re.search(
                    r"(?:^|[.!?,]\s+)([가-힣A-Za-z0-9· _-]{1,40}?)\s+같은\s+운영\s+정보는",
                    candidate,
                )
            if match:
                source_reference = match.group(1).strip()
                break

    def clean(value: object) -> str:
        raw = str(value or "")
        if source_reference:
            raw = raw.replace(source_reference, "학습 운영 기준")
        raw = raw.replace("지역내 모든 고등학교 가능", "학교별 적용 여부는 상담에서 확인해야 합니다")
        raw = raw.replace("지역 내 모든 고등학교 가능", "학교별 적용 여부는 상담에서 확인해야 합니다")
        raw = raw.replace("지역내 모든 중학교 가능", "학교별 적용 여부는 상담에서 확인해야 합니다")
        raw = raw.replace("지역 내 모든 중학교 가능", "학교별 적용 여부는 상담에서 확인해야 합니다")
        raw = raw.replace("오현초호매실중·능실중", "능실중")
        raw = raw.replace("오현초호매실중", "능실중")
        raw = raw.replace("남길 수 있습니다", "기록할 수 있습니다")
        first = site_polish(raw, local, config)
        grammar = content_engine.final_polish(first, local, config, verified_grades, schools)
        polished = site_polish(grammar, local, config)
        polished = polished.replace(
            "구체적으로 설명하는 데 다음 학습을 정하는 데 보탬이 됩니다",
            "구체적으로 설명하고 다음 학습을 정하는 데 도움이 됩니다",
        )
        # The source typo `오현초호매실중·능실중` can leave a leading
        # separator after the shared school-scope sanitizer removes the
        # malformed token.  Remove only a standalone separator so valid
        # school lists such as `영신중·능실중` remain intact.
        polished = re.sub(r"(?<![가-힣A-Za-z0-9])·(?=능실중)", "", polished)
        return content_engine.collapse_stacked_conditionals(polished)

    def clean_heading(value: object) -> str:
        """Stabilize H2-only rewrites so a later variation cannot rejoin heads."""
        result = clean(value)
        for _ in range(3):
            updated = clean(content_engine.polish_public_heading(result))
            if updated == result:
                break
            result = updated
        seen_priority = 0

        def replace_priority(match: re.Match[str]) -> str:
            nonlocal seen_priority
            seen_priority += 1
            return match.group(0) if seen_priority == 1 else "과목별 계획"

        result = re.sub("우선순위", replace_priority, result)
        result = result.replace("우선순위는 과목별 계획 비교에", "우선순위는 과목별 계획에")
        result = result.replace("숙제 수행·오답과 오답", "숙제 수행과 오답")
        result = re.sub(r"(학부모\s+질문[^:，,]{0,100}?)(?:안내|질문)\s*[:，,]\s*질문\s+기록", r"\1안내: 상담 기록", result)
        result = re.sub(r"(?:확인하는|확인할|물어볼)\s+질문\s*[:，,]\s*질문", "확인할 항목: 질문", result)
        result = re.sub(r"주간\s+실행\s+계획([^,.!?:]{0,100}?)다음\s+실행", r"주간 계획\1다음 실행", result)
        result = re.sub(r"주간\s+실행\s+계획([^,.!?:]{0,100}?)주간\s+계획", r"주간 계획\1가정 일정", result)
        result = re.sub(
            r"최근\s+풀이\s+기록과\s+주간\s+계획을\s+함께\s+살펴보는\s+선행\s+학생의\s+주간\s+계획\s+예시",
            "최근 풀이 기록을 함께 살펴보는 선행 학생의 주간 학습 예시",
            result,
        )
        heading_residue = re.search(
            r"숙제\s+수행·오답과\s+오답|질문\s+기록은\s+기록|질문\s+기록과\s+상담\s+질문|"
            r"(?:상담\s+후|주간)\s+실행\s+계획과\s+다음\s+실행|물어볼\s+질문:\s*질문|"
            r"복습(?:\s+간격)?과\s+복습\s+설계|오답은\s+오답\s+재확인|"
            r"첫\s+달\s+점검을\s+확인한\s+뒤\s+첫\s+달\s+점검|"
            r"함께\s+살펴보는\s+지역과\s+학년을\s+함께\s+봐야",
            result,
        )
        if heading_residue:
            raise ValueError(f"{config['slug']}/{local}: H2 의미 중복 {heading_residue.group(0)!r}")
        return result

    manuscript["meta"] = clean(manuscript.get("meta"))
    if len(str(manuscript["meta"])) < 70:
        manuscript["meta"] = (
            str(manuscript["meta"]).rstrip(" ,·.?!")
            + ". 최근 시험지와 과목별 학습 기록도 함께 확인하세요."
        )
    if len(str(manuscript["meta"])) > 100:
        meta = str(manuscript["meta"])
        selected: list[str] = []
        for sentence in re.split(r"(?<=[.!?])\s+", meta):
            candidate = " ".join([*selected, sentence]).strip()
            if len(candidate) > 100:
                break
            selected.append(sentence)
        compact = " ".join(selected).strip()
        if len(compact) < 70:
            compact = meta[:99].rsplit(" ", 1)[0].rstrip(" ,·.?!") + "."
        manuscript["meta"] = compact
    manuscript["intro"] = [clean(item) for item in manuscript.get("intro", [])]
    manuscript["sections"] = [
        (
            clean_heading(heading),
            [clean(paragraph) for paragraph in paragraphs],
        )
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


ELEMENTARY_REFERENCE_HEADING_PATTERNS = (
    re.compile(r"^(.+?)(?:을|를) 과장 없이 해석하는 법$"),
    re.compile(r"^(.+?)(?:이|가) 수업 안에서 작동하는 방식$"),
    re.compile(r"^(.+?) 관점의 세부 (?:확인|점검) 항목$"),
    re.compile(r"^(.+?)(?:과|와) 연결한 개인별 관리 포인트$"),
    re.compile(r"^(.+?)(?:을|를) 실제 관리로 (?:확인|점검)하는 질문$"),
)


@lru_cache(maxsize=1)
def elementary_reference_map() -> dict[str, tuple[int, str]]:
    """Read the unmodified archive so shared cleaners cannot hide the marker."""
    archive = SOURCE_DIR / "초등학생학원.zip"
    result: dict[str, tuple[int, str]] = {}
    with zipfile.ZipFile(archive) as bundle:
        for name in bundle.namelist():
            if name.endswith("/") or not name.lower().endswith(".txt"):
                continue
            raw = bundle.read(name).decode("utf-8")
            stem = Path(name).stem
            source_local = re.sub(r"\s+초등학생학원$", "", stem).strip()
            local = actual_local(source_local)
            matches: list[tuple[int, str]] = []
            headings = re.findall(r"^##\s+(.+?)\s*$", raw, flags=re.MULTILINE)
            for section_index, heading in enumerate(headings):
                for pattern in ELEMENTARY_REFERENCE_HEADING_PATTERNS:
                    match = pattern.fullmatch(heading.strip())
                    if match:
                        matches.append((section_index, match.group(1).strip()))
                        break
            if len(matches) != 1:
                raise ValueError(f"초등학생학원/{local}: 원본 참고 항목 식별 {len(matches)}개")
            result[local] = matches[0]
    if len(result) != 371:
        raise ValueError(f"초등학생학원 원본 참고 항목 매핑 {len(result)}개")
    return result


def normalize_elementary_source_reference(
    manuscript: dict[str, object],
    local: str,
    center: dict[str, object],
) -> tuple[str, ...]:
    """Remove the one arbitrary reference term supplied with each source.

    Every elementary source contains exactly one prompt-side reference term in
    a recognisable H2.  Some terms name unsupported facilities, programmes or
    outcomes.  Extracting the term from the heading lets us remove the whole
    class deterministically instead of maintaining an incomplete blacklist.
    The identified section is replaced with a verified, reader-facing learning
    record section before the shared language and fact scrub runs.
    """
    sections = [
        (str(heading), [str(value) for value in paragraphs])
        for heading, paragraphs in manuscript.get("sections", [])
    ]
    raw_reference_index, raw_reference_term = elementary_reference_map()[local]
    processed_matches: list[tuple[int, str]] = []
    for section_index, (heading, _paragraphs) in enumerate(sections):
        for pattern in ELEMENTARY_REFERENCE_HEADING_PATTERNS:
            match = pattern.fullmatch(heading.strip())
            if match:
                processed_matches.append((section_index, match.group(1).strip()))
                break
    if len(processed_matches) != 1:
        raise ValueError(
            f"초등학생학원/{local}: 변환된 참고 항목 식별 {len(processed_matches)}개"
        )
    reference_index, processed_reference_term = processed_matches[0]
    if reference_index >= len(sections):
        raise ValueError(f"초등학생학원/{local}: 참고 구획 위치 오류")
    if raw_reference_index >= len(sections):
        raise ValueError(f"초등학생학원/{local}: 원본 참고 구획 위치 오류")
    reference_terms = tuple(unique([raw_reference_term, processed_reference_term]))
    verified_grades = [
        str(value)
        for value in center.get("verified_grades", center.get("grades", []))
    ]
    heading_options = (
        f"{local} 초등 학습 기록에서 먼저 볼 순서",
        "영어 읽기·어휘와 수학 개념·연산을 나눠 보는 법",
        "정답 수보다 설명과 오답 재도전을 확인하는 법",
        "과제 시작과 짧은 복습을 기록으로 이어 보기",
        f"{local} 상담 뒤 다음 학습 계획을 정하는 기준",
    )
    controlled_heading = heading_options[ORDER.index(local) % len(heading_options)]
    controlled_paragraphs = [
        (
            f"{local} 상담에서는 최근 영어 읽기·어휘 활동과 수학 개념·연산 풀이를 "
            "나란히 놓고, 아이가 혼자 시작한 부분과 도움이 필요했던 지점을 표시해 보세요. "
            "정답 수보다 설명할 수 있는 과정과 다시 풀 수 있는 문제를 구분하면 "
            "첫 학습 목표를 더 구체적으로 정하기 쉽습니다."
        ),
        (
            f"확인된 초등 영어·수학 공통 가능 학년은 {'·'.join(verified_grades)}입니다. "
            "실제 교재·단원과 주간 분량은 자녀의 최근 기록을 바탕으로 상담에서 다시 확인해야 합니다."
            if verified_grades
            else
            "제공된 센터 자료에서 초등 영어·수학 공통 가능 학년이 확인되지 않습니다. "
            "자녀의 학년과 현재 교재를 알려 주고 수업 가능 여부와 시작 단원을 상담에서 먼저 확인해야 합니다."
        ),
    ]
    sections[reference_index] = (controlled_heading, controlled_paragraphs)
    manuscript["sections"] = sections

    def scrub(value: object) -> str:
        text = str(value or "")
        text = text.replace(
            "‘우리 아이의 영어와 수학에서 각각 첫 번째로 고칠 한 가지는 무엇이며, 그 이유를 어떤 자료로 판단했나요?’",
            "우리 아이의 영어와 수학에서 각각 먼저 고칠 한 가지와 그 판단 자료를 함께 물어보세요.",
        )
        text = text.replace(
            "‘누가, 언제, 무엇을 기록하고 다음 수업에서 어떻게 조정하나요?’",
            "누가 언제 무엇을 기록하고 다음 수업에서 어떻게 조정하는지 물어보세요.",
        )
        text = re.sub(
            r"아이와 함께 수업을 결정할 때는\s*‘좋았어\?’라고만 묻지 말고\s*"
            r"이해한 내용을 하나 설명해 보기,\s*모를 때 질문하기 쉬웠는지 말해 보기,\s*"
            r"과제를 혼자 시작할 수 있을지 예상해 보기를 권합니다(?=[.!?—–;]|$)",
            "아이와 함께 수업을 결정할 때는 수업이 어땠는지만 묻지 말고, "
            "이해한 내용 한 가지와 질문하기 쉬웠던 점, 과제를 혼자 시작할 수 있을지를 함께 확인해 보세요",
            text,
        )
        for reference_term in reference_terms:
            text = text.replace(reference_term, "학습 기록")
        text = text.replace("수업 가능 학교 항목에 기재된", "확인된 학교 정보에 포함된")
        text = text.replace("수업 학교 항목에 기재된", "확인된 학교 정보에 포함된")
        text = text.replace("학교 항목에 기재된", "확인된 학교 정보에 포함된")
        text = re.sub(
            r"이 행에는 수업 가능 학교명이 (?:따로 )?제공되지 않았으므로",
            "확인된 학교 정보가 없으므로",
            text,
        )
        text = re.sub(r"상담\s+첫\s+상담", "첫 상담", text)
        return text

    manuscript["meta"] = scrub(manuscript.get("meta"))
    manuscript["intro"] = [scrub(value) for value in manuscript.get("intro", [])]
    manuscript["sections"] = [
        (scrub(heading), [scrub(value) for value in paragraphs])
        for heading, paragraphs in manuscript.get("sections", [])
    ]
    manuscript["faqs"] = [
        {"question": scrub(item["question"]), "answer": scrub(item["answer"])}
        for item in manuscript.get("faqs", [])
    ]
    manuscript["reviews"] = [
        {"label": scrub(item.get("label", "")), "content": scrub(item["content"])}
        for item in manuscript.get("reviews", [])
    ]
    manuscript["summary"] = scrub(manuscript.get("summary"))
    manuscript["answer_heading"] = scrub(manuscript.get("answer_heading"))
    manuscript["answer_text"] = scrub(manuscript.get("answer_text"))
    manuscript["answer_tags"] = [scrub(value) for value in manuscript.get("answer_tags", [])]
    return reference_terms


def improve_elementary_student_manuscript(
    manuscript: dict[str, object],
    local: str,
    center: dict[str, object],
) -> dict[str, object]:
    """Give the elementary collection a direct, reader-first edit.

    The supplied manuscripts remain the source for the substantive sections.
    Seven-section variants are folded into six sections without discarding
    their paragraphs, while search-facing text, FAQ answers and the disclosed
    consultation example are normalized to the site's release contracts.
    """
    title = f"{local} 초등학생학원"
    meta = str(manuscript.get("meta", ""))
    if not meta.startswith(title):
        marker = "초등학생학원"
        marker_at = meta.find(marker)
        suffix = meta[marker_at + len(marker):] if marker_at >= 0 else " 상담 전 초등 영어·수학 교재와 과제·복습 기록을 확인하세요."
        meta = title + suffix
    if len(meta) > 100:
        meta = meta[:99].rsplit(" ", 1)[0].rstrip(" ,·.?!") + "."
    if len(meta) < 70:
        meta = meta.rstrip(" ,·.?!") + ". 최근 교재와 과제·오답 기록도 함께 확인하세요."
    manuscript["meta"] = meta

    verified_grades = [str(value) for value in center.get("verified_grades", center.get("grades", []))]
    grade_label = "·".join(verified_grades) if verified_grades else "초등학생"
    opening = (
        f"{local}에서 {grade_label}인 자녀가 영어 읽기·어휘와 수학 개념·연산의 시작점을 정하기 어려워하나요? "
        "최근 교재와 과제·오답 기록을 먼저 확인하고 과목별 작은 목표와 복습 순서를 구분하세요."
    )
    existing_intro = [str(value) for value in manuscript.get("intro", [])]
    manuscript["intro"] = [opening, *existing_intro[1:]]

    summary = str(manuscript.get("summary", "")).strip()
    direct_summary = f"{local}에서는 최근 초등 영어·수학 교재와 과제·복습 기록을 먼저 확인하세요."
    manuscript["summary"] = f"{direct_summary} {summary}".strip()

    fallback_headings = (
        f"{local} 초등 학습의 현재 어려움은 어디에서 시작될까요?",
        "영어 읽기·어휘와 수학 개념·연산을 어떻게 나눌까요?",
        "과제 습관과 질문 과정을 어떤 기록으로 확인할까요?",
        "짧은 복습과 오답 재도전 간격은 어떻게 정할까요?",
        "학교·주소 정보는 상담에서 어디까지 확인할까요?",
        "첫 상담 뒤 실행 기록은 어떻게 비교할까요?",
    )
    source_sections = [
        (str(heading), [str(value) for value in paragraphs])
        for heading, paragraphs in manuscript.get("sections", [])
    ]
    if len(source_sections) > 6:
        merged_heading, merged_paragraphs = source_sections[5]
        for _extra_heading, extra_paragraphs in source_sections[6:]:
            merged_paragraphs.extend(extra_paragraphs)
        source_sections = [*source_sections[:5], (merged_heading, merged_paragraphs)]

    normalized_sections: list[tuple[str, list[str]]] = []
    used_headings: set[str] = set()
    for index, (heading, paragraphs) in enumerate(source_sections):
        natural = re.split(r"\s+[·/|—]\s+", heading, maxsplit=1)[0].strip()
        if (
            len(natural) < 8
            or len(natural) > 78
            or natural in used_headings
            or re.search(r"[‘’\"']|운영\s*사실|관련\s*질문", natural)
            or re.search(r"^(?:이|해당)\s+초등|초등\s+(?:학습\s+과정|단계\s+관리\s+방식)", natural)
        ):
            natural = fallback_headings[min(index, len(fallback_headings) - 1)]
        used_headings.add(natural)
        normalized_sections.append((natural, paragraphs))
    manuscript["sections"] = normalized_sections

    schools = public_school_names([str(value) for value in center.get("schools", [])])

    def faq_lead(_question: str, index: int) -> str:
        if index == 0:
            return "최근 교재·과제·오답 기록과 아이가 혼자 설명한 내용을 먼저 준비하세요."
        if index == 1:
            return "영어 읽기·어휘와 수학 개념·연산에서 막힌 지점을 따로 나누어 점검하세요."
        if index == 2:
            if schools:
                return (
                    f"센터 자료에는 {'·'.join(schools)}가 초등학교 정보로 기재되어 있으며, "
                    "실제 수업 적용 여부는 자녀 학교의 현재 교재와 범위를 기준으로 상담에서 확인하세요."
                )
            return "특정 초등학교의 적용 여부는 상담에서 먼저 확인해야 합니다."
        if verified_grades:
            return f"확인된 수업 가능 학년은 {'·'.join(verified_grades)}이며 시작 교재와 단원은 상담에서 점검해야 합니다."
        return "수업 가능 학년과 시작 교재·단원은 상담에서 먼저 확인해야 합니다."

    direct_faqs: list[dict[str, str]] = []
    for index, item in enumerate(manuscript.get("faqs", [])[:4]):
        question = str(item["question"])
        lead = faq_lead(question, index)
        original_sentences = [
            part.strip()
            for part in re.findall(r"[^.!?]+(?:[.!?]+|$)", str(item["answer"]))
            if part.strip()
        ]
        answer_parts = [lead]
        for sentence in original_sentences[1:]:
            candidate = " ".join([*answer_parts, sentence])
            if len(answer_parts) >= 3 or len(candidate) > 235 or len(sentence) > 120:
                continue
            answer_parts.append(sentence)
        direct_faqs.append({"question": question, "answer": " ".join(answer_parts)})
    manuscript["faqs"] = direct_faqs

    concise_reviews: list[dict[str, str]] = []
    for item in manuscript.get("reviews", []):
        # The card already labels this as a reconstructed consultation
        # scenario.  Removing outer quotation marks before sentence-length
        # trimming prevents a closing quote from being stranded in a later
        # token and dropped when the concise excerpt is selected.
        content = str(item["content"]).strip().replace("‘", "").replace("’", "")
        content = content.replace("“", "").replace("”", "")
        pieces = [part.strip() for part in re.findall(r"[^.!?]+(?:[.!?]+|$)", content) if part.strip()]
        selected: list[str] = []
        for sentence in pieces:
            candidate = " ".join([*selected, sentence])
            if selected and len(candidate) > 430:
                break
            if not selected and len(sentence) > 430:
                sentence = sentence[:429].rsplit(" ", 1)[0].rstrip(" ,·") + "."
            selected.append(sentence)
        concise_reviews.append({"label": str(item["label"]), "content": " ".join(selected)})
    manuscript["reviews"] = concise_reviews
    return manuscript


def scrub_elementary_cross_level_facts(
    manuscript: dict[str, object],
    local: str,
    center: dict[str, object],
) -> dict[str, object]:
    """Remove any known middle/high school name left in elementary prose."""
    allowed = public_school_names([str(value) for value in center.get("schools", [])])
    all_verified = public_school_names(schools_for(row_for(local)))
    disallowed = [
        school for school in all_verified
        if school not in allowed and re.search(r"(?:중학교|고등학교|중|고)$", school)
    ]
    safe_sentence = (
        f"확인된 초등학교 정보는 {'·'.join(allowed)}이며, 실제 적용 범위는 상담에서 "
        "자녀 학교와 최근 교재를 기준으로 다시 확인해야 합니다."
        if allowed
        else
        "제공된 센터 자료에는 초등학교 정보가 확인되지 않아, 자녀 학교와 최근 교재를 "
        "기준으로 수업 적용 범위를 상담에서 확인해야 합니다."
    )

    def contains_school(text: str, school: str) -> bool:
        """Match a school name without mistaking it for part of a locality.

        For example, the verified middle-school name ``해운대중`` must not
        match the locality ``해운대중동``.  Korean particles and punctuation
        are accepted immediately after the school name.
        """
        suffix = r"(?=$|[\s,·.!?;:'\"“”‘’()\[\]<>]|은|는|이|가|을|를|의|과|와|에서|으로|까지)"
        return re.search(re.escape(school) + suffix, text) is not None

    def replace_school(text: str, school: str) -> str:
        suffix = r"(?=$|[\s,·.!?;:'\"“”‘’()\[\]<>]|은|는|이|가|을|를|의|과|와|에서|으로|까지)"
        return re.sub(re.escape(school) + suffix, "자녀 학교", text)

    canned_sentence_tails = (
        "에도 해당합니다",
        "확인에도 해당합니다",
        "사례에서도 살펴볼 내용입니다",
        "생활권에서도 확인해 보세요",
        "관련 상담 질문입니다",
        "상담 기준입니다",
        "학부모의 점검 항목입니다",
    )

    def prune_canned_sentences(text: str) -> str:
        """Remove source-template asides that do not help the reader."""
        text = re.sub(
            r"\s*[—–]\s*[^.!?]{0,100}?학습 기록(?:\s+점검)?\s+기준입니다\.?",
            ".",
            text,
        )
        parts = [
            part.strip()
            for part in re.findall(r"[^.!?]+(?:[.!?]+|$)", text)
            if part.strip()
        ]
        kept: list[str] = []
        for part in parts:
            probe = part.strip(" \t\r\n'\"‘’“”")
            probe = re.sub(r"[.!?]+$", "", probe).strip()
            if any(probe.endswith(tail) for tail in canned_sentence_tails):
                continue
            kept.append(part)
        return " ".join(kept)

    def polish_sentence(value: object) -> str:
        text = str(value or "")
        text = text.replace(
            "‘우리 아이의 영어와 수학에서 각각 첫 번째로 고칠 한 가지는 무엇이며, 그 이유를 어떤 자료로 판단했나요?’",
            "우리 아이의 영어와 수학에서 각각 먼저 고칠 한 가지와 그 판단 자료를 함께 물어보세요.",
        )
        text = text.replace(
            "‘누가, 언제, 무엇을 기록하고 다음 수업에서 어떻게 조정하나요?’",
            "누가 언제 무엇을 기록하고 다음 수업에서 어떻게 조정하는지 물어보세요.",
        )
        text = re.sub(
            r"아이와 함께 수업을 결정할 때는\s*‘좋았어\?’라고만 묻지 말고\s*"
            r"이해한 내용을 하나 설명해 보기,\s*모를 때 질문하기 쉬웠는지 말해 보기,\s*"
            r"과제를 혼자 시작할 수 있을지 예상해 보기를 권합니다(?=[.!?—–;]|$)",
            "아이와 함께 수업을 결정할 때는 수업이 어땠는지만 묻지 말고, "
            "이해한 내용 한 가지와 질문하기 쉬웠던 점, 과제를 혼자 시작할 수 있을지를 함께 확인해 보세요",
            text,
        )
        text = re.sub(r"상담\s+첫\s+상담", "첫 상담", text)
        text = text.replace("추가 설명이 확인할 필요가 있습니다", "상담에서 구체적인 설명을 확인해야 합니다")
        text = text.replace("추가 설명을 확인할 필요가 있습니다", "상담에서 구체적인 설명을 확인해야 합니다")
        text = text.replace(
            "연습 시간을 더 배정하는 설계가 확인할 필요가 있습니다",
            "연습 시간을 더 배정하는 설계인지 확인할 필요가 있습니다",
        )
        text = text.replace("과정을 보완해야 하는 상태입니다", "과정을 꾸준히 이어 갈 필요가 있습니다")
        text = text.replace("재설계가 우선 살펴볼 기준입니다", "재설계를 우선 검토해야 합니다")
        text = text.replace("시험 범위 확인는", "시험 범위 확인은")
        text = text.replace("시험 범위 확인가", "시험 범위 확인이")
        text = text.replace("많은 안내를 끝내는 방식", "상담 내용을 정리하는 방식")
        text = text.replace(
            "영어 과제는 상담 내용을 정리하는 방식보다",
            "영어 과제는 많은 분량을 한 번에 끝내기보다",
        )
        text = text.replace("교통·주차·차량 운행 여부", "이동·주차 관련 사항")
        text = text.replace("이동·주차 관련 사항는", "이동·주차 관련 사항은")
        text = text.replace("학습 기록 점검 확인", "학습 기록 확인")
        text = text.replace("학습 기록 점검 기록", "학습 기록")
        text = text.replace("학습 기록 점검의 실제 운영", "학습 기록을 활용하는 방법")
        text = text.replace("학습 기록 점검의 실제 절차", "학습 기록 활용 방법")
        text = text.replace(
            "학습 기록을 어떤 기록으로 확인할지",
            "학습 과정을 어떤 기록으로 확인할지",
        )
        text = text.replace("영어으로", "영어로")
        text = text.replace("초등 학교", "초등학교")
        text = re.sub(r"(초등\s+[1-6]학년)으로\s+영어는", r"\1이며 영어는", text)
        text = re.sub(r"(초등\s+(?:저|고)학년)으로\s+영어는", r"\1이며 영어는", text)
        text = text.replace("예시인 학생으로 영어는", "예시인 학생이며 영어는")
        text = text.replace("학생으로 영어는", "학생이며 영어는")
        text = text.replace(
            "우리 아이가 학생이며 영어는",
            "우리 아이는 영어",
        )
        text = text.replace(
            "우리 아이는 영어 짧은 문장은 이해하지만",
            "우리 아이는 짧은 영어 문장을 이해하지만",
        )
        text = text.replace(
            "우리 아이는 영어 영어 숙제는 끝내지만",
            "우리 아이는 영어 숙제를 끝내지만",
        )
        text = text.replace(
            "이 안내의 예시는 학생이며 영어는",
            "이 안내의 예시 학생은 영어",
        )
        text = re.sub(
            r"(?:[가-힣A-Za-z0-9]+(?:\s+[가-힣A-Za-z0-9]+){0,3})의 예시인 학생이며 영어는",
            "영어는",
            text,
        )
        text = text.replace("학생이며 영어는", "영어는")
        text = text.replace("영어는 영어 학습량은 많아도", "영어 학습량은 많아도")
        text = text.replace("영어는 영어 숙제는 끝내지만", "영어는 숙제를 끝내지만")
        text = text.replace("영어는 발음은 자신 있어도", "영어는 발음에 자신 있어도")
        text = text.replace(
            "영어는 단어 암기량은 충분한데",
            "영어는 외운 단어 수가 충분해도",
        )
        text = text.replace(
            "영어는 알파벳과 소리는 익숙하지만",
            "영어는 알파벳과 소리에 익숙하지만",
        )
        text = text.replace(
            "제공 데이터의 학교 항목이 비어 있어",
            "제공된 센터 자료에서 초등학교 정보가 확인되지 않아",
        )
        text = text.replace("학습 기록과 연결된 기록", "학습 과정과 연결된 기록")
        text = text.replace("이동·주차 관련 사항는", "이동·주차 관련 사항은")
        text = text.replace(
            "수학은 수학 개념 설명은 가능하지만",
            "수학은 개념을 설명할 수 있지만",
        )
        text = text.replace("수학은 계산은 빠르지만", "수학은 계산이 빠르지만")
        text = text.replace(
            "수학은 교과서 예제는 풀어도",
            "수학은 교과서 예제를 풀어도",
        )
        text = re.sub(
            r"((?:초|중|고)[1-6](?:·(?:초|중|고)[1-6])*)이\s+수업\s+가능",
            r"\1까지 수업 가능",
            text,
        )
        text = re.sub(
            r"확인된 학교 정보에 포함된\s+[^,.!?]{1,120}?"
            r"(?:(?:은|는)\s+|,\s*)상담 범위를 확인하는 참고 정보입니다\.?",
            safe_sentence,
            text,
        )
        text = prune_canned_sentences(text)
        parts = [
            part.strip()
            for part in re.findall(r"[^.!?]+(?:[.!?]+|$)", text)
            if part.strip()
        ]
        cleaned_school_parts: list[str] = []
        for part in parts:
            malformed_school_sentence = (
                ("제공 자료에는" in part and "수업 가능 학교 정보" in part)
                or "입력된 학교 정보 중" in part
                or "센터 안내 기준으로 수업 가능 학교로 확인되는 명칭은" in part
                or re.search(r"학교 정보에는\s*등이", part)
                or re.search(r"확인된 학교 예시는\s*등", part)
                or "등이 수업 가능 학교 정보에 들어 있습니다" in part
                or re.search(r"(?:초|초등학교)이\s+수업 가능 학교 정보로 제시되어 있습니다", part)
            )
            replacement = safe_sentence if malformed_school_sentence else part
            if not cleaned_school_parts or cleaned_school_parts[-1] != replacement:
                cleaned_school_parts.append(replacement)
        text = " ".join(cleaned_school_parts)
        text = re.sub(
            r"\s*[;—]\s*[^.!?]{0,120}?(?:확인에도 해당합니다|"
            r"사례에서도 살펴볼 내용입니다|생활권에서도 확인해 보세요|"
            r"관련 상담 질문입니다|상담 기준입니다|학부모의 점검 항목입니다)\.?",
            ".",
            text,
        )
        text = re.sub(r",\s*[—–]\s*(?=[.!?]|$)", ".", text)
        if not disallowed or not any(contains_school(text, school) for school in disallowed):
            return text
        parts = [
            part.strip()
            for part in re.findall(r"[^.!?]+(?:[.!?]+|$)", text)
            if part.strip()
        ]
        cleaned: list[str] = []
        for part in parts:
            replacement = safe_sentence if any(contains_school(part, school) for school in disallowed) else part
            if not cleaned or cleaned[-1] != replacement:
                cleaned.append(replacement)
        return " ".join(cleaned)

    def polish_meta(value: object) -> str:
        text = str(value or "")
        for school in disallowed:
            text = replace_school(text, school)
        text = re.sub(r"(?:자녀 학교\s*[,·]\s*)+자녀 학교", "자녀 학교", text)
        title = f"{local} 초등학생학원"
        if not text.startswith(title):
            text = f"{title} 상담 전 영어·수학 교재와 과제·복습 기록, 수업 가능 학년과 학교 자료 활용 기준을 확인하세요."
        if len(text) > 100:
            text = text[:99].rsplit(" ", 1)[0].rstrip(" ,·.?!") + "."
        if len(text) < 70:
            text = text.rstrip(" ,·.?!") + ". 최근 교재와 오답 기록도 함께 확인하세요."
        return text

    def polish_heading(value: object, fallback: str) -> str:
        text = str(value or "")
        if any(contains_school(text, school) for school in disallowed):
            return fallback
        return polish_sentence(text)

    manuscript["meta"] = polish_meta(manuscript.get("meta"))
    manuscript["intro"] = [polish_sentence(value) for value in manuscript.get("intro", [])]
    manuscript["sections"] = [
        (
            polish_heading(heading, f"{local} 초등학교 자료를 상담에서 확인하는 법"),
            [polish_sentence(value) for value in paragraphs],
        )
        for heading, paragraphs in manuscript.get("sections", [])
    ]
    manuscript["faqs"] = [
        {
            "question": polish_heading(item["question"], f"{local} 초등학교 자료의 적용 범위는 어떻게 확인하나요?"),
            "answer": polish_sentence(item["answer"]),
        }
        for item in manuscript.get("faqs", [])
    ]
    manuscript["reviews"] = [
        {"label": polish_sentence(item["label"]), "content": polish_sentence(item["content"])}
        for item in manuscript.get("reviews", [])
    ]
    manuscript["summary"] = polish_sentence(manuscript.get("summary"))
    manuscript["answer_heading"] = polish_heading(
        manuscript.get("answer_heading"), f"{local} 초등 영어·수학 상담 기준"
    )
    manuscript["answer_text"] = polish_sentence(manuscript.get("answer_text"))
    manuscript["answer_tags"] = [polish_sentence(value) for value in manuscript.get("answer_tags", [])]
    return manuscript


def finalize_elementary_manuscript(value: object) -> object:
    """Apply last-mile language fixes recursively to every manuscript field."""
    if isinstance(value, str):
        text = re.sub(r"상담\s+첫\s+상담", "첫 상담", value)
        text = text.replace("추가 설명이 확인할 필요가 있습니다", "상담에서 구체적인 설명을 확인해야 합니다")
        text = text.replace("추가 설명을 확인할 필요가 있습니다", "상담에서 구체적인 설명을 확인해야 합니다")
        text = text.replace("학습 기록과 연결된 기록", "학습 과정과 연결된 기록")
        text = text.replace(
            "학습 기록을 어떤 기록으로 확인할지",
            "학습 과정을 어떤 기록으로 확인할지",
        )
        text = text.replace("영어는 영어 학습량은 많아도", "영어 학습량은 많아도")
        text = text.replace("영어는 영어 숙제는 끝내지만", "영어는 숙제를 끝내지만")
        text = text.replace(
            "우리 아이가 학생이며 영어는",
            "우리 아이는 영어",
        )
        text = text.replace(
            "우리 아이는 영어 짧은 문장은 이해하지만",
            "우리 아이는 짧은 영어 문장을 이해하지만",
        )
        text = text.replace(
            "우리 아이는 영어 영어 숙제는 끝내지만",
            "우리 아이는 영어 숙제를 끝내지만",
        )
        text = text.replace(
            "이 안내의 예시는 학생이며 영어는",
            "이 안내의 예시 학생은 영어",
        )
        text = re.sub(
            r"(?:[가-힣A-Za-z0-9]+(?:\s+[가-힣A-Za-z0-9]+){0,3})의 예시인 학생이며 영어는",
            "영어는",
            text,
        )
        text = text.replace("학생이며 영어는", "영어는")
        text = text.replace("영어는 발음은 자신 있어도", "영어는 발음에 자신 있어도")
        text = text.replace(
            "영어는 단어 암기량은 충분한데",
            "영어는 외운 단어 수가 충분해도",
        )
        text = text.replace(
            "영어는 알파벳과 소리는 익숙하지만",
            "영어는 알파벳과 소리에 익숙하지만",
        )
        text = text.replace(
            "제공 데이터의 학교 항목이 비어 있어",
            "제공된 센터 자료에서 초등학교 정보가 확인되지 않아",
        )
        text = text.replace(
            "수학은 수학 개념 설명은 가능하지만",
            "수학은 개념을 설명할 수 있지만",
        )
        text = text.replace("수학은 계산은 빠르지만", "수학은 계산이 빠르지만")
        text = text.replace(
            "수학은 교과서 예제는 풀어도",
            "수학은 교과서 예제를 풀어도",
        )
        text = text.replace(
            "영어 과제는 상담 내용을 정리하는 방식보다",
            "영어 과제는 많은 분량을 한 번에 끝내기보다",
        )
        text = re.sub(r"([.!?])\s+([’”])", r"\1\2", text)
        return text
    if isinstance(value, dict):
        return {key: finalize_elementary_manuscript(item) for key, item in value.items()}
    if isinstance(value, list):
        return [finalize_elementary_manuscript(item) for item in value]
    if isinstance(value, tuple):
        return tuple(finalize_elementary_manuscript(item) for item in value)
    return value


ELEMENTARY_SCHOOL_FACT_SENTENCE_RE = re.compile(
    r"확인된 초등학교 정보는 [^.!?]{1,160}?이며,?\s*"
    r"실제 적용 범위는 상담에서 자녀 학교와 최근 교재를 기준으로 다시 확인해야 합니다\."
)


def dedupe_elementary_school_fact_sentences(
    manuscript: dict[str, object],
    local: str,
) -> dict[str, object]:
    """Keep one copy of each generated school-fact sentence per visible page.

    Cross-level school scrubbing can replace several source sentences with the
    same safe elementary-school statement.  Remove later copies across visible
    fields in display order while retaining the surrounding paragraph text.
    """
    seen: set[str] = set()

    def clean(value: object) -> str:
        text = str(value or "")
        parts = [
            part.strip()
            for part in re.findall(r"[^.!?]+(?:[.!?]+|$)", text)
            if part.strip()
        ]
        kept: list[str] = []
        for part in parts:
            match = ELEMENTARY_SCHOOL_FACT_SENTENCE_RE.search(part)
            if not match:
                kept.append(part)
                continue
            normalized = re.sub(r"\s+", " ", match.group(0)).replace("이며, 실제", "이며 실제")
            if normalized in seen:
                # The fact can follow a generated introductory bridge in the
                # same sentence. Dropping the whole sentence avoids leaving a
                # dangling fragment such as "...보면," behind.
                continue
            seen.add(normalized)
            kept.append(part)
        return " ".join(kept).strip()

    summary = clean(manuscript.get("summary"))
    manuscript["summary"] = summary or (
        f"{local}에서는 최근 초등 영어·수학 교재와 과제·복습 기록을 먼저 확인하세요."
    )

    manuscript["intro"] = [
        cleaned
        for value in manuscript.get("intro", [])
        if (cleaned := clean(value))
    ]

    sections: list[tuple[str, list[str]]] = []
    for heading, paragraphs in manuscript.get("sections", []):
        cleaned_paragraphs = [
            cleaned
            for value in paragraphs
            if (cleaned := clean(value))
        ]
        if not cleaned_paragraphs:
            cleaned_paragraphs = [
                "자녀 학교의 현재 교재와 범위를 준비해 상담에서 실제 적용 여부를 확인하세요."
            ]
        sections.append((str(heading), cleaned_paragraphs))
    manuscript["sections"] = sections

    answer_text = clean(manuscript.get("answer_text"))
    manuscript["answer_text"] = answer_text or (
        "최근 교재와 학습 기록을 준비해 과목별 시작점과 학교 자료의 적용 범위를 확인하세요."
    )

    reviews: list[dict[str, str]] = []
    for item in manuscript.get("reviews", []):
        content = clean(item.get("content"))
        reviews.append(
            {
                "label": str(item.get("label", "상담 상황 예시")),
                "content": content or (
                    "자녀 학교의 현재 교재와 학습 기록을 준비해 상담에서 적용 범위를 확인한 상황 예시입니다."
                ),
            }
        )
    manuscript["reviews"] = reviews

    faqs: list[dict[str, str]] = []
    for item in manuscript.get("faqs", []):
        answer = clean(item.get("answer"))
        faqs.append(
            {
                "question": str(item.get("question", "")),
                "answer": answer or (
                    "자녀 학교의 현재 교재와 범위를 준비해 상담에서 실제 적용 여부를 확인하세요."
                ),
            }
        )
    manuscript["faqs"] = faqs
    return manuscript


def improve_high_student_manuscript(
    manuscript: dict[str, object],
    local: str,
    center: dict[str, object],
) -> dict[str, object]:
    """Give the new high-school collection a direct, reader-first edit.

    The supplied manuscripts remain the source for the six substantive
    sections.  This pass only normalizes the search-facing lead, headings,
    concise FAQs and the disclosed consultation example so they fit the
    site's existing editorial and accessibility contracts.
    """
    title = f"{local} 고등학생학원"
    meta = str(manuscript.get("meta", ""))
    if not meta.startswith(title):
        marker = "고등학생학원"
        marker_at = meta.find(marker)
        suffix = meta[marker_at + len(marker):] if marker_at >= 0 else " 상담 전 고등 영어·수학 학습 기록과 시험 일정을 확인하세요."
        meta = title + suffix
    if len(meta) > 100:
        meta = meta[:99].rsplit(" ", 1)[0].rstrip(" ,·.?!") + "."
    if len(meta) < 70:
        meta = meta.rstrip(" ,·.?!") + ". 최근 답안과 과목별 복습 기록도 함께 확인하세요."
    manuscript["meta"] = meta

    verified_grades = [str(value) for value in center.get("verified_grades", center.get("grades", []))]
    grade_label = "·".join(verified_grades) if verified_grades else "고등학생"
    opening = (
        f"{local}에서 {grade_label}인 자녀가 영어·수학 시험 범위와 복습 순서를 정하기 어려워하나요? "
        "최근 시험지와 오답 기록을 먼저 확인하고 과목별 우선순위를 구분하세요."
    )
    existing_intro = [str(value) for value in manuscript.get("intro", [])]
    manuscript["intro"] = [opening, *existing_intro[1:]]

    summary = str(manuscript.get("summary", "")).strip()
    direct_summary = f"{local}에서는 최근 고등 영어·수학 답안과 시험 일정을 먼저 확인하세요."
    manuscript["summary"] = f"{direct_summary} {summary}".strip()

    fallback_headings = (
        f"{local} 고등 학습의 현재 어려움은 어디에서 시작될까요?",
        "최근 시험지에서 영어와 수학의 공백을 어떻게 찾을까요?",
        "학교 시험과 모의고사 준비 순서를 어떻게 나눌까요?",
        "과목별 시간 배분과 복습 간격은 어떻게 정할까요?",
        "학교·주소 정보는 상담에서 어디까지 확인할까요?",
        "첫 상담 뒤 실행 기록은 어떻게 비교할까요?",
    )
    normalized_sections: list[tuple[str, list[str]]] = []
    used_headings: set[str] = set()
    for index, (heading, paragraphs) in enumerate(manuscript.get("sections", [])):
        natural = re.split(r"\s+[·/|—]\s+", str(heading), maxsplit=1)[0].strip()
        if (
            len(natural) < 8
            or len(natural) > 78
            or natural in used_headings
            or re.search(r"[‘’\"']|운영\s*사실|관련\s*질문", natural)
        ):
            natural = fallback_headings[min(index, len(fallback_headings) - 1)]
        used_headings.add(natural)
        normalized_sections.append((natural, [str(value) for value in paragraphs]))
    manuscript["sections"] = normalized_sections

    schools = [str(value) for value in center.get("schools", [])]

    def faq_lead(_question: str, index: int) -> str:
        if index == 0:
            return "최근 시험지·교재·오답 기록을 먼저 준비하세요."
        if index == 1:
            return "최근 답안과 풀이를 비교해 개념 공백과 실수를 나누어 점검하세요."
        if index == 2:
            if schools:
                return f"확인된 고등학교 정보는 {'·'.join(schools)}이며 실제 적용 범위는 상담에서 다시 확인해야 합니다."
            return "특정 고등학교의 적용 여부는 상담에서 먼저 확인해야 합니다."
        if verified_grades:
            return f"확인된 수업 가능 학년은 {'·'.join(verified_grades)}이며 시작 단원은 상담에서 점검해야 합니다."
        return "수업 가능 학년과 시작 단원은 상담에서 먼저 확인해야 합니다."

    direct_faqs: list[dict[str, str]] = []
    for index, item in enumerate(manuscript.get("faqs", [])[:4]):
        question = str(item["question"])
        lead = faq_lead(question, index)
        original_sentences = [
            part.strip()
            for part in re.findall(r"[^.!?]+(?:[.!?]+|$)", str(item["answer"]))
            if part.strip()
        ]
        answer_parts = [lead]
        for sentence in original_sentences[1:]:
            candidate = " ".join([*answer_parts, sentence])
            if len(answer_parts) >= 3 or len(candidate) > 235 or len(sentence) > 120:
                continue
            answer_parts.append(sentence)
        direct_faqs.append({"question": question, "answer": " ".join(answer_parts)})
    manuscript["faqs"] = direct_faqs

    concise_reviews: list[dict[str, str]] = []
    for item in manuscript.get("reviews", []):
        content = str(item["content"]).strip()
        pieces = [part.strip() for part in re.findall(r"[^.!?]+(?:[.!?]+|$)", content) if part.strip()]
        selected: list[str] = []
        for sentence in pieces:
            candidate = " ".join([*selected, sentence])
            if selected and len(candidate) > 430:
                break
            if not selected and len(sentence) > 430:
                sentence = sentence[:429].rsplit(" ", 1)[0].rstrip(" ,·") + "."
            selected.append(sentence)
        concise_reviews.append({"label": str(item["label"]), "content": " ".join(selected)})
    manuscript["reviews"] = concise_reviews
    return manuscript


def improve_middle_student_manuscript(
    manuscript: dict[str, object],
    local: str,
    center: dict[str, object],
) -> dict[str, object]:
    """Give the middle-school collection a direct, reader-first edit.

    The supplied manuscripts remain the source for the six substantive
    sections. This pass normalizes search-facing text, keeps the FAQ concise,
    and makes the disclosed consultation example fit the existing contracts.
    """
    title = f"{local} 중학생학원"
    meta = str(manuscript.get("meta", ""))
    if not meta.startswith(title):
        marker = "중학생학원"
        marker_at = meta.find(marker)
        suffix = meta[marker_at + len(marker):] if marker_at >= 0 else " 상담 전 중등 영어·수학 학습 기록과 학교 진도·평가 일정을 확인하세요."
        meta = title + suffix
    if len(meta) > 100:
        meta = meta[:99].rsplit(" ", 1)[0].rstrip(" ,·.?!") + "."
    if len(meta) < 70:
        meta = meta.rstrip(" ,·.?!") + ". 최근 답안과 과제·오답 기록도 함께 확인하세요."
    manuscript["meta"] = meta

    verified_grades = [str(value) for value in center.get("verified_grades", center.get("grades", []))]
    grade_label = "·".join(verified_grades) if verified_grades else "중학생"
    opening = (
        f"{local}에서 {grade_label}인 자녀가 영어·수학 학교 진도와 과제·복습 순서를 정하기 어려워하나요? "
        "최근 시험지와 과제·오답 기록을 먼저 확인하고 과목별 시작점을 구분하세요."
    )
    existing_intro = [str(value) for value in manuscript.get("intro", [])]
    manuscript["intro"] = [opening, *existing_intro[1:]]

    summary = str(manuscript.get("summary", "")).strip()
    direct_summary = f"{local}에서는 최근 중등 영어·수학 답안과 학교 진도·평가 일정을 먼저 확인하세요."
    manuscript["summary"] = f"{direct_summary} {summary}".strip()

    fallback_headings = (
        f"{local} 중등 학습의 현재 어려움은 어디에서 시작될까요?",
        "최근 시험지에서 영어와 수학의 공백을 어떻게 찾을까요?",
        "학교 진도와 지필·수행평가 준비를 어떻게 나눌까요?",
        "과제 실행과 오답 복습 간격은 어떻게 정할까요?",
        "학교·주소 정보는 상담에서 어디까지 확인할까요?",
        "첫 상담 뒤 실행 기록은 어떻게 비교할까요?",
    )
    normalized_sections: list[tuple[str, list[str]]] = []
    used_headings: set[str] = set()
    for index, (heading, paragraphs) in enumerate(manuscript.get("sections", [])):
        natural = re.split(r"\s+[·/|—]\s+", str(heading), maxsplit=1)[0].strip()
        if (
            len(natural) < 8
            or len(natural) > 78
            or natural in used_headings
            or re.search(r"[‘’\"']|운영\s*사실|관련\s*질문", natural)
        ):
            natural = fallback_headings[min(index, len(fallback_headings) - 1)]
        used_headings.add(natural)
        normalized_sections.append((natural, [str(value) for value in paragraphs]))
    manuscript["sections"] = normalized_sections

    schools = [str(value) for value in center.get("schools", [])]

    def faq_lead(_question: str, index: int) -> str:
        if index == 0:
            return "최근 시험지·교재·과제·오답 기록을 먼저 준비하세요."
        if index == 1:
            return "최근 답안과 풀이를 비교해 개념 공백과 반복 실수를 나누어 점검하세요."
        if index == 2:
            if schools:
                return f"확인된 중학교 정보는 {'·'.join(schools)}이며 실제 적용 범위는 상담에서 다시 확인해야 합니다."
            return "특정 중학교의 적용 여부는 상담에서 먼저 확인해야 합니다."
        if verified_grades:
            return f"확인된 수업 가능 학년은 {'·'.join(verified_grades)}이며 시작 단원은 상담에서 점검해야 합니다."
        return "수업 가능 학년과 시작 단원은 상담에서 먼저 확인해야 합니다."

    direct_faqs: list[dict[str, str]] = []
    for index, item in enumerate(manuscript.get("faqs", [])[:4]):
        question = str(item["question"])
        lead = faq_lead(question, index)
        original_sentences = [
            part.strip()
            for part in re.findall(r"[^.!?]+(?:[.!?]+|$)", str(item["answer"]))
            if part.strip()
        ]
        answer_parts = [lead]
        for sentence in original_sentences[1:]:
            candidate = " ".join([*answer_parts, sentence])
            if len(answer_parts) >= 3 or len(candidate) > 235 or len(sentence) > 120:
                continue
            answer_parts.append(sentence)
        direct_faqs.append({"question": question, "answer": " ".join(answer_parts)})
    manuscript["faqs"] = direct_faqs

    concise_reviews: list[dict[str, str]] = []
    for item in manuscript.get("reviews", []):
        content = str(item["content"]).strip()
        pieces = [part.strip() for part in re.findall(r"[^.!?]+(?:[.!?]+|$)", content) if part.strip()]
        selected: list[str] = []
        for sentence in pieces:
            candidate = " ".join([*selected, sentence])
            if selected and len(candidate) > 430:
                break
            if not selected and len(sentence) > 430:
                sentence = sentence[:429].rsplit(" ", 1)[0].rstrip(" ,·") + "."
            selected.append(sentence)
        concise_reviews.append({"label": str(item["label"]), "content": " ".join(selected)})
    manuscript["reviews"] = concise_reviews
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
    if slug in {"초등학생학원", "중학생학원", "고등학생학원"} and len(manuscript.get("faqs", [])) != 4:
        raise ValueError(f"{slug}/{local}: FAQ가 정확히 4개가 아닙니다")
    if slug in {"초등학생학원", "중학생학원", "고등학생학원"} and len(manuscript.get("sections", [])) != 6:
        raise ValueError(f"{slug}/{local}: 본문 H2 구획이 정확히 6개가 아닙니다")
    visible_parts = (
        [meta, *[str(item) for item in manuscript.get("intro", [])]]
        + [str(value) for pair in manuscript.get("sections", []) for value in (pair[0], *pair[1])]
        + [str(value) for item in manuscript.get("faqs", []) for value in (item["question"], item["answer"])]
        + [str(value) for item in manuscript.get("reviews", []) for value in (item["label"], item["content"])]
        + [str(manuscript.get("summary", "")), str(manuscript.get("answer_heading", "")), str(manuscript.get("answer_text", ""))]
        + [str(item) for item in manuscript.get("answer_tags", [])]
    )
    visible = " ".join(visible_parts)
    forbidden = re.compile(
        r"(?:\bSEO\b|\bAEO\b|\bGEO\b|(?<![가-힣])원고(?![가-힣])|(?<![가-힣])키워드(?![가-힣])|"
        r"후기형\s*예시|설정한\s*학생\s*유형|놓치는\s*편\s*학생|것이라는\s*목표|"
        r"형식의\s*후기|수업학교|확인\s*항목[가는와]|학생와|학원라는|편\s*(?:학생|아이)|"
        r"학원\s*(?:실\s*시간|온라인|화상|대면)\s*수업|이\s*안내에서\s*설정한|"
        r"남길\s*수\s*있습니다|목표도\s*이런|(?<![가-힣])본문에서(?![가-힣])|"
        r"수업\s*설계은|피드백\s*구조은|선택\s*전\s*확인할\s*(?:확인\s*항목|선택\s*기준)|"
        r"자료에\s*(?:적힌|제시된)|제공된\s*주소\s*정보|구조화\s*데이터|"
        r"(?:(?:초등|중등|중|고등)(?:학교)?\s*[1-6]\s*학년|해당\s*학년)\s+중\s+"
        r"[^,.]{2,120}?학생|"
        r"수학\s*풀이이|영어\s*답안과\s*수학\s*풀이와|학생이\s*받은\s*학교에서\s*받은\s*자료|"
        r"학생이\s*가져온\s*제공된\s*학교\s*자료|과정이\s*필요한\s*과정|"
        r"보는\s*지도가\s*확인할\s*필요|최근\s*교재\s*활용과\s*교재|학습학습|"
        r"시험학습\s*성과|학생이\s*설명한\s*두\s*과목\s*내용을\s*학생의\s*설명|"
        r"[초중고][1-6](?:·[초중고][1-6])+?이\s+(?:확인된\s*수업\s*가능\s*학년|"
        r"전문학원\s*상담\s*가능\s*학년)|(?:루틴|장치|구조|절차|관리)(?:가|이)\s+확인할\s+필요|"
        r"상담\s+첫\s+상담)"
    )
    for part in visible_parts:
        forbidden_match = forbidden.search(part)
        if forbidden_match:
            raise ValueError(f"{slug}/{local}: 공개용 문장 금지 표현 {forbidden_match.group(0)!r}")
        malformed = MALFORMED_LANGUAGE_RE.search(part)
        if malformed:
            raise ValueError(f"{slug}/{local}: 공개용 문장 비문 {malformed.group(0)!r}")
        residue = PUBLIC_COPY_RESIDUE_RE.search(part)
        if residue:
            raise ValueError(f"{slug}/{local}: 공개용 문장 잔여 {residue.group(0)!r}")
    faq_leads: set[str] = set()
    faq_answer_leads: set[str] = set()
    faq_sentences: set[str] = set()
    for faq in manuscript.get("faqs", []):
        question = re.sub(r"\s+", " ", str(faq["question"])).strip()
        lead = question.split(",", 1)[0].strip()
        if 8 <= len(lead) <= 80 and lead.endswith(
            ("면", "보면", "살펴보면", "정리하면", "대조하면", "때")
        ):
            if lead in faq_leads:
                raise ValueError(f"{slug}/{local}: FAQ 조건 도입부 중복 {lead!r}")
            faq_leads.add(lead)
        for sentence in content_engine.shared.sentence_parts(str(faq["answer"])):
            normalized = re.sub(r"\s+", " ", sentence).strip()
            answer_lead = re.match(
                rf"^([^,.!?]{{8,140}}?(?:{content_engine.FAQ_CONDITIONAL_ENDINGS})),",
                normalized,
            )
            if answer_lead:
                answer_lead_text = answer_lead.group(1).strip()
                if answer_lead_text in faq_answer_leads:
                    raise ValueError(
                        f"{slug}/{local}: FAQ 답변 조건 도입부 중복 {answer_lead_text!r}"
                    )
                faq_answer_leads.add(answer_lead_text)
            if re.search(
                r"(?:하면|보면|살펴보면|맞춰\s+보면|대조하면|정리하면|"
                r"나란히\s+놓으면|놓고\s+보면|넣으면|바꾸면|이어\s+보면|"
                r"구체화하면|연결하면|배열하면|삼으면|포함하면),\s+"
                r"[^.!?]{2,190}?(?:하면|보면|살펴보면|맞춰\s+보면|대조하면|정리하면|"
                r"나란히\s+놓으면|놓고\s+보면|넣으면|바꾸면|이어\s+보면|"
                r"구체화하면|연결하면|배열하면|삼으면|포함하면)(?:,|\s)",
                normalized,
            ):
                raise ValueError(f"{slug}/{local}: FAQ 조건문 중첩 {normalized!r}")
            if normalized in faq_sentences:
                raise ValueError(f"{slug}/{local}: FAQ 답변 문장 중복 {normalized!r}")
            faq_sentences.add(normalized)
    review_sentences: set[str] = set()
    for review in manuscript.get("reviews", []):
        for sentence in content_engine.shared.sentence_parts(str(review["content"])):
            normalized = re.sub(r"\s+", " ", sentence).strip()
            if normalized in review_sentences:
                raise ValueError(f"{slug}/{local}: 상담 상황 문장 중복 {normalized!r}")
            review_sentences.add(normalized)
    heading_residue = re.compile(
        r"방법.{0,100}방법$|확인과\s+연결해\s+확인하기|"
        r"확인(?:한\s+뒤|하고).{0,40}확인|자료.{0,50}자료\s+확인|"
        r"우선순위.{0,60}우선순위|살펴보기을|점검을\s+점검|"
        r"(?P<head_repeat>기준|순서|학부모|현재).{0,100}\b(?P=head_repeat)\b|"
        r"(?:확인|점검|살펴보기)을\s+정하는\s+(?:순서|방법)|"
        r"(?:을|를)\s+[^,.!?:]{1,45}?(?:을|를)\s+연결하는\s+기준"
    )
    for heading, _paragraphs in manuscript.get("sections", []):
        match = heading_residue.search(str(heading))
        if match:
            raise ValueError(f"{slug}/{local}: H2 반복 표현 {match.group(0)!r}")
    if slug == "전문학원":
        generic_source_residue = re.search(
            r"자료에\s*함께\s*제시된|추가\s*확인\s*항목|"
            r"주소\s*정보는\s*.{5,180}?\s*기준으로\s*제공되어\s*있습니다|"
            r"같은\s*운영\s*정보는|관련\s*안내를\s*확인|같은\s*항목을\s*체크리스트",
            visible,
        )
        if generic_source_residue:
            raise ValueError(
                f"{slug}/{local}: 임의 참고 항목 잔여 {generic_source_residue.group(0)!r}"
            )
    if slug == "초등학생학원":
        elementary_residue = re.search(
            r"확인에도 해당합니다|사례에서도 살펴볼 내용입니다|"
            r"생활권에서도 확인해 보세요|교통·주차·차량 운행 여부|"
            r"이동·주차 관련 사항는|"
            r"정보에는\s*등이|(?:초|초등학교)이\s+수업 가능 학교 정보|"
            r"등이\s+수업 가능 학교 정보에 들어 있습니다|에도\s+해당합니다|"
            r"확인된 학교 예시는\s*등|학습 기록을 어떤 기록으로 확인할지|"
            r"학생이며\s+영어는|우리 아이가\s+학생이며|"
            r"우리 아이는\s+영어\s+[가-힣]+은|영어\s+영어|"
            r"확인된 학교 정보에 포함된[^.!?]{0,160}초(?:은|는)\s+상담 범위를|"
            r"센터 안내 기준으로 수업 가능 학교로 확인되는 명칭은|"
            r"입력된 학교 정보 중|(?:초등\s+(?:(?:저|고)학년|[1-6]학년)|학생)으로\s+영어는|"
            r"학생은\s+영어에서|영어에서\s+영어\s+학습량|"
            r"영어는\s+영어\s+(?:학습량은|숙제는)|제공 데이터|"
            r"영어는\s+(?:발음은|단어\s+암기량은|알파벳과\s+소리는)|"
            r"학습 기록과 연결된 기록|추가 설명(?:이|을)\s+확인할 필요|"
            r"수학은\s+(?:수학\s+개념\s+설명은|계산은|교과서\s+예제는)|"
            r"영어 과제는 상담 내용을 정리하는 방식보다|[.!?]\s+[’”]|"
            r"영어으로|설계가\s+확인할 필요가 있습니다",
            visible,
        )
        if elementary_residue:
            raise ValueError(
                f"{slug}/{local}: 초등 원고 문장 잔여 {elementary_residue.group(0)!r}"
            )
        for opening_quote, closing_quote in (("‘", "’"), ("“", "”")):
            if visible.count(opening_quote) != visible.count(closing_quote):
                raise ValueError(
                    f"{slug}/{local}: 인용부호 불균형 "
                    f"{opening_quote}{visible.count(opening_quote)}/"
                    f"{closing_quote}{visible.count(closing_quote)}"
                )
        school_fact_sentences: list[str] = []
        for part in visible_parts:
            school_fact_sentences.extend(ELEMENTARY_SCHOOL_FACT_SENTENCE_RE.findall(part))
        normalized_school_facts = [
            sentence.replace("이며, 실제", "이며 실제")
            for sentence in school_fact_sentences
        ]
        if len(normalized_school_facts) != len(set(normalized_school_facts)):
            raise ValueError(f"{slug}/{local}: 동일 학교 확인 문장 반복")
        intro_text = " ".join(str(value) for value in manuscript.get("intro", []))
        display_local = str(row_for(local).get("동네", "")).strip()
        if local not in intro_text and (not display_local or display_local not in intro_text):
            raise ValueError(f"{slug}/{local}: 도입부 지역명 누락")
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
            "extract_center_data": lambda local: category_center_data(local, config),
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
    errors: list[str] = []
    for source_local, manuscript in values.items():
        try:
            local = actual_local(str(source_local))
            if local in mapped:
                raise ValueError(f"원고 동네가 중복 매핑되었습니다: {local}")
            manuscript["title"] = f"{local} {config['label']}"
            center = namespace["extract_center_data"](local)
            source_references: tuple[str, ...] = ()
            if str(config["slug"]) == "초등학생학원":
                source_references = normalize_elementary_source_reference(manuscript, local, center)
            polish_manuscript(manuscript, local, config, center)
            if str(config["slug"]) == "초등학생학원":
                improve_elementary_student_manuscript(manuscript, local, center)
                scrub_elementary_cross_level_facts(manuscript, local, center)
                finalized = finalize_elementary_manuscript(manuscript)
                if not isinstance(finalized, dict):
                    raise ValueError(f"{config['slug']}/{local}: 원고 최종 정리 오류")
                manuscript = dedupe_elementary_school_fact_sentences(finalized, local)
            elif str(config["slug"]) == "고등학생학원":
                improve_high_student_manuscript(manuscript, local, center)
            elif str(config["slug"]) == "중학생학원":
                improve_middle_student_manuscript(manuscript, local, center)
            if source_references:
                for heading, _paragraphs in manuscript.get("sections", []):
                    if any(pattern.fullmatch(str(heading).strip()) for pattern in ELEMENTARY_REFERENCE_HEADING_PATTERNS):
                        raise ValueError(f"{config['slug']}/{local}: 원고 참고 H2 잔여 {heading!r}")
            validate_manuscript(str(config["slug"]), local, manuscript)
            mapped[local] = manuscript
        except ValueError as exc:
            errors.append(str(exc))
    if errors:
        details = "\n".join(f"- {error}" for error in errors[:40])
        raise ValueError(f"{config['slug']} 원고 검증 오류 {len(errors)}건:\n{details}")
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
            {"@type": "CollectionPage", "@id": url + "#webpage", "url": url, "name": f"과목별학원 | {DOMAIN_NAME}", "description": "종합·영수·영어·수학 전문학원과 초등학생·중학생·고등학생학원 안내를 371개 동네별로 찾고 현재 학습 상태, 센터 정보와 상담 준비 기준을 확인할 수 있습니다.", "inLanguage": "ko-KR", "isPartOf": {"@id": SITE_URL + "/#website"}, "breadcrumb": {"@id": url + "#breadcrumb"}, "mainEntity": {"@id": url + "#directory"}, "dateModified": TODAY},
            {"@type": "BreadcrumbList", "@id": url + "#breadcrumb", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "홈", "item": SITE_URL + "/"}, {"@type": "ListItem", "position": 2, "name": "과목별학원", "item": url}]},
            {"@type": "ItemList", "@id": url + "#directory", "name": "전문학원 분류", "numberOfItems": len(items), "itemListElement": items},
            {"@type": "FAQPage", "@id": url + "#faq", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]},
        ],
    }


def subject_root_faqs() -> list[tuple[str, str]]:
    return [
        ("과목별학원 페이지는 전국센터와 무엇이 다른가요?", "전국센터는 동네와 센터를 먼저 선택하는 구조이고, 과목별학원은 종합·영수·영어·수학 전문학원 또는 초등학생·중학생·고등학생학원 분류를 먼저 고른 뒤 해당 동네의 학습 안내를 확인하는 구조입니다."),
        ("전문학원 상담 전에는 어떤 자료를 준비하면 좋나요?", "최근 시험지와 현재 교재, 틀린 문제의 답안·풀이 기록, 학교 시험 범위와 일주일 공부 시간을 준비하면 현재 상태를 더 구체적으로 나눌 수 있습니다."),
        ("동네 페이지에 표시된 센터 정보는 어떻게 확인하나요?", "제공된 센터정보 자료의 센터명, 주소, 교육지원청 등록번호, 가능 학년과 학교 정보를 사용하며 실제 개설 여부와 시간표는 상담에서 다시 확인합니다."),
    ]


def render_subject_root() -> str:
    canonical = encoded_url("과목별학원")
    description = "종합·영수·영어·수학 전문학원과 초등학생·중학생·고등학생학원 안내를 371개 동네별로 찾고 현재 학습 상태, 센터 정보와 상담 준비 기준을 확인할 수 있습니다."
    cards = "".join(
        f'''<a class="home-link-card{' is-primary' if index == 0 else ''}" href="./{slug}/"><span>{esc(CATEGORY_COPY[slug]['eyebrow'])}</span><strong>{esc(CATEGORY_COPY[slug]['label'])}</strong><p>{esc(CATEGORY_COPY[slug]['lead'])}</p></a>'''
        for index, slug in enumerate(TARGET_SLUGS)
    )
    faq = "".join(f'<details{" open" if index == 0 else ""}><summary>{esc(q)}</summary><p>{esc(a)}</p></details>' for index, (q, a) in enumerate(subject_root_faqs()))
    return f'''{head(f"과목별학원 | {DOMAIN_NAME}", description, canonical, SITE_URL + "/assets/generated/site3-hero.webp", subject_root_schema(), 1, "website")}
<body class="center-page subject-page"><a class="skip-link" href="#main">본문 바로가기</a>{navigation("../", "과목별학원")}
  <main id="main">
    <section class="center-hero"><div class="wrap"><div class="crumbs"><span><a href="../">홈</a></span><span>과목별학원</span></div><div class="center-hero-card"><div class="center-hero-inner"><div><p class="eyebrow">SUBJECT ACADEMY DIRECTORY</p><h1>과목별학원</h1><p>{description}</p><div class="local-actions"><a class="btn btn-primary" href="#subject-categories">분류 선택</a><a class="btn btn-ghost" href="../전국센터/">전국센터 보기</a></div></div><aside class="hero-mini-panel"><span>전문학원 분류</span><strong>{len(TARGET_SLUGS)}개</strong><span>각 371개 동네 안내</span></aside></div></div></div></section>
    <section id="subject-categories" class="local-section"><div class="wrap"><article class="home-link-hub"><p class="eyebrow">CHOOSE A SUBJECT</p><h2>학생의 현재 상황에 맞는 안내를 선택하세요</h2><p>학습 일정과 관리 흐름은 전문학원, 두 과목의 균형은 영수 전문학원, 한 과목의 진단은 영어·수학 전문학원, 학령별 기초·학교 진도·평가·복습 관리는 초등학생·중학생·고등학생학원 안내에서 확인할 수 있습니다.</p><div class="home-link-grid">{cards}</div></article></div></section>
    <section class="local-section"><div class="wrap local-grid"><article class="local-card"><p class="eyebrow">HOW TO USE</p><h2>동네 페이지 확인 순서</h2><ol class="process-list"><li><strong>1. 분류 선택</strong>종합 관리, 영수·영어·수학 또는 중·고등 과정 가운데 현재 우선순위를 고릅니다.</li><li><strong>2. 동네 검색</strong>허브에서 동네명 또는 광역지역을 선택합니다.</li><li><strong>3. 자료 확인</strong>최근 교재·시험지, 센터 정보와 가능 학년을 함께 봅니다.</li><li><strong>4. 상담 질문</strong>진단·과제·오답 재확인 과정을 실제 시간표와 대조합니다.</li></ol></article><article class="local-card"><p class="eyebrow">FACT CHECK</p><h2>안내 정보의 기준</h2><p>센터명·주소·교육지원청 등록번호·가능 학년·참고 학교는 제공된 센터정보 자료를 사용합니다. 자료가 비어 있는 항목은 임의로 만들지 않으며 상담 확인이 필요하다고 표시합니다.</p><p class="verified-note">자료 기준: 센터정보 정리 자료 · 최종 검수 {TODAY}</p></article></div></section>
    <section id="faq-section" class="local-section"><div class="wrap faq-local"><p class="eyebrow">FAQ</p><h2>과목별학원 이용 전 확인사항</h2>{faq}</div></section>
  </main>{footer("../")}
</body></html>'''


def hub_faqs(slug: str) -> list[tuple[str, str]]:
    label = str(CATEGORY_COPY[slug]["label"])
    if slug == "전문학원":
        first = "센터 자료에서 확인된 수업 가능 범위와 학년을 먼저 보고, 현재 교재·시험 기록·학교 일정·숙제·오답·질문 기록이 어떻게 이어지는지 확인할 수 있습니다."
    elif slug == "영수전문학원":
        first = "영어와 수학의 최근 시험지·교재를 따로 놓고 취약 영역, 과목별 오답, 학교 일정과 주간 학습시간을 비교할 수 있습니다."
    elif slug == "영어전문학원":
        first = "최근 영어 시험지와 교재에서 어휘 누적, 문법 적용, 독해 근거와 서술형 표현을 나누어 확인할 수 있습니다."
    elif slug == "초등학생학원":
        first = "최근 초등 영어·수학 교재와 과제 기록에서 읽기·어휘, 개념·연산, 질문 습관과 짧은 복습 순서를 나누어 확인할 수 있습니다."
    elif slug == "중학생학원":
        first = "최근 중등 영어·수학 학습 자료에서 학교 진도, 지필·수행평가 준비, 과제 실행과 오답 복습 순서를 나누어 확인할 수 있습니다."
    elif slug == "고등학생학원":
        first = "최근 고등 영어·수학 시험지와 교재에서 학교 시험 범위, 모의고사 학습, 과목별 시간 배분과 오답 재확인 순서를 나누어 확인할 수 있습니다."
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
    schools = public_school_names([str(value) for value in center.get("schools", [])])
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
    if slug == "초등학생학원":
        sibling_slugs = [other for other in TARGET_SLUGS if other != slug]
    elif slug == "중학생학원":
        sibling_slugs = [*LEGACY_SLUGS, "고등학생학원"]
    elif slug == "고등학생학원":
        sibling_slugs = list(LEGACY_SLUGS)
    else:
        sibling_slugs = [other for other in LEGACY_SLUGS if other != slug]
    links = [
        {"name": f"{local} {CATEGORY_COPY[other]['label']}", "url": encoded_url("과목별학원", other, local)}
        for other in sibling_slugs
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
    schools = public_school_names([str(value) for value in center.get("schools", [])])
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
    body_width, body_height = center.get("body_size", (0, 0))
    body_dimensions = f' width="{body_width}" height="{body_height}"' if body_width and body_height else ""
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
    <section class="local-section subject-media-section"><div class="wrap local-image-pair"><img src="{esc(representative)}" alt="{esc(title)} {DOMAIN_NAME} 대표" style="display:none;"><picture class="local-responsive-picture"><source media="(max-width: 640px)" srcset="{esc(body_mobile)}"><img src="{esc(body_image)}" alt="{esc(title)} 본문 {SITE_NAME}" loading="lazy" decoding="async"{body_dimensions}></picture><figure class="location-card"><img src="{esc(center['map_image'])}" alt="{esc(title)} 지도 {SITE_NAME}" loading="lazy" decoding="async"{map_dimensions}><figcaption>{esc(center['region'])} {esc(center['city'])} {esc(local)} 상담 장소와 이동 동선을 확인할 때 참고하는 위치 안내입니다.</figcaption></figure></div></section>
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
    card = f'<a class="home-link-card" href="과목별학원/"><span>SUBJECT DIRECTORY</span><strong>과목별학원 {len(TARGET_SLUGS)}개 분류</strong><p>종합·영수·영어·수학 전문학원과 초등학생·중학생·고등학생학원 안내를 371개 동네별로 확인합니다.</p></a>\n          '
    card_pattern = re.compile(r'<a class="home-link-card" href="과목별학원/">.*?</a>\s*', re.DOTALL)
    if card_pattern.search(source):
        source = card_pattern.sub(card, source, count=1)
    else:
        marker = '<a class="home-link-card is-primary" href="전국센터/">'
        position = source.find(marker)
        if position >= 0:
            source = source[:position] + card + source[position:]
    path.write_text(source, encoding="utf-8", newline="\n")


def update_llms() -> None:
    path = ROOT / "llms.txt"
    source = path.read_text(encoding="utf-8")
    block = f'''\n## 과목별학원\n\n- 과목별학원: {encoded_url('과목별학원')}\n- 전문학원: {encoded_url('과목별학원', '전문학원')}\n- 영수 전문학원: {encoded_url('과목별학원', '영수전문학원')}\n- 영어 전문학원: {encoded_url('과목별학원', '영어전문학원')}\n- 수학 전문학원: {encoded_url('과목별학원', '수학전문학원')}\n- 초등학생학원: {encoded_url('과목별학원', '초등학생학원')}\n- 중학생학원: {encoded_url('과목별학원', '중학생학원')}\n- 고등학생학원: {encoded_url('과목별학원', '고등학생학원')}\n'''
    if "## 과목별학원" not in source:
        source = source.rstrip() + "\n" + block
    else:
        source = re.sub(r"\n## 과목별학원\n.*?(?=\n## |\Z)", "\n" + block.strip() + "\n", source, flags=re.DOTALL)
    path.write_text(source, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="과목별 전문학원 페이지 생성")
    parser.add_argument("--category", choices=TARGET_SLUGS, help="선택한 카테고리만 재생성")
    args = parser.parse_args()
    if set(ENGINE_CONFIGS) != set(TARGET_SLUGS):
        raise ValueError(f"콘텐츠 엔진 카테고리 누락: {set(TARGET_SLUGS) - set(ENGINE_CONFIGS)}")
    SUBJECT_ROOT.mkdir(parents=True, exist_ok=True)
    build_slugs = (args.category,) if args.category else TARGET_SLUGS
    prepared: dict[str, tuple[dict[str, dict[str, object]], object]] = {}
    for slug in build_slugs:
        prepared[slug] = prepare_manuscripts(ENGINE_CONFIGS[slug])
        print(f"{slug}: preflight=371")

    generated = 0
    for slug in build_slugs:
        config = ENGINE_CONFIGS[slug]
        manuscripts, namespace = prepared[slug]
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
    print(f"generated_details={generated} subject_hubs={1 + len(TARGET_SLUGS)} navigation_pages={nav_changed}")


if __name__ == "__main__":
    main()
