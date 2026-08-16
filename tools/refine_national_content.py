# -*- coding: utf-8 -*-
"""Deterministically refine the nationwide content without changing URLs.

This tool is intentionally separate from ``improve_exposure_quality.py``.
That older tool remains the source of truth for centre rows, physical-centre
relationships, school lists and available grades.  This tool only rebuilds
the following presentation blocks:

* the paragraph immediately following the local-page H1;
* ``#learning-plan`` (the existing image block is reused byte-for-byte);
* the ``quality-content`` student/checklist block;
* the visible FAQ and its matching ``FAQPage`` JSON-LD node;
* the new answer/comparison/FAQ block on 13 region and six curriculum hubs.

No school, address, grade, fee URL or centre name is inferred.  Missing source
data is stated as missing.  The transformation is deterministic, idempotent
and staged in memory before any file is written.

Usage (the default is a read-only preview)::

    python tools/refine_national_content.py
    python tools/refine_national_content.py --scope details
    python tools/refine_national_content.py --scope hubs
    python tools/refine_national_content.py --apply

The two base generators call :func:`run_refinement` after rebuilding their
own pages.  This keeps the refinements in place when either generator is run
again.  It is still safe to run this file directly for a preview or a
standalone, staged update.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence, TypeVar


TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import improve_exposure_quality as source  # noqa: E402


T = TypeVar("T")
DETAIL_MARKER_START = "<!-- quality-content:start -->"
DETAIL_MARKER_END = "<!-- quality-content:end -->"
HUB_MARKER_START = "<!-- hub-content-refinement:start -->"
HUB_MARKER_END = "<!-- hub-content-refinement:end -->"
KNOWN_COPY_ERRORS = {
    "풀이 기록 기록": "풀이 기록",
    "오답 기록 오류": "오답 기록에서 확인된 문제",
    "시험 일정 상태": "시험 준비 상태",
}
PARTICLE_PAIRS = (
    ("을", "를"),
    ("과", "와"),
    ("은", "는"),
    ("이", "가"),
    ("으로", "로"),
)
COMMON_PARTICLE_TERMS = {
    "이해",
    "독해",
    "정확도",
    "어휘",
    "진도",
    "읽기",
    "범위",
    "풀이",
    "문제",
    "평가자료",
    "기록",
    "개념",
    "유형",
    "분석",
    "실행",
    "접근",
    "기억",
    "오답",
    "과정",
    "해석",
    "일정",
    "표현",
    "적용",
    "누적",
    "문법",
    "본문",
    "구조",
    "관리",
    "대비",
    "기초",
    "재풀이",
    "자료",
}
REVISION_DATE = "2026-08-17"
ROOT_ORGANIZATION_ID = source.BASE_URL + "/#organization"

OFFICIAL_REGION_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"^서울(?:특별시)?\b", "서울특별시"),
    (r"^부산(?:광역시)?\b", "부산광역시"),
    (r"^대구(?:광역시)?\b", "대구광역시"),
    (r"^인천(?:광역시)?\b", "인천광역시"),
    (r"^광주(?:광역시)?\b", "광주광역시"),
    (r"^대전(?:광역시)?\b", "대전광역시"),
    (r"^울산(?:광역시)?\b", "울산광역시"),
    (r"^세종(?:특별자치시)?\b", "세종특별자치시"),
    (r"^(?:경기|경기도)\b", "경기도"),
    (r"^(?:강원|강원도|강원특별자치도)\b", "강원특별자치도"),
    (r"^(?:충북|충청북도)\b", "충청북도"),
    (r"^(?:충남|충청남도)\b", "충청남도"),
    (r"^(?:전북|전라북도|전북특별자치도)\b", "전북특별자치도"),
    (r"^(?:전남|전라남도)\b", "전라남도"),
    (r"^(?:경북|경상북도)\b", "경상북도"),
    (r"^(?:경남|경상남도)\b", "경상남도"),
    (r"^(?:제주|제주도|제주특별자치도)\b", "제주특별자치도"),
)


@dataclass(frozen=True)
class QA:
    question: str
    answer: str


@dataclass(frozen=True)
class HubContext:
    path: Path
    text: str
    data: dict[str, Any]
    graph: list[dict[str, Any]]
    url: str
    title: str
    h1: str
    name: str
    kind: str
    item_names: tuple[str, ...]
    district_names: tuple[str, ...]
    category: str


class StableChoice:
    """Namespace-based choices that do not change when another block is added."""

    def __init__(self, key: str) -> None:
        self.key = key

    def number(self, namespace: str) -> int:
        payload = f"{self.key}|{namespace}".encode("utf-8")
        return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")

    def pick(self, namespace: str, values: Sequence[T]) -> T:
        if not values:
            raise ValueError(f"Empty choice list: {namespace}")
        return values[self.number(namespace) % len(values)]

    def order(self, namespace: str, values: Iterable[T]) -> list[T]:
        return sorted(
            values,
            key=lambda value: hashlib.sha256(
                f"{self.key}|{namespace}|{value!r}".encode("utf-8")
            ).digest(),
        )


def clean(value: str) -> str:
    value = re.sub(
        r"<(?:script|style)\b[^>]*>.*?</(?:script|style)>",
        " ",
        value,
        flags=re.I | re.S,
    )
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value)).split())


def avoid_label_body_overlap(label: str, body: str) -> str:
    label_words = re.findall(r"[가-힣A-Za-z0-9]+", label)
    body_words = re.findall(r"[가-힣A-Za-z0-9]+", body)
    if label_words and body_words and label_words[-1] == body_words[0]:
        return "이 단계에서는 " + body
    return body


def repair_visible_copy_splices(text: str, ctx: source.PageContext) -> str:
    replacements = {
        "생활권 이름과 나누어 확인": "생활권 이름과 구분해 확인",
        "상담의 안내 센터": "상담을 안내하는 센터",
        "상담의 방문 주소": "상담의 실제 방문 주소",
        "상담 생활권": "상담 가능 지역",
        "물리센터": "실제 센터",
        " 관련 어떤": "과 관련해 어떤",
        "두 항목은 학생이": "학생이",
    }
    for old, new in replacements.items():
        text = replace_visible_text_nodes(text, old, new)
    for lead in (
        "이어서",
        "이때",
        "상담에서는",
        "준비한",
        "이후",
        "같은",
        "다음 확인에서는",
    ):
        text = replace_visible_text_nodes(text, f"니다, {lead}", f"니다. {lead}")
    for focus in fact_bundle(ctx)["checks"]:
        focus_replacements = {
            f"{focus} 실행 기록": f"{focus} 수행 결과",
            f"{focus} 기록": f"{focus} 관련 기록",
            f"{focus} 실행 시간": f"{focus}에 쓴 시간",
            f"현재 {focus}": focus if focus.startswith("현재 ") else f"현재 {focus}",
            f"{focus} 과제 난도": f"{focus} 관련 과제의 난도",
            f"{focus} 정답보다": f"{focus} 관련 문제의 정답만 보기보다",
            f"{focus} 오답 원인": f"{focus} 관련 오답이 생긴 이유",
            f"{focus} 최근 자료": f"최근 {focus} 자료",
        }
        for old, new in focus_replacements.items():
            if old != new:
                text = replace_visible_text_nodes(text, old, new)
    return text


def replace_visible_text_nodes(text: str, old: str, new: str) -> str:
    """Replace display text without touching attributes, scripts or styles."""

    if not old or old == new:
        return text
    result: list[str] = []
    protected_depth = 0
    for part in re.split(r"(<[^>]+>)", text):
        if part.startswith("<"):
            lowered = part.lower()
            if re.match(r"<\s*/\s*(?:script|style)\b", lowered):
                protected_depth = max(0, protected_depth - 1)
            result.append(part)
            if re.match(r"<\s*(?:script|style)\b", lowered):
                protected_depth += 1
        else:
            result.append(part if protected_depth else part.replace(old, new))
    return "".join(result)


def has_final_consonant(value: str) -> bool:
    """Return whether the final Korean syllable has a jongseong."""

    for character in reversed(value.strip()):
        codepoint = ord(character)
        if 0xAC00 <= codepoint <= 0xD7A3:
            return (codepoint - 0xAC00) % 28 != 0
    return False


def final_jongseong(value: str) -> int:
    for character in reversed(value.strip()):
        codepoint = ord(character)
        if 0xAC00 <= codepoint <= 0xD7A3:
            return (codepoint - 0xAC00) % 28
    return 0


def correct_particle_pair(
    term: str,
    consonant_form: str,
    vowel_form: str,
) -> tuple[str, str]:
    jong = final_jongseong(term)
    # 로 is used after a vowel and after the ㄹ jongseong (index 8).
    if (consonant_form, vowel_form) == ("으로", "로"):
        correct = vowel_form if jong in {0, 8} else consonant_form
    else:
        correct = consonant_form if jong else vowel_form
    wrong = vowel_form if correct == consonant_form else consonant_form
    return correct, wrong


def particle_terms(ctx: source.PageContext) -> set[str]:
    """Terms inserted into templates and therefore requiring particle checks."""

    terms = set(COMMON_PARTICLE_TERMS)
    terms.update(source.check_items(ctx))
    terms.update(label for label, _ in ctx.config["process"])
    terms.update(
        {
            ctx.config["label"],
            source.actual_center_name(ctx),
        }
    )
    schools = actual_schools(ctx)
    terms.update(schools)
    if schools:
        terms.add("·".join(schools[:4]))
    terms.update(
        {
            "현재 교재와 최근 평가자료",
            "완료한 과제와 남은 오답",
            "학생이 혼자 해결한 문제와 도움을 받은 문제",
            "학생이 정확히 해결한 문제와 도움을 받은 문제",
            "학교 진도와 실제 공부 가능한 시간",
            "과제 완료 시점과 다시 풀어 본 기록",
        }
    )
    return {term for term in terms if term}


def fix_particles_for_terms(text: str, terms: Iterable[str]) -> str:
    for term in sorted({value for value in terms if value}, key=len, reverse=True):
        for consonant_form, vowel_form in PARTICLE_PAIRS:
            correct, wrong = correct_particle_pair(
                term,
                consonant_form,
                vowel_form,
            )
            text = text.replace(term + wrong, term + correct)
    return text


def fix_korean_particles(text: str, ctx: source.PageContext) -> str:
    """Correct particles attached to deterministic template substitutions."""

    return fix_particles_for_terms(text, particle_terms(ctx))


def wrong_particle_tokens(ctx: source.PageContext) -> set[str]:
    result: set[str] = set()
    for term in particle_terms(ctx):
        for consonant_form, vowel_form in PARTICLE_PAIRS:
            _, wrong = correct_particle_pair(
                term,
                consonant_form,
                vowel_form,
            )
            result.add(term + wrong)
    return result


def hub_particle_terms(ctx: HubContext) -> set[str]:
    terms = set(COMMON_PARTICLE_TERMS)
    if ctx.category:
        config = source.CATEGORIES[ctx.category]
        checks = config["checks"]
        terms.update(
            checks
            if isinstance(checks, (list, tuple))
            else (value.strip() for value in str(checks).split(","))
        )
        terms.update(label for label, _ in config["process"])
    return terms


def match_one(text: str, pattern: str) -> str:
    found = re.search(pattern, text, re.I | re.S)
    return html.unescape(found.group(1)).strip() if found else ""


def replace_once(text: str, pattern: re.Pattern[str], value: str, label: str) -> str:
    new_text, count = pattern.subn(value, text, count=1)
    if count != 1:
        raise ValueError(f"{label}: expected one target, found {count}")
    return new_text


def node_types(node: dict[str, Any]) -> set[str]:
    value = node.get("@type", [])
    return set(value if isinstance(value, list) else [value])


def find_node(graph: list[dict[str, Any]], kind: str) -> dict[str, Any] | None:
    return next(
        (
            node
            for node in graph
            if isinstance(node, dict) and kind in node_types(node)
        ),
        None,
    )


def stamp_modified(graph: list[dict[str, Any]], *kinds: str) -> None:
    """Stamp only document-like nodes whose content this tool changed."""

    wanted = set(kinds)
    for node in graph:
        if isinstance(node, dict) and node_types(node) & wanted:
            node["dateModified"] = REVISION_DATE


def actual_schools(ctx: source.PageContext) -> list[str]:
    if not ctx.category:
        values = list(
            dict.fromkeys(
                ctx.info.schools["초등"]
                + ctx.info.schools["중등"]
                + ctx.info.schools["고등"]
            )
        )
    else:
        values = ctx.info.schools.get(ctx.config["stage"], [])
    return [value for value in values if source.is_specific_school(value)]


def fact_bundle(ctx: source.PageContext) -> dict[str, Any]:
    checks = source.check_items(ctx)
    schools = actual_schools(ctx)
    grades = source.available_grade_items(ctx)
    return {
        "checks": checks,
        "schools": schools,
        "school_text": "·".join(schools[:4]) if schools else source.SCHOOL_FALLBACK,
        "grades": grades,
        "grade_text": " / ".join(grades) if grades else source.GRADE_FALLBACK,
        "center": source.actual_center_name(ctx),
        "address": source.actual_address(ctx),
        "service_area": source.is_service_area_page(ctx),
    }


def page_topic(ctx: source.PageContext) -> str:
    """Return the stable reader-facing topic without reusing a mutated H1."""

    labels = {
        "": "학원",
        "초등영어학원": "초등 영어학원",
        "초등수학학원": "초등 수학학원",
        "중등영어학원": "중등 영어학원",
        "중등수학학원": "중등 수학학원",
        "고등영어학원": "고등 영어학원",
        "고등수학학원": "고등 수학학원",
    }
    locality = ctx.info.locality.strip() or ctx.locality
    return f"{locality} {labels[ctx.category]}"


def display_h1(ctx: source.PageContext) -> str:
    """Use an accurate intent label when the locality is a service area."""

    topic = page_topic(ctx)
    if not source.is_service_area_page(ctx):
        return topic
    if ctx.category:
        subject_label = topic.removeprefix(ctx.info.locality).strip()
        return f"{ctx.info.locality}에서 상담 가능한 {subject_label} 안내"
    return f"{ctx.info.locality}에서 상담 가능한 학원 안내"


def display_title(ctx: source.PageContext) -> str:
    current = match_one(ctx.text, r"<title>(.*?)</title>")
    return current.replace(ctx.title, display_h1(ctx), 1)


def official_address_region(ctx: source.PageContext) -> str:
    """Derive an official province-level name from the authoritative address."""

    address = source.actual_address(ctx).strip()
    for pattern, region in OFFICIAL_REGION_PATTERNS:
        if re.search(pattern, address):
            return region
    # The aggregate navigation labels (충청/경상/전라) are intentionally not
    # used as PostalAddress regions.  If an old address cannot disambiguate
    # them, omitting the optional value is safer than publishing a false one.
    fallback = {
        "서울": "서울특별시",
        "부산": "부산광역시",
        "대구": "대구광역시",
        "인천": "인천광역시",
        "광주": "광주광역시",
        "대전": "대전광역시",
        "울산": "울산광역시",
        "경기": "경기도",
        "강원": "강원특별자치도",
        "제주": "제주특별자치도",
    }
    return fallback.get(ctx.info.region, "")


def official_address_locality(ctx: source.PageContext) -> str:
    if official_address_region(ctx) == "세종특별자치시":
        # The legacy navigation field contains the road name 새롬중앙로.  The
        # physical centre represented by the shared registration identity is
        # in 새롬동; 다정동 remains a Service.areaServed value only.
        return "새롬동"
    address_parts = source.actual_address(ctx).strip().split()
    if len(address_parts) > 1:
        value = address_parts[1]
        if re.search(r"(?:특별자치시|특별시|광역시|시|군|구)$", value):
            return value
    return ""


def relationship_sentence(ctx: source.PageContext) -> str:
    facts = fact_bundle(ctx)
    picker = detail_picker(ctx)
    checks = picker.order("relationship-checks", facts["checks"])
    focus_a, focus_b, focus_c = checks[0], checks[1], checks[2]
    variants = [
        f"{focus_a}과 {focus_b} 상담의 실제 방문 센터는 {facts['center']}입니다. {focus_a} 상담 주소는 {facts['address']}이며 생활권 이름과 방문 위치를 구분해 확인해 주세요.",
        f"{focus_b} 관련 자료와 {focus_c} 계획 상담은 {facts['center']}에서 안내하며 실제 방문 주소는 {facts['address']}입니다. {focus_c} 상담에서 페이지의 동네명은 서비스 생활권을 뜻합니다.",
        f"{focus_c}과 {focus_a} 점검을 준비할 때 확인할 실제 방문 센터는 {facts['center']}입니다. {focus_c} 상담 주소는 {facts['address']}이며 생활권 표시와 센터 위치는 서로 구분합니다.",
        f"이 페이지의 {focus_a}·{focus_c} 상담 가능 지역과 실제 방문 위치는 구분해야 합니다. {focus_c} 상담의 실제 방문 센터는 {facts['center']}입니다. {focus_c} 상담 주소는 {facts['address']}입니다. {focus_a} 자료를 상담하기 전에 센터명과 주소를 따로 확인해 주세요.",
        f"{focus_b}과 {focus_a} 자료를 상담할 실제 센터는 {facts['center']}입니다. {focus_b} 상담의 실제 방문 주소는 {facts['address']}이며 동네명만 보고 센터 위치를 추정하지 않습니다.",
        f"{focus_c} 수행 자료를 점검하는 상담을 안내하는 센터는 {facts['center']}입니다. {focus_c} 상담의 실제 방문 주소는 {facts['address']}이며 페이지의 생활권 이름과 구분해 확인해 주세요.",
        f"이 지역의 {focus_a}·{focus_b} 상담은 {facts['center']}에서 안내합니다. {focus_a} 상담 방문지는 {facts['address']}이며 안내 지역과 실제 센터 주소가 다를 수 있습니다.",
        f"{focus_b} 우선순위와 {focus_c} 재확인의 실제 방문 센터는 {facts['center']}입니다. {focus_b} 상담 주소는 {facts['address']}이며 지역 안내명과 별도로 확인합니다.",
    ]
    sentence = picker.pick("relationship-frame-v4", variants)
    return sentence


def display_location_guide(value: str) -> str:
    value = re.sub(r"https?://\S+", " ", value or "")
    value = re.sub(r"학원\s*위치\s*안내드립니다[\^~!\s]*", " ", value)
    return re.sub(r"\s+", " ", value).strip(" ·,;:-")


def build_hero_center_fact(ctx: source.PageContext) -> str:
    picker = detail_picker(ctx)
    facts = fact_bundle(ctx)
    checks = picker.order("hero-center-fact-checks", facts["checks"])
    focus_a, focus_b = checks[0], checks[1]
    label = picker.pick(
        "hero-center-fact-label",
        [
            f"{focus_a} 상담 방문 정보",
            f"{focus_b} 점검 센터 정보",
            f"{focus_a}·{focus_b} 상담 장소",
            f"{focus_b} 계획 방문 기준",
        ],
    )
    strong = picker.pick(
        "hero-center-fact-strong",
        [
            f"{focus_a} 상담 센터 확인",
            f"{focus_b} 상담 장소 확인",
            "등록 센터 정보 확인",
            f"{focus_a} 방문 기준 확인",
        ],
    )
    if facts["service_area"]:
        notes = [
            f"{focus_a} 상담 가능 지역과 실제 방문 위치는 아래 정보에서 구분합니다.",
            f"{focus_b} 상담을 안내하는 센터명과 주소는 아래 확인 정보에 표시했습니다.",
            f"{focus_a}·{focus_b} 상담권역과 방문 센터는 서로 다를 수 있어 아래에서 함께 확인합니다.",
            f"{focus_b} 계획을 상담할 실제 센터명과 주소는 아래 사실 영역에서 확인합니다.",
        ]
    else:
        notes = [
            f"{focus_a} 상담의 등록 명칭과 주소는 아래 확인 정보에서 안내합니다.",
            f"{focus_b} 점검을 상담할 센터명과 실제 주소는 아래 사실 영역에 표시했습니다.",
            f"{focus_a}·{focus_b} 상담 장소는 아래 센터 정보에서 확인합니다.",
            f"{focus_b} 계획을 상담하기 전에 아래 등록 정보와 주소를 함께 확인합니다.",
        ]
    note = picker.pick("hero-center-fact-note", notes)
    return f'''              <div class="hero-center-fact">
                <span>{html.escape(label)}</span>
                <strong>{html.escape(strong)}</strong>
                <small>{html.escape(note)}</small>
              </div>'''


def build_refined_verified_section(ctx: source.PageContext) -> str:
    """Render source-backed centre facts with page-specific explanatory copy."""

    picker = detail_picker(ctx)
    facts = fact_bundle(ctx)
    checks = picker.order("verified-checks", facts["checks"])
    focus_a, focus_b, focus_c = checks[0], checks[1], checks[2]
    schools = facts["schools"]
    school_markup = (
        "".join(f"<span>{html.escape(school)}</span>" for school in schools)
        if schools
        else "<span>재학 학교 진도는 상담 시 확인</span>"
    )
    if ctx.info.tuition_url:
        tuition_block = (
            '          <a class="text-link" href="'
            + html.escape(ctx.info.tuition_url, quote=True)
            + '" target="_blank" rel="noopener noreferrer">센터 교습비 자료 확인</a>\n'
        )
    else:
        tuition_block = (
            '          <p class="verified-note fee-source-note">'
            + html.escape(f"{focus_a}·{focus_b} 상담의 센터 제공 교습비 자료가 없어 금액과 횟수는 상담 시 확인해야 합니다.")
            + "</p>\n"
        )
    location_guide = display_location_guide(ctx.info.location_guide)
    location_row = (
        f'            <div><dt>위치 안내</dt><dd>{html.escape(location_guide)}</dd></div>'
        if not ctx.category and location_guide
        else ""
    )
    relationship_label = (
        "연결 상담 센터 정보" if facts["service_area"] else "실제 방문 센터 정보"
    )
    relationship_note = picker.pick(
        "verified-relationship-v4",
        [
            f"이 페이지의 {focus_a}·{focus_b} 상담 안내 센터는 {facts['center']}입니다. {focus_b} 상담의 실제 방문 주소는 {facts['address']}이며 생활권 이름과 구분해 확인해 주세요.",
            f"이 페이지는 {focus_b}과 {focus_c} 상담 가능 지역을 안내합니다. {focus_b} 상담의 방문 센터는 {facts['center']}입니다. {focus_c} 확인을 위한 실제 주소는 {facts['address']}입니다.",
            f"{focus_c}과 {focus_a} 자료를 상담할 곳은 {facts['center']}입니다. {focus_c} 상담 주소는 {facts['address']}이며 이를 방문 기준으로 삼고 동네명만으로 위치를 추정하지 않습니다.",
            f"학생의 {focus_a} 상담은 {facts['center']}에서 안내합니다. {focus_a} 상담의 실제 방문지는 {facts['address']}이며 센터명과 주소를 함께 확인해야 합니다.",
            f"{focus_b} 수행 결과와 {focus_c} 재확인은 {facts['center']}에서 상담합니다. {focus_c} 상담의 실제 방문 주소는 {facts['address']}이고 지역 표시는 상담 가능 범위를 뜻합니다.",
            f"제공 자료에서 {focus_c}·{focus_b} 상담 센터는 {facts['center']}입니다. {focus_b} 상담의 실제 방문 주소는 {facts['address']}이며 생활권과 별도로 확인해 주세요.",
        ],
    )
    if schools:
        school_basis = f"제공된 참고 학교 목록은 {focus_a} 관련 교재·진도를 확인하는 상담 자료로만 사용합니다."
    else:
        school_basis = f"제공 자료에 구체적인 학교명이 없어 임의로 추가하지 않았으며 {focus_a} 관련 재학 학교의 교재·진도를 상담에서 확인합니다."
    verified_note = (
        school_basis
        + " "
        + contextual_learning_sentence(ctx, picker, "verified-context")
    )
    return f'''    <section id="verified-center" class="local-section verified-center-section">
      <div class="wrap verified-center-grid">
        <article class="verified-center-card">
          <p class="eyebrow">{html.escape(relationship_label)}</p>
          <h2>{html.escape(facts["center"])}</h2>
          <p class="verified-note">{html.escape(relationship_note)}</p>
          <dl class="verified-data-list">
            <div><dt>수업 가능 학년</dt><dd>{html.escape(facts["grade_text"])}</dd></div>
            <div><dt>주소</dt><dd>{html.escape(facts["address"])}</dd></div>
            <div><dt>등록 명칭</dt><dd>{html.escape(" ".join(ctx.info.registration_name.split()))}</dd></div>
            <div><dt>등록 정보</dt><dd>{html.escape(source.registration_value(ctx))}</dd></div>
{location_row}
          </dl>
{tuition_block}          <div class="verified-school-list" role="group" aria-label="상담 참고 학교">{school_markup}</div>
          <p class="verified-note">{html.escape(verified_note)}</p>
          <p class="verified-note source-note">{html.escape(build_source_note(ctx))}</p>
        </article>
        <figure class="verified-map-card">
          {ctx.map_image}
          <figcaption>실제 방문 센터 위치를 확인하는 지도 이미지입니다.</figcaption>
        </figure>
      </div>
    </section>'''


def build_source_note(ctx: source.PageContext) -> str:
    picker = detail_picker(ctx)
    basis = source.source_basis(ctx)
    checks = picker.order("source-note-checks", fact_bundle(ctx)["checks"])
    focus_a, focus_b = checks[0], checks[1]
    registration = source.registration_value(ctx)
    label = ctx.config["label"]
    variants = [
        f"{label} 확인 자료: {basis} · 등록 정보 {registration} · 점검 기준 {focus_a}·{focus_b} · 정리일 {REVISION_DATE}",
        f"{label} 안내 근거: {basis} · 등록 정보 {registration} · 확인 항목 {focus_b}·{focus_a} · 최종 확인 {REVISION_DATE}",
        f"{label} 센터 정보 출처: {basis} · 등록 정보 {registration} · 상담 자료 {focus_a}·{focus_b} · 페이지 확인일 {REVISION_DATE}",
        f"{label} 작성 기준: {basis} · 등록 정보 {registration} · 학습 기록 {focus_b}·{focus_a} · 정보 정리 {REVISION_DATE}",
    ]
    return picker.pick("source-note-v2", variants)


def detail_picker(ctx: source.PageContext) -> StableChoice:
    return StableChoice(ctx.page_url)


def selected_process(
    ctx: source.PageContext,
    picker: StableChoice,
    namespace: str,
) -> tuple[str, str]:
    label, variants = picker.pick(namespace + "-step", ctx.config["process"])
    return label, picker.pick(namespace + "-action", variants)


def contextual_learning_sentence(
    ctx: source.PageContext,
    picker: StableChoice,
    namespace: str,
) -> str:
    """Return a deterministic, page-specific sentence without repeating locality SEO terms."""

    checks = picker.order(namespace + "-checks", fact_bundle(ctx)["checks"])
    focus_a, focus_b, focus_c = checks[0], checks[1], checks[2]
    student = picker.pick(namespace + "-student", ctx.config["students"])
    process_label, _process_action = selected_process(ctx, picker, namespace + "-process")
    frames = [
        f"{focus_a}에서 확인된 어려움과 {focus_b} 관련 수행 결과를 나누고 {process_label} 단계에서 {focus_c}을 다시 살핍니다.",
        f"{student}의 경우 {focus_b} 관련 자료를 먼저 준비하고 {focus_a}과 {focus_c}의 확인 순서를 정합니다.",
        f"{process_label} 결과는 {focus_c} 자료와 비교하고 {focus_a}에서 달라진 부분을 다음 점검에 남깁니다.",
        f"{focus_a}과 {focus_b}을 동시에 늘리지 않고 {focus_c}을 확인할 날짜와 {process_label} 분량을 따로 정합니다.",
        f"{student}에게는 {focus_c} 상태를 확인하고 {focus_b}과 {focus_a} 중 먼저 바꿀 항목을 정합니다.",
        f"최근 자료에서 {focus_b}과 {focus_c}을 구분하고 {process_label} 결과로 {focus_a}의 변화를 확인합니다.",
        f"{focus_c} 관련 어려움이 반복되는 문제를 표시하고 {focus_a} 자료와 {focus_b}에 쓴 시간을 함께 비교합니다.",
        f"{process_label} 단계에서는 {focus_b}을 완료한 시점과 {focus_c}을 다시 확인한 결과로 {focus_a} 범위를 조정합니다.",
    ]
    return picker.pick(namespace + "-frame", frames)


def contextualize_statement(
    ctx: source.PageContext,
    picker: StableChoice,
    namespace: str,
    statement: str,
) -> str:
    """Add a page-specific, grammatical lead-in to shared factual copy."""

    checks = picker.order(namespace + "-checks", fact_bundle(ctx)["checks"])
    focus_a, focus_b, focus_c = checks[0], checks[1], checks[2]
    label, _ = selected_process(ctx, picker, namespace + "-process")
    lead_ins = [
        f"{focus_a}과 {focus_b} 자료를 함께 볼 때",
        f"{label} 순서를 정하는 과정에서",
        f"{focus_b} 수행 결과와 {focus_c} 확인 날짜를 비교할 때",
        f"{focus_a}·{focus_c} 상태를 다시 확인하면서",
        f"{focus_b}에서 달라져야 할 부분을 정리할 때",
        f"{focus_c} 관련 어려움과 {focus_b}에 쓴 시간을 함께 살필 때",
        f"{focus_a} 결과와 {focus_b} 관련 자료를 대조할 때",
        f"{label} 단계의 {focus_c} 자료를 준비하면서",
    ]
    lead_in = picker.pick(namespace + "-lead-in", lead_ins)
    return f"{lead_in} {statement.strip()}"


def build_meta_description(ctx: source.PageContext) -> str:
    picker = detail_picker(ctx)
    checks = picker.order("meta-description-checks", fact_bundle(ctx)["checks"])
    focus_a, focus_b, focus_c = checks[0], checks[1], checks[2]
    process_label, _ = selected_process(ctx, picker, "meta-description-process")
    locality = ctx.info.locality
    label = ctx.config["label"]
    candidates = [
        f"{locality} {label}: {focus_a}과 {focus_b} 관련 자료를 살피고 {process_label} 순서, 실제 센터 주소와 가능 학년을 안내합니다.",
        f"{locality} {label}: {focus_b}·{focus_c} 상태를 나누어 보고 {focus_a} 점검 자료, 방문 센터와 상담 범위를 정리했습니다.",
        f"{locality} {label}: {process_label} 전 {focus_c}과 {focus_a}을 확인하고 실제 방문 주소, 학교 참고자료와 가능 학년을 안내합니다.",
        f"{locality} {label}: {focus_a} 어려움과 {focus_c} 수행 결과를 구분해 {process_label} 계획과 센터 확인 정보를 안내합니다.",
        f"{locality} {label}: 최근 자료에서 {focus_b}과 {focus_a}을 점검하고 학생 일정에 맞춘 {process_label} 순서와 방문 정보를 정리했습니다.",
        f"{locality} {label}: {focus_c} 재확인 자료와 {focus_b}에 쓴 시간을 살피고 가능 학년, 실제 센터 주소와 상담 기준을 안내합니다.",
        f"{locality} {label}: {process_label} 결과로 {focus_a}과 {focus_c}의 우선순위를 정하고 학교·학년·방문 정보를 확인합니다.",
        f"{locality} {label}: {focus_b}에서 막힌 부분과 {focus_c} 완료 결과를 나누어 {focus_a} 점검 순서와 실제 상담 정보를 안내합니다.",
    ]
    eligible = [candidate for candidate in candidates if 60 <= len(candidate) <= 80]
    if not eligible:
        raise ValueError(f"No 60-80 character description: {ctx.path}")
    return picker.pick("meta-description-frame", eligible)


def service_area_name_from_info(info: source.CenterInfo) -> str:
    raw_region = info.region.strip()
    explicit_regions = {
        "서울": "서울특별시",
        "부산": "부산광역시",
        "대구": "대구광역시",
        "인천": "인천광역시",
        "광주": "광주광역시",
        "대전": "대전광역시",
        "울산": "울산광역시",
        "경기": "경기도",
        "강원": "강원특별자치도",
        "제주": "제주특별자치도",
    }
    address_region = ""
    for pattern, candidate in OFFICIAL_REGION_PATTERNS:
        if re.search(pattern, info.address.strip()):
            address_region = candidate
            break
    if address_region == "세종특별자치시":
        return f"세종특별자치시 {info.locality}"
    region = explicit_regions.get(raw_region, address_region or raw_region)
    locality = source.locality_without_district_prefix(info)
    return " ".join(
        part for part in (region, info.district.strip(), locality) if part
    )


def service_area_name(ctx: source.PageContext) -> str:
    return service_area_name_from_info(ctx.info)


def build_hero_answer(ctx: source.PageContext) -> str:
    picker = detail_picker(ctx)
    facts = fact_bundle(ctx)
    checks = picker.order("hero-focus-order", facts["checks"])
    focus_a, focus_b = checks[0], checks[1]
    student = picker.pick("hero-student", ctx.config["students"])
    process_label, process_action = selected_process(ctx, picker, "hero")
    evidence = picker.pick(
        "hero-evidence",
        [
            "현재 교재와 최근 평가자료",
            "완료한 과제와 남은 오답",
            "최근 시험지와 주간 학습기록",
            "학생이 혼자 해결한 문제와 도움을 받은 문제",
            "학교 진도와 실제 공부 가능한 시간",
            "교재 진도와 반복해서 틀린 문제",
            "과제 완료 시점과 다시 풀어 본 기록",
            "최근 단원에서 정확히 해결한 문제와 도움을 받은 문제",
        ],
    )
    frames = [
        (
            f"학생 상담은 성적표 한 장보다 {evidence}에서 시작합니다. "
            f"{focus_a}와 {focus_b}을 각각 살펴보고 {process_action} "
            f"{process_label} 단계의 실제 분량은 학생 일정에 맞춰 정합니다."
        ),
        (
            f"{student}이라면 문제 수를 늘리기 전에 {focus_a}에서 막힌 부분과 "
            f"{focus_b} 관련 자료를 구분해야 합니다. {evidence}을 준비하면 "
            f"{process_action} {focus_a}을 다시 볼 날짜도 함께 정할 수 있습니다."
        ),
        (
            f"{ctx.config['label']} 상담에서는 {evidence}을 바탕으로 {focus_a}에서 막힌 부분과 "
            f"{focus_b} 관련 계획이 실제로 이어졌는지를 나누어 봅니다. {process_action} "
            f"학생이 한 주 안에 이어갈 {focus_a}·{focus_b} 범위부터 계획합니다."
        ),
        (
            f"현재 점수만으로 {focus_a}·{focus_b} 시작 범위를 정하지 않습니다. {focus_a}을 혼자 해결할 수 있는지, "
            f"{focus_b}을 계획대로 이어 갔는지 {evidence}에서 확인하고 "
            f"{process_label} 순서를 조정합니다."
        ),
        (
            f"상담을 준비한다면 {evidence}에 {focus_a} 관련 어려움이 "
            f"나타난 부분을 표시해 주세요. {focus_b}까지 한꺼번에 넓히지 않고 "
            f"{process_action} 실행 결과로 다음 범위를 정합니다."
        ),
        (
            f"{student}의 학습 계획은 {focus_a}과 {focus_b}을 같은 문제로 묶지 않는 데서 시작합니다. "
            f"{evidence}을 검토하고 {process_action} {focus_a}·{focus_b} 개설 학년과 시간은 센터 자료로 확인합니다."
        ),
        (
            f"최근 기록에서 {focus_a}이 어려웠던 문제와 {focus_b}을 마치지 못한 시점을 따로 봅니다. "
            f"{process_action} {focus_a}과 {focus_b}을 같은 기준으로 다시 확인할 문제와 날짜를 정합니다."
        ),
        (
            f"{ctx.config['label']}의 첫 단계는 {evidence}에서 학생이 스스로 해결한 범위를 찾는 일입니다. "
            f"{focus_a}과 {focus_b} 중 우선할 항목을 정하고 {process_action}"
        ),
    ]
    return picker.pick("hero-frame-v3", frames) + " " + relationship_sentence(ctx)


def process_body(
    ctx: source.PageContext,
    picker: StableChoice,
    index: int,
    label: str,
    variants: Sequence[str],
) -> str:
    facts = fact_bundle(ctx)
    checks = picker.order(f"process-{index}-focus", facts["checks"])
    focus_a = checks[index % len(checks)]
    focus_b = checks[(index + 1) % len(checks)]
    action = picker.pick(f"process-{index}-action", variants).rstrip(".。 ")
    frames = [
        f"{focus_a} 관련 어려움이 나타난 문제를 표시하고 {action}. 다음 점검에서는 {label} 결과를 {focus_b} 관련 자료와 비교합니다.",
        f"학생의 최근 자료에서 {focus_a}을 먼저 살피고 {action}. 완료한 {label} 범위는 {focus_b} 자료로 재확인합니다.",
        f"{focus_a}과 {focus_b}을 동시에 늘리지 않고 우선순위를 정해 {action}. {label} 단계에서는 학생이 설명할 수 있는 범위만 다음 단계로 옮깁니다.",
        f"최근 자료에서 {focus_a} 관련 어려움이 드러난 부분을 찾고 {action}. 다른 문제에서도 어려움이 남는지 확인하고 {label}의 다음 범위를 정합니다.",
        f"{label} 단계에서는 {focus_b}을 기준으로 {action}. 학생의 주중·주말 학습 시간에 맞춰 {label} 일정을 조정합니다.",
        f"{focus_a}에서 확인된 어려움을 개념·실수·시간으로 구분한 다음 {action}. {focus_b} 자료를 보고 다음 {label} 단계의 분량을 조정합니다.",
        f"학교 진도와 별개로 학생의 현재 {focus_a} 상태를 살펴보고 {action}. 이후 {label} 과정에서 {focus_b}의 달라진 점도 기록합니다.",
        f"학생이 {focus_a} 상태를 직접 설명할 수 있는지 살펴보고 {action}. {label}을 진행한 뒤에도 같은 어려움이 반복되면 앞 단계를 다시 살펴봅니다.",
    ]
    return picker.pick(f"process-{index}-frame-v3", frames)


def build_primary_section(ctx: source.PageContext) -> str:
    picker = detail_picker(ctx)
    facts = fact_bundle(ctx)
    checks = picker.order("primary-focus", facts["checks"])
    focus_a, focus_b, focus_c = checks[0], checks[1], checks[2]
    student = picker.pick("primary-student", ctx.config["students"])
    heading = picker.pick(
        "primary-heading-v3",
        [
            "학생의 학습 신호를 나누는 기준",
            f"{ctx.config['label']} 시작 범위를 정하는 방법",
            f"최근 자료에서 우선순위를 찾는 과정",
            "상담 전에 확인할 학습 기록",
            f"학생 일정에 맞는 실행 순서를 만드는 법",
            f"오답과 진도를 함께 살펴야 하는 이유",
            f"첫 상담이 현재 교재에서 시작되는 이유",
            f"{ctx.config['subject']} 학습 계획을 구체화하는 순서",
        ],
    )
    paragraph1 = picker.pick(
        "primary-intro",
        [
            f"학생 상담에서는 {focus_a}, {focus_b}, {focus_c}을 같은 문제로 묶지 않습니다. {student}이라면 최근 자료에서 각 어려움이 나타난 시점을 구분해야 실행 가능한 순서를 정할 수 있습니다.",
            f"{student}에게는 학습량을 바로 늘리기보다 {focus_a}과 {focus_b}에서 확인된 문제를 먼저 구분하는 과정이 필요합니다. {focus_c} 결과까지 확인하면 학생이 혼자 이어갈 범위와 도움이 필요한 범위가 분명해집니다.",
            f"첫 확인 항목은 {focus_a}입니다. {focus_b}과 {focus_c}이 함께 흔들리는 경우에는 최근 교재·시험지·과제 기록을 나누어 보고 한 주 안에 실행할 순서를 정합니다.",
            f"현재 점수가 같아도 {focus_a}에서 어려움을 겪는 학생과 {focus_b}에서 어려움을 겪는 학생의 계획은 달라야 합니다. 상담에서는 {focus_c}까지 살핀 뒤 다음 확인 시점을 정합니다.",
            f"상담에서는 {focus_a} 관련 어려움, {focus_b}의 실행 가능성, {focus_c}의 재확인 방법을 따로 정리합니다. 학생이 실제로 완료할 {focus_a}·{focus_c} 분량부터 시작합니다.",
            f"{student}이라면 최근 단원에서 {focus_a} 상태를 직접 설명할 수 있는지 먼저 봅니다. 이후 {focus_b}과 {focus_c}을 순서대로 확인해 반복되는 어려움과 일시적인 실수를 나눕니다.",
        ],
    )
    school_clause = (
        f"제공된 참고 학교 목록의 {focus_a} 관련 교재·진도는 상담에서 확인합니다"
        if facts["schools"]
        else f"제공 자료에 구체적인 학교명이 없어 {focus_a} 관련 재학 학교 정보는 상담에서 확인합니다"
    )
    grade_clause = (
        f"센터 자료의 가능 학년은 {facts['grade_text']}이며 {focus_b} 개설 시간은 등록 전에 다시 확인합니다"
        if facts["grades"]
        else f"가능 학년 자료가 없어 {focus_b} 개설 여부와 시간을 상담에서 확인합니다"
    )
    paragraph2 = picker.pick(
        "primary-facts-v4",
        [
            f"{school_clause}. {grade_clause}. {focus_c} 자료와 실제 방문 센터 정보도 함께 대조합니다.",
            f"{focus_c} 범위를 정할 때 {school_clause}. 실제 방문 센터와 주소는 아래 사실 영역에서 확인하며 {grade_clause}.",
            f"{focus_c} 상담의 실제 방문 센터와 주소는 사실 영역에서 확인합니다. {school_clause}. {grade_clause}.",
            f"{school_clause}. {grade_clause}. 방문 전 센터 주소와 {focus_c} 상담 일정을 따로 확인합니다.",
            f"{focus_b} 상담 전에 센터 자료의 방문 정보를 확인합니다. {school_clause}. {grade_clause}.",
            f"{focus_c} 자료를 준비할 때 {school_clause}. {grade_clause}. {focus_a} 상담 장소는 센터 정보에서 확인합니다.",
        ],
    )
    items = []
    for index, (label, variants) in enumerate(ctx.config["process"]):
        body = process_body(ctx, picker, index, label, variants)
        body = avoid_label_body_overlap(label, body)
        items.append(
            f"            <li><strong>{html.escape(label)}</strong>: {html.escape(body)}</li>"
        )
    summary_items = [
        (
            "우선 확인",
            f"{focus_a} 관련 어려움이 나타난 시점과 {focus_b} 자료",
        ),
        (
            "학생 상황",
            f"{student}에게 필요한 {focus_c} 점검",
        ),
        ("가능 학년", facts["grade_text"]),
        (
            "학교 참고",
            f"제공 목록 {len(facts['schools'])}곳" if facts["schools"] else source.SCHOOL_FALLBACK,
        ),
        ("실제 안내 센터", "아래 센터 정보에서 확인"),
        (
            "상담에서 결정",
            picker.pick(
                "summary-decision",
                [
                    f"{focus_a}부터 시작할지 {focus_b}을 함께 볼지",
                    f"{focus_c} 재확인 시점과 한 주 실행 분량",
                    "최근 자료로 확인할 범위와 다음 점검 날짜",
                    f"{focus_a} 보완과 {focus_c} 복습의 우선순위",
                    "학생 일정에 맞는 과제·복습 분량",
                    f"{focus_b} 결과를 확인할 교재와 문제 범위",
                ],
            ),
        ),
    ]
    summary_markup = "\n".join(
        f"            <li><strong>{html.escape(label)}</strong> {html.escape(value)}</li>"
        for label, value in summary_items
    )
    return f'''    <section id="learning-plan" class="local-section">
      <div class="wrap local-grid">
        <article class="local-card">
          <h2>{html.escape(heading)}</h2>
          <p>{html.escape(paragraph1)}</p>
          <p>{html.escape(paragraph2)}</p>
          <h3>{html.escape(ctx.config["label"])} 실행 순서</h3>
          <ul class="process-list">
{chr(10).join(items)}
          </ul>
          {ctx.image_block}
        </article>
        <aside class="local-card" aria-labelledby="consult-summary-title">
          <h2 id="consult-summary-title">상담 요약</h2>
          <ul class="summary-list">
{summary_markup}
          </ul>
        </aside>
      </div>
    </section>'''


def student_card_answer(
    ctx: source.PageContext,
    picker: StableChoice,
    student: str,
    index: int,
) -> str:
    facts = fact_bundle(ctx)
    checks = picker.order(f"student-{index}-checks", facts["checks"])
    focus_a, focus_b = checks[0], checks[1]
    process_label, process_action = selected_process(
        ctx, picker, f"student-{index}"
    )
    frames = [
        f"최근 자료에서 {focus_a} 관련 어려움이 나타난 문제를 표시합니다. {process_action} 이후 {focus_b} 자료를 확인해 {process_label} 범위를 조정합니다.",
        f"{focus_a}과 {focus_b}을 한꺼번에 늘리지 않고 학생이 혼자 설명할 수 있는 부분부터 구분합니다. {process_action} {focus_b} 완료 결과는 {focus_a} 자료와 다음 상담에서 다시 비교합니다.",
        f"현재 교재에서 {focus_a} 관련 어려움이 처음 드러난 부분을 찾습니다. {process_action} 다른 문제에서는 {focus_b} 관련 어려움이 반복되는지 확인합니다.",
        f"학습 계획은 {focus_a}을 진단한 뒤 {focus_b}을 실행 가능한 분량으로 나누어 세웁니다. {process_label} 단계의 기록은 학생의 실제 공부 시간과 함께 살펴봅니다.",
        f"{facts['grade_text']} 범위가 제공 자료에 표시되어 있어도 {focus_a}과 {focus_b}의 실제 진도는 학생마다 다를 수 있습니다. 두 항목의 차이를 정리하고 {process_action}",
        f"{focus_a}과 {focus_b}을 살필 때 이 학생의 어려움을 성적만으로 판단하지 않습니다. 두 항목에서 확인된 문제와 달라진 점을 구분하고 {process_action}",
        f"{focus_a}에서 도움이 필요한 부분과 혼자 해결한 부분을 나눈 다음 {process_action} 다음 점검에서는 {focus_b}의 변화가 남았는지 확인합니다.",
        f"{focus_b}의 미완료 원인을 분량·난도·시간으로 나눕니다. {focus_a}부터 다시 살펴보고 {process_action}",
    ]
    answer = picker.pick(f"student-{index}-frame-v3", frames)
    if index == 0:
        answer += f" {focus_a}과 {focus_b}의 실제 개설 여부는 센터 시간표와 대조합니다."
    return answer


def build_quality_section(ctx: source.PageContext) -> str:
    picker = detail_picker(ctx)
    facts = fact_bundle(ctx)
    students = picker.order("quality-students", ctx.config["students"])[:3]
    checks = picker.order("quality-checks", facts["checks"])
    focus_a, focus_b, focus_c, focus_d = checks[:4]
    cards = []
    for index, student in enumerate(students):
        body = student_card_answer(ctx, picker, student, index)
        cards.append(
            f'''            <article class="geo-answer-card">
              <strong>{html.escape(student)}</strong>
              <p>{html.escape(body)}</p>
            </article>'''
        )
    fit_intro = picker.pick(
        "quality-intro-v3",
        [
            f"상담에서는 {focus_a}과 {focus_b}에서 확인된 어려움을 먼저 나눈 뒤 {focus_c}이 계획대로 이어졌는지 확인합니다. 아래 예시는 {focus_a}과 {focus_c} 상태를 살피기 위한 기준이며 실제 범위는 최근 자료로 결정합니다.",
            f"같은 학년이라도 {focus_a}, {focus_b}, {focus_c} 상태는 서로 다를 수 있습니다. 학생의 {focus_c} 상태를 확인한 뒤 한 가지 목표부터 정합니다.",
            f"{ctx.config['label']} 계획은 학생 유형을 정답처럼 분류하는 일이 아닙니다. {focus_a}과 {focus_d} 관련 자료를 바탕으로 우선 확인할 항목을 좁히는 과정입니다.",
            f"학생은 최근 자료에서 {focus_b} 관련 어려움이 반복되는지, {focus_c}을 계획대로 실행했는지 따로 살펴야 합니다.",
            f"아래 {focus_a}·{focus_d} 항목은 상담 준비를 돕기 위한 점검 기준입니다. 실제 시작 범위는 {focus_a}과 {focus_d} 기록을 확인한 뒤 정합니다.",
            f"센터 상담에서는 현재 결과보다 {focus_a}의 막힘과 {focus_b}의 실행 습관을 먼저 구분합니다. {focus_a}과 {focus_b} 중 해당되는 상황부터 확인해 보세요.",
        ],
    )
    fit_intro = contextualize_statement(
        ctx, picker, "quality-intro-context", fit_intro
    )
    recent = picker.pick(
        "check-recent",
        [
            f"최근 교재·시험지·과제에서 {focus_a}과 {focus_b}이 드러나는 부분을 각각 표시합니다.",
            f"{focus_a} 관련 어려움이 나타난 자료와 {focus_c} 관련 미완료 기록을 함께 준비합니다.",
            f"혼자 해결한 문제, 설명을 듣고 푼 문제, 다시 틀린 문제를 나누어 {focus_b} 상태를 확인합니다.",
            f"최근 단원의 정답률보다 {focus_a}에서 처음 어려웠던 문제와 {focus_d} 재확인 기록을 챙깁니다.",
            f"사용 중인 교재와 평가자료에서 {focus_c}이 반복되는 날짜와 문제 범위를 적습니다.",
            f"{students[0]} 상황을 확인할 수 있도록 최근 과제 완료 기록과 {focus_a} 점검 자료를 준비합니다.",
        ],
    )
    if facts["schools"]:
        school = picker.pick(
            "check-school",
            [
                "제공된 참고 학교 목록과 별개로 재학 학교의 실제 교재·진도·시험 일정을 상담에서 확인합니다.",
                "참고 학교 정보만 따르지 않고 학생이 사용하는 교재와 시험 범위를 직접 준비합니다.",
                "제공된 학교 목록만으로 수업을 정하지 않고 현재 진도와 센터 시간표를 대조합니다.",
                "재학 학교가 참고 목록에 포함되더라도 실제 시험 범위와 일정은 상담 때 다시 확인합니다.",
            ],
        )
    else:
        school = picker.pick(
            "check-school",
            [
                "제공 자료에 학교명이 없어 임의로 넣지 않았습니다. 재학 학교의 교재·진도·시험 일정을 준비합니다.",
                "학교 정보는 상담에서 확인하므로 현재 교재와 다음 시험 일정을 직접 알려 주세요.",
                "재학 학교의 실제 진도와 시험 범위를 준비하고 센터의 가능 시간표와 대조합니다.",
                "학교명 대신 학생이 사용하는 교재, 최근 평가자료, 다음 시험 일정을 기준으로 범위를 정합니다.",
            ],
        )
    time = picker.pick(
        "check-time",
        [
            f"{students[1]}의 경우 평일과 주말에 {focus_b}을 실제로 이어갈 수 있는 시간을 따로 계산합니다.",
            f"{focus_c}과 {focus_d}에 사용할 요일별 시간을 학교·다른 일정과 함께 적습니다.",
            f"계획한 분량이 무너지지 않도록 {focus_a} 확인 시간과 {focus_b}에 쓸 시간을 구분합니다.",
            f"한 주에 사용할 수 있는 시간을 먼저 적고 {focus_c}과 {focus_d} 중 한 가지를 우선 배치합니다.",
            f"센터 시간표와 학생 일정을 대조해 {focus_a} 확인, 수업, {focus_b} 복습에 필요한 시간을 현실적으로 나눕니다.",
            f"{students[2]}에게 무리한 분량을 정하지 않도록 최근 완료 기록을 기준으로 시간을 계산합니다.",
        ],
    )
    goal_label, goal_action = selected_process(ctx, picker, "check-goal")
    goal = picker.pick(
        "check-goal-frame",
        [
            f"{focus_a}을 먼저 바꿀지 {focus_b}을 함께 관리할지 정하고, {goal_action}",
            f"{goal_label} 단계에서 확인할 목표를 한 가지로 좁혀 {goal_action}",
            f"{focus_c}의 단기 목표와 {focus_d}의 누적 목표를 구분하고 {goal_action}",
            f"다음 상담에서 다시 확인할 {focus_a} 기준을 정하고 {goal_action}",
            f"학생이 설명할 수 있는 {focus_b} 범위를 목표로 정해 {goal_action}",
            f"이번 주에 완료할 {focus_c} 분량과 재확인할 {focus_d} 범위를 정합니다.",
        ],
    )
    recent = contextualize_statement(ctx, picker, "check-recent-context", recent)
    school = contextualize_statement(ctx, picker, "check-school-context", school)
    time = contextualize_statement(ctx, picker, "check-time-context", time)
    goal = contextualize_statement(ctx, picker, "check-goal-context", goal)
    return f'''    {DETAIL_MARKER_START}
    <section class="local-section seo-geo-section" aria-label="{html.escape(ctx.info.locality)} 학생 학습 및 상담 안내">
      <div class="wrap seo-geo-enhancement">
        <article id="student-fit" class="geo-answer-panel">
          <p class="eyebrow">학습 점검</p>
          <h2>학생 상황별 학습 점검</h2>
          <p>{html.escape(fit_intro)}</p>
          <div class="geo-answer-grid">
{chr(10).join(cards)}
          </div>
        </article>

        <article id="consult-checklist" class="geo-checklist-panel">
          <p class="eyebrow">상담 준비</p>
          <h2>상담 전에 준비할 자료</h2>
          <div class="geo-checklist-grid">
            <article class="geo-check-card"><b>01</b><strong>최근 학습 자료</strong><p>{html.escape(recent)}</p></article>
            <article class="geo-check-card"><b>02</b><strong>학교 일정</strong><p>{html.escape(school)}</p></article>
            <article class="geo-check-card"><b>03</b><strong>공부 가능 시간</strong><p>{html.escape(time)}</p></article>
            <article class="geo-check-card"><b>04</b><strong>이번 상담 목표</strong><p>{html.escape(goal)}</p></article>
          </div>
        </article>
      </div>
    </section>
    {DETAIL_MARKER_END}'''


def diagnostic_qa(ctx: source.PageContext, picker: StableChoice) -> QA:
    facts = fact_bundle(ctx)
    checks = picker.order("faq-diagnostic-checks", facts["checks"])
    focus_a, focus_b = checks[0], checks[1]
    process_label, process_action = selected_process(ctx, picker, "faq-diagnostic")
    recent_focus_b = focus_b if focus_b.startswith("현재 ") else f"최근 {focus_b}"
    questions = [
        f"{ctx.info.locality} 학생은 {focus_a}과 {focus_b} 중 무엇을 먼저 확인하나요?",
        f"{focus_a} 시작 범위와 {focus_b}을 실제로 이어 갔는지는 어떤 기록으로 확인하나요?",
        f"첫 상담에서 {focus_b}과 {focus_a}을 구분하려면 무엇을 살펴보나요?",
        f"{process_label} 순서를 정할 때 {focus_a}과 {focus_b} 중 어떤 자료가 필요한가요?",
        f"{focus_b} 상담 전에 {focus_a}과 관련해 어떤 문제를 표시해 두면 좋나요?",
        f"{focus_a} 계획을 세울 때 {recent_focus_b} 자료를 함께 보는 이유는 무엇인가요?",
    ]
    answers = [
        f"최근 교재와 평가자료에서 {focus_a} 관련 어려움이 드러난 부분을 찾고 {focus_b}이 계획대로 이어졌는지 확인합니다. {process_action}",
        f"{focus_a}과 {focus_b} 시작 범위를 성적만으로 정하지 않습니다. 혼자 해결한 문제와 도움이 필요했던 문제를 나눈 뒤 {focus_a}·{focus_b} 우선순위를 정합니다.",
        f"현재 진도, {focus_a} 관련 오답이 생긴 이유, {focus_b}을 마친 시점, 실제 공부 가능 시간을 함께 봅니다. {process_label} 단계에서는 {process_action}",
        f"최근 자료에서 {focus_a}과 {focus_b} 관련 어려움이 나타난 문제를 구분합니다. 학생이 한 주 안에 실행할 {focus_a}·{focus_b} 범위를 먼저 정합니다.",
        f"{focus_a} 관련 문제의 정답만 보기보다 풀이 중 처음 어려웠던 부분을 표시해 주세요. 그 기록으로 {focus_b} 관련 문제를 구분하고 {process_action}",
        f"학생이 현재 사용하는 자료가 {focus_a}·{focus_b} 상태를 가장 직접적으로 보여 주기 때문입니다. 두 자료로 {focus_a}·{focus_b}의 다음 점검 범위를 정합니다.",
    ]
    answer = picker.pick("faq-diagnostic-a", answers)
    answer += f" 상담에서는 {focus_a} 자료와 {focus_b}에 쓴 시간을 함께 대조합니다."
    answer += " " + contextual_learning_sentence(ctx, picker, "faq-diagnostic-context")
    return QA(picker.pick("faq-diagnostic-q", questions), answer)


def grade_qa(ctx: source.PageContext, picker: StableChoice) -> QA:
    facts = fact_bundle(ctx)
    checks = picker.order("faq-grade-checks", facts["checks"])
    focus_a, focus_b = checks[0], checks[1]
    questions = [
        f"{focus_a}과 {focus_b} 상담이 가능한 학년은 자료에서 어떻게 확인하나요?",
        f"{focus_b} 계획과 {focus_a} 점검을 등록하기 전에 어떤 학년 정보를 다시 확인해야 하나요?",
        f"{facts['center']}에서 {focus_a}과 {focus_b}을 상담할 수 있는 학년은 어디까지인가요?",
        f"학생 학년에 맞는 {focus_b} 수업과 {focus_a} 점검은 어떻게 확인하나요?",
    ]
    if facts["grades"]:
        answers = [
            f"센터 자료의 {focus_a}·{focus_b} 가능 범위는 {facts['grade_text']}입니다. 두 항목의 진도와 실행 시간이 학생마다 다르므로 {focus_a}·{focus_b} 최신 개설 정보를 등록 전에 확인해 주세요.",
            f"센터 자료에서 {focus_a}·{focus_b} 상담으로 확인되는 범위는 {facts['grade_text']}입니다. 이 {focus_b} 계획을 수업 확정 정보로 보지 않고 {focus_a} 자료와 센터 개설 시간을 대조합니다.",
            f"제공 자료에는 {focus_a}·{focus_b} 기준 {facts['grade_text']} 학년 정보가 있습니다. 상담에서는 {focus_a} 교재와 {focus_b} 진도를 확인한 뒤 가능한 반과 시간을 안내합니다.",
            f"제공 자료 기준 {focus_a}·{focus_b} 가능 학년은 {facts['grade_text']}입니다. 방문 전 현재 학년과 {focus_a}·{focus_b} 개설 여부를 문의해 주세요.",
        ]
    else:
        answers = [
            f"{facts['center']} 자료에는 해당 학년 범위가 따로 표시되지 않아 임의로 안내하지 않습니다. 학생 학년과 {focus_a}·{focus_b} 개설 여부를 확인해 주세요.",
            f"현재 자료만으로 {focus_a} 개설 학년을 확정하기 어렵습니다. {focus_b} 계획은 {facts['center']}의 최신 시간표를 기준으로 상담해야 합니다.",
            f"가능 학년 정보가 따로 제공되지 않았습니다. 학생의 현재 학년과 {focus_a} 교재·{focus_b} 진도를 알려주고 센터의 가능 시간을 확인해 주세요.",
        ]
    answer = picker.pick("faq-grade-a", answers)
    answer += " " + contextual_learning_sentence(ctx, picker, "faq-grade-context")
    return QA(picker.pick("faq-grade-q", questions), answer)


def school_qa(ctx: source.PageContext, picker: StableChoice) -> QA:
    facts = fact_bundle(ctx)
    schools = "·".join(facts["schools"][:4])
    if facts["schools"]:
        questions = [
            f"{schools} 등 학교 진도는 상담에 어떻게 반영하나요?",
            f"{schools} 등 재학 학교의 교재와 시험 일정도 확인하나요?",
            f"{schools} 등 학교별 진도 차이는 어떤 자료로 확인하나요?",
        ]
        answers = [
            f"{schools}은 제공된 참고 학교입니다. 학교명만으로 수업을 정하지 않고 학생이 사용하는 교재·진도·시험 일정과 {facts['center']} 시간표를 함께 확인합니다.",
            f"재학 학교의 실제 교재와 시험 범위를 상담 때 확인합니다. 제공된 학교 목록은 상담 범위를 이해하기 위한 참고 정보이며 개설을 보장하지 않습니다.",
            f"학교별 일정은 학생이 가져온 자료를 기준으로 확인합니다. 현재 진도와 남은 시험 기간을 {facts['center']}의 가능한 일정과 대조합니다.",
        ]
    else:
        questions = [
            "상담에서 재학 학교의 진도도 확인하나요?",
            "학교명이 페이지에 없으면 어떤 자료로 상담하나요?",
            f"{ctx.info.locality} 학생의 학교별 시험 범위는 어떻게 확인하나요?",
        ]
        answers = [
            f"제공 자료에 구체적인 학교명이 없어 임의로 추가하지 않았습니다. 학생이 사용하는 교재·현재 진도·시험 일정을 준비하면 {facts['center']} 상담에서 범위를 정할 수 있습니다.",
            "학교명보다 실제 교재와 최근 시험지를 우선 확인합니다. 다음 시험 일정과 어려운 단원을 알려주면 필요한 순서를 구체화할 수 있습니다.",
            f"재학 학교의 시험 범위는 상담에서 직접 확인합니다. 제공되지 않은 학교 정보는 추정하지 않고 {facts['center']}의 현재 시간표와 대조합니다.",
        ]
    answer = picker.pick("faq-school-a", answers)
    answer += " 이 학교 자료는 수업 확정 정보가 아닌 상담 참고 기준으로 사용합니다."
    return QA(picker.pick("faq-school-q", questions), answer)


def location_qa(ctx: source.PageContext, picker: StableChoice) -> QA:
    facts = fact_bundle(ctx)
    checks = picker.order("faq-location-checks", facts["checks"])
    focus_a, focus_b = checks[0], checks[1]
    questions = [
        f"{focus_a}과 {focus_b} 상담을 안내하는 실제 방문 센터는 어디인가요?",
        f"{focus_b} 계획과 {focus_a} 점검을 상담할 생활권과 실제 방문 센터 위치가 다를 수 있나요?",
        f"{focus_a} 점검과 {focus_b} 계획을 상담하려면 어떤 실제 방문 주소를 확인해야 하나요?",
    ]
    answers = [
        f"이 페이지의 {focus_a}·{focus_b} 상담에서 확인할 실제 방문 센터는 {facts['center']}입니다. {focus_b} 계획을 상담할 실제 방문 주소는 {facts['address']}입니다.",
        f"{focus_a}·{focus_b} 상담 가능 지역과 실제 방문 위치는 다를 수 있습니다. {focus_a}·{focus_b} 상담의 실제 방문 센터는 {facts['center']}입니다. {focus_a} 상담의 실제 방문 주소는 {facts['address']}이며 페이지 지역명과 구분해 확인해야 합니다.",
        f"{focus_a} 점검을 안내하는 실제 방문 센터는 {facts['center']}입니다. {focus_a} 상담 주소는 {facts['address']}입니다. {focus_b} 계획은 동네명만으로 실제 센터 위치를 추정하지 않고 이 주소를 기준으로 상담합니다.",
    ]
    answer = picker.pick("faq-location-a", answers)
    answer += " " + contextual_learning_sentence(ctx, picker, "faq-location-context")
    return QA(picker.pick("faq-location-q", questions), answer)


def fee_qa(ctx: source.PageContext, picker: StableChoice) -> QA:
    facts = fact_bundle(ctx)
    return QA(
        picker.pick(
            "faq-fee-q",
            [
                f"{ctx.info.locality} 상담의 교습비 자료는 어디에서 확인할 수 있나요?",
                f"{facts['center']}의 교습비는 페이지에서 확인할 수 있나요?",
                f"{ctx.info.locality} {ctx.config['label']} 수강료는 어떻게 확인하나요?",
            ],
        ),
        picker.pick(
            "faq-fee-a",
            [
                f"‘센터 교습비 자료 확인’ 링크에서 {facts['center']}의 연결 공개자료를 볼 수 있습니다. 실제 금액은 과목·학년·수업 시간에 따라 달라질 수 있어 등록 전 다시 확인해야 합니다.",
                f"페이지에 연결된 {facts['center']}의 교습비 자료를 안내합니다. 학생이 선택할 과목과 시간에 맞는 최종 금액은 상담에서 확인해 주세요.",
                "연결된 공개자료 링크에서 센터 교습비를 확인할 수 있습니다. 현재 수강 가능 여부와 실제 적용 금액은 등록 전에 다시 확인해야 합니다.",
            ],
        ),
    )


def management_qa(ctx: source.PageContext, picker: StableChoice) -> QA:
    facts = fact_bundle(ctx)
    checks = picker.order("faq-management-checks", facts["checks"])
    focus_a, focus_b = checks[0], checks[1]
    label, action = selected_process(ctx, picker, "faq-management")
    questions = [
        f"{focus_a} 관련 어려움이 반복될 때 {focus_b} 관련 기록은 어떻게 점검하나요?",
        f"{focus_a}과 {focus_b} 우선순위는 어떤 학습 기록으로 정하나요?",
        f"{label} 뒤 {focus_b} 결과와 {focus_a} 변화는 언제 다시 확인하나요?",
        f"상담 후 {focus_a} 계획이 실행되지 않으면 {focus_b}에서 무엇을 바꾸나요?",
    ]
    answers = [
        f"최근 자료에서 {focus_a} 관련 어려움이 처음 드러난 부분을 찾고 개념·실수·시간 요인을 구분합니다. {action} 이후 다른 문제에서도 {focus_b} 관련 어려움이 반복되는지 확인합니다.",
        f"{focus_a}과 {focus_b}을 한꺼번에 늘리지 않고 학생이 혼자 해결할 수 있는 항목부터 정합니다. {focus_a} 완료 결과를 {focus_b} 자료와 비교해 다음 범위를 조정합니다.",
        f"{label} 단계의 기록은 정한 분량을 실행한 뒤 {focus_a} 유형의 문제에서 다시 확인합니다. {focus_b} 관련 어려움이 남으면 분량·난도·시간 중 무엇을 바꿀지 정합니다.",
        f"{focus_a} 계획을 지키지 못한 이유를 의지 문제로 단정하지 않습니다. 실제 공부 시간과 {focus_b} 관련 과제의 난도를 확인해 분량을 다시 조정합니다.",
    ]
    answer = picker.pick("faq-management-a", answers)
    answer += f" {focus_a}과 {focus_b} 계획은 이 재확인 결과에 맞춰 조정합니다."
    answer += " " + contextual_learning_sentence(ctx, picker, "faq-management-context")
    return QA(picker.pick("faq-management-q", questions), answer)


def build_faqs(ctx: source.PageContext) -> list[QA]:
    picker = detail_picker(ctx)
    facts = fact_bundle(ctx)
    result = [diagnostic_qa(ctx, picker), grade_qa(ctx, picker)]
    result.extend([location_qa(ctx, picker), management_qa(ctx, picker)])
    if len({item.question for item in result}) != 4:
        raise ValueError(f"Duplicate FAQ question: {ctx.path}")
    return result


def faq_html(title: str, faqs: Sequence[QA], section_id: str = "faq-section") -> str:
    items = "\n".join(
        f'''      <details>
        <summary>{html.escape(item.question)}</summary>
        <p>{html.escape(item.answer)}</p>
      </details>'''
        for item in faqs
    )
    return f'''<section id="{html.escape(section_id, quote=True)}" class="local-section">
  <div class="wrap faq-local">
    <h2>{html.escape(title)} 자주 묻는 질문</h2>
{items}
  </div>
</section>'''


def deduplicate_visible_paragraph_sentences(
    text: str,
    ctx: source.PageContext,
) -> str:
    """Contextualize a repeated prose sentence on its later occurrence.

    The generated prose occasionally selects the same useful process sentence
    for two different cards.  Keeping both verbatim adds no value, so the later
    occurrence is tied to a different source-backed learning signal.  Markup
    containing child elements is intentionally left untouched.
    """

    seen: set[str] = set()
    duplicate_index = 0
    pattern = re.compile(r"(<p\b[^>]*>)(.*?)(</p>)", re.I | re.S)

    checks = list(fact_bundle(ctx)["checks"])
    process_labels = [label for label, _variants in ctx.config["process"]]

    def contextualized_duplicate(sentence: str) -> str:
        nonlocal duplicate_index
        base = re.sub(
            r"^(?:이후|다음\s+점검에서는|다음\s+확인에서는)\s*",
            "",
            sentence,
        )
        attempts = max(1, len(checks) * 2)
        for offset in range(attempts):
            index = duplicate_index + offset
            focus = checks[index % len(checks)]
            if index < len(checks):
                prefix = f"{focus} 점검에서는 "
            else:
                label = process_labels[index % len(process_labels)]
                prefix = f"{label} 단계의 {focus} 점검에서는 "
            candidate = prefix + base
            if candidate not in seen:
                duplicate_index = index + 1
                return candidate
        duplicate_index += attempts
        return f"이번 {checks[duplicate_index % len(checks)]} 점검에서는 {base}"

    def replace_paragraph(match: re.Match[str]) -> str:
        nonlocal duplicate_index
        inner = match.group(2)
        if "<" in inner or ">" in inner:
            return match.group(0)
        decoded = html.unescape(inner)
        chunks = re.split(r"((?<=[.!?])\s+)", decoded)
        changed = False
        for index in range(0, len(chunks), 2):
            sentence = re.sub(r"\s+", " ", chunks[index]).strip()
            if len(sentence) < 20:
                continue
            if sentence in seen:
                replacement = contextualized_duplicate(sentence)
                chunks[index] = replacement
                seen.add(replacement)
                changed = True
            else:
                seen.add(sentence)
        if not changed:
            return match.group(0)
        rebuilt = "".join(chunks).strip()
        return match.group(1) + html.escape(rebuilt) + match.group(3)

    return pattern.sub(replace_paragraph, text)


def contextualize_comparison_copy(text: str, ctx: source.PageContext) -> str:
    pattern = re.compile(
        r"(<p>)([^<>]{2,80} 안에서 함께 비교해볼 수 있는 동네 페이지입니다\.)(</p>)"
    )
    counter = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal counter
        statement = contextualize_statement(
            ctx,
            detail_picker(ctx),
            f"comparison-copy-{counter}",
            html.unescape(match.group(2)),
        )
        counter += 1
        return match.group(1) + html.escape(statement) + match.group(3)

    return pattern.sub(replace, text)


def faq_entities(faqs: Sequence[QA]) -> list[dict[str, Any]]:
    return [
        {
            "@type": "Question",
            "name": item.question,
            "acceptedAnswer": {"@type": "Answer", "text": item.answer},
        }
        for item in faqs
    ]


def school_mentions(ctx: source.PageContext) -> list[dict[str, str]]:
    return [
        {"@type": "Organization", "name": school}
        for school in actual_schools(ctx)
    ]


def sync_detail_schema(
    text: str,
    ctx: source.PageContext,
    faqs: Sequence[QA],
) -> str:
    """Synchronize visible facts with schema while preserving every URL."""

    data, match = source.parse_jsonld(text)

    def normalize_semantic(value: Any, key: str = "") -> Any:
        if isinstance(value, list):
            return [normalize_semantic(item, key) for item in value]
        if isinstance(value, dict):
            return {
                child_key: normalize_semantic(child, child_key)
                for child_key, child in value.items()
            }
        if isinstance(value, str) and key not in {
            "@id",
            "url",
            "item",
            "contentUrl",
        }:
            return value.replace(ctx.locality, ctx.info.locality)
        return value

    data = normalize_semantic(data)
    graph = data["@graph"]
    stable_id = ctx.center.primary_url + "#organization"
    mentions: list[dict[str, str]] = [{"@id": stable_id}, *school_mentions(ctx)]

    faq = find_node(graph, "FAQPage")
    if faq is None:
        faq = {"@type": "FAQPage", "@id": ctx.page_url + "#faq"}
        graph.append(faq)
    faq["@type"] = "FAQPage"
    faq["@id"] = ctx.page_url + "#faq"
    faq["mainEntity"] = faq_entities(faqs)

    organization = find_node(graph, "EducationalOrganization")
    if organization is not None:
        organization["@id"] = stable_id
        organization["name"] = source.actual_center_name(ctx)
        organization["url"] = ctx.center.primary_url
        organization["branchOf"] = {"@id": ROOT_ORGANIZATION_ID}
        for unsupported in ("telephone", "contactPoint", "openingHours"):
            organization.pop(unsupported, None)
        address: dict[str, str] = {
            "@type": "PostalAddress",
            "streetAddress": source.actual_address(ctx),
            "addressCountry": "KR",
        }
        region = official_address_region(ctx)
        locality = official_address_locality(ctx)
        if region:
            address["addressRegion"] = region
        if locality:
            address["addressLocality"] = locality
        organization["address"] = address
        served_names = list(ctx.center.areas)
        served_nodes = [
            {"@type": "Place", "name": name}
            for name in dict.fromkeys(served_names)
            if name
        ]
        if served_nodes:
            organization["areaServed"] = (
                served_nodes[0] if len(served_nodes) == 1 else served_nodes
            )
        if ctx.info.registration_number:
            organization["identifier"] = {
                "@type": "PropertyValue",
                "propertyID": "교육지원청 등록번호",
                "value": ctx.info.registration_number,
            }

    webpage = find_node(graph, "WebPage")
    if webpage is not None:
        webpage["name"] = display_title(ctx)
        webpage["description"] = build_meta_description(ctx)
        webpage["author"] = {"@id": ROOT_ORGANIZATION_ID}
        webpage["publisher"] = {"@id": ROOT_ORGANIZATION_ID}
        webpage["mentions"] = mentions
        webpage["about"] = [
            {"@type": "Place", "name": ctx.info.locality},
            {"@type": "Thing", "name": ctx.config["label"]},
        ]

    article = find_node(graph, "Article")
    if article is not None:
        article["headline"] = display_h1(ctx)
        article["description"] = build_meta_description(ctx)
        article["author"] = {"@id": ROOT_ORGANIZATION_ID}
        article["publisher"] = {"@id": ROOT_ORGANIZATION_ID}
        article["mentions"] = mentions
        article["about"] = [
            {"@type": "Place", "name": ctx.info.locality},
            {"@type": "Thing", "name": ctx.config["label"]},
        ]

    service = find_node(graph, "Service")
    if service is not None:
        service["name"] = display_h1(ctx) + " 학습코칭"
        service["description"] = build_meta_description(ctx)
        service["provider"] = {"@id": stable_id}
        service["areaServed"] = {
            "@type": "Place",
            "name": service_area_name(ctx),
        }

    breadcrumb = find_node(graph, "BreadcrumbList")
    if breadcrumb is not None:
        elements = breadcrumb.get("itemListElement", [])
        if isinstance(elements, list) and elements:
            last = elements[-1]
            if isinstance(last, dict) and last.get("item") == ctx.page_url:
                last["name"] = display_h1(ctx)

    stamp_modified(graph, "WebPage", "Article")
    return replace_jsonld(text, data, match)


def replace_jsonld(text: str, data: dict[str, Any], match: re.Match[str]) -> str:
    compact = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return text[: match.start(1)] + compact + text[match.end(1) :]


def transform_detail(ctx: source.PageContext) -> str:
    text = re.sub(
        r"&((?:amp|nbsp|quot|apos|lt|gt|#[0-9]+|#x[0-9A-Fa-f]+))\.",
        r"&\1;",
        ctx.text,
        flags=re.I,
    )
    heading = display_h1(ctx)
    description = build_meta_description(ctx)
    if heading != ctx.title:
        text = replace_visible_text_nodes(text, ctx.title, heading)
        text = source.replace_meta(
            text,
            key="og:title",
            value=display_title(ctx),
            attr_name="property",
        )
    text = source.replace_meta(
        text,
        key="description",
        value=description,
        attr_name="name",
    )
    text = source.replace_meta(
        text,
        key="og:description",
        value=description,
        attr_name="property",
    )
    faqs = build_faqs(ctx)
    hero_pattern = re.compile(
        r'(<section class="local-hero">.*?<h1\b[^>]*>.*?</h1>)\s*<p\b[^>]*>.*?</p>',
        re.S,
    )
    text = replace_once(
        text,
        hero_pattern,
        lambda match: (
            match.group(1)
            + "\n              <p>"
            + html.escape(build_hero_answer(ctx))
            + "</p>"
        ),
        f"hero {ctx.path}",
    )
    hero_fact_pattern = re.compile(
        r'<div class="hero-center-fact">.*?</div>',
        re.S,
    )
    text = replace_once(
        text,
        hero_fact_pattern,
        build_hero_center_fact(ctx).strip(),
        f"hero center fact {ctx.path}",
    )
    primary_pattern = re.compile(
        r'\s*<section id="learning-plan" class="local-section">.*?</section>',
        re.S,
    )
    text = replace_once(
        text,
        primary_pattern,
        "\n\n" + build_primary_section(ctx),
        f"learning-plan {ctx.path}",
    )
    verified_pattern = re.compile(
        r'\s*<section id="verified-center" class="local-section verified-center-section">'
        r".*?</section>",
        re.S,
    )
    text = replace_once(
        text,
        verified_pattern,
        "\n\n" + build_refined_verified_section(ctx),
        f"verified center {ctx.path}",
    )
    quality_pattern = re.compile(
        r'\s*<!-- (?:seo-geo-enhancement|quality-content):start -->.*?'
        r'<!-- (?:seo-geo-enhancement|quality-content):end -->',
        re.S,
    )
    text = replace_once(
        text,
        quality_pattern,
        "\n\n" + build_quality_section(ctx),
        f"quality block {ctx.path}",
    )
    faq_pattern = re.compile(
        r'<section id="faq-section" class="local-section">.*?</section>'
        r'\s*(?=<section id="internal-links")',
        re.S,
    )
    text = replace_once(
        text,
        faq_pattern,
        faq_html(
            f"{ctx.config['subject']} 학습 상담",
            faqs,
        )
        + "\n",
        f"FAQ {ctx.path}",
    )
    source_note_pattern = re.compile(
        r'<p class="verified-note source-note">.*?</p>',
        re.S,
    )
    text = replace_once(
        text,
        source_note_pattern,
        '<p class="verified-note source-note">'
        + html.escape(build_source_note(ctx))
        + "</p>",
        f"source note {ctx.path}",
    )
    text = re.sub(
        r"참고 학교와 별개로 학생의 현재 진도와 "
        r"([^<]+?) 시간표를 대조한 뒤",
        r"참고 학교와 별개로 학생의 현재 진도를 \1 시간표와 대조한 뒤",
        text,
    )
    text = re.sub(
        rf'\s*<p>{re.escape(ctx.info.locality)} 종합 안내와 학년·과목별 상세 페이지를 함께 확인할 수 있습니다\.</p>',
        "",
        text,
        count=1,
    )
    text = text.replace(
        f"<h2>{html.escape(ctx.info.locality)} 학습 페이지 이동</h2>",
        "<h2>관련 학습 페이지 이동</h2>",
    )
    for old, new in KNOWN_COPY_ERRORS.items():
        text = text.replace(old, new)
    text = replace_visible_text_nodes(
        text,
        ctx.locality,
        ctx.info.locality,
    )
    text = contextualize_comparison_copy(text, ctx)
    text = repair_visible_copy_splices(text, ctx)
    text = fix_korean_particles(text, ctx)
    text = deduplicate_visible_paragraph_sentences(text, ctx)
    faqs = visible_faq(text, "faq-section")
    text = sync_detail_schema(text, ctx, faqs)
    text = fix_korean_particles(text, ctx)
    text = deduplicate_visible_paragraph_sentences(text, ctx)
    faqs = visible_faq(text, "faq-section")
    text = sync_detail_schema(text, ctx, faqs)
    text = fix_korean_particles(text, ctx)
    for old, new in KNOWN_COPY_ERRORS.items():
        text = text.replace(old, new)
    text = re.sub(r"(?m)^[ \t]+$", "", text)
    return text


def visible_faq(text: str, section_id: str) -> list[QA]:
    block = match_one(
        text,
        rf'<section\b[^>]*id=["\']{re.escape(section_id)}["\'][^>]*>'
        r"(.*?)</section>",
    )
    result = []
    for details in re.findall(r"<details\b[^>]*>(.*?)</details>", block, re.I | re.S):
        question = clean(match_one(details, r"<summary\b[^>]*>(.*?)</summary>"))
        answer = clean(match_one(details, r"<p\b[^>]*>(.*?)</p>"))
        if question and answer:
            result.append(QA(question, answer))
    return result


def schema_faq(text: str) -> list[QA]:
    data, _ = source.parse_jsonld(text)
    faq = find_node(data["@graph"], "FAQPage")
    if not faq:
        return []
    result = []
    for entity in faq.get("mainEntity", []):
        if not isinstance(entity, dict):
            continue
        answer = entity.get("acceptedAnswer", {})
        result.append(
            QA(
                str(entity.get("name", "")).strip(),
                str(answer.get("text", "")).strip()
                if isinstance(answer, dict)
                else "",
            )
        )
    return result


def meta_value(text: str, key: str, attr: str) -> str:
    return match_one(
        text,
        rf'<meta\b(?=[^>]*{attr}=["\']{re.escape(key)}["\'])'
        r'[^>]*content=["\']([^"\']*)["\']',
    )


def validate_detail(ctx: source.PageContext, text: str) -> list[str]:
    errors: list[str] = []
    visible_text = clean(text)
    after_title = match_one(text, r"<title>(.*?)</title>")
    after_h1 = clean(match_one(text, r"<h1\b[^>]*>(.*?)</h1>"))
    before_canonical = match_one(
        ctx.text,
        r'<link\b(?=[^>]*rel=["\']canonical["\'])'
        r'[^>]*href=["\']([^"\']*)["\']',
    )
    after_canonical = match_one(
        text,
        r'<link\b(?=[^>]*rel=["\']canonical["\'])'
        r'[^>]*href=["\']([^"\']*)["\']',
    )
    if display_title(ctx) != after_title:
        errors.append("title accuracy")
    if display_h1(ctx) != after_h1 or len(re.findall(r"<h1\b", text, re.I)) != 1:
        errors.append("H1 accuracy/count")
    if before_canonical != after_canonical:
        errors.append("canonical changed")
    if Counter(re.findall(r"<img\b[^>]*>", ctx.text, re.I | re.S)) != Counter(
        re.findall(r"<img\b[^>]*>", text, re.I | re.S)
    ):
        errors.append("image markup changed")
    if ctx.map_image not in text:
        errors.append("map image changed")
    if source.actual_center_name(ctx) not in text:
        errors.append("actual centre missing")
    if source.actual_address(ctx) not in text:
        errors.append("actual address missing")
    if text.count(DETAIL_MARKER_START) != 1 or text.count(DETAIL_MARKER_END) != 1:
        errors.append("quality marker count")
    for section_id in ("learning-plan", "student-fit", "consult-checklist", "faq-section"):
        if len(re.findall(rf'\bid=["\']{re.escape(section_id)}["\']', text)) != 1:
            errors.append(f"{section_id} count")
    for bad in KNOWN_COPY_ERRORS:
        if bad in text:
            errors.append(f"remaining copy error: {bad}")
    copy_regressions = {
        "점로 연결": r"점로\s+연결",
        "오류의 첫 지점": r"오류의\s+첫\s+지점",
        "same-way block": r"같은\s+방식으로\s+막히는지",
        "range-centre splice": r"가능한\s+범위를\s+와와",
        "cause split splice": r"(?:시험\s+일정|\S+)의\s+원인을\s+나누",
        "adjacent role duplication": r"(?:기록\s+(?:실행\s+)?기록|실행\s+실행|현재\s+현재|구문\s+구문|누적\s+누적|기초\s+기초|오답\s+오답)",
        "bad topic grammar": r"(?:두\s+항목은\s+학생이|상담의\s+안내\s+센터|생활권\s+이름과\s+나누어|관련\s+어떤|\S+\s+과제\s+난도)",
        "legacy location jargon": r"(?:물리센터|상담의\s+방문\s+주소|상담\s+생활권|https?://(?:www\.)?naver\.me|\^\^)",
        "particle/copy remnants": r"(?:층라고|점\(모두\)가며|센터정보에는)",
        "diagnostic noun splice": r"두\s+자료로\s+[^.!?]+(?<!의)\s+다음\s+점검",
        "recent-current splice": r"최근\s+현재",
        "generic signal as solvable object": r"(?:현재\s+진도|시험\s+일정|오답\s+기록|과제\s+실행)(?:을|를)?\s+(?:해결하지|해결할\s+수)",
        "generic signal as student type": r"학생이\s+[^.!?]{1,40}\s+상황에\s+가까운지",
        "process label as difficulty": r"(?:학습\s+진단|주간\s+계획|실행\s+확인|오답\s+재학습)\s+(?:관련\s+어려움|실행\s+분량)",
        "signal treated as execution": r"의\s+어려움과\s+[^.!?]{1,40}의\s+실행\s+여부",
        "finished sentence comma splice": r"(?:니다|합니다),\s*(?:이어서|이때|상담에서는|준비한|이후|같은|다음)",
        "authored semicolon splice": r";",
        "legacy date": r"2026-07-31",
    }
    for label, pattern in copy_regressions.items():
        if re.search(pattern, visible_text):
            errors.append(f"copy regression: {label}")
    for focus in fact_bundle(ctx)["checks"]:
        if re.search(
            rf"{re.escape(focus)}\s+(?:정답보다|오답\s+원인|최근\s+자료|과제\s+난도)",
            visible_text,
        ):
            errors.append(f"copy regression: signal noun splice ({focus})")
    repeated_behind = False
    repeated_confirmation = False
    for _tag, inner in re.findall(
        r"<(p|li)\b[^>]*>(.*?)</\1>", text, re.I | re.S
    ):
        for sentence in re.split(r"(?<=[.!?])\s+", clean(inner)):
            if len(re.findall(r"\b뒤\b", sentence)) >= 2:
                repeated_behind = True
                break
            if sentence.count("확인하고") >= 2:
                repeated_confirmation = True
                break
        if repeated_behind or repeated_confirmation:
            break
    if repeated_behind:
        errors.append("copy regression: repeated 뒤 in one sentence")
    if repeated_confirmation:
        errors.append("copy regression: repeated 확인하고 in one sentence")
    if ctx.info.locality != ctx.locality and ctx.locality in visible_text:
        errors.append("compact URL locality leaked into visible copy")
    remaining_particles = sorted(
        token for token in wrong_particle_tokens(ctx) if token in text
    )
    if remaining_particles:
        errors.append(
            "remaining particle errors: " + ", ".join(remaining_particles[:5])
        )
    source_note = match_one(
        text,
        r'<p class="verified-note source-note">(.*?)</p>',
    )
    source_dates = re.findall(r"\d{4}-\d{2}-\d{2}", source_note)
    if source_dates != [REVISION_DATE]:
        errors.append("visible revision date")
    visible = visible_faq(text, "faq-section")
    schema = schema_faq(text)
    if len(visible) != 4:
        errors.append(f"visible FAQ count {len(visible)}")
    if visible != schema:
        errors.append("FAQ screen/schema mismatch")
    if len({item.question for item in visible}) != len(visible):
        errors.append("duplicate visible FAQ")
    try:
        data, _ = source.parse_jsonld(text)
        graph = data["@graph"]
        required = {
            "EducationalOrganization",
            "LocalBusiness",
            "WebPage",
            "Service",
            "FAQPage",
            "BreadcrumbList",
            "ItemList",
            "Article",
        }
        present = set().union(
            *(node_types(node) for node in graph if isinstance(node, dict))
        )
        missing = required - present
        if missing:
            errors.append("missing JSON-LD: " + ",".join(sorted(missing)))
        for kind in ("WebPage", "Article"):
            node = find_node(graph, kind)
            if node is not None and node.get("dateModified") != REVISION_DATE:
                errors.append(f"{kind} dateModified")
            if node is not None:
                if node.get("author") != {"@id": ROOT_ORGANIZATION_ID}:
                    errors.append(f"{kind} author")
                if node.get("publisher") != {"@id": ROOT_ORGANIZATION_ID}:
                    errors.append(f"{kind} publisher")
                mentioned = {
                    str(item.get("name", ""))
                    for item in node.get("mentions", [])
                    if isinstance(item, dict) and item.get("name")
                }
                if mentioned != set(actual_schools(ctx)):
                    errors.append(f"{kind} school mentions")
        organization = find_node(graph, "EducationalOrganization")
        if organization is not None:
            if organization.get("@id") != ctx.center.primary_url + "#organization":
                errors.append("physical organization id")
            if any(
                key in organization
                for key in ("telephone", "contactPoint", "openingHours")
            ):
                errors.append("unsupported physical organization contact")
            address = organization.get("address", {})
            if not isinstance(address, dict):
                errors.append("physical organization address")
            else:
                if address.get("streetAddress") != source.actual_address(ctx):
                    errors.append("physical organization streetAddress")
                if address.get("addressRegion") != official_address_region(ctx):
                    errors.append("physical organization addressRegion")
                expected_locality = official_address_locality(ctx)
                if expected_locality:
                    if address.get("addressLocality") != expected_locality:
                        errors.append("physical organization addressLocality")
                elif "addressLocality" in address:
                    errors.append("unsupported addressLocality")
        service = find_node(graph, "Service")
        if service is not None:
            if service.get("provider") != {
                "@id": ctx.center.primary_url + "#organization"
            }:
                errors.append("Service provider")
            area = service.get("areaServed", {})
            if not isinstance(area, dict) or area.get("name") != service_area_name(ctx):
                errors.append("Service areaServed")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"JSON-LD invalid: {exc}")
    return errors


def hub_context(path: Path, root: Path, category_names: set[str]) -> HubContext:
    text = path.read_text(encoding="utf-8")
    data, _ = source.parse_jsonld(text)
    graph = data["@graph"]
    collection = find_node(graph, "CollectionPage")
    item_list = find_node(graph, "ItemList")
    if collection is None or item_list is None:
        raise ValueError(f"CollectionPage/ItemList missing: {path}")
    title = clean(match_one(text, r"<title>(.*?)</title>"))
    h1 = clean(match_one(text, r"<h1\b[^>]*>(.*?)</h1>"))
    name = path.parent.name
    category = name if name in category_names else ""
    kind = "category" if category else "region"
    items = item_list.get("itemListElement", [])
    item_names = tuple(
        str(item.get("name", "")).strip()
        for item in items
        if isinstance(item, dict) and item.get("name")
    )
    district_names = tuple(
        dict.fromkeys(
            clean(value)
            for value in re.findall(r"<h3\b[^>]*>(.*?)</h3>", text, re.I | re.S)
            if clean(value)
        )
    )
    return HubContext(
        path=path,
        text=text,
        data=data,
        graph=graph,
        url=str(collection.get("url", source.page_url(path, root))),
        title=title,
        h1=h1,
        name=name,
        kind=kind,
        item_names=item_names,
        district_names=district_names,
        category=category,
    )


def hub_faqs(ctx: HubContext) -> list[QA]:
    picker = StableChoice(ctx.url)
    count = len(ctx.item_names)
    if ctx.kind == "category":
        config = source.CATEGORIES[ctx.category]
        checks = source.check_items(
            # ``check_items`` only reads ``config``; a tiny proxy keeps one source.
            type("ConfigProxy", (), {"config": config})()  # type: ignore[arg-type]
        )
        process_names = "·".join(label for label, _ in config["process"])
        focus_text = "·".join(checks)
        label = config["label"]
        return [
            QA(
                f"전국 {label} 페이지는 어떤 기준으로 비교하나요?",
                f"{count}개 동네 페이지에서 {focus_text} 기준과 실제 연결 센터의 주소·가능 학년을 함께 확인합니다. 지역명만 보고 방문 위치를 판단하지 마세요.",
            ),
            QA(
                f"{label} 상담 전에 어떤 학습 자료를 준비하면 좋나요?",
                f"현재 교재, 최근 평가자료, 오답 기록, 학교 시험 일정을 준비하면 좋습니다. {process_names} 가운데 먼저 확인할 단계를 동네별 페이지에서 좁힐 수 있습니다.",
            ),
            QA(
                "동네명과 실제 상담 센터 위치가 다를 수 있나요?",
                "그럴 수 있습니다. 일부 페이지는 제공된 상담권역 자료에 따라 인접 센터로 연결되므로 각 상세페이지의 실제 센터명과 주소를 기준으로 확인해야 합니다.",
            ),
            QA(
                f"{label}의 개설 학년과 시간은 어디에서 확인하나요?",
                "각 동네 상세페이지에는 제공 자료에서 확인된 학년 범위를 표시합니다. 실제 개설 반과 시간은 등록 전에 연결 센터의 최신 시간표로 다시 확인해야 합니다.",
            ),
        ]
    district = "·".join(ctx.district_names[:4])
    district_note = (
        f"{district} 등 {len(ctx.district_names)}개 시·군·구"
        if ctx.district_names
        else "페이지에 표시된 시·군·구"
    )
    return [
        QA(
            f"{ctx.name} 지역 학원 페이지에서 무엇을 확인할 수 있나요?",
            f"{district_note}의 {count}개 동네 안내를 볼 수 있습니다. 각 상세페이지에서 실제 센터명·주소·가능 학년·참고 학교를 구분해 확인하세요.",
        ),
        QA(
            f"{ctx.name} 동네명 페이지가 모두 해당 동네 안의 독립 센터를 뜻하나요?",
            "항상 그렇지는 않습니다. 제공된 상담권역에 따라 인접 센터로 연결되는 페이지가 있으므로 상세페이지의 ‘실제 안내 센터’와 주소를 기준으로 방문 위치를 확인해야 합니다.",
        ),
        QA(
            f"{ctx.name} 지역에서 학년과 과목별 안내를 어떻게 비교하나요?",
            "동네 종합안내에서 영어·수학 가능 학년을 확인한 뒤 초등·중등·고등 영어·수학 상세페이지를 비교하세요. 실제 개설 시간은 센터 상담에서 다시 확인합니다.",
        ),
        QA(
            f"{ctx.name} 지역 상담 전에 어떤 자료를 준비하면 좋나요?",
            "현재 교재, 최근 시험지, 오답 기록, 다음 시험 일정, 실제 공부 가능한 시간을 준비하면 상세페이지의 점검 기준을 학생 상황에 맞게 확인할 수 있습니다.",
        ),
    ]


def hub_content(ctx: HubContext, faqs: Sequence[QA]) -> str:
    picker = StableChoice(ctx.url)
    count = len(ctx.item_names)
    if ctx.kind == "category":
        config = source.CATEGORIES[ctx.category]
        checks = source.check_items(
            type("ConfigProxy", (), {"config": config})()  # type: ignore[arg-type]
        )
        ordered = picker.order("hub-checks", checks)
        process_names = [label for label, _ in config["process"]]
        heading = f"{config['label']} 페이지를 비교할 때 먼저 볼 기준"
        direct = (
            f"이 허브는 {count}개 동네의 {config['label']} 안내를 연결합니다. "
            f"{ordered[0]}과 {ordered[1]}의 현재 상태를 먼저 확인한 뒤, "
            "실제 센터 주소·가능 학년·학교 참고 정보가 학생 상황과 맞는지 비교하세요."
        )
        cards = [
            (
                "현재 자료",
                f"교재와 최근 평가자료에서 {ordered[0]}과 {ordered[2]}이 드러나는 부분을 표시합니다.",
            ),
            (
                "관리 순서",
                f"{' → '.join(process_names)} 중 학생이 먼저 확인할 단계를 한 가지로 좁힙니다.",
            ),
            (
                "실제 센터",
                "동네 상세페이지의 센터명·주소·가능 학년을 확인하고 등록 전 최신 시간표를 다시 문의합니다.",
            ),
        ]
    else:
        district = "·".join(ctx.district_names[:5])
        heading = f"{ctx.name} 지역에서 동네 학원 안내를 확인하는 순서"
        direct = (
            f"{ctx.name} 허브는 {len(ctx.district_names)}개 시·군·구의 "
            f"{count}개 동네 페이지를 연결합니다. "
            f"{district + ' 등' if district else '표시된 지역별로'} 동네를 선택한 뒤 "
            "페이지의 실제 센터명·주소와 가능 학년을 먼저 확인하세요."
        )
        cards = [
            (
                "동네 페이지",
                "동네명은 상담 가능 지역을 찾기 위한 기준이며 실제 방문 장소는 상세페이지의 센터 정보로 구분합니다.",
            ),
            (
                "학년·과목",
                "종합안내와 초등·중등·고등 영어·수학 페이지를 함께 보고 제공된 가능 학년을 비교합니다.",
            ),
            (
                "상담 준비",
                "현재 교재·최근 시험지·오답 기록·학교 일정을 준비하고 센터의 최신 시간표를 확인합니다.",
            ),
        ]
    card_markup = "\n".join(
        f'''          <article class="geo-answer-card">
            <strong>{html.escape(label)}</strong>
            <p>{html.escape(body)}</p>
          </article>'''
        for label, body in cards
    )
    evidence = (
        "근거: 하위 상세페이지의 센터명·주소·가능 학년·학교 참고 정보는 "
        "학원 제공 센터정보와 교육지원청 등록정보를 기준으로 정리했습니다. "
        "교습비 공개자료가 연결된 센터는 해당 링크를 함께 확인하고, "
        "실제 개설 여부는 등록 전에 최신 시간표로 다시 확인해야 합니다."
    )
    return f'''  {HUB_MARKER_START}
  <section id="hub-decision-guide" class="local-section seo-geo-section" aria-label="{html.escape(ctx.h1)} 비교 안내">
    <div class="wrap seo-geo-enhancement">
      <article class="geo-answer-panel">
        <p class="eyebrow">선택 기준</p>
        <h2>{html.escape(heading)}</h2>
        <p>{html.escape(direct)}</p>
        <div class="geo-answer-grid">
{card_markup}
        </div>
        <p class="verified-note source-note">{html.escape(evidence)}</p>
      </article>
    </div>
  </section>
  {faq_html(ctx.h1, faqs, "hub-faq-section")}
  {HUB_MARKER_END}'''


def sync_hub_schema(text: str, ctx: HubContext, faqs: Sequence[QA]) -> str:
    data, match = source.parse_jsonld(text)
    graph = data["@graph"]
    faq = find_node(graph, "FAQPage")
    if faq is None:
        faq = {"@type": "FAQPage"}
        graph.append(faq)
    faq["@type"] = "FAQPage"
    faq["@id"] = ctx.url + "#faq"
    faq["mainEntity"] = faq_entities(faqs)
    collection = find_node(graph, "CollectionPage")
    if collection is None:
        raise ValueError(f"CollectionPage missing: {ctx.path}")
    existing = collection.get("hasPart", [])
    if isinstance(existing, dict):
        existing = [existing]
    if not isinstance(existing, list):
        existing = []
    preserved = [
        item
        for item in existing
        if not (
            isinstance(item, dict)
            and str(item.get("url", "")).endswith(
                ("#hub-decision-guide", "#hub-faq-section")
            )
        )
    ]
    preserved.extend(
        [
            {
                "@type": "WebPageElement",
                "name": "학원 안내 선택 기준",
                "url": ctx.url + "#hub-decision-guide",
            },
            {
                "@type": "WebPageElement",
                "name": "자주 묻는 질문",
                "url": ctx.url + "#hub-faq-section",
            },
        ]
    )
    collection["hasPart"] = preserved
    stamp_modified(graph, "CollectionPage")
    return replace_jsonld(text, data, match)


def transform_hub(ctx: HubContext) -> str:
    faqs = hub_faqs(ctx)
    block = hub_content(ctx, faqs)
    marker_pattern = re.compile(
        r"\s*" + re.escape(HUB_MARKER_START) + r".*?" + re.escape(HUB_MARKER_END),
        re.S,
    )
    if marker_pattern.search(ctx.text):
        text = replace_once(
            ctx.text,
            marker_pattern,
            "\n" + block,
            f"hub marker {ctx.path}",
        )
    else:
        if ctx.text.count("</main>") != 1:
            raise ValueError(f"Hub </main> count: {ctx.path}")
        closing_main = "  </main>" if "  </main>" in ctx.text else "</main>"
        text = ctx.text.replace(closing_main, block + "\n  </main>", 1)
    text = sync_hub_schema(text, ctx, faqs)
    return fix_particles_for_terms(text, hub_particle_terms(ctx))


def validate_hub(ctx: HubContext, text: str) -> list[str]:
    errors: list[str] = []
    invariants = [
        (
            "title",
            match_one(ctx.text, r"<title>(.*?)</title>"),
            match_one(text, r"<title>(.*?)</title>"),
        ),
        (
            "H1",
            clean(match_one(ctx.text, r"<h1\b[^>]*>(.*?)</h1>")),
            clean(match_one(text, r"<h1\b[^>]*>(.*?)</h1>")),
        ),
        (
            "canonical",
            match_one(
                ctx.text,
                r'<link\b(?=[^>]*rel=["\']canonical["\'])'
                r'[^>]*href=["\']([^"\']*)["\']',
            ),
            match_one(
                text,
                r'<link\b(?=[^>]*rel=["\']canonical["\'])'
                r'[^>]*href=["\']([^"\']*)["\']',
            ),
        ),
    ]
    for label, old, new in invariants:
        if old != new:
            errors.append(f"{label} changed")
    old_hrefs = set(re.findall(r'<a\b[^>]*href=["\']([^"\']+)["\']', ctx.text, re.I))
    new_hrefs = set(re.findall(r'<a\b[^>]*href=["\']([^"\']+)["\']', text, re.I))
    if not old_hrefs.issubset(new_hrefs):
        errors.append("existing hub links removed")
    if text.count(HUB_MARKER_START) != 1 or text.count(HUB_MARKER_END) != 1:
        errors.append("hub marker count")
    visible = visible_faq(text, "hub-faq-section")
    schema = schema_faq(text)
    if len(visible) != 4:
        errors.append(f"hub FAQ count {len(visible)}")
    if visible != schema:
        errors.append("hub FAQ screen/schema mismatch")
    guide = match_one(
        text,
        r'<section\b[^>]*id=["\']hub-decision-guide["\'][^>]*>(.*?)</section>',
    )
    # Three comparison cards plus a source note provide enough decision
    # context even for short region names; do not make character count depend
    # on whether a province happens to have long district labels.
    if len(clean(guide)) < 350:
        errors.append("hub guide too thin")
    for term in hub_particle_terms(ctx):
        for consonant_form, vowel_form in PARTICLE_PAIRS:
            _, wrong = correct_particle_pair(
                term,
                consonant_form,
                vowel_form,
            )
            if term + wrong in text:
                errors.append(f"hub particle error: {term + wrong}")
                break
    try:
        data, _ = source.parse_jsonld(text)
        graph = data["@graph"]
        for kind in ("CollectionPage", "ItemList", "BreadcrumbList", "FAQPage"):
            if find_node(graph, kind) is None:
                errors.append(f"hub missing JSON-LD {kind}")
        collection = find_node(graph, "CollectionPage")
        if (
            collection is not None
            and collection.get("dateModified") != REVISION_DATE
        ):
            errors.append("CollectionPage dateModified")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"hub JSON-LD invalid: {exc}")
    return errors


def normalized_signature(ctx: source.PageContext, value: str) -> str:
    facts = fact_bundle(ctx)
    replacements = {
        ctx.title,
        ctx.locality,
        ctx.info.locality,
        display_h1(ctx),
        ctx.config["label"],
        ctx.category,
        facts["center"],
        facts["address"],
        facts["grade_text"],
        *facts["schools"],
    }
    result = clean(value)
    for replacement in sorted(
        (item for item in replacements if item), key=len, reverse=True
    ):
        result = result.replace(replacement, " {ENTITY} ")
    result = re.sub(r"\d+(?:[.,]\d+)*", " {N} ", result)
    return re.sub(r"\s+", " ", result).strip()


def detail_section_signatures(
    ctx: source.PageContext, text: str
) -> dict[str, str]:
    hero = match_one(
        text,
        r'<section class="local-hero">.*?<h1\b[^>]*>.*?</h1>'
        r"\s*<p\b[^>]*>(.*?)</p>",
    )
    learning = match_one(
        text,
        r'<section id="learning-plan" class="local-section">(.*?)</section>',
    )
    summary = match_one(
        learning,
        r'<ul\b[^>]*class=["\'][^"\']*summary-list[^"\']*["\'][^>]*>'
        r"(.*?)</ul>",
    )
    checklist = match_one(
        text,
        r'<article id="consult-checklist"[^>]*>(.*?)</article>\s*</div>',
    )
    faq = match_one(
        text,
        r'<section id="faq-section"[^>]*>(.*?)</section>',
    )
    return {
        "hero": normalized_signature(ctx, hero),
        "summary": normalized_signature(ctx, summary),
        "learning": normalized_signature(ctx, learning),
        "checklist": normalized_signature(ctx, checklist),
        "faq": normalized_signature(ctx, faq),
    }


def diversity_report(
    staged: Sequence[tuple[source.PageContext, str]],
) -> dict[str, dict[str, float | int]]:
    values: dict[str, list[str]] = {
        "hero": [],
        "summary": [],
        "learning": [],
        "checklist": [],
        "faq": [],
    }
    for ctx, text in staged:
        signatures = detail_section_signatures(ctx, text)
        for name, value in signatures.items():
            values[name].append(value)
    result: dict[str, dict[str, float | int]] = {}
    for name, items in values.items():
        counts = Counter(items)
        result[name] = {
            "pages": len(items),
            "unique": len(counts),
            "unique_rate": round(len(counts) / len(items) * 100, 2),
            "largest_group": max(counts.values()),
        }
    return result


def prepare_detail_contexts(root: Path) -> list[source.PageContext]:
    center = root / source.CENTER_DIRNAME
    center_info = source.load_center_info(root)
    local_pages = [
        path
        for path in sorted(center.glob("*/index.html"))
        if source.normalize_locality(path.parent.name) in center_info
    ]
    local_names = {path.parent.name for path in local_pages}
    child_pages = [
        path
        for path in sorted(center.glob("*/*/index.html"))
        if path.parent.parent.name in local_names
        and path.parent.name in source.CATEGORIES
        and path.parent.name
    ]
    records, locality_to_key = source.build_center_records(root, local_pages)
    for record in records.values():
        record.areas = []
    for locality, key in locality_to_key.items():
        info = center_info.get(source.normalize_locality(locality))
        if info:
            area = service_area_name_from_info(info)
            if area and area not in records[key].areas:
                records[key].areas.append(area)
    for record in records.values():
        record.areas.sort()
    return [
        source.context_for(
            path, root, records, locality_to_key, center_info
        )
        for path in local_pages + child_pages
    ]


def prepare_hub_contexts(root: Path) -> list[HubContext]:
    center = root / source.CENTER_DIRNAME
    categories = {name for name in source.CATEGORIES if name}
    paths = [
        path / "index.html"
        for path in sorted(center.iterdir(), key=lambda item: item.name)
        if path.is_dir()
        and (path / "index.html").is_file()
        and not any(child.is_dir() for child in path.iterdir())
    ]
    result = [hub_context(path, root, categories) for path in paths]
    category_count = sum(context.kind == "category" for context in result)
    region_count = sum(context.kind == "region" for context in result)
    if category_count != 6 or region_count != 13:
        raise ValueError(
            f"Unexpected hub topology: regions={region_count} categories={category_count}"
        )
    return result


def write_staged(staged: Sequence[tuple[Path, str]]) -> None:
    temp_paths: list[tuple[Path, Path]] = []
    try:
        for path, text in staged:
            temp = path.with_name(path.name + ".refine-tmp")
            temp.write_text(text, encoding="utf-8", newline="\n")
            temp_paths.append((path, temp))
        for path, temp in temp_paths:
            temp.replace(path)
    finally:
        for _, temp in temp_paths:
            if temp.exists():
                temp.unlink()


def run_refinement(
    root: Path,
    *,
    scope: str = "all",
    apply: bool = False,
    emit: bool = True,
) -> dict[str, Any]:
    """Build and validate every requested change before optionally writing.

    This is the stable integration point used by both base generators.  It
    deliberately has no dependency on their command-line arguments.
    """

    if scope not in {"all", "details", "hubs"}:
        raise ValueError(f"Unsupported refinement scope: {scope}")
    root = root.resolve()
    staged_files: list[tuple[Path, str]] = []
    detail_stage: list[tuple[source.PageContext, str]] = []
    failures: list[tuple[str, list[str]]] = []

    if scope in ("all", "details"):
        for ctx in prepare_detail_contexts(root):
            try:
                transformed = transform_detail(ctx)
                errors = validate_detail(ctx, transformed)
            except Exception as exc:  # noqa: BLE001
                transformed = ""
                errors = [f"exception: {exc}"]
            if errors:
                failures.append((ctx.path.relative_to(root).as_posix(), errors))
            else:
                detail_stage.append((ctx, transformed))
                if transformed != ctx.text:
                    staged_files.append((ctx.path, transformed))

    if scope in ("all", "hubs"):
        for ctx in prepare_hub_contexts(root):
            try:
                transformed = transform_hub(ctx)
                errors = validate_hub(ctx, transformed)
            except Exception as exc:  # noqa: BLE001
                transformed = ""
                errors = [f"exception: {exc}"]
            if errors:
                failures.append((ctx.path.relative_to(root).as_posix(), errors))
            elif transformed != ctx.text:
                staged_files.append((ctx.path, transformed))

    diversity = diversity_report(detail_stage) if detail_stage else {}
    minimum_rates = {
        "hero": 65.0,
        "summary": 65.0,
        "learning": 80.0,
        "checklist": 65.0,
        "faq": 90.0,
    }
    for name, minimum in minimum_rates.items():
        if name in diversity and float(diversity[name]["unique_rate"]) < minimum:
            failures.append(
                (
                    "DIVERSITY",
                    [
                        f"{name} normalized unique rate "
                        f"{diversity[name]['unique_rate']} < {minimum}"
                    ],
                )
            )

    report: dict[str, Any] = {
        "scope": scope,
        "detail_pages": len(detail_stage),
        "staged_files": len(staged_files),
        "failures": failures,
        "apply": apply,
        "revision_date": REVISION_DATE,
        "diversity": diversity,
    }
    if emit:
        print(
            "scope={scope} detail_pages={details} staged_files={staged} "
            "failures={failures} apply={apply} revision_date={revision}".format(
            scope=scope,
            details=len(detail_stage),
            staged=len(staged_files),
            failures=len(failures),
            apply=apply,
            revision=REVISION_DATE,
            )
        )
        if diversity:
            print(
                json.dumps(
                    {"diversity": diversity},
                    ensure_ascii=False,
                    indent=2,
                )
            )
        for relative, errors in failures[:30]:
            print(f"FAIL {relative}: {', '.join(errors)}")
    if failures:
        raise RuntimeError(
            f"Refinement validation failed for {len(failures)} target(s)"
        )
    if apply:
        write_staged(staged_files)
        if emit:
            print(f"written={len(staged_files)}")
    elif emit:
        print("preview-only: no files written; rerun with --apply after review")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refine nationwide detail and hub copy; preview is the default."
    )
    parser.add_argument(
        "--scope",
        choices=("all", "details", "hubs"),
        default="all",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write only after every staged page passes validation.",
    )
    args = parser.parse_args()

    try:
        run_refinement(
            Path(__file__).resolve().parents[1],
            scope=args.scope,
            apply=args.apply,
        )
    except RuntimeError:
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
