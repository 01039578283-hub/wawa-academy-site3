from __future__ import annotations

"""Strict, read-only release audit for 코칭학원.com/전국센터.

The audit has two deliberately separate responsibilities:

* reconstruct the immutable nationwide URL collection from the 371-row source;
* reject content/schema changes that are not supported by the common-data CSVs.

It never writes a manifest or modifies HTML.  Source-specific exceptions (empty
fees/grades/schools, legacy compound school cells, and service-area localities)
are derived from the CSVs instead of being filled with invented facts.
"""

import argparse
import csv
import html
import json
import re
import statistics
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote, urlsplit
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
NATIONAL_ROOT = ROOT / "전국센터"
COMMON_ROOT = ROOT.parent / "참고자료" / "공통자료"
MAIN_CSV = COMMON_ROOT / "센터정보 정리.csv"
SCHOOL_CSV = COMMON_ROOT / "타깃학교.csv"
ORGANIZATION_CSV = COMMON_ROOT / "EducationalOrganization.csv"

BASE_URL = "https://xn--sp5b72l1taf0p.com"
ROOT_ORGANIZATION_ID = BASE_URL + "/#organization"
EXPECTED_SOURCE_ROWS = 371
EXPECTED_PHYSICAL_CENTERS = 188
EXPECTED_NATIONAL_PAGES = 2_617
EXPECTED_FACT_PAGES = 2_597
EXPECTED_SERVICE_LOCALITIES = 159
EXPECTED_SERVICE_PAGES = EXPECTED_SERVICE_LOCALITIES * 7

COURSE_SLUGS = (
    "초등영어학원",
    "초등수학학원",
    "중등영어학원",
    "중등수학학원",
    "고등영어학원",
    "고등수학학원",
)
COURSE_INFO = {
    "초등영어학원": ("초", "영어", "초등"),
    "초등수학학원": ("초", "수학", "초등"),
    "중등영어학원": ("중", "영어", "중등"),
    "중등수학학원": ("중", "수학", "중등"),
    "고등영어학원": ("고", "영어", "고등"),
    "고등수학학원": ("고", "수학", "고등"),
}

LOCALITY_FIELD = "근처 수업가능 동네"
REGION_FIELD = "지역"
DISTRICT_FIELD = "시or구"
CENTER_FIELD = "센터명"
FEE_FIELD = "센터 교습비"
OFFICE_FIELD = "교육지원청명칭"
REGISTRATION_FIELD = "교육지원청 등록번호"
ADDRESS_FIELD = "센터 주소"
LOCATION_GUIDE_FIELD = "위치안내"
SCHOOL_FIELDS = {
    "초등": "타깃학교\n(초)",
    "중등": "타깃학교\n(중)",
    "고등": "타깃학교\n(고)",
}
GRADE_FIELDS = {
    "국어": "가능학년\n(국어)",
    "영어": "가능학년\n(영어)",
    "수학": "가능학년\n(수학)",
    "과학": "가능학년\n(과학)",
    "사회": "가능학년\n(사회)",
}

EXPECTED_MAIN_HEADERS = {
    "근처 수업가능 동네",
    "동 영어",
    "지역",
    "지역 영어",
    "시or구",
    "시or구 영어",
    "센터명",
    "센터 교습비",
    "교육지원청명칭",
    "교육지원청 등록번호",
    "센터 주소",
    "위치안내",
    "타깃학교\n(초)",
    "타깃학교\n(중)",
    "타깃학교\n(고)",
    "가능학년\n(국어)",
    "가능학년\n(영어)",
    "가능학년\n(수학)",
    "가능학년\n(과학)",
    "가능학년\n(사회)",
}
EXPECTED_EMPTY_COUNTS = {
    FEE_FIELD: 2,
    LOCATION_GUIDE_FIELD: 118,
    SCHOOL_FIELDS["초등"]: 74,
    SCHOOL_FIELDS["중등"]: 53,
    SCHOOL_FIELDS["고등"]: 63,
    GRADE_FIELDS["국어"]: 65,
    GRADE_FIELDS["영어"]: 8,
    GRADE_FIELDS["수학"]: 13,
    GRADE_FIELDS["과학"]: 127,
    GRADE_FIELDS["사회"]: 193,
}
EXPECTED_PHYSICAL_GROUP_SIZES = Counter({1: 52, 2: 96, 3: 34, 4: 5, 5: 1})
EXPECTED_LEAF_GRADE_EMPTY = {
    ("영어", "초"): 8,
    ("영어", "중"): 8,
    ("영어", "고"): 9,
    ("수학", "초"): 13,
    ("수학", "중"): 13,
    ("수학", "고"): 17,
}

OFFICIAL_ADDRESS_REGIONS = {
    "서울": "서울특별시",
    "서울특별시": "서울특별시",
    "경기": "경기도",
    "경기도": "경기도",
    "인천": "인천광역시",
    "인천광역시": "인천광역시",
    "대전": "대전광역시",
    "대전광역시": "대전광역시",
    "충북": "충청북도",
    "충청북도": "충청북도",
    "충남": "충청남도",
    "충청남도": "충청남도",
    "세종특별자치시": "세종특별자치시",
    "대구": "대구광역시",
    "대구광역시": "대구광역시",
    "울산": "울산광역시",
    "울산광역시": "울산광역시",
    "부산": "부산광역시",
    "부산광역시": "부산광역시",
    "경남": "경상남도",
    "경상남도": "경상남도",
    "경북": "경상북도",
    "경상북도": "경상북도",
    "광주": "광주광역시",
    "광주광역시": "광주광역시",
    "전북": "전북특별자치도",
    "전북특별자치도": "전북특별자치도",
    "전남": "전라남도",
    "전라남도": "전라남도",
    "강원": "강원특별자치도",
    "강원특별자치도": "강원특별자치도",
    "제주": "제주특별자치도",
    "제주특별자치도": "제주특별자치도",
}

REQUIRED_FACT_TYPES = {
    "EducationalOrganization",
    "LocalBusiness",
    "WebPage",
    "Article",
    "Service",
    "FAQPage",
    "BreadcrumbList",
    "ItemList",
}
REQUIRED_HUB_TYPES = {"CollectionPage", "FAQPage", "BreadcrumbList", "ItemList"}

SCRIPT_STYLE_RE = re.compile(
    r"<(?:script|style|noscript|svg)\b.*?</(?:script|style|noscript|svg)>",
    re.I | re.S,
)
TAG_RE = re.compile(r"<[^>]+>")
ATTR_RE = re.compile(r"([:\w-]+)\s*=\s*([\"'])(.*?)\2", re.S)
JSON_LD_RE = re.compile(
    r"<script\b[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
    re.I | re.S,
)
VALID_GRADE_RE = re.compile(r"^(?:초[1-6]|중[1-3]|고[1-3])$")
GRADE_TOKEN_RE = re.compile(r"(?<![가-힣\d])([초중고][1-6])(?!\d)")
GENERIC_HIGH_SCHOOL_RE = re.compile(r"지역\s*내\s*모든\s*고등학교\s*가능")
FULL_SCHOOL_NAME_RE = re.compile(r"\S+(?:초등학교|중학교|고등학교|초|중|고)$")
TRUTHFUL_EMPTY_SCHOOL_RE = re.compile(
    r"(?:학교|학교명|학교 목록).{0,45}(?:자료에\s*없|제공되지\s*않|임의로\s*(?:넣|추가)하지\s*않|상담에서\s*확인)",
    re.S,
)
TRUTHFUL_EMPTY_GRADE_RE = re.compile(
    r"(?:학년\s*범위|가능\s*학년|개설\s*여부).{0,45}(?:상담|문의|확인)|"
    r"(?:상담|문의).{0,45}(?:학년\s*범위|가능\s*학년|개설\s*여부)",
    re.S,
)
OFF_LOCALITY_CUE_RE = re.compile(
    r"상담\s*권역|연결\s*상담|실제\s*(?:방문|상담)\s*(?:센터|장소|주소)|"
    r"(?:지역명|동네명).{0,30}다를\s*수|독립\s*센터를\s*뜻하지\s*않|"
    r"가까운\s*센터|인근\s*센터|상담\s*가능한\s*센터",
    re.S,
)
OFF_LOCALITY_HEADING_CUE_RE = re.compile(
    r"상담\s*권역|연결|가까운|인근|상담\s*가능|실제\s*(?:방문|상담)"
)
PLACEHOLDER_RE = re.compile(
    r"Lorem\s+ipsum|\bTODO\b|\bTBD\b|\{\{[^{}]+\}\}|\[\[[^\[\]]+\]\]",
    re.I,
)
OVERCLAIM_RE = re.compile(
    r"(?:성적|점수|실력).{0,18}(?:상승|향상|올리|오르)|"
    r"(?:상승|향상).{0,18}(?:성적|점수|실력)|"
    r"(?:성적|점수|합격|성과).{0,18}(?:보장|약속)",
    re.S,
)
UNNATURAL_RE = re.compile(
    r"점로\s*연결|점를\s|기록와|기록를|(?:초|고)이\s*포함|"
    r"센터정보에는|제공된\s*자료\s*기준\s*가능\s*학년"
)


class Findings:
    def __init__(self, sample_limit: int = 5) -> None:
        self.sample_limit = sample_limit
        self.counts: Counter[str] = Counter()
        self.samples: defaultdict[str, list[str]] = defaultdict(list)

    def add(self, code: str, location: str | Path, message: str) -> None:
        self.counts[code] += 1
        if len(self.samples[code]) >= self.sample_limit:
            return
        if isinstance(location, Path):
            try:
                label = location.relative_to(ROOT).as_posix()
            except ValueError:
                label = str(location)
        else:
            label = location
        self.samples[code].append(f"{label}: {message}")

    def compare_set(
        self, code: str, current: Iterable[str], expected: Iterable[str]
    ) -> None:
        current_set = set(current)
        expected_set = set(expected)
        missing = sorted(expected_set - current_set)
        extra = sorted(current_set - expected_set)
        if missing or extra:
            self.add(
                code,
                "collection",
                f"missing={len(missing)} extra={len(extra)} "
                f"missing_sample={missing[:3]!r} extra_sample={extra[:3]!r}",
            )

    def report(self) -> int:
        total = sum(self.counts.values())
        print(f"strict_errors={total}")
        print(f"strict_error_codes={len(self.counts)}")
        for code in sorted(self.counts):
            print(f"ERROR_COUNT {code}={self.counts[code]}")
            for sample in self.samples[code]:
                print(f"ERROR {code} {sample}")
        return 1 if total else 0


def normalized_space(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value or "")).strip()


def locality_key(value: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value or "")).strip()


def strip_tags(value: str) -> str:
    value = SCRIPT_STYLE_RE.sub(" ", value or "")
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", value))).strip()


def attrs(tag: str) -> dict[str, str]:
    return {
        match.group(1).lower(): html.unescape(match.group(3))
        for match in ATTR_RE.finditer(tag)
    }


def tag_texts(source: str, tag: str) -> list[str]:
    return [
        strip_tags(value)
        for value in re.findall(
            rf"<{re.escape(tag)}\b[^>]*>(.*?)</{re.escape(tag)}>",
            source,
            re.I | re.S,
        )
    ]


def meta_values(source: str, attribute: str, value: str) -> list[str]:
    result: list[str] = []
    for tag in re.findall(r"<meta\b[^>]*>", source, re.I):
        data = attrs(tag)
        if data.get(attribute, "").lower() == value.lower():
            result.append(data.get("content", "").strip())
    return result


def canonical_values(source: str) -> list[str]:
    result: list[str] = []
    for tag in re.findall(r"<link\b[^>]*>", source, re.I):
        data = attrs(tag)
        if "canonical" in data.get("rel", "").lower().split():
            result.append(data.get("href", "").strip())
    return result


def node_types(node: dict[str, Any]) -> set[str]:
    value = node.get("@type", [])
    if isinstance(value, str):
        return {value}
    if isinstance(value, list):
        return {str(item) for item in value}
    return set()


def graph_nodes(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict) and isinstance(value.get("@graph"), list):
        return [item for item in value["@graph"] if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def parse_jsonld(path: Path, source: str, findings: Findings) -> list[dict[str, Any]]:
    blocks = JSON_LD_RE.findall(source)
    if not blocks:
        findings.add("jsonld_missing", path, "no JSON-LD block")
        return []
    result: list[dict[str, Any]] = []
    for index, block in enumerate(blocks, start=1):
        try:
            result.extend(graph_nodes(json.loads(block)))
        except json.JSONDecodeError as exc:
            findings.add("jsonld_invalid", path, f"block={index} {exc}")
    identifiers = [
        str(node.get("@id"))
        for node in result
        if isinstance(node.get("@id"), str) and node.get("@id")
    ]
    if len(identifiers) != len(set(identifiers)):
        findings.add(
            "jsonld_duplicate_id",
            path,
            f"duplicates={len(identifiers) - len(set(identifiers))}",
        )
    return result


def recursive_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from recursive_dicts(item)
    elif isinstance(value, list):
        for item in value:
            yield from recursive_dicts(item)


def recursive_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from recursive_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from recursive_strings(item)


def reference_id(value: Any) -> str:
    return str(value.get("@id", "")) if isinstance(value, dict) else ""


def csv_parts(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"[,，]", value or "") if part.strip()]


def is_school_name(value: str) -> bool:
    """Accept the six exact source suffixes; notably, 중학교 is not 중등학교."""

    return bool(FULL_SCHOOL_NAME_RE.fullmatch(value.strip()))


def authoritative_school_values(value: str) -> list[str]:
    """Resolve known source forms without inventing a school.

    Source cells use commas, slashes, full stops, middle dots and newlines as
    delimiters.  Some compound cells use whitespace only; split those only
    when every token is itself a complete school name.  This matches the
    generator contract without treating free-form copy as a school list.
    """

    result: list[str] = []
    groups = [
        part.strip()
        for part in re.split(r"[,，/·.\r\n]+", value or "")
        if part.strip()
    ]
    for group in groups:
        if GENERIC_HIGH_SCHOOL_RE.fullmatch(group):
            continue
        tokens = group.split()
        if len(tokens) > 1 and all(is_school_name(item) for item in tokens):
            result.extend(tokens)
        else:
            result.append(group)
    return list(dict.fromkeys(result))


def school_columns(record: dict[str, str]) -> dict[str, list[str]]:
    return {
        level: authoritative_school_values(record.get(field, ""))
        for level, field in SCHOOL_FIELDS.items()
    }


def expected_school_values(record: dict[str, str], level: str | None) -> list[str]:
    values = school_columns(record)
    if level is not None:
        return values[level]
    result: list[str] = []
    for item in ("초등", "중등", "고등"):
        result.extend(values[item])
    return list(dict.fromkeys(result))


def grade_values(record: dict[str, str], subject: str) -> list[str]:
    return csv_parts(record.get(GRADE_FIELDS[subject], ""))


def physical_key(record: dict[str, str]) -> tuple[str, str, str]:
    return (
        normalized_space(record.get(CENTER_FIELD, "")),
        normalized_space(record.get(ADDRESS_FIELD, "")),
        normalized_space(record.get(REGISTRATION_FIELD, "")),
    )


def locality_stem(value: str) -> str:
    tokens = re.findall(r"[^\s]+", unicodedata.normalize("NFKC", value or "").strip())
    compact = locality_key(tokens[-1] if tokens else value)
    return re.sub(r"(?:국제도시|신도시|중앙|마을|지구|동|읍|면|리)$", "", compact)


def is_service_area_record(record: dict[str, str]) -> bool:
    stem = locality_stem(record.get(LOCALITY_FIELD, ""))
    if len(stem) < 2:
        return False
    physical = locality_key(
        f"{record.get(CENTER_FIELD, '')} {record.get(ADDRESS_FIELD, '')}"
    )
    return stem not in physical


def locality_without_district_prefix(record: dict[str, str]) -> str:
    locality = normalized_space(record.get(LOCALITY_FIELD, ""))
    district = normalized_space(record.get(DISTRICT_FIELD, ""))
    district_stem = re.sub(r"(?:특별자치시|광역시|특별시|시|군|구)$", "", district)
    if district_stem:
        shortened = re.sub(rf"^\s*{re.escape(district_stem)}\s*", "", locality, count=1)
        if shortened.strip():
            return shortened.strip()
    return locality


def full_service_area(record: dict[str, str]) -> str:
    raw_region = normalized_space(record.get(REGION_FIELD, ""))
    region = OFFICIAL_ADDRESS_REGIONS.get(raw_region) or official_address_region(
        normalized_space(record.get(ADDRESS_FIELD, ""))
    )
    locality = locality_without_district_prefix(record)
    if region == "세종특별자치시":
        # The legacy district cell contains the road name 새롬중앙로.  It is
        # valid in streetAddress, but never as an administrative areaServed.
        return " ".join(value for value in (region, locality) if value)
    return " ".join(
        value
        for value in (
            region,
            normalized_space(record.get(DISTRICT_FIELD, "")),
            locality,
        )
        if value
    )


def page_url(path: Path) -> str:
    relative = path.parent.relative_to(ROOT).as_posix()
    return BASE_URL + "/" + quote(relative, safe="/") + "/"


def visible_faq(source: str) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for block in re.findall(r"<details\b[^>]*>(.*?)</details>", source, re.I | re.S):
        questions = tag_texts(block, "summary")
        answers = tag_texts(block, "p")
        if questions and answers:
            result.append((questions[0], answers[0]))
    return result


def schema_faq(nodes: list[dict[str, Any]]) -> list[tuple[str, str]]:
    node = next((item for item in nodes if "FAQPage" in node_types(item)), {})
    result: list[tuple[str, str]] = []
    for question in node.get("mainEntity", []) if isinstance(node, dict) else []:
        if not isinstance(question, dict):
            continue
        answer = question.get("acceptedAnswer", {})
        result.append(
            (
                str(question.get("name", "")).strip(),
                str(answer.get("text", "")).strip() if isinstance(answer, dict) else "",
            )
        )
    return result


def official_address_region(address: str) -> str:
    tokens = normalized_space(address).split()
    return OFFICIAL_ADDRESS_REGIONS.get(tokens[0], "") if tokens else ""


def expected_address_locality(address: str) -> str:
    tokens = normalized_space(address).split()
    if not tokens:
        return ""
    if tokens[0] == "세종특별자치시":
        return "새롬동"
    return tokens[1] if len(tokens) > 1 else ""


@dataclass
class SourceData:
    records: list[dict[str, str]]
    by_locality: dict[str, dict[str, str]]
    physical_groups: dict[tuple[str, str, str], list[dict[str, str]]]
    representative: dict[tuple[str, str, str], tuple[str, str]]
    all_school_names: set[str]
    central_phone: str
    central_hours: str
    central_website: str


def load_dict_csv(path: Path, findings: Findings) -> tuple[list[str], list[dict[str, str]]]:
    if not path.is_file():
        findings.add("source_missing", path, "required CSV missing")
        return [], []
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            return list(reader.fieldnames or []), list(reader)
    except (OSError, UnicodeError, csv.Error) as exc:
        findings.add("source_invalid", path, str(exc))
        return [], []


def validate_sources(findings: Findings) -> SourceData:
    headers, records = load_dict_csv(MAIN_CSV, findings)
    if set(headers) != EXPECTED_MAIN_HEADERS:
        findings.add(
            "source_headers",
            MAIN_CSV,
            f"missing={sorted(EXPECTED_MAIN_HEADERS - set(headers))!r} "
            f"extra={sorted(set(headers) - EXPECTED_MAIN_HEADERS)!r}",
        )
    if len(records) != EXPECTED_SOURCE_ROWS:
        findings.add("source_row_count", MAIN_CSV, f"rows={len(records)} expected=371")
    by_locality: dict[str, dict[str, str]] = {}
    for record in records:
        key = locality_key(record.get(LOCALITY_FIELD, ""))
        if not key:
            findings.add("source_locality_empty", MAIN_CSV, repr(record))
            continue
        if key in by_locality:
            findings.add("source_locality_duplicate", MAIN_CSV, f"locality={key!r}")
        by_locality[key] = record
    for field, expected in EXPECTED_EMPTY_COUNTS.items():
        actual = sum(not normalized_space(record.get(field, "")) for record in records)
        if actual != expected:
            findings.add(
                "source_empty_count",
                MAIN_CSV,
                f"field={field!r} actual={actual} expected={expected}",
            )
    mandatory = {
        LOCALITY_FIELD,
        REGION_FIELD,
        DISTRICT_FIELD,
        CENTER_FIELD,
        OFFICE_FIELD,
        REGISTRATION_FIELD,
        ADDRESS_FIELD,
    }
    for field in mandatory:
        for index, record in enumerate(records, start=2):
            if not normalized_space(record.get(field, "")):
                findings.add("source_mandatory_empty", MAIN_CSV, f"row={index} field={field!r}")

    physical_groups: defaultdict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for record in records:
        physical_groups[physical_key(record)].append(record)
    if len(physical_groups) != EXPECTED_PHYSICAL_CENTERS:
        findings.add(
            "source_physical_count",
            MAIN_CSV,
            f"physical={len(physical_groups)} expected=188",
        )
    group_sizes = Counter(len(group) for group in physical_groups.values())
    if group_sizes != EXPECTED_PHYSICAL_GROUP_SIZES:
        findings.add(
            "source_physical_group_sizes",
            MAIN_CSV,
            f"actual={dict(group_sizes)!r} expected={dict(EXPECTED_PHYSICAL_GROUP_SIZES)!r}",
        )
    for position, field in enumerate((CENTER_FIELD, ADDRESS_FIELD, REGISTRATION_FIELD)):
        values: defaultdict[str, set[tuple[str, str, str]]] = defaultdict(set)
        for key in physical_groups:
            values[key[position]].add(key)
        for value, keys in values.items():
            if value and len(keys) > 1:
                findings.add(
                    "source_identity_collision",
                    MAIN_CSV,
                    f"field={field!r} value={value!r} keys={len(keys)}",
                )
    consistent_fields = [FEE_FIELD, OFFICE_FIELD, *GRADE_FIELDS.values()]
    for key, group in physical_groups.items():
        for field in consistent_fields:
            values = {normalized_space(record.get(field, "")) for record in group}
            if len(values) > 1:
                findings.add(
                    "source_physical_inconsistent",
                    MAIN_CSV,
                    f"center={key!r} field={field!r} values={sorted(values)!r}",
                )

    for record in records:
        fee = normalized_space(record.get(FEE_FIELD, ""))
        if fee:
            split = urlsplit(fee)
            if split.scheme != "https" or split.hostname != "drive.google.com":
                findings.add("source_fee_url", MAIN_CSV, f"locality={record.get(LOCALITY_FIELD)!r} url={fee!r}")
        for subject, field in GRADE_FIELDS.items():
            values = csv_parts(record.get(field, ""))
            if len(values) != len(set(values)):
                findings.add("source_grade_duplicate", MAIN_CSV, f"locality={record.get(LOCALITY_FIELD)!r} subject={subject}")
            invalid = [value for value in values if not VALID_GRADE_RE.fullmatch(value)]
            if invalid:
                findings.add("source_grade_invalid", MAIN_CSV, f"locality={record.get(LOCALITY_FIELD)!r} subject={subject} values={invalid!r}")
    for (subject, prefix), expected in EXPECTED_LEAF_GRADE_EMPTY.items():
        actual = sum(
            not any(value.startswith(prefix) for value in grade_values(record, subject))
            for record in records
        )
        if actual != expected:
            findings.add(
                "source_leaf_grade_empty_count",
                MAIN_CSV,
                f"subject={subject} prefix={prefix} actual={actual} expected={expected}",
            )

    all_school_names: set[str] = set()
    for record in records:
        columns = school_columns(record)
        for values in columns.values():
            all_school_names.update(values)
            invalid = [value for value in values if not is_school_name(value)]
            if invalid:
                findings.add(
                    "source_school_name_invalid",
                    MAIN_CSV,
                    f"locality={record.get(LOCALITY_FIELD)!r} values={invalid!r}",
                )
        overlap = (
            set(columns["초등"]) & set(columns["중등"])
            | set(columns["초등"]) & set(columns["고등"])
            | set(columns["중등"]) & set(columns["고등"])
        )
        if overlap:
            findings.add("source_school_cross_level", MAIN_CSV, f"locality={record.get(LOCALITY_FIELD)!r} overlap={sorted(overlap)!r}")

    school_headers, school_rows = load_dict_csv(SCHOOL_CSV, findings)
    if len(school_rows) != EXPECTED_SOURCE_ROWS or LOCALITY_FIELD not in school_headers:
        findings.add("school_source_shape", SCHOOL_CSV, f"rows={len(school_rows)} headers={school_headers!r}")
    school_map = {locality_key(row.get(LOCALITY_FIELD, "")): row for row in school_rows}
    for key, record in by_locality.items():
        other = school_map.get(key)
        if not other:
            findings.add("school_source_missing_locality", SCHOOL_CSV, f"locality={key!r}")
            continue
        for field in SCHOOL_FIELDS.values():
            if normalized_space(record.get(field, "")) != normalized_space(other.get(field, "")):
                findings.add("school_source_mismatch", SCHOOL_CSV, f"locality={key!r} field={field!r}")

    org_headers, org_rows = load_dict_csv(ORGANIZATION_CSV, findings)
    expected_org_headers = {
        "실제 센터명",
        "도로명 주소",
        "전화번호",
        "운영 시간",
        "서비스 제공 지역",
        "공식 홈페이지",
    }
    if set(org_headers) != expected_org_headers or len(org_rows) != EXPECTED_SOURCE_ROWS:
        findings.add("organization_source_shape", ORGANIZATION_CSV, f"rows={len(org_rows)} headers={org_headers!r}")
    for index, (record, org) in enumerate(zip(records, org_rows), start=2):
        if normalized_space(record.get(CENTER_FIELD, "")) != normalized_space(org.get("실제 센터명", "")):
            findings.add("organization_source_name", ORGANIZATION_CSV, f"row={index}")
        if normalized_space(record.get(ADDRESS_FIELD, "")) != normalized_space(org.get("도로명 주소", "")):
            findings.add("organization_source_address", ORGANIZATION_CSV, f"row={index}")
    phones = {normalized_space(row.get("전화번호", "")) for row in org_rows}
    hours = {normalized_space(row.get("운영 시간", "")) for row in org_rows}
    websites = {normalized_space(row.get("공식 홈페이지", "")) for row in org_rows}
    if phones != {"010-3957-8283"}:
        findings.add("organization_source_phone", ORGANIZATION_CSV, f"values={sorted(phones)!r}")
    if hours != {"12시-24시"}:
        findings.add("organization_source_hours", ORGANIZATION_CSV, f"values={sorted(hours)!r}")
    normalized_websites = {value.rstrip("/") for value in websites}
    if normalized_websites != {"https://wawa-center.kr"}:
        findings.add("organization_source_website", ORGANIZATION_CSV, f"values={sorted(websites)!r}")

    representative: dict[tuple[str, str, str], tuple[str, str]] = {}
    for key, group in physical_groups.items():
        candidates = sorted(
            (
                locality_key(record[LOCALITY_FIELD]),
                page_url(NATIONAL_ROOT / locality_key(record[LOCALITY_FIELD]) / "index.html"),
            )
            for record in group
        )
        _locality, entity_url = candidates[0]
        representative[key] = (entity_url + "#organization", entity_url)

    return SourceData(
        records=records,
        by_locality=by_locality,
        physical_groups=dict(physical_groups),
        representative=representative,
        all_school_names=all_school_names,
        central_phone=next(iter(phones), ""),
        central_hours=next(iter(hours), ""),
        central_website=next(iter(websites), ""),
    )


@dataclass
class Page:
    path: Path
    source: str
    relative_parts: tuple[str, ...]
    kind: str
    record: dict[str, str] | None
    canonical: str
    title: str
    description: str
    h1: str
    main_html: str
    visible_text: str
    paragraphs: list[str]
    headings: list[str]
    nodes: list[dict[str, Any]]
    faqs: list[tuple[str, str]]


def expected_relative_files(source: SourceData) -> set[str]:
    result = {"전국센터/index.html"}
    regions = {record[REGION_FIELD].strip() for record in source.records}
    result.update(f"전국센터/{region}/index.html" for region in regions)
    result.update(f"전국센터/{slug}/index.html" for slug in COURSE_SLUGS)
    for record in source.records:
        locality = locality_key(record[LOCALITY_FIELD])
        result.add(f"전국센터/{locality}/index.html")
        result.update(f"전국센터/{locality}/{slug}/index.html" for slug in COURSE_SLUGS)
    return result


def expected_url_for_relative(relative: str) -> str:
    parent = Path(relative).parent.as_posix()
    return BASE_URL + "/" + quote(parent, safe="/") + "/"


def sitemap_national_urls(findings: Findings) -> set[str]:
    path = ROOT / "sitemap.xml"
    try:
        tree = ET.parse(path)
    except (OSError, ET.ParseError) as exc:
        findings.add("sitemap_invalid", path, str(exc))
        return set()
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    result: list[str] = []
    for entry in tree.findall(".//sm:url", namespace):
        location = entry.find("sm:loc", namespace)
        value = (location.text or "").strip() if location is not None else ""
        if value.startswith(BASE_URL + "/" + quote("전국센터") + "/"):
            result.append(value)
    if len(result) != len(set(result)):
        findings.add("sitemap_national_duplicates", path, f"duplicates={len(result)-len(set(result))}")
    return set(result)


def load_pages(source_data: SourceData, findings: Findings) -> list[Page]:
    expected_files = expected_relative_files(source_data)
    actual_paths = sorted(NATIONAL_ROOT.rglob("index.html")) if NATIONAL_ROOT.is_dir() else []
    actual_files = {path.relative_to(ROOT).as_posix() for path in actual_paths}
    findings.compare_set("national_file_set", actual_files, expected_files)
    if len(actual_files) != EXPECTED_NATIONAL_PAGES:
        findings.add("national_page_count", NATIONAL_ROOT, f"actual={len(actual_files)} expected=2617")

    expected_urls = {expected_url_for_relative(value) for value in expected_files}
    sitemap_urls = sitemap_national_urls(findings)
    findings.compare_set("national_sitemap_set", sitemap_urls, expected_urls)

    pages: list[Page] = []
    current_canonicals: list[str] = []
    for path in actual_paths:
        try:
            html_source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            findings.add("html_read_error", path, str(exc))
            continue
        relative = path.parent.relative_to(NATIONAL_ROOT)
        parts = () if str(relative) == "." else relative.parts
        record = source_data.by_locality.get(locality_key(parts[0])) if parts else None
        if not parts:
            kind = "root"
        elif len(parts) == 1 and record is not None:
            kind = "local"
        elif len(parts) == 2 and record is not None and parts[1] in COURSE_SLUGS:
            kind = "leaf"
        else:
            kind = "hub"

        canonical = canonical_values(html_source)
        og_url = meta_values(html_source, "property", "og:url")
        expected_url = page_url(path)
        if canonical != [expected_url]:
            findings.add("canonical_mismatch", path, f"actual={canonical!r} expected={[expected_url]!r}")
        if og_url != [expected_url]:
            findings.add("og_url_mismatch", path, f"actual={og_url!r} expected={[expected_url]!r}")
        if canonical:
            current_canonicals.append(canonical[0])

        main_match = re.search(r"<main\b[^>]*>(.*?)</main>", html_source, re.I | re.S)
        main_html = main_match.group(1) if main_match else html_source
        titles = tag_texts(html_source, "title")
        h1s = tag_texts(main_html, "h1")
        descriptions = meta_values(html_source, "name", "description")
        if len(titles) != 1:
            findings.add("title_count", path, f"count={len(titles)}")
        if len(h1s) != 1:
            findings.add("h1_count", path, f"count={len(h1s)}")
        if len(descriptions) != 1 or not descriptions[0]:
            findings.add("description_count", path, f"count={len(descriptions)}")
        nodes = parse_jsonld(path, html_source, findings)
        faqs = visible_faq(main_html)
        pages.append(
            Page(
                path=path,
                source=html_source,
                relative_parts=tuple(parts),
                kind=kind,
                record=record,
                canonical=canonical[0] if len(canonical) == 1 else "",
                title=titles[0] if len(titles) == 1 else "",
                description=descriptions[0] if len(descriptions) == 1 else "",
                h1=h1s[0] if len(h1s) == 1 else "",
                main_html=main_html,
                visible_text=strip_tags(main_html),
                paragraphs=[text for text in tag_texts(main_html, "p") if len(text) >= 30],
                headings=tag_texts(main_html, "h2") + tag_texts(main_html, "h3"),
                nodes=nodes,
                faqs=faqs,
            )
        )
    if len(current_canonicals) != len(set(current_canonicals)):
        findings.add("canonical_duplicates", NATIONAL_ROOT, f"duplicates={len(current_canonicals)-len(set(current_canonicals))}")
    findings.compare_set("national_canonical_set", current_canonicals, expected_urls)
    return pages


def org_area_names(organization: dict[str, Any]) -> set[str]:
    value = organization.get("areaServed", [])
    items = value if isinstance(value, list) else [value]
    return {
        str(item.get("name", "")).strip()
        for item in items
        if isinstance(item, dict) and str(item.get("name", "")).strip()
    }


def schema_school_names(nodes: list[dict[str, Any]]) -> set[str]:
    result: set[str] = set()
    for node in nodes:
        if not ({"WebPage", "Article"} & node_types(node)):
            continue
        mentions = node.get("mentions", [])
        items = mentions if isinstance(mentions, list) else [mentions]
        for item in items:
            if not isinstance(item, dict) or "Organization" not in node_types(item):
                continue
            name = str(item.get("name", "")).strip()
            if name:
                result.add(name)
    return result


def visible_school_names(page: Page) -> set[str]:
    match = re.search(
        r"<div\b[^>]*class=[\"'][^\"']*verified-school-list[^\"']*[\"'][^>]*>(.*?)</div>",
        page.main_html,
        re.I | re.S,
    )
    if not match:
        return set()
    result: set[str] = set()
    for text in tag_texts(match.group(1), "span"):
        if re.search(r"상담|확인|학교\s*진도", text):
            continue
        result.add(text)
    return result


def visible_grade_field(page: Page) -> tuple[list[str], str]:
    match = re.search(
        r"<dt>\s*수업\s*가능\s*학년\s*</dt>\s*<dd>(.*?)</dd>",
        page.main_html,
        re.I | re.S,
    )
    if not match:
        return [], ""
    text = strip_tags(match.group(1))
    return GRADE_TOKEN_RE.findall(text), text


def check_root_contact(source: SourceData, findings: Findings) -> None:
    path = ROOT / "index.html"
    if not path.is_file():
        findings.add("root_home_missing", path, "index.html missing")
        return
    html_source = path.read_text(encoding="utf-8")
    nodes = parse_jsonld(path, html_source, findings)
    organization = next(
        (
            node
            for node in nodes
            if node.get("@id") == ROOT_ORGANIZATION_ID
            and "EducationalOrganization" in node_types(node)
        ),
        {},
    )
    if not organization:
        findings.add("root_organization_missing", path, ROOT_ORGANIZATION_ID)
        return
    if organization.get("telephone") != source.central_phone:
        findings.add("root_central_phone", path, f"actual={organization.get('telephone')!r} expected={source.central_phone!r}")
    contact = organization.get("contactPoint", {})
    if not isinstance(contact, dict) or contact.get("telephone") != source.central_phone:
        findings.add("root_contact_point", path, f"contactPoint={contact!r}")


def check_fact_page(
    page: Page,
    source: SourceData,
    findings: Findings,
    observed_ids: defaultdict[tuple[str, str, str], set[str]],
    observed_urls: defaultdict[tuple[str, str, str], set[str]],
    phone_centers: defaultdict[str, set[tuple[str, str, str]]],
) -> None:
    assert page.record is not None
    record = page.record
    physical = physical_key(record)
    expected_identity = source.representative.get(physical, ("", ""))
    present_types: set[str] = set()
    for node in page.nodes:
        present_types.update(node_types(node))
    missing = REQUIRED_FACT_TYPES - present_types
    if missing:
        findings.add("schema_required_types", page.path, f"missing={sorted(missing)!r}")
    if any(
        "Review" in node_types(item) or "aggregateRating" in item or "review" in item
        for item in recursive_dicts(page.nodes)
    ):
        findings.add("unsupported_review_schema", page.path, "Review/rating data present")

    organizations = [node for node in page.nodes if "LocalBusiness" in node_types(node)]
    if len(organizations) != 1:
        findings.add("physical_org_count", page.path, f"count={len(organizations)}")
    organization = organizations[0] if organizations else {}
    organization_id = str(organization.get("@id", "")).strip()
    organization_url = str(organization.get("url", "")).strip()
    observed_ids[physical].add(organization_id)
    observed_urls[physical].add(organization_url)
    if (organization_id, organization_url) != expected_identity:
        findings.add(
            "physical_org_identity",
            page.path,
            f"actual={(organization_id, organization_url)!r} expected={expected_identity!r}",
        )
    if reference_id(organization.get("branchOf")) != ROOT_ORGANIZATION_ID:
        findings.add("physical_org_branch", page.path, f"branchOf={organization.get('branchOf')!r}")

    expected_name = normalized_space(record.get(CENTER_FIELD, ""))
    expected_address = normalized_space(record.get(ADDRESS_FIELD, ""))
    expected_registration = normalized_space(record.get(REGISTRATION_FIELD, ""))
    if organization.get("name") != expected_name:
        findings.add("center_name", page.path, f"actual={organization.get('name')!r} expected={expected_name!r}")
    address = organization.get("address", {})
    if not isinstance(address, dict) or address.get("streetAddress") != expected_address:
        findings.add("center_address", page.path, f"actual={address!r} expected={expected_address!r}")
    expected_region = official_address_region(expected_address)
    expected_locality = expected_address_locality(expected_address)
    if not expected_region:
        findings.add("source_address_region_unknown", page.path, expected_address)
    elif not isinstance(address, dict) or address.get("addressRegion") != expected_region:
        findings.add("postal_address_region", page.path, f"actual={address.get('addressRegion') if isinstance(address,dict) else None!r} expected={expected_region!r}")
    if expected_locality and (
        not isinstance(address, dict) or address.get("addressLocality") != expected_locality
    ):
        findings.add("postal_address_locality", page.path, f"actual={address.get('addressLocality') if isinstance(address,dict) else None!r} expected={expected_locality!r}")
    identifier = organization.get("identifier", {})
    if (
        not isinstance(identifier, dict)
        or identifier.get("@type") != "PropertyValue"
        or identifier.get("propertyID") != REGISTRATION_FIELD
        or identifier.get("value") != expected_registration
    ):
        findings.add("center_registration", page.path, f"identifier={identifier!r} expected={expected_registration!r}")
    for fact_name, fact in (
        ("center", expected_name),
        ("address", expected_address),
        ("registration", expected_registration),
    ):
        if fact and fact not in page.visible_text:
            findings.add("visible_center_fact", page.path, f"missing {fact_name}={fact!r}")

    unsupported_contact = [
        field for field in ("telephone", "contactPoint", "openingHours") if field in organization
    ]
    if unsupported_contact:
        findings.add(
            "branch_uses_central_contact",
            page.path,
            f"properties={unsupported_contact!r}; 371-row organization source contains one central value",
        )
    telephone = str(organization.get("telephone", "")).strip()
    if telephone:
        phone_centers[telephone].add(physical)

    expected_areas = {
        full_service_area(item) for item in source.physical_groups.get(physical, [])
    }
    actual_areas = org_area_names(organization)
    if actual_areas != expected_areas:
        findings.add("organization_area_served", page.path, f"actual={sorted(actual_areas)!r} expected={sorted(expected_areas)!r}")

    services = [node for node in page.nodes if "Service" in node_types(node)]
    if len(services) != 1:
        findings.add("service_count", page.path, f"count={len(services)}")
    service = services[0] if services else {}
    if reference_id(service.get("provider")) != organization_id:
        findings.add("service_provider", page.path, f"actual={service.get('provider')!r} expected={organization_id!r}")
    service_area = service.get("areaServed", {})
    service_area_name = service_area.get("name") if isinstance(service_area, dict) else ""
    expected_service_area = full_service_area(record)
    if service_area_name != expected_service_area:
        findings.add("service_area", page.path, f"actual={service_area_name!r} expected={expected_service_area!r}")

    web_pages = [node for node in page.nodes if "WebPage" in node_types(node)]
    articles = [node for node in page.nodes if "Article" in node_types(node)]
    web_page = web_pages[0] if web_pages else {}
    article = articles[0] if articles else {}
    if len(web_pages) != 1 or len(articles) != 1:
        findings.add("article_webpage_count", page.path, f"WebPage={len(web_pages)} Article={len(articles)}")
    web_page_id = str(web_page.get("@id", ""))
    service_id = str(service.get("@id", ""))
    for node_name, node in (("WebPage", web_page), ("Article", article)):
        for property_name in ("author", "publisher"):
            if reference_id(node.get(property_name)) != ROOT_ORGANIZATION_ID:
                findings.add(
                    "root_author_publisher",
                    page.path,
                    f"{node_name}.{property_name}={reference_id(node.get(property_name))!r} expected={ROOT_ORGANIZATION_ID!r}",
                )
    if reference_id(web_page.get("mainEntity")) != service_id:
        findings.add("webpage_main_entity", page.path, f"actual={web_page.get('mainEntity')!r} expected={service_id!r}")
    if reference_id(article.get("mainEntityOfPage")) != web_page_id:
        findings.add("article_main_entity", page.path, f"actual={article.get('mainEntityOfPage')!r} expected={web_page_id!r}")

    visible_pairs = page.faqs
    schema_pairs = schema_faq(page.nodes)
    if visible_pairs != schema_pairs:
        findings.add("faq_visible_schema", page.path, f"visible={len(visible_pairs)} schema={len(schema_pairs)}")
    if len(visible_pairs) < 3:
        findings.add("faq_too_few", page.path, f"count={len(visible_pairs)}")

    school_level = COURSE_INFO[page.relative_parts[1]][2] if page.kind == "leaf" else None
    expected_schools = set(expected_school_values(record, school_level))
    actual_visible_schools = visible_school_names(page)
    actual_schema_schools = schema_school_names(page.nodes)
    if actual_visible_schools != expected_schools:
        findings.add("visible_school_facts", page.path, f"actual={sorted(actual_visible_schools)!r} expected={sorted(expected_schools)!r}")
    if actual_schema_schools != expected_schools:
        findings.add("schema_school_facts", page.path, f"actual={sorted(actual_schema_schools)!r} expected={sorted(expected_schools)!r}")
    if not expected_schools and not TRUTHFUL_EMPTY_SCHOOL_RE.search(page.visible_text):
        findings.add("school_empty_disclosure", page.path, "authoritative school field is empty")
    generic_school = GENERIC_HIGH_SCHOOL_RE.search(page.visible_text)
    if generic_school:
        findings.add("generic_school_claim", page.path, generic_school.group(0))
    if any(GENERIC_HIGH_SCHOOL_RE.search(value) for value in recursive_strings(page.nodes)):
        findings.add("generic_school_claim_schema", page.path, "generic all-high-school claim in JSON-LD")

    if page.kind == "leaf":
        prefix, subject, _level = COURSE_INFO[page.relative_parts[1]]
        expected_grades = [value for value in grade_values(record, subject) if value.startswith(prefix)]
        actual_grades, field_text = visible_grade_field(page)
        if expected_grades:
            if actual_grades != expected_grades:
                findings.add("visible_grade_facts", page.path, f"actual={actual_grades!r} expected={expected_grades!r}")
        else:
            if actual_grades:
                findings.add("visible_grade_without_source", page.path, f"actual={actual_grades!r}")
            if not TRUTHFUL_EMPTY_GRADE_RE.search(field_text + " " + page.visible_text):
                findings.add("grade_empty_disclosure", page.path, f"subject={subject} prefix={prefix}")
        authored_grades = set(GRADE_TOKEN_RE.findall(page.visible_text))
        schema_grades = set(GRADE_TOKEN_RE.findall(" ".join(recursive_strings(page.nodes))))
        expected_grade_set = set(expected_grades)
        if authored_grades - expected_grade_set:
            findings.add("visible_grade_unsupported", page.path, f"unexpected={sorted(authored_grades - expected_grade_set)!r}")
        if schema_grades - expected_grade_set:
            findings.add("schema_grade_unsupported", page.path, f"unexpected={sorted(schema_grades - expected_grade_set)!r}")

    links = [attrs(tag).get("href", "").strip() for tag in re.findall(r"<a\b[^>]*>", page.source, re.I)]
    fee_url = normalized_space(record.get(FEE_FIELD, ""))
    offers = [item for item in recursive_dicts(page.nodes) if "Offer" in node_types(item)]
    if fee_url:
        if fee_url not in links:
            findings.add("fee_link_missing", page.path, f"expected={fee_url!r}")
        if not any(item.get("url") == fee_url for item in offers):
            findings.add("fee_offer_missing", page.path, f"expected={fee_url!r}")
    else:
        if any((urlsplit(link).hostname or "") == "drive.google.com" for link in links):
            findings.add("fee_link_without_source", page.path, "Drive fee link exists")
        if offers:
            findings.add("fee_offer_without_source", page.path, f"offers={offers!r}")
        if not re.search(r"교습비|수강료", page.visible_text) or not re.search(r"자료.{0,30}(?:없|제공되지\s*않)|(?:없|제공되지\s*않).{0,30}자료", page.visible_text):
            findings.add("fee_empty_disclosure", page.path, "fee URL source is empty")

    if is_service_area_record(record):
        combined_heading = page.title + " " + page.h1
        if not OFF_LOCALITY_HEADING_CUE_RE.search(combined_heading):
            findings.add("offlocal_heading_intent", page.path, f"title/H1 lack service-area qualifier: {combined_heading!r}")
        if not OFF_LOCALITY_CUE_RE.search(page.visible_text):
            findings.add("offlocal_disclosure", page.path, "service-area/physical-location distinction missing")
        hero_match = re.search(r"<section\b[^>]*>.*?<h1\b[^>]*>.*?</section>", page.main_html, re.I | re.S)
        hero_text = strip_tags(hero_match.group(0)) if hero_match else ""
        if expected_name not in hero_text or expected_address not in hero_text:
            findings.add("offlocal_above_fold", page.path, "actual center name/address not both present in H1 hero")
        faq_text = " ".join(value for pair in visible_pairs for value in pair)
        if expected_name not in faq_text or expected_address not in faq_text or not OFF_LOCALITY_CUE_RE.search(faq_text):
            findings.add("offlocal_faq", page.path, "FAQ lacks actual center/address/location distinction")
        if re.search(r"확인된\s*센터\s*정보", page.visible_text):
            findings.add("offlocal_verified_label", page.path, "use connected consultation center wording")

    for pattern, code in (
        (PLACEHOLDER_RE, "placeholder"),
        (OVERCLAIM_RE, "unsupported_outcome_claim"),
        (UNNATURAL_RE, "unnatural_generated_phrase"),
    ):
        match = pattern.search(page.visible_text)
        if match:
            findings.add(code, page.path, f"phrase={match.group(0)!r}")


def normalize_authored_text(page: Page) -> str:
    assert page.record is not None
    record = page.record
    value = unicodedata.normalize("NFKC", page.visible_text).lower()
    replacements: list[tuple[str, str]] = []
    locality = normalized_space(record.get(LOCALITY_FIELD, ""))
    course = page.relative_parts[1] if page.kind == "leaf" else ""
    school_values = expected_school_values(
        record, COURSE_INFO[course][2] if course in COURSE_INFO else None
    )
    for label, values in (
        ("ADDRESS", [record.get(ADDRESS_FIELD, "")]),
        ("CENTER", [record.get(CENTER_FIELD, "")]),
        ("REGISTRATION", [record.get(REGISTRATION_FIELD, "")]),
        ("SCHOOL", school_values),
        ("COURSE", [course, page.h1[len(locality) :].strip() if page.h1.startswith(locality) else ""]),
        ("LOCALITY", [locality, locality.replace("-", " "), locality_key(locality)]),
    ):
        for item in values:
            item = normalized_space(item).lower()
            if item:
                replacements.append((item, label))
    for item, label in sorted(set(replacements), key=lambda pair: len(pair[0]), reverse=True):
        value = re.sub(re.escape(item), f" {label} ", value, flags=re.I)
    value = GRADE_TOKEN_RE.sub(" GRADE ", value)
    value = re.sub(r"20\d{2}[-./]\d{1,2}[-./]\d{1,2}", " DATE ", value)
    value = re.sub(r"0\d{1,2}[-\s]\d{3,4}[-\s]\d{4}", " PHONE ", value)
    value = re.sub(r"\d+(?:[.,]\d+)*", " NUMBER ", value)
    value = re.sub(r"[^가-힣a-zA-Z0-9_]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_fragment(page: Page, fragment: str) -> str:
    original = page.visible_text
    page.visible_text = fragment
    try:
        return normalize_authored_text(page)
    finally:
        page.visible_text = original


def words(value: str) -> list[str]:
    return re.findall(r"[가-힣A-Za-z0-9]+", value or "")


def split_sentences(value: str) -> list[str]:
    return [
        item.strip()
        for item in re.split(r"(?<=[.!?])\s+|[\r\n]+", value)
        if len(item.strip()) >= 20
    ]


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * fraction)]


def check_collection_quality(pages: list[Page], findings: Findings) -> dict[str, float]:
    fact_pages = [page for page in pages if page.kind in {"local", "leaf"}]
    if len(fact_pages) != EXPECTED_FACT_PAGES:
        findings.add("fact_page_count", NATIONAL_ROOT, f"actual={len(fact_pages)} expected=2597")
    for field in ("title", "description", "h1"):
        values = [getattr(page, field) for page in pages]
        duplicates = {value: count for value, count in Counter(values).items() if value and count > 1}
        if duplicates:
            findings.add("exact_metadata_duplicate", NATIONAL_ROOT, f"field={field} groups={len(duplicates)} sample={list(duplicates.items())[:3]!r}")

    paragraph_df: Counter[str] = Counter()
    normalized_paragraph_df: Counter[str] = Counter()
    normalized_paragraphs: dict[Path, list[str]] = {}
    normalized_sentences: dict[Path, list[str]] = {}
    faq_question_df: Counter[str] = Counter()
    faq_answer_df: Counter[str] = Counter()
    normalized_description_df: Counter[str] = Counter()
    for page in fact_pages:
        paragraph_df.update(set(page.paragraphs))
        normalized = [normalize_fragment(page, item) for item in page.paragraphs]
        normalized_paragraphs[page.path] = normalized
        normalized_paragraph_df.update(set(normalized))
        sentences: list[str] = []
        for paragraph in page.paragraphs:
            sentences.extend(normalize_fragment(page, item) for item in split_sentences(paragraph))
        normalized_sentences[page.path] = sentences
        faq_question_df.update(
            set(normalize_fragment(page, question) for question, _answer in page.faqs)
        )
        faq_answer_df.update(
            set(normalize_fragment(page, answer) for _question, answer in page.faqs)
        )
        normalized_description_df[normalize_fragment(page, page.description)] += 1

        token_count = len(words(page.visible_text))
        target_occurrences = page.visible_text.count(page.h1) if page.h1 else 0
        locality = normalized_space(page.record.get(LOCALITY_FIELD, "")) if page.record else ""
        locality_occurrences = page.visible_text.count(locality) if locality else 0
        locality_headings = sum(locality in heading for heading in page.headings) if locality else 0
        h1_faqs = sum(page.h1 in question for question, _answer in page.faqs if page.h1)
        if token_count < 450:
            findings.add("content_too_thin", page.path, f"tokens={token_count}")
        if target_occurrences > 6:
            findings.add("exact_keyword_repetition", page.path, f"H1 phrase occurrences={target_occurrences} max=6")
        if locality_occurrences > 20:
            findings.add("locality_repetition", page.path, f"occurrences={locality_occurrences} max=20")
        if locality_headings > 3:
            findings.add("locality_heading_repetition", page.path, f"headings={locality_headings} max=3")
        if h1_faqs > 1:
            findings.add("faq_exact_keyword_repetition", page.path, f"questions containing full H1={h1_faqs} max=1")
        if token_count and 1_000 * page.visible_text.count("학원") / token_count > 30:
            findings.add("academy_keyword_density", page.path, f"per_1000={1_000*page.visible_text.count('학원')/token_count:.2f}")
        sentence_counts = Counter(
            sentence
            for paragraph in page.paragraphs
            for sentence in split_sentences(paragraph)
        )
        repeated_inside = {sentence: count for sentence, count in sentence_counts.items() if count > 1}
        if repeated_inside:
            findings.add("sentence_repeated_within_page", page.path, f"sample={list(repeated_inside.items())[:2]!r}")

    overused_exact = [(text, count) for text, count in paragraph_df.items() if count > 10]
    if overused_exact:
        findings.add("exact_paragraph_overuse", NATIONAL_ROOT, f"groups={len(overused_exact)} sample={sorted(overused_exact,key=lambda x:x[1],reverse=True)[:3]!r}")
    sentence_df: Counter[str] = Counter()
    for values in normalized_sentences.values():
        sentence_df.update(set(values))

    normalized_para_instances = sum(len(values) for values in normalized_paragraphs.values())
    duplicated_para_instances = sum(
        1
        for values in normalized_paragraphs.values()
        for value in values
        if normalized_paragraph_df[value] >= 2
    )
    normalized_para_duplicate_pct = (
        100 * duplicated_para_instances / normalized_para_instances
        if normalized_para_instances
        else 0.0
    )
    paragraph_coverage: list[float] = []
    sentence_coverage_10: list[float] = []
    for page in fact_pages:
        paragraphs = normalized_paragraphs[page.path]
        denominator = sum(len(words(value)) for value in paragraphs)
        numerator = sum(
            len(words(value)) for value in paragraphs if normalized_paragraph_df[value] >= 2
        )
        paragraph_coverage.append(100 * numerator / denominator if denominator else 0.0)
        sentences = normalized_sentences[page.path]
        denominator = sum(len(words(value)) for value in sentences)
        numerator = sum(len(words(value)) for value in sentences if sentence_df[value] >= 10)
        sentence_coverage_10.append(100 * numerator / denominator if denominator else 0.0)

    median_paragraph_coverage = percentile(paragraph_coverage, 0.5)
    median_sentence_coverage_10 = percentile(sentence_coverage_10, 0.5)
    if normalized_para_duplicate_pct > 60:
        findings.add("normalized_paragraph_duplication", NATIONAL_ROOT, f"duplicate_instances_pct={normalized_para_duplicate_pct:.2f} max=60")
    if median_paragraph_coverage > 60:
        findings.add("normalized_paragraph_coverage", NATIONAL_ROOT, f"median={median_paragraph_coverage:.2f} max=60")
    if median_sentence_coverage_10 > 50:
        findings.add("normalized_sentence_coverage", NATIONAL_ROOT, f"median_df_ge_10={median_sentence_coverage_10:.2f} max=50")
    max_question_df = max(faq_question_df.values(), default=0)
    max_answer_df = max(faq_answer_df.values(), default=0)
    max_description_df = max(normalized_description_df.values(), default=0)
    if max_question_df > 75:
        findings.add("faq_question_template_overuse", NATIONAL_ROOT, f"max_normalized_df={max_question_df} max=75")
    if max_answer_df > 75:
        findings.add("faq_answer_template_overuse", NATIONAL_ROOT, f"max_normalized_df={max_answer_df} max=75")
    if max_description_df > 20:
        findings.add("description_template_overuse", NATIONAL_ROOT, f"max_normalized_df={max_description_df} max=20")
    max_sentence_df = max(sentence_df.values(), default=0)
    if max_sentence_df > 200:
        findings.add("sentence_template_overuse", NATIONAL_ROOT, f"max_normalized_df={max_sentence_df} max=200")

    signatures = Counter(tuple(normalized_paragraphs[page.path]) for page in fact_pages)
    duplicate_signatures = sum(count for count in signatures.values() if count > 1)
    if duplicate_signatures:
        findings.add("normalized_full_page_duplicate", NATIONAL_ROOT, f"pages={duplicate_signatures}")
    return {
        "normalized_paragraph_duplicate_pct": normalized_para_duplicate_pct,
        "median_paragraph_token_coverage": median_paragraph_coverage,
        "median_sentence_df10_token_coverage": median_sentence_coverage_10,
        "max_normalized_faq_question_df": float(max_question_df),
        "max_normalized_faq_answer_df": float(max_answer_df),
        "max_normalized_description_df": float(max_description_df),
        "max_normalized_sentence_df": float(max_sentence_df),
    }


def check_schema_and_facts(
    pages: list[Page], source: SourceData, findings: Findings
) -> tuple[int, int]:
    observed_ids: defaultdict[tuple[str, str, str], set[str]] = defaultdict(set)
    observed_urls: defaultdict[tuple[str, str, str], set[str]] = defaultdict(set)
    phone_centers: defaultdict[str, set[tuple[str, str, str]]] = defaultdict(set)
    service_pages = 0
    fact_pages = 0
    for page in pages:
        if page.kind in {"local", "leaf"}:
            fact_pages += 1
            assert page.record is not None
            if is_service_area_record(page.record):
                service_pages += 1
            check_fact_page(
                page,
                source,
                findings,
                observed_ids,
                observed_urls,
                phone_centers,
            )
        else:
            present: set[str] = set()
            for node in page.nodes:
                present.update(node_types(node))
            missing = REQUIRED_HUB_TYPES - present
            if missing:
                findings.add("hub_schema_types", page.path, f"missing={sorted(missing)!r}")

    if len(observed_ids) != EXPECTED_PHYSICAL_CENTERS:
        findings.add("observed_physical_count", NATIONAL_ROOT, f"actual={len(observed_ids)} expected=188")
    for key in source.physical_groups:
        ids = observed_ids.get(key, set())
        urls = observed_urls.get(key, set())
        if len(ids) != 1:
            findings.add("physical_id_not_stable", NATIONAL_ROOT, f"center={key!r} ids={sorted(ids)!r}")
        if len(urls) != 1:
            findings.add("physical_url_not_stable", NATIONAL_ROOT, f"center={key!r} urls={sorted(urls)!r}")
    all_ids = {identifier for values in observed_ids.values() for identifier in values if identifier}
    all_urls = {value for values in observed_urls.values() for value in values if value}
    if len(all_ids) != EXPECTED_PHYSICAL_CENTERS or len(all_urls) != EXPECTED_PHYSICAL_CENTERS:
        findings.add("physical_identity_unique_count", NATIONAL_ROOT, f"ids={len(all_ids)} urls={len(all_urls)} expected=188")
    for telephone, centers in phone_centers.items():
        if telephone and len(centers) > 1:
            findings.add("same_phone_multiple_branches", NATIONAL_ROOT, f"telephone={telephone!r} physical_centers={len(centers)}")
    if service_pages != EXPECTED_SERVICE_PAGES:
        findings.add("offlocal_page_count", NATIONAL_ROOT, f"actual={service_pages} expected={EXPECTED_SERVICE_PAGES}")
    return fact_pages, service_pages


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-limit", type=int, default=5)
    args = parser.parse_args()
    findings = Findings(sample_limit=max(1, args.sample_limit))

    source = validate_sources(findings)
    pages = load_pages(source, findings)
    check_root_contact(source, findings)
    fact_pages, service_pages = check_schema_and_facts(pages, source, findings)
    quality = check_collection_quality(pages, findings)

    source_school_empty_leaf_pages = 0
    source_grade_empty_leaf_pages = 0
    source_fee_empty_fact_pages = 0
    for record in source.records:
        for slug in COURSE_SLUGS:
            prefix, subject, level = COURSE_INFO[slug]
            if not expected_school_values(record, level):
                source_school_empty_leaf_pages += 1
            if not any(value.startswith(prefix) for value in grade_values(record, subject)):
                source_grade_empty_leaf_pages += 1
        if not normalized_space(record.get(FEE_FIELD, "")):
            source_fee_empty_fact_pages += 7

    print(f"root={ROOT}")
    print(f"source_rows={len(source.records)}")
    print(f"source_physical_centers={len(source.physical_groups)}")
    print(f"source_service_localities={sum(is_service_area_record(record) for record in source.records)}")
    print(f"source_school_empty_leaf_pages={source_school_empty_leaf_pages}")
    print(f"source_grade_empty_leaf_pages={source_grade_empty_leaf_pages}")
    print(f"source_fee_empty_fact_pages={source_fee_empty_fact_pages}")
    print(f"national_pages={len(pages)}")
    print(f"fact_pages={fact_pages}")
    print(f"offlocal_fact_pages={service_pages}")
    for key, value in quality.items():
        print(f"quality_{key}={value:.2f}")
    return findings.report()


if __name__ == "__main__":
    raise SystemExit(main())
