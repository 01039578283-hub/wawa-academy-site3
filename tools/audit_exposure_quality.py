"""Full local audit for crawlability, content quality and entity consistency."""

from __future__ import annotations

import hashlib
import html
import json
import re
import statistics
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote, urlsplit


DOMAIN = "xn--sp5b72l1taf0p.com"
BASE = f"https://{DOMAIN}"
LOCAL_ROOT = "전국센터"


def clean(value: str) -> str:
    value = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", value, flags=re.I | re.S)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value)).split())


def match_one(text: str, pattern: str) -> str | None:
    found = re.search(pattern, text, re.I | re.S)
    return html.unescape(found.group(1)).strip() if found else None


def jsonld(text: str) -> dict:
    raw = match_one(text, r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>')
    if raw is None:
        raise ValueError("missing JSON-LD")
    return json.loads(raw)


def types(node: dict) -> set[str]:
    value = node.get("@type")
    return set(value if isinstance(value, list) else [value])


def find_node(graph: list[dict], kind: str) -> dict | None:
    return next((node for node in graph if isinstance(node, dict) and kind in types(node)), None)


def visible_faq(text: str) -> list[tuple[str, str]]:
    block = match_one(
        text,
        r'<section\b[^>]*id=["\'](?:faq-section|hub-faq-section|faq)["\']'
        r"[^>]*>(.*?)</section>",
    )
    if block is None:
        return []
    result = []
    for details in re.findall(r"<details\b[^>]*>(.*?)</details>", block, re.I | re.S):
        q = match_one(details, r"<summary\b[^>]*>(.*?)</summary>")
        a = match_one(details, r"<p\b[^>]*>(.*?)</p>")
        if q is not None and a is not None:
            result.append((clean(q), clean(a)))
    if result:
        return result
    for article in re.findall(r'<article\b[^>]*class=["\'][^"\']*faq-item[^"\']*["\'][^>]*>(.*?)</article>', block, re.I | re.S):
        q = match_one(article, r"<h[2-4]\b[^>]*>(.*?)</h[2-4]>")
        a = match_one(article, r"<p\b[^>]*>(.*?)</p>")
        if q is not None and a is not None:
            result.append((clean(q), clean(a)))
    return result


def schema_faq(graph: list[dict]) -> list[tuple[str, str]]:
    node = find_node(graph, "FAQPage")
    if not node:
        return []
    result = []
    for item in node.get("mainEntity", []):
        answer = item.get("acceptedAnswer", {}) if isinstance(item, dict) else {}
        result.append((str(item.get("name", "")).strip(), str(answer.get("text", "")).strip()))
    return result


def href_target(root: Path, page: Path, href: str) -> Path | None:
    if not href or href.startswith(("#", "tel:", "mailto:", "javascript:", "data:")):
        return None
    parts = urlsplit(html.unescape(href))
    if parts.scheme in ("http", "https"):
        if parts.hostname not in (DOMAIN, "코칭학원.com"):
            return None
        relative = unquote(parts.path).lstrip("/")
        target = root / relative
    else:
        target = (page.parent / unquote(parts.path)).resolve()
    if str(href).endswith("/") or target.is_dir():
        target = target / "index.html"
    return target


def ngrams(value: str, n: int = 5) -> set[str]:
    compact = re.sub(r"\s+", "", value)
    return {compact[index:index + n] for index in range(max(0, len(compact) - n + 1))}


def jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right) if left or right else 1.0


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    pages = sorted(root.rglob("index.html"))
    # A neighbourhood directory always owns curriculum children.  Deriving the
    # set structurally keeps newly-added region/category collection hubs out of
    # locality metrics without relying on a hard-coded Korean slug list.
    local_parent_dirs = sorted(
        path.parent
        for path in (root / LOCAL_ROOT).glob("*/index.html")
        if any(path.parent.glob("*/index.html"))
    )
    local_pages = [path / "index.html" for path in local_parent_dirs]
    local_pages.extend(
        child
        for parent in local_parent_dirs
        for child in sorted(parent.glob("*/index.html"))
    )
    local_page_set = set(local_pages)

    missing = Counter()
    canonical_values: list[str] = []
    descriptions: list[str] = []
    org_ids: set[str] = set()
    provider_ids: set[str] = set()
    review_nodes = 0
    rating_nodes = 0
    faq_mismatch = 0
    breadcrumb_mismatch = 0
    type_counts = Counter()
    broken_links: set[tuple[str, str]] = set()
    local_mentions: list[int] = []
    visible_hashes: set[str] = set()
    paragraph_counts: Counter[str] = Counter()
    grammar_counts = Counter()
    grouped_text: dict[str, list[str]] = defaultdict(list)

    bad_tokens = [
        "수학는", "수학를", "관리을", "학습관리은", "풀이을",
        "현재 수준과 목표에 맞춰 다시 확인합니다", "동일하게 적용합니다",
        "SEO GEO", "KEY SUMMARY", "ANSWER READY", "Local Search Guide", "점는",
        "친구와 함께 등록하면 할인", "PARENT REVIEW",
    ]

    for page in pages:
        text = page.read_text(encoding="utf-8")
        title = match_one(text, r"<title>(.*?)</title>")
        description = match_one(text, r'<meta\b(?=[^>]*name=["\']description["\'])[^>]*content=["\']([^"\']*)["\']')
        canonical = match_one(text, r'<link\b(?=[^>]*rel=["\']canonical["\'])[^>]*href=["\']([^"\']+)["\']')
        og_url = match_one(text, r'<meta\b(?=[^>]*property=["\']og:url["\'])[^>]*content=["\']([^"\']+)["\']')
        h1_count = len(re.findall(r"<h1\b", text, re.I))
        if not title: missing["title"] += 1
        if not description: missing["description"] += 1
        if not canonical: missing["canonical"] += 1
        if not og_url: missing["og:url"] += 1
        if h1_count != 1: missing["h1_not_one"] += 1
        if canonical:
            canonical_values.append(canonical)
            if not canonical.startswith(BASE): missing["canonical_non_punycode"] += 1
        if canonical != og_url: missing["canonical_og_mismatch"] += 1
        if description is not None: descriptions.append(description)

        try:
            data = jsonld(text)
            graph = data.get("@graph", [])
            if not isinstance(graph, list): raise ValueError("graph")
            for node in graph:
                if not isinstance(node, dict): continue
                for kind in types(node): type_counts[kind] += 1
                if "Review" in types(node): review_nodes += 1
                if "AggregateRating" in types(node): rating_nodes += 1
                if any(key in node for key in ("review", "aggregateRating")):
                    review_nodes += len(node.get("review", [])) if isinstance(node.get("review"), list) else int("review" in node)
                    rating_nodes += int("aggregateRating" in node)
            org = find_node(graph, "EducationalOrganization")
            if org and page in local_page_set:
                org_ids.add(str(org.get("@id", "")))
            service = find_node(graph, "Service")
            if service and page in local_page_set:
                provider = service.get("provider", {})
                if isinstance(provider, dict): provider_ids.add(str(provider.get("@id", "")))
            if page in local_page_set:
                for expected_type in ("EducationalOrganization", "LocalBusiness", "WebPage", "Service", "FAQPage", "BreadcrumbList", "ItemList", "Article"):
                    if not find_node(graph, expected_type):
                        missing[f"local_missing_{expected_type}"] += 1
            if visible_faq(text) != schema_faq(graph): faq_mismatch += 1
            breadcrumb = find_node(graph, "BreadcrumbList")
            if breadcrumb and canonical:
                items = breadcrumb.get("itemListElement", [])
                last = items[-1].get("item") if items and isinstance(items[-1], dict) else None
                if last != canonical: breadcrumb_mismatch += 1
            webpage = find_node(graph, "WebPage") or find_node(graph, "CollectionPage") or find_node(graph, "ContactPage")
            if webpage and canonical and webpage.get("url") != canonical: missing["webpage_url_mismatch"] += 1
        except Exception:
            missing["jsonld_error"] += 1

        for href in re.findall(r'<a\b[^>]*href=["\']([^"\']+)["\']', text, re.I):
            target = href_target(root, page, href)
            if target is not None and not target.exists():
                broken_links.add((page.relative_to(root).as_posix(), href))

        for token in bad_tokens:
            grammar_counts[token] += text.count(token)

        if page in local_page_set:
            main_block = match_one(text, r"<main\b[^>]*>(.*?)</main>") or ""
            visible = clean(main_block)
            visible_hashes.add(hashlib.sha256(visible.encode("utf-8")).hexdigest())
            parts = page.relative_to(root).parts
            locality = parts[1]
            local_mentions.append(visible.count(locality))
            category = parts[2] if len(parts) == 4 else "동네부모"
            grouped_text[category].append(visible)
            for block in re.findall(r"<(?:p|li)\b[^>]*>(.*?)</(?:p|li)>", main_block, re.I | re.S):
                paragraph = clean(block)
                if len(paragraph) >= 35:
                    paragraph_counts[paragraph] += 1

    similarities = []
    for values in grouped_text.values():
        grams = [ngrams(value) for value in values]
        similarities.extend(jaccard(grams[index - 1], grams[index]) for index in range(1, len(grams)))

    sitemap = ET.parse(root / "sitemap.xml")
    sitemap_urls = [node.text.strip() for node in sitemap.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc") if node.text]
    rss_items = 0
    if (root / "rss.xml").is_file():
        rss_items = len(ET.parse(root / "rss.xml").findall("./channel/item"))

    p95 = statistics.quantiles(similarities, n=20)[18] if len(similarities) >= 20 else 0.0
    repeated = [(text, count) for text, count in paragraph_counts.most_common(15) if count > 1]
    print(json.dumps({
        "pages": len(pages),
        "local_pages": len(local_pages),
        "missing_or_mismatch": dict(missing),
        "unique_canonical": len(set(canonical_values)),
        "unique_descriptions": len(set(descriptions)),
        "description_length": {
            "min": min(map(len, descriptions)), "median": statistics.median(map(len, descriptions)), "max": max(map(len, descriptions)),
        },
        "jsonld_types": dict(type_counts),
        "local_organization_ids": len(org_ids),
        "local_service_provider_ids": len(provider_ids),
        "review_nodes": review_nodes,
        "rating_nodes": rating_nodes,
        "faq_mismatch": faq_mismatch,
        "breadcrumb_mismatch": breadcrumb_mismatch,
        "broken_internal_links": len(broken_links),
        "sitemap_urls": len(sitemap_urls),
        "sitemap_unique": len(set(sitemap_urls)),
        "sitemap_matches_canonical": set(sitemap_urls) == set(canonical_values),
        "rss_items": rss_items,
        "local_visible_unique": len(visible_hashes),
        "locality_mentions": {
            "min": min(local_mentions), "median": statistics.median(local_mentions), "max": max(local_mentions),
        },
        "adjacent_category_similarity": {
            "mean": round(statistics.mean(similarities), 4), "median": round(statistics.median(similarities), 4), "p95": round(p95, 4),
        },
        "bad_token_occurrences": {key: value for key, value in grammar_counts.items() if value},
        "top_repeated_paragraphs": [{"count": count, "text": text[:160]} for text, count in repeated],
        "broken_link_examples": list(sorted(broken_links))[:10],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
