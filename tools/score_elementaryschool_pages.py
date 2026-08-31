#!/usr/bin/env python3
"""Strict 100-point audit for 코칭학원.com 초등학생학원 detail pages.

The score is a transparent content and release-quality rubric.  It is not a
Naver (or any other search engine) ranking prediction.  Technical, factual,
and uniqueness failures are hard errors; points in another section cannot
offset them.  The collection must also contain exactly 371 pages, every page
must score at least 90, and the collection mean must be at least 95.

Only Python's standard library is used.  The scorer deliberately reads the
authoritative centre CSV itself instead of importing generation-time state.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import statistics
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
CATEGORY_SLUG = "초등학생학원"
CATEGORY_LABEL = "초등학생학원"
CATEGORY_ROOT = ROOT / "과목별학원" / CATEGORY_SLUG
DEFAULT_CENTER_CSV = ROOT.parent / "참고자료" / "공통자료" / "센터정보 정리.csv"
SITE_URL = "https://xn--sp5b72l1taf0p.com"
SITE_NAME = "코칭학원.com"
EXPECTED_PAGE_COUNT = 371
MIN_PAGE_SCORE = 90
MIN_MEAN_SCORE = 95
SIMILARITY_LIMIT = 0.75


# The group totals are part of the public scoring contract: 30 + 30 + 25 + 15.
WEIGHTS: dict[str, int] = {
    # Technical SEO: 30
    "technical_meta_identity": 8,
    "technical_schema": 7,
    "technical_faq_sync": 5,
    "technical_images": 5,
    "technical_toc": 5,
    # Content: 30
    "content_body_length": 6,
    "content_h2_six": 4,
    "content_faq_four": 4,
    "content_consultation_example": 4,
    "content_reader_problem_action": 5,
    "content_natural_h2": 3,
    "content_faq_concise": 4,
    # Factual grounding: 25
    "factual_elementary_grades_visible": 6,
    "factual_elementary_grades_schema": 4,
    "factual_elementary_schools_visible": 5,
    "factual_elementary_schools_schema": 4,
    "factual_no_cross_level": 3,
    "factual_safe_claims": 3,
    # Collection differentiation: 15
    "uniqueness_exact": 5,
    "uniqueness_similarity": 10,
}

GROUPS: dict[str, tuple[str, ...]] = {
    "technical_seo": tuple(name for name in WEIGHTS if name.startswith("technical_")),
    "content": tuple(name for name in WEIGHTS if name.startswith("content_")),
    "factual": tuple(name for name in WEIGHTS if name.startswith("factual_")),
    "uniqueness": tuple(name for name in WEIGHTS if name.startswith("uniqueness_")),
}
GROUP_TOTALS = {name: sum(WEIGHTS[item] for item in items) for name, items in GROUPS.items()}
assert GROUP_TOTALS == {
    "technical_seo": 30,
    "content": 30,
    "factual": 25,
    "uniqueness": 15,
}
assert sum(WEIGHTS.values()) == 100


TAG_RE = re.compile(r"<[^>]+>", re.DOTALL)
SCRIPT_STYLE_RE = re.compile(
    r"<(?:script|style)\b[^>]*>.*?</(?:script|style)>", re.IGNORECASE | re.DOTALL
)
ATTR_RE = re.compile(
    r"(?P<name>[:\w-]+)\s*=\s*(?:\"(?P<double>[^\"]*)\"|'(?P<single>[^']*)')",
    re.DOTALL,
)
IMG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE | re.DOTALL)
JSON_LD_RE = re.compile(
    r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
ARTICLE_RE = re.compile(
    r'<article\b[^>]*class=["\'][^"\']*\bsubject-article\b[^"\']*["\'][^>]*>'
    r"(.*?)</article>",
    re.IGNORECASE | re.DOTALL,
)
PROSE_SECTION_RE = re.compile(
    r"<section\b(?P<attrs>[^>]*)>(?P<body>.*?)</section>",
    re.IGNORECASE | re.DOTALL,
)
H2_RE = re.compile(r"<h2\b[^>]*>(.*?)</h2>", re.IGNORECASE | re.DOTALL)
DETAIL_RE = re.compile(r"<details\b[^>]*>(.*?)</details>", re.IGNORECASE | re.DOTALL)
SUMMARY_RE = re.compile(r"<summary\b[^>]*>(.*?)</summary>", re.IGNORECASE | re.DOTALL)
PARAGRAPH_RE = re.compile(r"<p\b[^>]*>(.*?)</p>", re.IGNORECASE | re.DOTALL)
REVIEW_CARD_RE = re.compile(
    r'<article\b[^>]*class=["\'][^"\']*\breview-card\b[^"\']*["\'][^>]*>'
    r"(.*?)</article>",
    re.IGNORECASE | re.DOTALL,
)
TOC_RE = re.compile(
    r'<nav\b[^>]*class=["\'][^"\']*\bsubject-page-toc\b[^"\']*["\'][^>]*>'
    r"(.*?)</nav>",
    re.IGNORECASE | re.DOTALL,
)
TOC_LINK_RE = re.compile(
    r'<a\b[^>]*href=["\']#(?P<target>section-\d+)["\'][^>]*>.*?'
    r'<span\b[^>]*class=["\'][^"\']*\bsubject-page-toc-text\b[^"\']*["\'][^>]*>'
    r"(?P<label>.*?)</span>.*?</a>",
    re.IGNORECASE | re.DOTALL,
)
GRADE_RE = re.compile(
    r"(?<![가-힣A-Za-z0-9])(?:예비\s*)?"
    r"(?P<level>초등학교|초등|초|중학교|중등|중|고등학교|고등|고)\s*"
    r"(?P<number>[1-6])\s*(?:학년)?(?![0-9])"
)
GRADE_PREFIX = {
    "초등학교": "초", "초등": "초", "초": "초",
    "중학교": "중", "중등": "중", "중": "중",
    "고등학교": "고", "고등": "고", "고": "고",
}
ELEMENTARY_GRADE_RE = re.compile(r"초[1-6]")
SCHOOL_NAME_RE = re.compile(r"[가-힣A-Za-z0-9]+?(?:초등학교|중학교|고등학교|초|중|고)$")

READER_RE = re.compile(r"초등학생|학생|자녀|아이|학부모|보호자")
PROBLEM_RE = re.compile(
    r"어렵|막히|틀리|실수|오답|헷갈|부족|부담|고민|불안|취약|밀리|"
    r"시간\s*배분|시험\s*범위|복습|모의고사|서술형"
)
ACTION_RE = re.compile(
    r"확인|점검|준비|정리|비교|구분|분류|기록|대조|재확인|계획|"
    r"나누|조정|분석|복습|재풀이"
)
AUTHORING_RE = re.compile(
    r"(?<![가-힣])원고(?:의|에서|에는|를|로|처럼|라면)?(?![가-힣])|"
    r"프롬프트|작성\s*지시|다음과\s*같이\s*작성|메타\s*설명|"
    r"검색\s*키워드|참고\s*키워드|운영\s*키워드|검색\s*의도|검색자|"
    r"(?<![A-Za-z])SEO(?![A-Za-z])|JSON-LD|구조화\s*데이터|"
    r"D열|분량을\s*맞|본문에\s*삽입|이\s*페이지|페이지여야|설정한\s*학생|"
    r"자료상\s*수업\s*학교|수업\s*학교\s*항목|"
    r"학부모후기",
    re.IGNORECASE,
)
UNVERIFIED_OPERATION_RE = re.compile(
    r"입시(?:컨설팅학원|컨설팅반|컨설팅|합격관리|합격전략|성공사례|자료분석|"
    r"일정관리|로드맵|준비반|캠프반|캠프|실적|특강|설계|분석|평가|결과)|"
    r"방학(?:특강|캠프)|셔틀|주말(?:집중반|수업)|오전수업|"
    r"온라인수업|화상수업|녹화수업|실시간수업|대면수업|무료체험수업|"
    r"소그룹수업|그룹수업|소수정예수업|일대일수업|정원제수업|특강수업|"
    r"집중수업|밀착관리수업|수준별수업|보충수업|내신보강수업|"
    r"과제관리수업|플래너관리수업|토론형수업|집중관리수업|성적향상수업|"
    r"학습클리닉반|장기관리반|플래너관리반|성적관리반|학습관리반|"
    r"동기관리반|진도관리반|시험집중관리|학원교재실|"
    r"자습실|스터디룸|강의실|휴게실|사물함"
)
POSITIVE_RESULT_RE = re.compile(
    r"(?:성적|점수|등급|합격|입시\s*결과).{0,28}"
    r"(?:향상|상승|개선|달성|보장|성공|증명)|"
    r"(?:향상|상승|개선|달성|보장).{0,28}(?:성적|점수|등급|합격)|"
    r"(?:100\s*%|전원\s*합격|무조건\s*합격)",
    re.IGNORECASE,
)
RESULT_NEGATION_RE = re.compile(
    r"보장하지\s*않|단정하지\s*않|보장할\s*수\s*없|"
    r"단정하기\s*보다|확정하기\s*보다|정보가\s*아니|성과를\s*뜻하지\s*않|"
    r"보장하는\s*표현보다|향상을\s*단정할\s*수는\s*없|상승을\s*단정하는\s*문구보다|"
    r"실제\s*(?:수강\s*)?후기나\s*특정\s*성적\s*결과가\s*아니|"
    r"결과를\s*뜻하지\s*않|확정하지\s*않|"
    r"(?:점수|정답률)만으로.{0,24}(?:판단|평가).{0,12}어렵|"
    r"성적\s*변화에\s*대한\s*단정적인\s*표현보다"
)
FORBIDDEN_SCHEMA_TYPES = {"Product", "Review", "AggregateRating"}
FORBIDDEN_SCHEMA_KEYS = {
    "review", "reviewRating", "aggregateRating", "ratingValue",
    "ratingCount", "reviewCount", "bestRating", "worstRating",
}
REQUIRED_SCHEMA_TYPES = {
    "WebPage",
    "ImageObject",
    "EducationalOrganization",
    "LocalBusiness",
    "BreadcrumbList",
    "Article",
    "Service",
    "FAQPage",
    "ItemList",
    "CreativeWork",
}


@dataclass(frozen=True)
class SourceRow:
    locality: str
    display_locality: str
    values: dict[str, str]
    elementary_grades: tuple[str, ...]
    elementary_schools: tuple[str, ...]
    all_schools: tuple[str, ...]


@dataclass
class SourceModel:
    rows: dict[str, SourceRow]
    all_school_names: tuple[str, ...]
    errors: list[str]


def normalize_key(value: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value or "")).strip()


def unique(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = re.sub(r"\s+", " ", str(value or "")).strip(" ,·/|")
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def split_values(value: str) -> list[str]:
    return unique(re.split(r"[,，]", value or ""))


def split_school_values(value: str) -> list[str]:
    return unique(re.split(r"[,，.;；/|]+", value or ""))


def public_school_names(values: Iterable[str]) -> list[str]:
    """Mirror the generator's conservative public-school splitting contract."""

    result: list[str] = []
    for raw in values:
        parts = [part for part in re.split(r"\s+", raw.strip()) if part]
        if len(parts) > 1 and all(SCHOOL_NAME_RE.fullmatch(part) for part in parts):
            result.extend(parts)
        else:
            result.append(raw)
    return unique(result)


def is_elementary_school(value: str) -> bool:
    return bool(re.search(r"(?:초등학교|초)$", value))


def attributes(tag: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for match in ATTR_RE.finditer(tag):
        result[match.group("name").lower()] = html.unescape(
            match.group("double") if match.group("double") is not None else match.group("single")
        )
    return result


def plain_text(fragment: str) -> str:
    without_code = SCRIPT_STYLE_RE.sub(" ", fragment)
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", without_code))).strip()


def find_element(source: str, tag: str, *, element_id: str | None = None, class_name: str | None = None) -> tuple[str, str] | None:
    pattern = re.compile(
        rf"<{re.escape(tag)}\b(?P<attrs>[^>]*)>(?P<body>.*?)</{re.escape(tag)}>",
        re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(source):
        attrs = attributes("<x " + match.group("attrs") + ">")
        classes = set(attrs.get("class", "").split())
        if element_id is not None and attrs.get("id") != element_id:
            continue
        if class_name is not None and class_name not in classes:
            continue
        return match.group(0), match.group("body")
    return None


def meta_value(source: str, attr_name: str, attr_value: str) -> str:
    for match in re.finditer(r"<meta\b[^>]*>", source, re.IGNORECASE | re.DOTALL):
        attrs = attributes(match.group(0))
        if attrs.get(attr_name.lower()) == attr_value:
            return attrs.get("content", "").strip()
    return ""


def link_value(source: str, rel: str) -> str:
    for match in re.finditer(r"<link\b[^>]*>", source, re.IGNORECASE | re.DOTALL):
        attrs = attributes(match.group(0))
        if rel in attrs.get("rel", "").split():
            return attrs.get("href", "").strip()
    return ""


def document_title(source: str) -> str:
    match = re.search(r"<title\b[^>]*>(.*?)</title>", source, re.IGNORECASE | re.DOTALL)
    return plain_text(match.group(1)) if match else ""


def h1_values(source: str) -> list[str]:
    return [plain_text(value) for value in re.findall(r"<h1\b[^>]*>(.*?)</h1>", source, re.IGNORECASE | re.DOTALL)]


def encoded_url(*parts: str) -> str:
    path = "/".join(quote(part, safe="") for part in parts)
    return f"{SITE_URL}/{path}/"


def parse_json_ld(source: str) -> tuple[list[dict[str, Any]], list[str]]:
    scripts = JSON_LD_RE.findall(source)
    errors: list[str] = []
    if len(scripts) != 1:
        errors.append(f"application/ld+json scripts={len(scripts)} expected=1")
    nodes: list[dict[str, Any]] = []
    for script in scripts:
        try:
            value = json.loads(html.unescape(script))
        except (json.JSONDecodeError, TypeError) as exc:
            errors.append(f"invalid JSON-LD: {exc}")
            continue
        graph = value.get("@graph", []) if isinstance(value, dict) else []
        if not isinstance(graph, list):
            errors.append("JSON-LD @graph is not a list")
            continue
        nodes.extend(node for node in graph if isinstance(node, dict))
    return nodes, errors


def node_types(node: dict[str, Any]) -> set[str]:
    kinds = node.get("@type", [])
    if isinstance(kinds, str):
        return {kinds}
    return {str(item) for item in kinds if isinstance(item, str)} if isinstance(kinds, list) else set()


def find_nodes(nodes: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    return [node for node in nodes if kind in node_types(node)]


def schema_types(nodes: list[dict[str, Any]]) -> set[str]:
    result: set[str] = set()
    for node in nodes:
        result.update(node_types(node))
    return result


def json_object_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    stack: list[Any] = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            keys.update(str(key) for key in current)
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)
    return keys


def visible_faq(source: str) -> list[tuple[str, str]]:
    section = find_element(source, "section", element_id="faq-section")
    if not section:
        return []
    result: list[tuple[str, str]] = []
    for block in DETAIL_RE.findall(section[1]):
        question_match = SUMMARY_RE.search(block)
        answer_match = PARAGRAPH_RE.search(block)
        if question_match and answer_match:
            result.append((plain_text(question_match.group(1)), plain_text(answer_match.group(1))))
    return result


def schema_faq(nodes: list[dict[str, Any]]) -> list[tuple[str, str]]:
    faq_nodes = find_nodes(nodes, "FAQPage")
    if len(faq_nodes) != 1:
        return []
    result: list[tuple[str, str]] = []
    for item in faq_nodes[0].get("mainEntity", []):
        if not isinstance(item, dict):
            continue
        answer = item.get("acceptedAnswer", {})
        if not isinstance(answer, dict):
            continue
        result.append((plain_text(str(item.get("name", ""))), plain_text(str(answer.get("text", "")))))
    return result


def grade_tokens(value: Any) -> list[str]:
    if isinstance(value, list):
        source = " ".join(str(item) for item in value)
    else:
        source = str(value or "")
    return unique(
        GRADE_PREFIX[match.group("level")] + match.group("number")
        for match in GRADE_RE.finditer(source)
    )


def schema_school_mentions(node: dict[str, Any]) -> list[str]:
    result: list[str] = []
    mentions = node.get("mentions", [])
    if not isinstance(mentions, list):
        return result
    for item in mentions:
        if not isinstance(item, dict) or "Organization" not in node_types(item):
            continue
        name = re.sub(r"\s+", " ", str(item.get("name", ""))).strip()
        if name:
            result.append(name)
    return unique(result)


def expected_elementary_grades(row: dict[str, str]) -> list[str]:
    english_grades = split_values(row.get("가능학년\n(영어)", ""))
    math_grades = set(split_values(row.get("가능학년\n(수학)", "")))
    return [
        grade for grade in english_grades
        if grade in math_grades and ELEMENTARY_GRADE_RE.fullmatch(grade)
    ]


def expected_elementary_schools(row: dict[str, str]) -> list[str]:
    scope_values = {
        "지역내 모든 초등학교 가능", "지역 내 모든 초등학교 가능",
        "초등학교",
    }
    raw = [
        value
        for value in split_school_values(row.get("타깃학교\n(초)", ""))
        if value not in scope_values
    ]
    return public_school_names(raw)


def row_all_schools(row: dict[str, str]) -> list[str]:
    values: list[str] = []
    for field in ("타깃학교\n(초)", "타깃학교\n(중)", "타깃학교\n(고)"):
        values.extend(split_school_values(row.get(field, "")))
    excluded = {
        "초등학교", "중학교", "고등학교",
        "지역내 모든 초등학교 가능", "지역 내 모든 초등학교 가능",
        "지역내 모든 중학교 가능", "지역 내 모든 중학교 가능",
        "지역내 모든 고등학교 가능", "지역 내 모든 고등학교 가능",
        "오현초호매실중",
    }
    return public_school_names(value for value in values if value not in excluded)


def load_source_model(path: Path) -> SourceModel:
    errors: list[str] = []
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = [
                {str(key): str(value or "").strip() for key, value in row.items()}
                for row in reader
            ]
            headers = set(reader.fieldnames or [])
    except (OSError, UnicodeError, csv.Error) as exc:
        return SourceModel({}, (), [f"center-csv:{path}:{exc}"])

    required = {
        "근처 수업가능 동네",
        "센터명",
        "센터 주소",
        "교육지원청 등록번호",
        "시or구",
        "지역",
        "가능학년\n(영어)",
        "가능학년\n(수학)",
        "타깃학교\n(초)",
        "타깃학교\n(중)",
        "타깃학교\n(고)",
    }
    if not required <= headers:
        errors.append(f"center-csv-headers:missing={sorted(required - headers)}")
    if len(rows) != EXPECTED_PAGE_COUNT:
        errors.append(f"center-csv-rows:expected={EXPECTED_PAGE_COUNT}:actual={len(rows)}")

    existing: dict[str, str] = {}
    national_root = ROOT / "전국센터"
    if national_root.is_dir():
        for candidate in national_root.iterdir():
            if candidate.is_dir() and (candidate / "고등수학학원" / "index.html").is_file():
                existing[normalize_key(candidate.name)] = candidate.name
    aliases = {
        normalize_key("부천 상동"): "부천상동",
        normalize_key("당진 읍내동"): "당진읍내동",
        normalize_key("전주 장동"): "전주장동",
    }

    mapped: dict[str, SourceRow] = {}
    all_schools: list[str] = []
    for row in rows:
        display = row.get("근처 수업가능 동네", "")
        locality = existing.get(normalize_key(display)) or aliases.get(normalize_key(display))
        if not locality:
            errors.append(f"center-locality-map:{display!r}")
            continue
        elementary_grades = expected_elementary_grades(row)
        elementary_schools = expected_elementary_schools(row)
        invalid_elementary = [name for name in elementary_schools if not is_elementary_school(name)]
        if invalid_elementary:
            errors.append(f"center-elementary-school-invalid:{display}:{invalid_elementary}")
        row_schools = row_all_schools(row)
        all_schools.extend(row_schools)
        if locality in mapped:
            errors.append(f"center-locality-duplicate:{locality}")
            continue
        mapped[locality] = SourceRow(
            locality=locality,
            display_locality=display,
            values=row,
            elementary_grades=tuple(elementary_grades),
            elementary_schools=tuple(elementary_schools),
            all_schools=tuple(row_schools),
        )

    if len(mapped) != EXPECTED_PAGE_COUNT:
        errors.append(f"center-localities:expected={EXPECTED_PAGE_COUNT}:actual={len(mapped)}")
    return SourceModel(mapped, tuple(unique(all_schools)), errors)


def visible_grade_values(source: str) -> tuple[list[str], str]:
    center = find_element(source, "section", element_id="verified-center")
    if not center:
        return [], "verified-center missing"
    pattern = re.compile(
        rf"<dt\b[^>]*>\s*{re.escape(CATEGORY_LABEL)}\s*가능\s*학년\s*</dt>\s*"
        r"<dd\b[^>]*>(.*?)</dd>",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(center[1])
    if not match:
        return [], "grade row missing"
    value = plain_text(match.group(1))
    return grade_tokens(value), value


def visible_school_values(source: str) -> tuple[list[str], str]:
    center = find_element(source, "section", element_id="verified-center")
    if not center:
        return [], "verified-center missing"
    block = find_element(center[1], "div", class_name="verified-school-list")
    if not block:
        return [], plain_text(center[1])
    schools = [
        plain_text(value)
        for value in re.findall(r"<span\b[^>]*>(.*?)</span>", block[1], re.IGNORECASE | re.DOTALL)
    ]
    return public_school_names(unique(schools)), plain_text(block[1])


def section_data(article_markup: str) -> tuple[list[str], list[str], bool]:
    headings: list[str] = []
    ids: list[str] = []
    complete = True
    for match in PROSE_SECTION_RE.finditer(article_markup):
        attrs = attributes("<section " + match.group("attrs") + ">")
        if "subject-prose-section" not in set(attrs.get("class", "").split()):
            continue
        heading_matches = H2_RE.findall(match.group("body"))
        if len(heading_matches) != 1:
            complete = False
            continue
        ids.append(attrs.get("id", ""))
        headings.append(plain_text(heading_matches[0]))
    return headings, ids, complete


def sentence_count(value: str) -> int:
    return len([part for part in re.split(r"[.!?]+", value) if part.strip()])


def image_checks(source: str, expected_title: str, nodes: list[dict[str, Any]]) -> tuple[bool, str]:
    tags = IMG_RE.findall(source)
    hidden = [tag for tag in tags if re.sub(r"\s+", "", attributes(tag).get("style", "")).lower() == "display:none;"]
    errors: list[str] = []
    if len(hidden) != 1:
        errors.append(f"hidden-representative={len(hidden)}")
        representative_src = ""
    else:
        hidden_attrs = attributes(hidden[0])
        representative_src = hidden_attrs.get("src", "")
        alt = hidden_attrs.get("alt", "")
        if expected_title not in alt or "대표" not in alt:
            errors.append("representative-alt")
        if not local_asset_exists(representative_src):
            errors.append("representative-file")

    picture = find_element(source, "picture", class_name="local-responsive-picture")
    if not picture:
        errors.append("responsive-picture")
    else:
        source_match = re.search(r"<source\b[^>]*>", picture[1], re.IGNORECASE | re.DOTALL)
        image_match = IMG_RE.search(picture[1])
        if not source_match or not image_match:
            errors.append("responsive-picture-content")
        else:
            source_attrs = attributes(source_match.group(0))
            image_attrs = attributes(image_match.group(0))
            if not local_asset_exists(source_attrs.get("srcset", "").split()[0]):
                errors.append("mobile-body-file")
            if not local_asset_exists(image_attrs.get("src", "")):
                errors.append("body-file")
            if image_attrs.get("loading") != "lazy" or image_attrs.get("decoding") != "async":
                errors.append("body-loading")
            if expected_title not in image_attrs.get("alt", "") or "본문" not in image_attrs.get("alt", ""):
                errors.append("body-alt")
            if not positive_dimensions(image_attrs):
                errors.append("body-dimensions")

    map_figure = find_element(source, "figure", class_name="location-card")
    if not map_figure:
        errors.append("map-figure")
    else:
        map_match = IMG_RE.search(map_figure[1])
        if not map_match:
            errors.append("map-image")
        else:
            map_attrs = attributes(map_match.group(0))
            if not local_asset_exists(map_attrs.get("src", "")):
                errors.append("map-file")
            if map_attrs.get("loading") != "lazy" or map_attrs.get("decoding") != "async":
                errors.append("map-loading")
            if expected_title not in map_attrs.get("alt", "") or "지도" not in map_attrs.get("alt", ""):
                errors.append("map-alt")
            if not positive_dimensions(map_attrs):
                errors.append("map-dimensions")

    image_nodes = find_nodes(nodes, "ImageObject")
    expected_absolute = SITE_URL + representative_src if representative_src.startswith("/") else representative_src
    if len(image_nodes) != 1 or image_nodes[0].get("contentUrl") != expected_absolute:
        errors.append("image-schema")
    return not errors, ", ".join(errors)


def positive_dimensions(attrs: dict[str, str]) -> bool:
    return attrs.get("width", "").isdigit() and int(attrs["width"]) > 0 and attrs.get("height", "").isdigit() and int(attrs["height"]) > 0


def local_asset_exists(value: str) -> bool:
    if not value or value.startswith(("http://", "https://", "data:")):
        return False
    clean_value = value.split("?", 1)[0].split("#", 1)[0]
    if clean_value.startswith("/"):
        path = ROOT / clean_value.lstrip("/")
    else:
        path = ROOT / clean_value.lstrip("./")
    return path.is_file()


def toc_checks(source: str, headings: list[str], ids: list[str], article_node: dict[str, Any] | None) -> tuple[bool, str]:
    errors: list[str] = []
    blocks = TOC_RE.findall(source)
    if source.count("<!-- subject-page-anchor-toc:start -->") != 1 or source.count("<!-- subject-page-anchor-toc:end -->") != 1:
        errors.append("toc-markers")
    if len(blocks) != 1:
        errors.append(f"toc-blocks={len(blocks)}")
        links: list[tuple[str, str]] = []
    else:
        links = [
            (match.group("target"), plain_text(match.group("label")))
            for match in TOC_LINK_RE.finditer(blocks[0])
        ]
    expected = list(zip(ids, headings))
    if len(expected) != 6 or links != expected:
        errors.append("toc-links-labels")
    all_ids = re.findall(r"\bid=[\"']([^\"']+)[\"']", source, re.IGNORECASE)
    if len(all_ids) != len(set(all_ids)):
        errors.append("duplicate-id")
    if any(all_ids.count(target) != 1 for target, _label in links):
        errors.append("toc-target-count")
    if article_node is None:
        errors.append("article-node")
    else:
        parts: list[tuple[str, str]] = []
        for item in article_node.get("hasPart", []):
            if not isinstance(item, dict):
                continue
            parts.append((urlsplit(str(item.get("url", ""))).fragment, plain_text(str(item.get("name", "")))))
        if parts != expected:
            errors.append("article-hasPart")
    toc_position = source.find('<nav class="local-section subject-page-toc"')
    article_position = source.find("subject-article")
    verified_position = source.find('id="verified-center"')
    if toc_position < 0 or article_position < 0 or not (verified_position < toc_position < article_position):
        errors.append("toc-placement")
    return not errors, ", ".join(errors)


def organization_school_sets(nodes: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    webpages = find_nodes(nodes, "WebPage")
    articles = find_nodes(nodes, "Article")
    webpage = schema_school_mentions(webpages[0]) if len(webpages) == 1 else []
    article = schema_school_mentions(articles[0]) if len(articles) == 1 else []
    return webpage, article


def schema_grade_checks(nodes: list[dict[str, Any]], expected: list[str]) -> tuple[bool, str]:
    organizations = find_nodes(nodes, "EducationalOrganization")
    services = find_nodes(nodes, "Service")
    errors: list[str] = []
    if len(organizations) != 1 or len(services) != 1:
        return False, f"organizations={len(organizations)} services={len(services)}"
    actual_org = grade_tokens(organizations[0].get("educationalLevel", []))
    audience = services[0].get("audience")
    actual_service = grade_tokens(audience.get("audienceType", "")) if isinstance(audience, dict) else []
    if actual_org != expected:
        errors.append(f"organization={actual_org} expected={expected}")
    if actual_service != expected:
        errors.append(f"service={actual_service} expected={expected}")
    schema_grades = grade_tokens(json.dumps(nodes, ensure_ascii=False))
    if any(not ELEMENTARY_GRADE_RE.fullmatch(value) for value in schema_grades):
        errors.append(f"cross-level={schema_grades}")
    return not errors, ", ".join(errors)


def result_claims(value: str) -> list[str]:
    results: list[str] = []
    for match in POSITIVE_RESULT_RE.finditer(value):
        context = value[max(0, match.start() - 55): match.end() + 55]
        if not RESULT_NEGATION_RE.search(context):
            results.append(match.group(0))
    return results


def known_school_regex(names: Iterable[str]) -> re.Pattern[str] | None:
    # Two-character abbreviations such as "남고" can also be ordinary Korean
    # predicates ("기록이 남고"). Exact verified-card and schema checks still
    # retain those values; the free-prose contamination scan uses 3+ chars.
    escaped = [
        re.escape(name)
        for name in sorted(set(names), key=len, reverse=True)
        if name and len(name) >= 3
    ]
    if not escaped:
        return None
    return re.compile(
        r"(?<![가-힣A-Za-z0-9])(?:" + "|".join(escaped) + r")(?![가-힣A-Za-z0-9])",
        re.IGNORECASE,
    )


def mask_article(article: str, row: SourceRow, all_school_re: re.Pattern[str] | None) -> set[str]:
    text = unicodedata.normalize("NFKC", plain_text(article)).lower()
    replacements: list[tuple[str, str]] = []
    for value in unique([row.locality, row.display_locality]):
        replacements.append((value.lower(), " LOCALMASK "))
    for field in ("센터명", "교육지원청명칭", "교육지원청 등록번호", "센터 주소"):
        value = row.values.get(field, "").strip()
        if value:
            replacements.append((value.lower(), " CENTERMASK "))
    for field in ("지역", "시or구"):
        value = row.values.get(field, "").strip()
        if value:
            replacements.append((value.lower(), " REGIONMASK "))
    for school in row.all_schools:
        replacements.append((school.lower(), " SCHOOLMASK "))
    for value, token in sorted(replacements, key=lambda item: len(item[0]), reverse=True):
        text = text.replace(value, token)
    if all_school_re:
        text = all_school_re.sub(" SCHOOLMASK ", text)
    text = re.sub(r"[초중고][1-6]", " GRADEMASK ", text)
    text = re.sub(r"https?://\S+", " URLMASK ", text)
    text = re.sub(r"\b\d{2,4}[-.)/\s]\d[\d()./\s-]{2,}\b", " NUMBERMASK ", text)
    text = re.sub(r"\d+", " NUMBERMASK ", text)
    tokens = re.findall(r"[가-힣a-z]+|[A-Z]+MASK", text)
    if len(tokens) < 5:
        return set()
    return {" ".join(tokens[index:index + 5]) for index in range(len(tokens) - 4)}


def page_similarity(records: list[dict[str, Any]]) -> tuple[list[float], int]:
    best = [0.0] * len(records)
    pairs_over = 0
    for left_index, left_record in enumerate(records):
        left = left_record["shingles"]
        for right_index in range(left_index + 1, len(records)):
            right = records[right_index]["shingles"]
            intersection = len(left & right)
            union = len(left) + len(right) - intersection
            similarity = intersection / union if union else 1.0
            if similarity >= SIMILARITY_LIMIT:
                pairs_over += 1
            best[left_index] = max(best[left_index], similarity)
            best[right_index] = max(best[right_index], similarity)
    return best, pairs_over


def initial_record(
    path: Path,
    source_row: SourceRow | None,
    sitemap_urls: set[str],
    all_school_re: re.Pattern[str] | None,
) -> dict[str, Any]:
    source = path.read_text(encoding="utf-8")
    locality = path.parent.name
    expected_title = f"{locality} {CATEGORY_LABEL}"
    expected_url = encoded_url("과목별학원", CATEGORY_SLUG, locality)
    criteria: dict[str, bool] = {name: False for name in WEIGHTS}
    details: dict[str, str] = {}

    title = document_title(source)
    h1s = h1_values(source)
    meta = meta_value(source, "name", "description")
    meta_ok = (
        title == f"{expected_title} | {SITE_NAME}"
        and h1s == [expected_title]
        and 70 <= len(meta) <= 110
        and meta.startswith(expected_title)
        and link_value(source, "canonical") == expected_url
        and meta_value(source, "name", "robots").replace(" ", "") in {"index,follow", "follow,index"}
        and meta_value(source, "property", "og:type") == "article"
        and meta_value(source, "property", "og:url") == expected_url
        and meta_value(source, "property", "og:title") == title
        and meta_value(source, "property", "og:description") == meta
        and meta_value(source, "name", "twitter:title") == title
        and meta_value(source, "name", "twitter:description") == meta
        and expected_url in sitemap_urls
    )
    criteria["technical_meta_identity"] = meta_ok
    if not meta_ok:
        details["technical_meta_identity"] = f"title={title!r} h1={h1s!r} meta_chars={len(meta)} canonical={link_value(source, 'canonical')!r} sitemap={expected_url in sitemap_urls}"

    nodes, json_errors = parse_json_ld(source)
    types = schema_types(nodes)
    schema_keys = json_object_keys(nodes)
    webpages = find_nodes(nodes, "WebPage")
    articles = find_nodes(nodes, "Article")
    images = find_nodes(nodes, "ImageObject")
    article_node = articles[0] if len(articles) == 1 else None
    schema_ok = (
        not json_errors
        and REQUIRED_SCHEMA_TYPES <= types
        and not (FORBIDDEN_SCHEMA_TYPES & types)
        and not (FORBIDDEN_SCHEMA_KEYS & schema_keys)
        and len(webpages) == 1
        and len(articles) == 1
        and len(images) == 1
        and webpages[0].get("url") == expected_url
        and webpages[0].get("name") == title
        and articles[0].get("headline") == expected_title
        and str(articles[0].get("mainEntityOfPage", {}).get("@id", "")) == expected_url + "#webpage"
    )
    criteria["technical_schema"] = schema_ok
    if not schema_ok:
        details["technical_schema"] = (
            f"json_errors={json_errors} missing_types={sorted(REQUIRED_SCHEMA_TYPES - types)} "
            f"forbidden_types={sorted(FORBIDDEN_SCHEMA_TYPES & types)} "
            f"forbidden_keys={sorted(FORBIDDEN_SCHEMA_KEYS & schema_keys)} "
            f"webpage={len(webpages)} article={len(articles)}"
        )

    screen_faq = visible_faq(source)
    structured_faq = schema_faq(nodes)
    faq_sync = len(screen_faq) == 4 and screen_faq == structured_faq
    criteria["technical_faq_sync"] = faq_sync
    if not faq_sync:
        details["technical_faq_sync"] = f"visible={len(screen_faq)} schema={len(structured_faq)} equal={screen_faq == structured_faq}"

    image_ok, image_detail = image_checks(source, expected_title, nodes)
    criteria["technical_images"] = image_ok
    if not image_ok:
        details["technical_images"] = image_detail

    article_match = ARTICLE_RE.search(source)
    article_markup = article_match.group(1) if article_match else ""
    article_text = plain_text(article_markup)
    article_chars = len(re.sub(r"\s+", "", article_text))
    headings, section_ids, sections_complete = section_data(article_markup)
    toc_ok, toc_detail = toc_checks(source, headings, section_ids, article_node)
    criteria["technical_toc"] = toc_ok
    if not toc_ok:
        details["technical_toc"] = toc_detail

    criteria["content_body_length"] = 2000 <= article_chars <= 7500
    if not criteria["content_body_length"]:
        details["content_body_length"] = f"nonspace_chars={article_chars} expected=2000..7500"
    expected_ids = [f"section-{index}" for index in range(1, 7)]
    criteria["content_h2_six"] = sections_complete and len(headings) == 6 and section_ids == expected_ids
    if not criteria["content_h2_six"]:
        details["content_h2_six"] = f"headings={len(headings)} ids={section_ids} complete={sections_complete}"
    criteria["content_faq_four"] = len(screen_faq) == 4
    if len(screen_faq) != 4:
        details["content_faq_four"] = f"visible_faq={len(screen_faq)}"

    scenarios = [plain_text(block) for block in REVIEW_CARD_RE.findall(source)]
    disclaimer_ok = bool(re.search(r"실제\s*수강\s*후기.*아니|상담.*상황.*예시", plain_text(source), re.DOTALL))
    criteria["content_consultation_example"] = (
        len(scenarios) == 1
        and all(30 <= len(value) <= 500 for value in scenarios)
        and disclaimer_ok
    )
    if not criteria["content_consultation_example"]:
        details["content_consultation_example"] = f"cards={len(scenarios)} lengths={[len(value) for value in scenarios]} disclaimer={disclaimer_ok}"

    intro = find_element(article_markup, "div", class_name="subject-article-intro")
    opening = plain_text(intro[1]) if intro else article_text[:700]
    criteria["content_reader_problem_action"] = (
        locality in opening
        and bool(READER_RE.search(opening))
        and bool(PROBLEM_RE.search(opening))
        and bool(ACTION_RE.search(opening))
    )
    if not criteria["content_reader_problem_action"]:
        details["content_reader_problem_action"] = f"local={locality in opening} reader={bool(READER_RE.search(opening))} problem={bool(PROBLEM_RE.search(opening))} action={bool(ACTION_RE.search(opening))}"

    natural_h2 = (
        len(headings) == 6
        and len(set(headings)) == 6
        and all(4 <= len(value) <= 78 for value in headings)
        and not any(AUTHORING_RE.search(value) for value in headings)
    )
    criteria["content_natural_h2"] = natural_h2
    if not natural_h2:
        details["content_natural_h2"] = f"headings={headings}"
    concise = bool(screen_faq) and all(
        8 <= len(question) <= 110
        and 20 <= len(answer) <= 235
        and sentence_count(answer) <= 3
        for question, answer in screen_faq
    )
    criteria["content_faq_concise"] = concise
    if not concise:
        details["content_faq_concise"] = f"lengths={[(len(q), len(a), sentence_count(a)) for q, a in screen_faq]}"

    if source_row is None:
        details["factual_safe_claims"] = "authoritative row missing"
        article_hash = hashlib.sha256(article_text.encode("utf-8")).hexdigest()
        return {
            "locality": locality,
            "path": path.relative_to(ROOT).as_posix(),
            "criteria": criteria,
            "details": details,
            "article_hash": article_hash,
            "shingles": set(),
            "article_chars": article_chars,
            "title": title,
            "meta": meta,
        }

    expected_grades = list(source_row.elementary_grades)
    visible_grades, visible_grade_text = visible_grade_values(source)
    visible_grade_ok = visible_grades == expected_grades and (
        bool(expected_grades) or (not visible_grades and bool(re.search(r"상담|확인", visible_grade_text)))
    )
    criteria["factual_elementary_grades_visible"] = visible_grade_ok
    if not visible_grade_ok:
        details["factual_elementary_grades_visible"] = f"actual={visible_grades} expected={expected_grades} raw={visible_grade_text!r}"

    grade_schema_ok, grade_schema_detail = schema_grade_checks(nodes, expected_grades)
    criteria["factual_elementary_grades_schema"] = grade_schema_ok
    if not grade_schema_ok:
        details["factual_elementary_grades_schema"] = grade_schema_detail

    expected_schools = list(source_row.elementary_schools)
    visible_schools, visible_school_text = visible_school_values(source)
    visible_school_ok = visible_schools == expected_schools and (
        bool(expected_schools) or bool(re.search(r"학교.*(?:없|임의|확인)|특정\s*학교", visible_school_text))
    )
    criteria["factual_elementary_schools_visible"] = visible_school_ok
    if not visible_school_ok:
        details["factual_elementary_schools_visible"] = f"actual={visible_schools} expected={expected_schools}"

    webpage_schools, article_schools = organization_school_sets(nodes)
    school_schema_ok = webpage_schools == expected_schools and article_schools == expected_schools
    criteria["factual_elementary_schools_schema"] = school_schema_ok
    if not school_schema_ok:
        details["factual_elementary_schools_schema"] = f"webpage={webpage_schools} article={article_schools} expected={expected_schools}"

    main = find_element(source, "main")
    main_text = plain_text(main[1]) if main else plain_text(source)
    schema_text = json.dumps(nodes, ensure_ascii=False)
    known_mentions = set(all_school_re.findall(main_text + " " + schema_text)) if all_school_re else set()
    unexpected_schools = sorted(known_mentions - set(expected_schools))
    relevant_grades = grade_tokens(
        article_text
        + " "
        + " ".join(q + " " + a for q, a in screen_faq)
        + " "
        + " ".join(scenarios)
        + " "
        + visible_grade_text
        + " "
        + schema_text
    )
    unexpected_grades = [grade for grade in relevant_grades if grade not in expected_grades]
    cross_level = [grade for grade in relevant_grades if not ELEMENTARY_GRADE_RE.fullmatch(grade)]
    all_declared_elementary = all(
        is_elementary_school(name)
        for name in visible_schools + webpage_schools + article_schools
    )
    criteria["factual_no_cross_level"] = (
        not unexpected_schools
        and not unexpected_grades
        and not cross_level
        and all_declared_elementary
    )
    if not criteria["factual_no_cross_level"]:
        details["factual_no_cross_level"] = (
            f"unexpected_schools={unexpected_schools[:10]} "
            f"unexpected_grades={unexpected_grades} cross_level_grades={cross_level} "
            f"declared_elementary_only={all_declared_elementary}"
        )

    fact_scope = " ".join(
        [article_text, *[q + " " + a for q, a in screen_faq], *scenarios]
    )
    operations = unique(match.group(0) for match in UNVERIFIED_OPERATION_RE.finditer(fact_scope))
    claims = result_claims(fact_scope)
    authoring = unique(match.group(0) for match in AUTHORING_RE.finditer(fact_scope))
    organizations = find_nodes(nodes, "EducationalOrganization")
    organization_fact_ok = False
    if len(organizations) == 1:
        organization = organizations[0]
        address = organization.get("address", {})
        organization_fact_ok = (
            organization.get("name") == source_row.values.get("센터명", "")
            and isinstance(address, dict)
            and address.get("streetAddress") == source_row.values.get("센터 주소", "")
        )
    criteria["factual_safe_claims"] = not operations and not claims and not authoring and organization_fact_ok
    if not criteria["factual_safe_claims"]:
        details["factual_safe_claims"] = f"operations={operations[:5]} claims={claims[:5]} authoring={authoring[:5]} organization={organization_fact_ok}"

    normalized_article = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", article_text)).strip()
    return {
        "locality": locality,
        "path": path.relative_to(ROOT).as_posix(),
        "criteria": criteria,
        "details": details,
        "article_hash": hashlib.sha256(normalized_article.encode("utf-8")).hexdigest(),
        "shingles": mask_article(article_markup, source_row, all_school_re),
        "article_chars": article_chars,
        "title": title,
        "meta": meta,
    }


def read_sitemap_urls() -> tuple[set[str], str | None]:
    path = ROOT / "sitemap.xml"
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return set(), f"sitemap:{exc}"
    return set(html.unescape(value.strip()) for value in re.findall(r"<loc>(.*?)</loc>", source, re.DOTALL)), None


def build_report(center_csv: Path) -> dict[str, Any]:
    source_model = load_source_model(center_csv)
    sitemap_urls, sitemap_error = read_sitemap_urls()
    pages = sorted(CATEGORY_ROOT.glob("*/index.html")) if CATEGORY_ROOT.is_dir() else []
    actual_localities = {page.parent.name for page in pages}
    expected_localities = set(source_model.rows)
    collection_errors = list(source_model.errors)
    if sitemap_error:
        collection_errors.append(sitemap_error)
    if len(pages) != EXPECTED_PAGE_COUNT:
        collection_errors.append(f"page-count:expected={EXPECTED_PAGE_COUNT}:actual={len(pages)}")
    missing = sorted(expected_localities - actual_localities)
    extra = sorted(actual_localities - expected_localities)
    if missing or extra:
        collection_errors.append(f"locality-set:missing={missing[:10]} extra={extra[:10]}")

    all_school_re = known_school_regex(source_model.all_school_names)
    records = [
        initial_record(page, source_model.rows.get(page.parent.name), sitemap_urls, all_school_re)
        for page in pages
    ]

    article_hashes = Counter(record["article_hash"] for record in records)
    title_counts = Counter(record["title"] for record in records)
    meta_counts = Counter(record["meta"] for record in records)
    similarities, pairs_over = page_similarity(records)
    for record, similarity in zip(records, similarities):
        criteria = record["criteria"]
        exact_unique = article_hashes[record["article_hash"]] == 1
        similarity_unique = similarity < SIMILARITY_LIMIT
        criteria["uniqueness_exact"] = exact_unique
        criteria["uniqueness_similarity"] = similarity_unique
        if not exact_unique:
            record["details"]["uniqueness_exact"] = f"article_hash_count={article_hashes[record['article_hash']]}"
        if not similarity_unique:
            record["details"]["uniqueness_similarity"] = f"best_masked_5shingle={similarity:.4f} limit<{SIMILARITY_LIMIT}"
        if title_counts[record["title"]] != 1 or meta_counts[record["meta"]] != 1:
            criteria["technical_meta_identity"] = False
            record["details"]["technical_meta_identity"] = (
                record["details"].get("technical_meta_identity", "")
                + f" duplicate_title={title_counts[record['title']]} duplicate_meta={meta_counts[record['meta']]}"
            ).strip()
        record["best_similarity"] = round(similarity, 4)
        record["group_scores"] = {
            group: sum(WEIGHTS[name] for name in names if criteria[name])
            for group, names in GROUPS.items()
        }
        record["score"] = sum(record["group_scores"].values())

    issue_counts: Counter[str] = Counter()
    issue_examples: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    hard_errors: list[str] = list(collection_errors)
    scores: list[int] = []
    for record in records:
        score = int(record["score"])
        scores.append(score)
        for criterion, passed in record["criteria"].items():
            if passed:
                continue
            issue_counts[criterion] += 1
            if len(issue_examples[criterion]) < 5:
                issue_examples[criterion].append(
                    {
                        "path": str(record["path"]),
                        "detail": str(record["details"].get(criterion, "")),
                    }
                )
            if criterion.startswith(("technical_", "factual_", "uniqueness_")):
                hard_errors.append(f"{criterion}:{record['path']}")
        if score < MIN_PAGE_SCORE:
            hard_errors.append(f"score-min:{record['path']}:{score}")

    mean_score = round(statistics.mean(scores), 2) if scores else 0.0
    if mean_score < MIN_MEAN_SCORE:
        hard_errors.append(f"score-mean:{mean_score}:required={MIN_MEAN_SCORE}")
    if pairs_over:
        hard_errors.append(f"similarity-pairs-at-or-above-{SIMILARITY_LIMIT}:{pairs_over}")
    duplicate_pages = sum(count for count in article_hashes.values() if count > 1)
    if duplicate_pages:
        hard_errors.append(f"exact-duplicate-pages:{duplicate_pages}")

    worst = sorted(
        records,
        key=lambda item: (int(item["score"]), -float(item["best_similarity"]), str(item["locality"])),
    )[:15]
    return {
        "site": SITE_NAME,
        "scope": f"과목별학원/{CATEGORY_SLUG}/*/index.html",
        "score_type": "transparent content and release-quality score; not a search ranking prediction",
        "score_warning_ko": "이 점수는 검색순위 예측이나 네이버 노출 보장이 아닙니다.",
        "weights": WEIGHTS,
        "group_totals": GROUP_TOTALS,
        "hard_gates": {
            "exact_page_count": EXPECTED_PAGE_COUNT,
            "minimum_page_score": MIN_PAGE_SCORE,
            "minimum_collection_mean": MIN_MEAN_SCORE,
            "technical_factual_uniqueness_must_all_pass": True,
            "exact_duplicate_pages": 0,
            "masked_5shingle_pair_similarity": f"<{SIMILARITY_LIMIT}",
        },
        "source": {
            "center_csv": str(center_csv.resolve()),
            "rows": len(source_model.rows),
            "errors": source_model.errors,
        },
        "strict_pass": not hard_errors,
        "strict_error_count": len(hard_errors),
        "strict_errors": hard_errors[:200],
        "collection": {
            "pages": len(records),
            "expected_pages": EXPECTED_PAGE_COUNT,
            "score_min": min(scores) if scores else 0,
            "score_mean": mean_score,
            "score_median": round(statistics.median(scores), 2) if scores else 0.0,
            "pages_below_90": sum(score < MIN_PAGE_SCORE for score in scores),
            "exact_duplicate_pages": duplicate_pages,
            "pairs_at_or_above_0_75": pairs_over,
            "max_masked_5shingle_similarity": round(max(similarities), 4) if similarities else 0.0,
            "unique_titles": len(title_counts),
            "unique_meta_descriptions": len(meta_counts),
        },
        "criteria_pass_ratio": {
            name: round(sum(bool(record["criteria"][name]) for record in records) / len(records), 4)
            if records else 0.0
            for name in WEIGHTS
        },
        "issue_counts": dict(sorted(issue_counts.items())),
        "issue_examples": dict(sorted(issue_examples.items())),
        "worst_pages": [
            {
                "path": record["path"],
                "score": record["score"],
                "group_scores": record["group_scores"],
                "best_similarity": record["best_similarity"],
                "failed": [name for name, passed in record["criteria"].items() if not passed],
            }
            for record in worst
        ],
    }


def human_summary(report: dict[str, Any]) -> str:
    collection = report["collection"]
    status = "PASS" if report["strict_pass"] else "FAIL"
    lines = [
        f"초등학생학원 엄격 채점: {status}",
        "※ 이 점수는 검색순위 예측이나 네이버 노출 보장이 아닙니다.",
        (
            f"pages={collection['pages']}/{collection['expected_pages']} "
            f"score min/mean/median={collection['score_min']}/"
            f"{collection['score_mean']}/{collection['score_median']}"
        ),
        (
            f"exact_duplicate_pages={collection['exact_duplicate_pages']} "
            f"pairs>=0.75={collection['pairs_at_or_above_0_75']} "
            f"max_masked_5shingle={collection['max_masked_5shingle_similarity']}"
        ),
        f"strict_errors={report['strict_error_count']}",
    ]
    if report["issue_counts"]:
        lines.append("issues=" + ", ".join(f"{name}:{count}" for name, count in report["issue_counts"].items()))
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "코칭학원.com 초등학생학원 371개 페이지를 100점 기준으로 채점합니다. "
            "점수는 검색순위 예측이 아닙니다."
        )
    )
    parser.add_argument(
        "--center-csv",
        type=Path,
        default=DEFAULT_CENTER_CSV,
        help="authoritative 센터정보 정리.csv path",
    )
    parser.add_argument("--json", action="store_true", dest="json_stdout", help="print the complete report as JSON")
    parser.add_argument("--json-out", type=Path, help="write the complete JSON report to this path")
    args = parser.parse_args()

    report = build_report(args.center_csv)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.json_stdout:
        print(rendered)
    else:
        print(human_summary(report))
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered + "\n", encoding="utf-8", newline="\n")
    return 0 if report["strict_pass"] else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
