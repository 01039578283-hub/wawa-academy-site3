"""Read-only release audit for the subject-professional page collection.

The generator creates one subject directory, four category hubs, and
4 x 371 locality detail pages.  This audit deliberately does not import the
generator: it checks the files that would actually be deployed against the
independent centre-information source and the site's existing map mapping.

Exit status is zero only when every release-blocking assertion passes.  The
script never writes to the site.
"""

from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SITE_URL = "https://xn--sp5b72l1taf0p.com"
SITE_HOSTS = {"xn--sp5b72l1taf0p.com", "코칭학원.com"}
DOMAIN_NAME = "코칭학원.com"
SITE_NAME = "와와학습코칭학원"
PHONE = "010-3957-8283"
SUBJECT_ROOT = ROOT / "과목별학원"
CENTER_CSV = ROOT.parent / "참고자료" / "공통자료" / "센터정보 정리.csv"

CATEGORIES: dict[str, dict[str, Any]] = {
    "영수전문학원": {
        "label": "영수 전문학원",
        "focus": "combined",
        "subjects": ("영어", "수학"),
    },
    "영어전문학원": {
        "label": "영어 전문학원",
        "focus": "english",
        "subjects": ("영어",),
    },
    "수학전문학원": {
        "label": "수학 전문학원",
        "focus": "math",
        "subjects": ("수학",),
    },
    "전문학원": {
        "label": "전문학원",
        "focus": "combined",
        "subjects": ("영어", "수학"),
    },
}

DETAIL_SCHEMA_TYPES = {
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
HUB_SCHEMA_TYPES = {"CollectionPage", "BreadcrumbList", "ItemList", "FAQPage"}

# Production-language residue and known malformed source phrases are never
# appropriate in reader-facing detail content.
BLOCKED_TEXT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("authoring_seo_aeo_geo", re.compile(r"(?<![A-Za-z])(?:SEO|AEO|GEO|JSON-LD)(?![A-Za-z])", re.I)),
    ("authoring_manuscript", re.compile(r"(?<![가-힣])원고(?:처럼|라면|입니다|에서는|에서|에는|에|의|를|로|가|는|와)?(?![가-힣])")),
    ("authoring_page_intent", re.compile(r"이 페이지|페이지여야|검색 의도|검색자|참고 키워드|운영 키워드|설정한 학생")),
    ("synthetic_review_wording", re.compile(r"후기형\s*예시|후기\s*예시|형식의\s*후기|내용으로\s*정리할\s*수\s*있습니다")),
    ("source_column_wording", re.compile(r"D열|수업학교|본문에서\s*학교명|자료에\s*없는\s*학교를\s*임의로")),
    ("broken_student_particle", re.compile(r"학생(?:를|가|와|라는)")),
    ("broken_grade_particle", re.compile(r"학년(?:를|가|와)")),
    ("broken_awkward_student", re.compile(r"편\s*학생|학부모에게는\s*학부모|것이라는\s*목표")),
    ("broken_semicolon", re.compile(r"(?:합니다|입니다|있습니다);")),
    ("broken_subject_spacing", re.compile(r"영어\s+수학")),
    ("broken_address_split", re.compile(r"304\.[가-힣]|305으로")),
    ("broken_duplicate_noun", re.compile(r"(?P<noun>학생|상담|관리|학습|수업)\s+(?P=noun)")),
    ("broken_design_particle", re.compile(r"수업\s*설계은|피드백\s*구조은")),
    ("broken_choice_phrase", re.compile(r"선택\s*전\s*확인할\s*(?:확인\s*항목|선택\s*기준)")),
    ("authoring_source_wording", re.compile(r"자료에\s*(?:적힌|제시된)|제공된\s*주소\s*정보|구조화\s*데이터")),
    ("broken_grade_student_phrase", re.compile(r"(?:(?:초등|중등|중|고등)(?:학교)?\s*[1-6]\s*학년|해당\s*학년)\s+중\s+[^,.]{2,120}?학생")),
    ("authoring_address_wording", re.compile(r"주소\s*정보는\s*.{5,180}?\s*기준으로\s*제공되어\s*있습니다")),
    ("broken_math_solution_particle", re.compile(r"수학\s*풀이이|영어\s*답안과\s*수학\s*풀이와")),
    ("broken_repeated_school_source", re.compile(r"학생이\s*받은\s*학교에서\s*받은\s*자료|학생이\s*가져온\s*제공된\s*학교\s*자료")),
    ("broken_repeated_process", re.compile(r"과정이\s*필요한\s*과정|학습학습|시험학습\s*성과")),
    ("broken_guidance_phrase", re.compile(r"보는\s*지도가\s*확인할\s*필요|최근\s*교재\s*활용과\s*교재")),
    ("broken_repeated_student_explanation", re.compile(r"학생이\s*설명한\s*두\s*과목\s*내용을\s*학생의\s*설명")),
    ("broken_grade_list_particle", re.compile(r"[초중고][1-6](?:·[초중고][1-6])+?이\s+(?:확인된\s*수업\s*가능\s*학년|전문학원\s*상담\s*가능\s*학년)")),
    ("broken_object_particle", re.compile(r"(?:루틴|장치|구조|절차|관리)(?:가|이)\s+확인할\s+필요")),
    ("broken_repeated_consultation", re.compile(r"상담\s+첫\s+상담")),
)

# These terms came from an unrelated keyword bank and cannot be asserted as
# centre services without a separate verified source.
UNVERIFIED_OPERATION_PATTERN = re.compile(
    r"입시실적|입시성공사례|입시합격(?:관리|전략)|학원창업|학원운영자|"
    r"학원차량|차량\s*운행|학원주차|셔틀|학원온라인등록|"
    r"(?:학원)?(?:온라인|화상|녹화|실시간)수업|방학캠프|입시캠프|성적향상수업"
)


class Audit:
    """Collect bounded examples while retaining exact issue totals."""

    def __init__(self) -> None:
        self.counts: Counter[str] = Counter()
        self.examples: dict[str, list[dict[str, str]]] = defaultdict(list)

    def fail(self, code: str, page: Path | str, detail: object) -> None:
        self.counts[code] += 1
        if len(self.examples[code]) >= 5:
            return
        if isinstance(page, Path):
            try:
                label = page.relative_to(ROOT).as_posix()
            except ValueError:
                label = str(page)
        else:
            label = str(page)
        self.examples[code].append({"page": label, "detail": str(detail)[:500]})


def normalize(value: object) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(value or ""))).strip()


def normalize_space(value: object) -> str:
    return " ".join(str(value or "").split())


def clean_markup(value: str) -> str:
    value = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", value, flags=re.I | re.S)
    return normalize_space(html.unescape(re.sub(r"<[^>]+>", " ", value)))


def match_one(value: str, pattern: str) -> str | None:
    found = re.search(pattern, value, re.I | re.S)
    return html.unescape(found.group(1)).strip() if found else None


def tag_attr(tag: str, name: str) -> str | None:
    found = re.search(rf"\b{re.escape(name)}\s*=\s*([\"'])(.*?)\1", tag, re.I | re.S)
    return html.unescape(found.group(2)).strip() if found else None


def meta_content(source: str, key: str, value: str) -> str | None:
    pattern = rf"<{key}\b(?=[^>]*\b(?:name|property)=[\"']{re.escape(value)}[\"'])[^>]*>"
    tag = match_one(source, f"({pattern})")
    return tag_attr(tag, "content") if tag else None


def canonical_value(source: str) -> str | None:
    tag = match_one(source, r"(<link\b(?=[^>]*\brel=[\"']canonical[\"'])[^>]*>)")
    return tag_attr(tag, "href") if tag else None


def encoded_url(*parts: str) -> str:
    suffix = "/".join(quote(part, safe="") for part in parts)
    return f"{SITE_URL}/{suffix}/" if suffix else SITE_URL + "/"


def split_grades(value: str) -> list[str]:
    return unique(part.strip() for part in re.split(r"[,/|\s]+", value or ""))


def split_schools(value: str) -> list[str]:
    return unique(part.strip() for part in re.split(r"[,./|\s]+", value or ""))


def unique(values: Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = str(value or "").strip(" ,·/|")
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def load_centres(audit: Audit) -> tuple[list[str], dict[str, dict[str, str]], dict[str, str]]:
    if not CENTER_CSV.is_file():
        audit.fail("missing_center_csv", CENTER_CSV, "센터정보 정리.csv가 없습니다")
        return [], {}, {}
    with CENTER_CSV.open(encoding="utf-8-sig", newline="") as handle:
        source_rows = list(csv.DictReader(handle))
    if len(source_rows) != 371:
        audit.fail("center_row_count", CENTER_CSV, f"expected=371 actual={len(source_rows)}")

    existing: dict[str, str] = {}
    centre_root = ROOT / "전국센터"
    if centre_root.is_dir():
        for folder in centre_root.iterdir():
            if folder.is_dir() and (folder / "index.html").is_file():
                existing[normalize(folder.name)] = folder.name
    aliases = {
        normalize("부천 상동"): "부천상동",
        normalize("당진 읍내동"): "당진읍내동",
        normalize("전주 장동"): "전주장동",
    }

    order: list[str] = []
    rows: dict[str, dict[str, str]] = {}
    displays: dict[str, str] = {}
    for raw in source_rows:
        row = {str(key): str(value or "").strip() for key, value in raw.items()}
        display = row.get("근처 수업가능 동네", "")
        folder = existing.get(normalize(display)) or aliases.get(normalize(display), "")
        if not folder or not (centre_root / folder / "index.html").is_file():
            audit.fail("center_locality_mapping", CENTER_CSV, display)
            continue
        if folder in rows:
            audit.fail("duplicate_center_locality", CENTER_CSV, folder)
            continue
        order.append(folder)
        rows[folder] = row
        displays[folder] = display
    if len(order) != 371 or len(set(order)) != 371:
        audit.fail("mapped_center_count", CENTER_CSV, f"mapped={len(order)} unique={len(set(order))}")
    return order, rows, displays


def expected_grades(row: dict[str, str], focus: str) -> list[str]:
    english = split_grades(row.get("가능학년\n(영어)", ""))
    math = split_grades(row.get("가능학년\n(수학)", ""))
    if focus == "english":
        return english
    if focus == "math":
        return math
    math_set = set(math)
    return [grade for grade in english if grade in math_set]


def expected_schools(row: dict[str, str]) -> list[str]:
    return unique(
        school
        for key in ("타깃학교\n(초)", "타깃학교\n(중)", "타깃학교\n(고)")
        for school in split_schools(row.get(key, ""))
        if school not in {"초등학교", "중학교", "고등학교"}
        and re.search(r"(?:초|중|고|초등학교|중학교|고등학교)$", school)
    )


def school_aliases(schools: list[str] | set[str]) -> set[str]:
    result: set[str] = set()
    for school in schools:
        result.add(school)
        shortened = (
            school.replace("초등학교", "초")
            .replace("중학교", "중")
            .replace("고등학교", "고")
        )
        if shortened not in {"초", "중", "고"}:
            result.add(shortened)
    return result


def normalize_asset_path(source: str) -> str:
    path = unquote(urlsplit(html.unescape(source)).path)
    path = "/" + path.lstrip("./").replace("../", "")
    return path


def expected_map(local: str, audit: Audit) -> str:
    reference = ROOT / "전국센터" / local / "고등수학학원" / "index.html"
    if not reference.is_file():
        audit.fail("missing_map_reference_page", reference, local)
        return ""
    source = reference.read_text(encoding="utf-8")
    images = re.findall(r"<img\b[^>]*\bsrc=([\"'])(.*?)\1", source, re.I | re.S)
    maps = [normalize_asset_path(value) for _, value in images if "/assets/maps/" in value or "assets/maps/" in value]
    if not maps:
        audit.fail("missing_reference_map", reference, local)
        return ""
    return maps[-1]


def schema_graph(source: str, page: Path, audit: Audit) -> list[dict[str, Any]]:
    scripts = re.findall(
        r"<script\b[^>]*\btype=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
        source,
        re.I | re.S,
    )
    if not scripts:
        audit.fail("missing_jsonld", page, "application/ld+json")
        return []
    graph: list[dict[str, Any]] = []
    for raw in scripts:
        try:
            data = json.loads(html.unescape(raw))
        except Exception as exc:  # noqa: BLE001 - report the malformed deployed payload
            audit.fail("invalid_jsonld", page, exc)
            continue
        values = data.get("@graph") if isinstance(data, dict) else data
        if isinstance(values, list):
            graph.extend(item for item in values if isinstance(item, dict))
        elif isinstance(data, dict):
            graph.append(data)
    ids = [str(node.get("@id", "")) for node in graph if node.get("@id")]
    if len(ids) != len(set(ids)):
        audit.fail("duplicate_schema_id", page, "duplicate @id in graph")
    return graph


def node_types(node: dict[str, Any]) -> set[str]:
    value = node.get("@type")
    if isinstance(value, list):
        return {str(item) for item in value}
    return {str(value)} if value else set()


def nodes_of_type(graph: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    return [node for node in graph if kind in node_types(node)]


def one_node(graph: list[dict[str, Any]], kind: str, page: Path, audit: Audit) -> dict[str, Any]:
    nodes = nodes_of_type(graph, kind)
    if len(nodes) != 1:
        audit.fail("schema_type_count", page, f"{kind}: expected=1 actual={len(nodes)}")
        return nodes[0] if nodes else {}
    return nodes[0]


def visible_faq(source: str) -> list[tuple[str, str]]:
    block = match_one(source, r"<section\b[^>]*\bid=[\"']faq-section[\"'][^>]*>(.*?)</section>")
    if block is None:
        return []
    result: list[tuple[str, str]] = []
    for details in re.findall(r"<details\b[^>]*>(.*?)</details>", block, re.I | re.S):
        question = match_one(details, r"<summary\b[^>]*>(.*?)</summary>")
        answer = match_one(details, r"<p\b[^>]*>(.*?)</p>")
        if question is not None and answer is not None:
            result.append((clean_markup(question), clean_markup(answer)))
    return result


def schema_faq(graph: list[dict[str, Any]]) -> list[tuple[str, str]]:
    nodes = nodes_of_type(graph, "FAQPage")
    if len(nodes) != 1:
        return []
    result: list[tuple[str, str]] = []
    entities = nodes[0].get("mainEntity", [])
    if not isinstance(entities, list):
        return result
    for item in entities:
        if not isinstance(item, dict):
            continue
        answer = item.get("acceptedAnswer", {})
        result.append(
            (
                normalize_space(item.get("name", "")),
                normalize_space(answer.get("text", "") if isinstance(answer, dict) else ""),
            )
        )
    return result


def visible_breadcrumb(source: str) -> list[str]:
    block = match_one(source, r"<div\b[^>]*\bclass=[\"'][^\"']*\bcrumbs\b[^\"']*[\"'][^>]*>(.*?)</div>")
    if block is None:
        return []
    return [clean_markup(item) for item in re.findall(r"<span\b[^>]*>(.*?)</span>", block, re.I | re.S)]


def schema_breadcrumb(graph: list[dict[str, Any]]) -> list[tuple[str, str]]:
    nodes = nodes_of_type(graph, "BreadcrumbList")
    if len(nodes) != 1:
        return []
    items = nodes[0].get("itemListElement", [])
    if not isinstance(items, list):
        return []
    ordered = sorted(
        (item for item in items if isinstance(item, dict)),
        key=lambda item: int(item.get("position", 0) or 0),
    )
    return [(normalize_space(item.get("name", "")), str(item.get("item", ""))) for item in ordered]


def href_target(page: Path, href: str, audit: Audit) -> Path | None:
    href = html.unescape(href.strip())
    if not href or href.startswith(("#", "tel:", "mailto:", "javascript:", "data:")):
        return None
    parts = urlsplit(href)
    if parts.scheme in {"http", "https"}:
        if parts.hostname not in SITE_HOSTS:
            return None
        target = ROOT / unquote(parts.path).lstrip("/")
    elif parts.scheme or href.startswith("//"):
        return None
    else:
        relative = unquote(parts.path)
        target = (page.parent / relative).resolve() if relative else page
    root = ROOT.resolve()
    try:
        target.resolve().relative_to(root)
    except ValueError:
        audit.fail("internal_link_path_escape", page, href)
        return target
    if parts.path.endswith("/") or target.is_dir():
        target = target / "index.html"
    return target


def audit_internal_links(page: Path, source: str, audit: Audit) -> None:
    for href in re.findall(r"<a\b[^>]*\bhref=([\"'])(.*?)\1", source, re.I | re.S):
        target = href_target(page, href[1], audit)
        if target is not None and not target.exists():
            audit.fail("broken_internal_link", page, href[1])


def audit_metadata(
    page: Path,
    source: str,
    expected_title: str,
    expected_h1: str,
    expected_url: str,
    audit: Audit,
    *,
    detail: bool,
) -> tuple[str, str, str]:
    titles = re.findall(r"<title\b[^>]*>(.*?)</title>", source, re.I | re.S)
    if len(titles) != 1:
        audit.fail("title_count", page, len(titles))
    title = clean_markup(titles[0]) if titles else ""
    if title != expected_title:
        audit.fail("title_mismatch", page, f"expected={expected_title!r} actual={title!r}")

    descriptions = re.findall(
        r"<meta\b(?=[^>]*\bname=[\"']description[\"'])[^>]*>", source, re.I | re.S
    )
    if len(descriptions) != 1:
        audit.fail("meta_description_count", page, len(descriptions))
    description = tag_attr(descriptions[0], "content") if descriptions else ""
    description = description or ""
    if not description:
        audit.fail("empty_meta_description", page, "")
    if detail and not 70 <= len(description) <= 100:
        audit.fail("detail_meta_length", page, len(description))

    h1_values = [clean_markup(value) for value in re.findall(r"<h1\b[^>]*>(.*?)</h1>", source, re.I | re.S)]
    if len(h1_values) != 1:
        audit.fail("h1_count", page, len(h1_values))
    h1 = h1_values[0] if h1_values else ""
    if h1 != expected_h1:
        audit.fail("h1_mismatch", page, f"expected={expected_h1!r} actual={h1!r}")

    canonical = canonical_value(source) or ""
    og_url = meta_content(source, "meta", "og:url") or ""
    if canonical != expected_url:
        audit.fail("canonical_mismatch", page, f"expected={expected_url} actual={canonical}")
    if og_url != expected_url:
        audit.fail("og_url_mismatch", page, f"expected={expected_url} actual={og_url}")
    if canonical != og_url:
        audit.fail("canonical_og_mismatch", page, f"canonical={canonical} og={og_url}")
    if canonical and any("가" <= char <= "힣" for char in canonical):
        audit.fail("canonical_not_percent_encoded", page, canonical)
    if meta_content(source, "meta", "og:title") != expected_title:
        audit.fail("og_title_mismatch", page, meta_content(source, "meta", "og:title"))
    if meta_content(source, "meta", "og:description") != description:
        audit.fail("og_description_mismatch", page, "og:description differs from meta")
    return title, description, canonical


def audit_hub(
    page: Path,
    expected_url: str,
    expected_title: str,
    expected_h1: str,
    expected_crumbs: list[str],
    expected_items: list[tuple[str, str]],
    audit: Audit,
) -> dict[str, str]:
    if not page.is_file():
        audit.fail("missing_hub", page, expected_url)
        return {"title": "", "description": "", "canonical": ""}
    source = page.read_text(encoding="utf-8")
    title, description, canonical = audit_metadata(
        page, source, expected_title, expected_h1, expected_url, audit, detail=False
    )
    graph = schema_graph(source, page, audit)
    present_types = set().union(*(node_types(node) for node in graph)) if graph else set()
    for kind in HUB_SCHEMA_TYPES - present_types:
        audit.fail("hub_missing_schema_type", page, kind)
    collection = one_node(graph, "CollectionPage", page, audit)
    if collection and collection.get("url") != expected_url:
        audit.fail("hub_collection_url", page, collection.get("url"))

    faq_visible = visible_faq(source)
    faq_structured = schema_faq(graph)
    if len(faq_visible) < 3:
        audit.fail("hub_visible_faq_count", page, len(faq_visible))
    if faq_visible != faq_structured:
        audit.fail("faq_schema_mismatch", page, f"visible={len(faq_visible)} schema={len(faq_structured)}")

    crumbs = visible_breadcrumb(source)
    if crumbs != expected_crumbs:
        audit.fail("visible_breadcrumb_mismatch", page, f"expected={expected_crumbs} actual={crumbs}")
    structured_crumbs = schema_breadcrumb(graph)
    if [name for name, _ in structured_crumbs] != expected_crumbs:
        audit.fail("schema_breadcrumb_names", page, structured_crumbs)
    if not structured_crumbs or structured_crumbs[-1][1] != expected_url:
        audit.fail("schema_breadcrumb_last_url", page, structured_crumbs[-1] if structured_crumbs else "missing")

    item_list = one_node(graph, "ItemList", page, audit)
    items = item_list.get("itemListElement", []) if item_list else []
    actual_items: list[tuple[str, str]] = []
    if isinstance(items, list):
        for item in sorted(
            (value for value in items if isinstance(value, dict)),
            key=lambda value: int(value.get("position", 0) or 0),
        ):
            actual_items.append((normalize_space(item.get("name", "")), str(item.get("url", ""))))
    if actual_items != expected_items:
        audit.fail("hub_itemlist_mismatch", page, f"expected={len(expected_items)} actual={len(actual_items)}")
    audit_internal_links(page, source, audit)
    return {"title": title, "description": description, "canonical": canonical}


def flatten_school_names(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for value in values:
        if isinstance(value, dict):
            result.extend(split_schools(str(value.get("name", ""))))
        else:
            result.extend(split_schools(str(value)))
    return unique(result)


def extract_explicit_grades(value: str) -> set[str]:
    grades = set(re.findall(r"(?<![가-힣0-9])([초중고][1-6])(?![0-9])", value))
    prefix = {"초등학교": "초", "초등": "초", "중학교": "중", "중등": "중", "고등학교": "고", "고등": "고"}
    for level, number in re.findall(r"(초등학교|초등|중학교|중등|고등학교|고등)\s*([1-6])\s*학년", value):
        grades.add(prefix[level] + number)
    return grades


def known_school_mentions(value: str) -> set[str]:
    """Return longest verified school-name matches from visible prose.

    Some centre rows contain a short name that is also the suffix of a longer
    school name (for example, ``중앙고``).  Keeping only non-contained longest
    matches prevents the shorter school from being reported as a foreign
    entity when the visible text contains the verified longer name.
    """
    locality_spans = [
        (match.start(), match.end())
        for locality in ALL_LOCAL_NAMES
        for match in re.finditer(re.escape(locality), value)
    ]
    candidates: list[tuple[int, int, str]] = []
    for school in ALL_SCHOOL_NAMES:
        if len(school) < 3:
            continue
        for match in re.finditer(re.escape(school), value):
            if any(start <= match.start() and match.end() <= end for start, end in locality_spans):
                continue
            candidates.append((match.start(), match.end(), school))
    return {
        school
        for start, end, school in candidates
        if not any(
            other_start <= start
            and end <= other_end
            and other_end - other_start > end - start
            for other_start, other_end, _ in candidates
        )
    }


def expected_reference_map(local: str, cache: dict[str, str], audit: Audit) -> str:
    if local not in cache:
        cache[local] = expected_map(local, audit)
    return cache[local]


def file_for_asset(source: str) -> Path:
    return ROOT / normalize_asset_path(source).lstrip("/")


def audit_media(
    page: Path,
    source: str,
    title: str,
    local: str,
    row: dict[str, str],
    map_cache: dict[str, str],
    audit: Audit,
) -> str:
    block = match_one(
        source,
        r"<section\b[^>]*\bclass=[\"'][^\"']*subject-media-section[^\"']*[\"'][^>]*>(.*?)</section>",
    )
    if block is None:
        audit.fail("missing_subject_media", page, "subject-media-section")
        return ""
    tags = re.findall(r"<img\b[^>]*>", block, re.I | re.S)
    hidden = [tag for tag in tags if re.search(r"display\s*:\s*none", tag_attr(tag, "style") or "", re.I)]
    if len(hidden) != 1:
        audit.fail("hidden_representative_count", page, len(hidden))
        representative = ""
    else:
        representative = tag_attr(hidden[0], "src") or ""
        if not normalize_asset_path(representative).startswith("/assets/representative/"):
            audit.fail("representative_path", page, representative)
        if tag_attr(hidden[0], "alt") != f"{title} {DOMAIN_NAME} 대표":
            audit.fail("representative_alt", page, tag_attr(hidden[0], "alt"))
        if not file_for_asset(representative).is_file():
            audit.fail("missing_representative_asset", page, representative)

    picture = match_one(source, r"<picture\b[^>]*\bclass=[\"'][^\"']*local-responsive-picture[^\"']*[\"'][^>]*>(.*?)</picture>")
    expected_body = "/assets/centers/common/seoul-q92.webp" if row.get("지역") == "서울" else "/assets/centers/common/local-q92.webp"
    expected_mobile = "/assets/centers/common/seoul-mobile.webp" if row.get("지역") == "서울" else "/assets/centers/common/local-mobile.webp"
    if picture is None:
        audit.fail("missing_body_picture", page, "local-responsive-picture")
    else:
        source_tag = match_one(picture, r"(<source\b[^>]*>)") or ""
        image_tag = match_one(picture, r"(<img\b[^>]*>)") or ""
        actual_mobile = normalize_asset_path(tag_attr(source_tag, "srcset") or "")
        actual_body = normalize_asset_path(tag_attr(image_tag, "src") or "")
        if actual_mobile != expected_mobile:
            audit.fail("body_mobile_mismatch", page, f"expected={expected_mobile} actual={actual_mobile}")
        if actual_body != expected_body:
            audit.fail("body_image_mismatch", page, f"expected={expected_body} actual={actual_body}")
        for asset in (actual_mobile, actual_body):
            if asset and not (ROOT / asset.lstrip("/")).is_file():
                audit.fail("missing_body_asset", page, asset)

    figure = match_one(source, r"<figure\b[^>]*\bclass=[\"'][^\"']*location-card[^\"']*[\"'][^>]*>(.*?)</figure>")
    if figure is None:
        audit.fail("missing_map_figure", page, "location-card")
    else:
        image_tag = match_one(figure, r"(<img\b[^>]*>)") or ""
        actual_map = normalize_asset_path(tag_attr(image_tag, "src") or "")
        wanted_map = expected_reference_map(local, map_cache, audit)
        if actual_map != wanted_map:
            audit.fail("map_image_mismatch", page, f"expected={wanted_map} actual={actual_map}")
        if actual_map and not (ROOT / actual_map.lstrip("/")).is_file():
            audit.fail("missing_map_asset", page, actual_map)
    return normalize_asset_path(representative) if representative else ""


def article_markup(source: str) -> str:
    return match_one(
        source,
        r"<article\b[^>]*\bclass=[\"'][^\"']*subject-article[^\"']*[\"'][^>]*>(.*?)</article>",
    ) or ""


def mask_facts(
    value: str,
    local: str,
    display: str,
    row: dict[str, str],
    category: dict[str, Any],
) -> str:
    facts = [
        local,
        display,
        str(category["label"]),
        str(row.get("지역", "")),
        str(row.get("시or구", "")),
        str(row.get("센터명", "")),
        str(row.get("교육지원청명칭", "")),
        str(row.get("교육지원청 등록번호", "")),
        str(row.get("센터 주소", "")),
        *expected_grades(row, str(category["focus"])),
        *expected_schools(row),
    ]
    result = unicodedata.normalize("NFKC", value)
    for fact in sorted(set(filter(None, facts)), key=len, reverse=True):
        result = result.replace(fact, " <FACT> ")
    result = re.sub(r"\d+", "0", result)
    return normalize_space(result)


def five_word_shingles(value: str) -> set[tuple[str, ...]]:
    tokens = re.findall(r"[가-힣A-Za-z]+|<FACT>|0", value.lower())
    if len(tokens) < 5:
        return {tuple(tokens)} if tokens else set()
    return {tuple(tokens[index:index + 5]) for index in range(len(tokens) - 4)}


def jaccard(left: set[tuple[str, ...]], right: set[tuple[str, ...]]) -> float:
    return len(left & right) / len(left | right) if left or right else 1.0


def check_blocked_text(page: Path, value: str, audit: Audit) -> None:
    for code, pattern in BLOCKED_TEXT_PATTERNS:
        match = pattern.search(value)
        if match:
            audit.fail(code, page, match.group(0))
    match = UNVERIFIED_OPERATION_PATTERN.search(value)
    if match:
        audit.fail("unverified_operation_term", page, match.group(0))


def audit_detail(
    page: Path,
    slug: str,
    category: dict[str, Any],
    local: str,
    display: str,
    row: dict[str, str],
    order: list[str],
    index: int,
    map_cache: dict[str, str],
    audit: Audit,
) -> dict[str, Any]:
    expected_title = f"{local} {category['label']}"
    expected_url = encoded_url("과목별학원", slug, local)
    if not page.is_file():
        audit.fail("missing_detail", page, expected_url)
        return {"title": "", "meta": "", "canonical": "", "representative": "", "article": ""}
    source = page.read_text(encoding="utf-8")
    title, description, canonical = audit_metadata(
        page,
        source,
        f"{expected_title} | {DOMAIN_NAME}",
        expected_title,
        expected_url,
        audit,
        detail=True,
    )
    graph = schema_graph(source, page, audit)
    present_types = set().union(*(node_types(node) for node in graph)) if graph else set()
    for kind in DETAIL_SCHEMA_TYPES - present_types:
        audit.fail("detail_missing_schema_type", page, kind)

    expected_grade_list = expected_grades(row, str(category["focus"]))
    expected_school_list = expected_schools(row)
    expected_school_set = set(expected_school_list)
    expected_school_alias_set = school_aliases(expected_school_set)
    centre_url = encoded_url("전국센터", local)
    centre_id = centre_url + "#organization"

    webpage = one_node(graph, "WebPage", page, audit)
    if webpage:
        if webpage.get("url") != expected_url or webpage.get("name") != f"{expected_title} | {DOMAIN_NAME}":
            audit.fail("webpage_identity", page, f"url={webpage.get('url')} name={webpage.get('name')}")
        if webpage.get("description") != description:
            audit.fail("webpage_description", page, webpage.get("description"))
        for key in ("about", "mentions", "breadcrumb", "mainEntity", "primaryImageOfPage"):
            if not webpage.get(key):
                audit.fail("webpage_missing_relation", page, key)

    organizations = [node for node in graph if {"EducationalOrganization", "LocalBusiness"}.issubset(node_types(node))]
    if len(organizations) != 1:
        audit.fail("combined_organization_type", page, len(organizations))
        organization = organizations[0] if organizations else {}
    else:
        organization = organizations[0]
    if organization:
        if organization.get("@id") != centre_id:
            audit.fail("organization_id", page, organization.get("@id"))
        if organization.get("name") != row.get("센터명"):
            audit.fail("organization_name", page, organization.get("name"))
        if organization.get("url") != centre_url:
            audit.fail("organization_url", page, organization.get("url"))
        if organization.get("telephone") != PHONE:
            audit.fail("organization_phone", page, organization.get("telephone"))
        address = organization.get("address", {})
        if not isinstance(address, dict) or address.get("streetAddress") != row.get("센터 주소"):
            audit.fail("organization_address", page, address)
        identifier = organization.get("identifier")
        expected_identifier = row.get("교육지원청 등록번호", "")
        actual_identifier = identifier.get("value", "") if isinstance(identifier, dict) else ""
        if actual_identifier != expected_identifier:
            audit.fail("organization_identifier", page, f"expected={expected_identifier!r} actual={actual_identifier!r}")
        levels = organization.get("educationalLevel", [])
        if levels != expected_grade_list:
            audit.fail("organization_grades", page, f"expected={expected_grade_list} actual={levels}")
        teaches = organization.get("teaches", [])
        if expected_grade_list and teaches != list(category["subjects"]):
            audit.fail("organization_teaches", page, f"expected={category['subjects']} actual={teaches}")
        if not expected_grade_list and (teaches or organization.get("makesOffer")):
            audit.fail("unverified_empty_grade_offer", page, "teaches/makesOffer must be absent")
        if expected_grade_list and row.get("센터 교습비"):
            offers = organization.get("makesOffer", [])
            offer_urls = [offer.get("url") for offer in offers if isinstance(offer, dict)] if isinstance(offers, list) else []
            if row["센터 교습비"] not in offer_urls:
                audit.fail("organization_tuition_offer", page, offer_urls)

    article = one_node(graph, "Article", page, audit)
    if article:
        if article.get("headline") != expected_title:
            audit.fail("article_headline", page, article.get("headline"))
        for key in ("about", "mentions", "hasPart", "articleSection", "mainEntityOfPage", "isBasedOn"):
            if not article.get(key):
                audit.fail("article_missing_relation", page, key)
        article_school_set = set(flatten_school_names([
            item for item in article.get("mentions", [])
            if isinstance(item, dict) and item.get("@type") == "Organization"
        ]))
        if article_school_set != expected_school_set:
            audit.fail("article_school_mentions", page, f"expected={sorted(expected_school_set)} actual={sorted(article_school_set)}")

    service = one_node(graph, "Service", page, audit)
    if service:
        provider = service.get("provider", {})
        if not isinstance(provider, dict) or provider.get("@id") != centre_id:
            audit.fail("service_provider", page, provider)
        if not service.get("about"):
            audit.fail("service_about", page, "missing")
        audience = service.get("audience")
        actual_audience = audience.get("audienceType", "") if isinstance(audience, dict) else ""
        expected_audience = " · ".join(expected_grade_list)
        if actual_audience != expected_audience:
            audit.fail("service_audience", page, f"expected={expected_audience!r} actual={actual_audience!r}")
        if not expected_grade_list and service.get("offers"):
            audit.fail("service_unverified_offer", page, "offers must be absent")

    image = one_node(graph, "ImageObject", page, audit)
    faq_visible = visible_faq(source)
    faq_structured = schema_faq(graph)
    if len(faq_visible) < 3:
        audit.fail("detail_visible_faq_count", page, len(faq_visible))
    if faq_visible != faq_structured:
        audit.fail("faq_schema_mismatch", page, f"visible={len(faq_visible)} schema={len(faq_structured)}")

    expected_crumbs = ["홈", "과목별학원", str(category["label"]), expected_title]
    crumbs = visible_breadcrumb(source)
    if crumbs != expected_crumbs:
        audit.fail("visible_breadcrumb_mismatch", page, f"expected={expected_crumbs} actual={crumbs}")
    structured_crumbs = schema_breadcrumb(graph)
    if [name for name, _ in structured_crumbs] != expected_crumbs:
        audit.fail("schema_breadcrumb_names", page, structured_crumbs)
    expected_crumb_urls = [
        SITE_URL + "/",
        encoded_url("과목별학원"),
        encoded_url("과목별학원", slug),
        expected_url,
    ]
    if [url for _, url in structured_crumbs] != expected_crumb_urls:
        audit.fail("schema_breadcrumb_urls", page, structured_crumbs)

    sections = re.findall(
        r"<section\b[^>]*\bid=[\"']section-(\d+)[\"'][^>]*>(.*?)</section>",
        article_markup(source),
        re.I | re.S,
    )
    section_headings = [clean_markup(match_one(block, r"<h2\b[^>]*>(.*?)</h2>") or "") for _, block in sections]
    if not 5 <= len(section_headings) <= 7 or any(not heading for heading in section_headings):
        audit.fail("article_section_count", page, len(section_headings))
    if article:
        has_parts = article.get("hasPart", [])
        part_pairs = [
            (normalize_space(item.get("name", "")), str(item.get("url", "")))
            for item in has_parts if isinstance(item, dict)
        ] if isinstance(has_parts, list) else []
        expected_parts = [(heading, expected_url + f"#section-{number}") for number, heading in enumerate(section_headings, 1)]
        if part_pairs != expected_parts:
            audit.fail("article_haspart_mismatch", page, f"expected={len(expected_parts)} actual={len(part_pairs)}")

    item_list = one_node(graph, "ItemList", page, audit)
    item_urls = []
    if item_list:
        items = item_list.get("itemListElement", [])
        if isinstance(items, list):
            item_urls = [str(item.get("url", "")) for item in items if isinstance(item, dict)]
    sibling_urls = [encoded_url("과목별학원", other, local) for other in CATEGORIES if other != slug]
    previous_local = order[index - 1] if index else order[-1]
    next_local = order[index + 1] if index + 1 < len(order) else order[0]
    expected_related = [
        *sibling_urls,
        encoded_url("전국센터", local),
        encoded_url("과목별학원", slug),
        encoded_url("과목별학원"),
        encoded_url("학습관리"),
        encoded_url("과목별학원", slug, previous_local),
        encoded_url("과목별학원", slug, next_local),
    ]
    if item_urls != expected_related:
        audit.fail("related_itemlist_mismatch", page, f"expected={expected_related} actual={item_urls}")

    representative = audit_media(page, source, expected_title, local, row, map_cache, audit)
    if image:
        wanted = SITE_URL + representative if representative else ""
        if image.get("contentUrl") != wanted or image.get("url") != wanted:
            audit.fail("schema_primary_image", page, f"expected={wanted} actual={image.get('contentUrl')}")

    verified = match_one(source, r"<section\b[^>]*\bid=[\"']verified-center[\"'][^>]*>(.*?)</section>") or ""
    verified_text = clean_markup(verified)
    for fact_name, fact in (
        ("center_name", row.get("센터명", "")),
        ("center_address", row.get("센터 주소", "")),
        ("center_identifier", row.get("교육지원청 등록번호", "")),
    ):
        if fact and fact not in verified_text:
            audit.fail("visible_verified_fact", page, f"{fact_name}={fact}")
    school_block = match_one(verified, r"<div\b[^>]*\bclass=[\"'][^\"']*verified-school-list[^\"']*[\"'][^>]*>(.*?)</div>") or ""
    visible_schools = unique(
        school
        for span in re.findall(r"<span\b[^>]*>(.*?)</span>", school_block, re.I | re.S)
        for school in split_schools(clean_markup(span))
    )
    if set(visible_schools) != expected_school_set:
        audit.fail("visible_verified_schools", page, f"expected={sorted(expected_school_set)} actual={sorted(visible_schools)}")
    if expected_grade_list:
        if not all(grade in verified_text for grade in expected_grade_list):
            audit.fail("visible_verified_grades", page, expected_grade_list)
    elif "상담 확인" not in verified_text:
        audit.fail("empty_grades_not_disclosed", page, "상담 확인 문구 없음")

    main = match_one(source, r"<main\b[^>]*>(.*?)</main>") or ""
    visible_main = clean_markup(main)
    check_blocked_text(page, visible_main, audit)
    if slug == "전문학원":
        generic_source_residue = re.search(
            r"자료에\s*함께\s*제시된|추가\s*확인\s*항목|같은\s*운영\s*정보는|"
            r"관련\s*안내를\s*확인|같은\s*항목을\s*체크리스트",
            visible_main,
        )
        if generic_source_residue:
            audit.fail("authoring_reference_term", page, generic_source_residue.group(0))
    unsupported_grades = extract_explicit_grades(visible_main) - set(expected_grade_list)
    if unsupported_grades:
        audit.fail("unsupported_visible_grade", page, sorted(unsupported_grades))

    # Only names occurring in the verified national source are treated as
    # school entities.  Three-or-more-syllable matching avoids Korean verb
    # endings such as "남고" being misread as school names.
    actual_school_mentions = known_school_mentions(visible_main)
    if not actual_school_mentions.issubset(expected_school_alias_set):
        audit.fail(
            "unsupported_visible_school",
            page,
            sorted(actual_school_mentions - expected_school_alias_set),
        )

    audit_internal_links(page, source, audit)
    article_text = clean_markup(article_markup(source))
    if len(article_text) < 900:
        audit.fail("article_too_short", page, len(article_text))
    return {
        "title": title,
        "meta": description,
        "canonical": canonical,
        "representative": representative,
        "article": article_text,
    }


ALL_SCHOOL_NAMES: set[str] = set()
ALL_LOCAL_NAMES: set[str] = set()


def audit_nav(audit: Audit) -> dict[str, int]:
    checked = 0
    missing = 0
    wanted = (SUBJECT_ROOT / "index.html").resolve()
    for page in sorted(ROOT.rglob("index.html")):
        if any(part in {".git", ".vercel", "node_modules"} for part in page.parts):
            continue
        source = page.read_text(encoding="utf-8")
        block = match_one(source, r"<div\b[^>]*\bclass=[\"'][^\"']*nav-links[^\"']*[\"'][^>]*>(.*?)</div>")
        if block is None:
            audit.fail("missing_nav_links", page, "nav-links")
            missing += 1
            continue
        anchors = re.findall(r"<a\b[^>]*\bhref=([\"'])(.*?)\1[^>]*>(.*?)</a>", block, re.I | re.S)
        matches = [(href, clean_markup(label)) for _, href, label in anchors if clean_markup(label) == "과목별학원"]
        if len(matches) != 1:
            audit.fail("subject_nav_count", page, len(matches))
            missing += 1
        else:
            target = href_target(page, matches[0][0], audit)
            if target is None or target.resolve() != wanted:
                audit.fail("subject_nav_target", page, matches[0][0])
                missing += 1
        checked += 1
    return {"checked": checked, "failed": missing}


def audit_sitemap(expected_urls: set[str], audit: Audit) -> dict[str, int]:
    path = ROOT / "sitemap.xml"
    if not path.is_file():
        audit.fail("missing_sitemap", path, "")
        return {"urls": 0, "unique": 0, "expected_missing": len(expected_urls)}
    try:
        tree = ET.parse(path)
    except Exception as exc:  # noqa: BLE001
        audit.fail("invalid_sitemap", path, exc)
        return {"urls": 0, "unique": 0, "expected_missing": len(expected_urls)}
    namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    values = [normalize_space(node.text) for node in tree.findall(f"{namespace}url/{namespace}loc") if node.text]
    duplicates = len(values) - len(set(values))
    if duplicates:
        audit.fail("duplicate_sitemap_url", path, duplicates)
    missing = expected_urls - set(values)
    for url in sorted(missing)[:5]:
        audit.fail("subject_url_missing_from_sitemap", path, url)
    return {"urls": len(values), "unique": len(set(values)), "expected_missing": len(missing)}


def audit_rss(audit: Audit) -> dict[str, int]:
    path = ROOT / "rss.xml"
    if not path.is_file():
        audit.fail("missing_rss", path, "")
        return {"items": 0, "unique": 0, "subject_hubs": 0, "subject_details": 0}
    try:
        channel = ET.parse(path).getroot().find("channel")
    except Exception as exc:  # noqa: BLE001
        audit.fail("invalid_rss", path, exc)
        return {"items": 0, "unique": 0, "subject_hubs": 0, "subject_details": 0}
    if channel is None:
        audit.fail("missing_rss_channel", path, "")
        return {"items": 0, "unique": 0, "subject_hubs": 0, "subject_details": 0}

    links: list[str] = []
    for item in channel.findall("item"):
        link = normalize_space(item.findtext("link"))
        guid = normalize_space(item.findtext("guid"))
        if not link or guid != link:
            audit.fail("rss_link_guid", path, f"link={link!r} guid={guid!r}")
        if link:
            links.append(link)
    if len(links) != len(set(links)):
        audit.fail("duplicate_rss_link", path, len(links) - len(set(links)))

    expected_subject = {
        encoded_url("과목별학원"),
        *[encoded_url("과목별학원", slug) for slug in CATEGORIES],
    }
    for url in expected_subject:
        if links.count(url) != 1:
            audit.fail("rss_subject_hub", path, f"{url} count={links.count(url)}")
    subject_prefix = encoded_url("과목별학원")
    subject_links = {url for url in links if url.startswith(subject_prefix)}
    detail_links = subject_links - expected_subject
    for url in sorted(detail_links)[:5]:
        audit.fail("rss_subject_detail", path, url)
    expected_count = 10 + len(CATEGORIES)
    if len(links) != expected_count:
        audit.fail("rss_item_count", path, f"expected={expected_count} actual={len(links)}")
    return {
        "items": len(links),
        "unique": len(set(links)),
        "subject_hubs": len(subject_links & expected_subject),
        "subject_details": len(detail_links),
    }


def audit_discovery(audit: Audit) -> None:
    home = ROOT / "index.html"
    if home.is_file():
        source = home.read_text(encoding="utf-8")
        target = (SUBJECT_ROOT / "index.html").resolve()
        found = False
        for _, href in re.findall(r"<a\b[^>]*\bhref=([\"'])(.*?)\1", source, re.I | re.S):
            resolved = href_target(home, href, audit)
            if resolved is not None and resolved.resolve() == target:
                found = True
                break
        if not found:
            audit.fail("homepage_subject_discovery", home, "과목별학원 링크 없음")
    llms = ROOT / "llms.txt"
    if not llms.is_file():
        audit.fail("missing_llms", llms, "")
    else:
        value = llms.read_text(encoding="utf-8")
        for url in [encoded_url("과목별학원"), *[encoded_url("과목별학원", slug) for slug in CATEGORIES]]:
            if url not in value:
                audit.fail("llms_subject_url_missing", llms, url)


def category_similarity(
    slug: str,
    records: list[tuple[str, str, str]],
    audit: Audit,
) -> dict[str, Any]:
    raw_hashes: dict[str, str] = {}
    masked_hashes: dict[str, str] = {}
    shingles: list[tuple[str, set[tuple[str, ...]]]] = []
    for local, raw, masked in records:
        raw_digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        masked_digest = hashlib.sha256(masked.encode("utf-8")).hexdigest()
        if raw_digest in raw_hashes:
            audit.fail("exact_article_duplicate", SUBJECT_ROOT / slug / local / "index.html", raw_hashes[raw_digest])
        else:
            raw_hashes[raw_digest] = local
        if masked_digest in masked_hashes:
            audit.fail("masked_exact_article_duplicate", SUBJECT_ROOT / slug / local / "index.html", masked_hashes[masked_digest])
        else:
            masked_hashes[masked_digest] = local
        shingles.append((local, five_word_shingles(masked)))

    maximum = 0.0
    pair = ("", "")
    for left_index in range(len(shingles)):
        left_name, left = shingles[left_index]
        for right_name, right in shingles[left_index + 1:]:
            score = jaccard(left, right)
            if score > maximum:
                maximum = score
                pair = (left_name, right_name)
    if maximum >= 0.75:
        audit.fail(
            "masked_five_shingle_similarity",
            SUBJECT_ROOT / slug,
            f"max={maximum:.4f} pair={pair[0]}/{pair[1]} threshold<0.75",
        )
    return {
        "raw_unique": len(raw_hashes),
        "masked_unique": len(masked_hashes),
        "masked_five_shingle_max": round(maximum, 4),
        "worst_pair": list(pair),
    }


def main() -> int:
    audit = Audit()
    order, rows, displays = load_centres(audit)
    global ALL_LOCAL_NAMES, ALL_SCHOOL_NAMES
    ALL_SCHOOL_NAMES = school_aliases({
        school
        for row in rows.values()
        for school in expected_schools(row)
    })
    ALL_LOCAL_NAMES = set(order) | set(displays.values())

    expected_urls: set[str] = {encoded_url("과목별학원")}
    metadata_titles: list[str] = []
    metadata_descriptions: list[str] = []
    metadata_canonicals: list[str] = []
    per_category: dict[str, dict[str, Any]] = {}
    map_cache: dict[str, str] = {}

    root_items = [
        (str(config["label"]), encoded_url("과목별학원", slug))
        for slug, config in CATEGORIES.items()
    ]
    root_result = audit_hub(
        SUBJECT_ROOT / "index.html",
        encoded_url("과목별학원"),
        f"과목별학원 | {DOMAIN_NAME}",
        "과목별학원",
        ["홈", "과목별학원"],
        root_items,
        audit,
    )
    metadata_titles.append(root_result["title"])
    metadata_descriptions.append(root_result["description"])
    metadata_canonicals.append(root_result["canonical"])

    for slug, category in CATEGORIES.items():
        hub_url = encoded_url("과목별학원", slug)
        expected_urls.add(hub_url)
        hub_items = [(f"{local} {category['label']}", encoded_url("과목별학원", slug, local)) for local in order]
        hub_result = audit_hub(
            SUBJECT_ROOT / slug / "index.html",
            hub_url,
            f"{category['label']} 지역 안내 | {DOMAIN_NAME}",
            f"동네별 {category['label']} 안내",
            ["홈", "과목별학원", f"{category['label']} 지역 안내"],
            hub_items,
            audit,
        )
        metadata_titles.append(hub_result["title"])
        metadata_descriptions.append(hub_result["description"])
        metadata_canonicals.append(hub_result["canonical"])

        category_root = SUBJECT_ROOT / slug
        actual_details = {
            path.parent.name
            for path in category_root.glob("*/index.html")
            if path.parent != category_root
        } if category_root.is_dir() else set()
        if actual_details != set(order):
            audit.fail(
                "category_detail_set",
                category_root,
                f"missing={sorted(set(order)-actual_details)[:5]} extra={sorted(actual_details-set(order))[:5]}",
            )

        records: list[tuple[str, str, str]] = []
        representatives: list[str] = []
        for index, local in enumerate(order):
            expected_urls.add(encoded_url("과목별학원", slug, local))
            page = category_root / local / "index.html"
            result = audit_detail(
                page,
                slug,
                category,
                local,
                displays.get(local, local),
                rows[local],
                order,
                index,
                map_cache,
                audit,
            )
            metadata_titles.append(result["title"])
            metadata_descriptions.append(result["meta"])
            metadata_canonicals.append(result["canonical"])
            if result["representative"]:
                representatives.append(result["representative"])
            if result["article"]:
                masked = mask_facts(result["article"], local, displays.get(local, local), rows[local], category)
                records.append((local, result["article"], masked))

        if len(representatives) != 371 or len(set(representatives)) != 371:
            audit.fail(
                "category_representative_uniqueness",
                category_root,
                f"count={len(representatives)} unique={len(set(representatives))}",
            )
        similarity = category_similarity(slug, records, audit) if len(records) == 371 else {
            "raw_unique": len({raw for _, raw, _ in records}),
            "masked_unique": len({masked for _, _, masked in records}),
            "masked_five_shingle_max": None,
            "worst_pair": [],
        }
        per_category[slug] = {
            "expected_details": 371,
            "audited_details": len(records),
            "representative_unique": len(set(representatives)),
            **similarity,
        }

    expected_page_count = 1 + len(CATEGORIES) + 371 * len(CATEGORIES)
    subject_pages = list(SUBJECT_ROOT.rglob("index.html")) if SUBJECT_ROOT.is_dir() else []
    if len(subject_pages) != expected_page_count:
        audit.fail("subject_page_count", SUBJECT_ROOT, f"expected={expected_page_count} actual={len(subject_pages)}")

    for name, values in (
        ("title", metadata_titles),
        ("description", metadata_descriptions),
        ("canonical", metadata_canonicals),
    ):
        nonempty = [value for value in values if value]
        if len(nonempty) != len(set(nonempty)):
            duplicates = [value for value, count in Counter(nonempty).items() if count > 1]
            audit.fail(f"duplicate_{name}", SUBJECT_ROOT, duplicates[:5])

    sitemap = audit_sitemap(expected_urls, audit)
    rss = audit_rss(audit)
    nav = audit_nav(audit)
    audit_discovery(audit)

    report = {
        "status": "PASS" if not audit.counts else "FAIL",
        "expected": {
            "subject_root_hubs": 1,
            "category_hubs": len(CATEGORIES),
            "detail_pages": 371 * len(CATEGORIES),
            "total_subject_pages": expected_page_count,
            "masked_five_shingle_threshold": "<0.75",
        },
        "actual": {
            "subject_pages": len(subject_pages),
            "unique_titles": len(set(filter(None, metadata_titles))),
            "unique_descriptions": len(set(filter(None, metadata_descriptions))),
            "unique_canonicals": len(set(filter(None, metadata_canonicals))),
            "sitemap": sitemap,
            "rss": rss,
            "navigation": nav,
        },
        "categories": per_category,
        "issue_counts": dict(sorted(audit.counts.items())),
        "issue_examples": dict(sorted(audit.examples.items())),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if audit.counts else 0


if __name__ == "__main__":
    sys.exit(main())
