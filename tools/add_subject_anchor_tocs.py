#!/usr/bin/env python3
"""Add page-specific anchor navigation to subject detail pages.

Only ``과목별학원/<category>/<locality>/index.html`` is targeted.  Each TOC
reuses the existing ``section-1`` through ``section-N`` anchors that are also
referenced by the page's Article JSON-LD, so manuscripts and structured data
remain untouched.  Run this script after a full page regeneration.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
SUBJECT_ROOT = ROOT / "과목별학원"
TOC_START = "<!-- subject-page-anchor-toc:start -->"
TOC_END = "<!-- subject-page-anchor-toc:end -->"

TOC_BLOCK_RE = re.compile(
    rf"{re.escape(TOC_START)}.*?{re.escape(TOC_END)}",
    re.IGNORECASE | re.DOTALL,
)
TOC_REMOVE_RE = re.compile(
    rf"{re.escape(TOC_START)}.*?{re.escape(TOC_END)}\n[ \t]*",
    re.IGNORECASE | re.DOTALL,
)
SECTION_OPEN_RE = re.compile(r"<section(?P<attrs>[^>]*)>", re.IGNORECASE)
SECTION_TAG_RE = re.compile(r"</?section\b[^>]*>", re.IGNORECASE)
ARTICLE_OPEN_RE = re.compile(r"\s*<article(?P<attrs>[^>]*)>", re.IGNORECASE)
H2_RE = re.compile(r"<h2\b[^>]*>(?P<body>.*?)</h2>", re.IGNORECASE | re.DOTALL)
CLASS_RE = re.compile(
    r"\bclass\s*=\s*([\"'])(?P<class_names>[^\"']+)\1", re.IGNORECASE
)
ID_RE = re.compile(r"\bid\s*=\s*([\"'])(?P<id>[^\"']+)\1", re.IGNORECASE)
ANY_ID_RE = re.compile(r"\bid\s*=\s*([\"'])(?P<id>[^\"']+)\1", re.IGNORECASE)
JSON_LD_RE = re.compile(
    r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
TOC_LINK_RE = re.compile(
    r'<a href="#(?P<id>[^"]+)">.*?'
    r'<span class="subject-page-toc-text">(?P<label>.*?)</span>\s*</a>',
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True)
class TocTarget:
    target_id: str
    text: str
    start: int
    closing_end: int


def visible_text(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", fragment)
    return " ".join(html.unescape(text).split())


def class_names(attrs: str) -> set[str]:
    match = CLASS_RE.search(attrs)
    return set(match.group("class_names").split()) if match else set()


def element_id(attrs: str) -> str | None:
    match = ID_RE.search(attrs)
    return match.group("id") if match else None


def detail_pages() -> list[Path]:
    if not SUBJECT_ROOT.exists():
        return []
    return sorted(
        SUBJECT_ROOT.glob("*/*/index.html"), key=lambda path: path.as_posix()
    )


def section_end(source: str, opening: re.Match[str]) -> int | None:
    depth = 0
    for match in SECTION_TAG_RE.finditer(source, opening.start()):
        if match.group(0).lower().startswith("</section"):
            depth -= 1
            if depth == 0:
                return match.end()
        else:
            depth += 1
    return None


def select_targets(source: str) -> list[TocTarget]:
    targets: list[TocTarget] = []
    for opening in SECTION_OPEN_RE.finditer(source):
        attrs = opening.group("attrs")
        if "subject-prose-section" not in class_names(attrs):
            continue
        target_id = element_id(attrs)
        if not target_id or not re.fullmatch(r"section-\d+", target_id):
            continue
        closing_end = section_end(source, opening)
        if closing_end is None:
            continue
        heading = H2_RE.search(source, opening.end(), closing_end)
        if not heading:
            continue
        text = visible_text(heading.group("body"))
        if not text:
            continue
        targets.append(
            TocTarget(
                target_id=target_id,
                text=text,
                start=opening.start(),
                closing_end=closing_end,
            )
        )
    return targets


def subject_article_start(source: str) -> int | None:
    for opening in SECTION_OPEN_RE.finditer(source):
        if "local-section" not in class_names(opening.group("attrs")):
            continue
        article = ARTICLE_OPEN_RE.match(source, opening.end())
        if article and "subject-article" in class_names(article.group("attrs")):
            return opening.start()
    return None


def verified_center_end(source: str) -> int | None:
    for opening in SECTION_OPEN_RE.finditer(source):
        if element_id(opening.group("attrs")) == "verified-center":
            return section_end(source, opening)
    return None


def article_parts(source: str) -> list[tuple[str, str]]:
    articles: list[dict] = []
    for script in JSON_LD_RE.findall(source):
        data = json.loads(script)
        graph = data.get("@graph", []) if isinstance(data, dict) else []
        for node in graph:
            if not isinstance(node, dict):
                continue
            kinds = node.get("@type", [])
            kinds = [kinds] if isinstance(kinds, str) else kinds
            if "Article" in kinds:
                articles.append(node)
    if len(articles) != 1:
        raise ValueError(f"Article JSON-LD count is {len(articles)}")

    result: list[tuple[str, str]] = []
    for part in articles[0].get("hasPart", []):
        if not isinstance(part, dict):
            continue
        fragment = urlsplit(str(part.get("url", ""))).fragment
        name = " ".join(str(part.get("name", "")).split())
        result.append((fragment, name))
    return result


def toc_markup(targets: list[TocTarget]) -> str:
    items = []
    for index, target in enumerate(targets, start=1):
        items.append(
            "        <li>"
            f'<a href="#{html.escape(target.target_id, quote=True)}">'
            f'<span class="subject-page-toc-number" aria-hidden="true">{index:02d}</span>'
            f'<span class="subject-page-toc-text">{html.escape(target.text)}</span>'
            "</a></li>"
        )
    return (
        TOC_START
        + "\n"
        + '    <nav class="local-section subject-page-toc" aria-labelledby="subject-page-toc-title">\n'
        + '      <div class="wrap subject-page-toc-shell">\n'
        + '        <div class="subject-page-toc-heading">\n'
        + '          <p class="eyebrow">PAGE CONTENTS</p>\n'
        + '          <strong id="subject-page-toc-title">상담 안내 목차</strong>\n'
        + "        </div>\n"
        + '        <ol class="subject-page-toc-list">\n'
        + "\n".join(items)
        + "\n        </ol>\n"
        + "      </div>\n"
        + "    </nav>\n"
        + "    "
        + TOC_END
        + "\n    "
    )


def render_page(original: str) -> tuple[str, int]:
    source = TOC_REMOVE_RE.sub("", original, count=1)
    targets = select_targets(source)
    if not 5 <= len(targets) <= 7:
        raise ValueError(f"Expected 5-7 content anchors, found {len(targets)}")
    expected_ids = [f"section-{index}" for index in range(1, len(targets) + 1)]
    actual_ids = [target.target_id for target in targets]
    if actual_ids != expected_ids:
        raise ValueError(f"Non-contiguous content anchors: {actual_ids}")
    structured_parts = article_parts(source)
    visible_parts = [(target.target_id, target.text) for target in targets]
    if structured_parts != visible_parts:
        raise ValueError("Visible headings and Article.hasPart do not match")

    insertion_point = subject_article_start(source)
    if insertion_point is None:
        raise ValueError("Subject article container not found")
    return source[:insertion_point] + toc_markup(targets) + source[insertion_point:], len(targets)


def validate_page(source: str) -> list[str]:
    errors: list[str] = []
    if source.count(TOC_START) != 1 or source.count(TOC_END) != 1:
        errors.append("TOC marker count is not exactly one")
    toc = TOC_BLOCK_RE.search(source)
    if not toc:
        errors.append("TOC block missing")
        return errors

    targets = select_targets(source)
    links = [
        (match.group("id"), visible_text(match.group("label")))
        for match in TOC_LINK_RE.finditer(toc.group(0))
    ]
    expected = [(target.target_id, target.text) for target in targets]
    if links != expected:
        errors.append("TOC links or labels do not match visible content headings")
    try:
        if article_parts(source) != expected:
            errors.append("TOC targets do not match Article.hasPart")
    except Exception as exc:
        errors.append(str(exc))

    all_ids = [match.group("id") for match in ANY_ID_RE.finditer(source)]
    if len(all_ids) != len(set(all_ids)):
        errors.append("Duplicate id found")
    for target_id, _ in links:
        if all_ids.count(target_id) != 1:
            errors.append(
                f"Anchor target count for {target_id!r} is {all_ids.count(target_id)}"
            )

    verified_end = verified_center_end(source)
    article_start = subject_article_start(source)
    if verified_end is None or toc.start() < verified_end:
        errors.append("TOC appears before the verified-center section ends")
    if article_start is None or toc.end() > article_start:
        errors.append("TOC is not immediately before the subject article")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="Write generated TOCs")
    parser.add_argument(
        "--check", action="store_true", help="Fail when a page is not up to date"
    )
    args = parser.parse_args()

    pages = detail_pages()
    changed = 0
    counts: Counter[int] = Counter()
    category_counts: Counter[str] = Counter()
    failures: list[str] = []

    for path in pages:
        original = path.read_bytes().decode("utf-8")
        relative = path.relative_to(ROOT)
        newline = "\r\n" if "\r\n" in original else "\n"
        normalized = original.replace("\r\n", "\n").replace("\r", "\n")
        try:
            rendered_normalized, link_count = render_page(normalized)
        except Exception as exc:
            failures.append(f"{relative}: {exc}")
            continue
        validation_errors = validate_page(rendered_normalized)
        if validation_errors:
            failures.append(f"{relative}: " + "; ".join(validation_errors))
            continue
        rendered = (
            rendered_normalized
            if newline == "\n"
            else rendered_normalized.replace("\n", "\r\n")
        )

        counts[link_count] += 1
        category_counts[relative.parts[1]] += 1
        if rendered != original:
            changed += 1
            if args.write:
                path.write_bytes(rendered.encode("utf-8"))

    print(f"pages={len(pages)} validated={sum(counts.values())}")
    print(
        "toc_link_distribution="
        + ",".join(f"{count}:{pages_count}" for count, pages_count in sorted(counts.items()))
    )
    print(f"toc_links_total={sum(count * pages_count for count, pages_count in counts.items())}")
    print(
        "categories="
        + ",".join(
            f"{category}:{page_count}"
            for category, page_count in sorted(category_counts.items())
        )
    )
    print(f"changed={changed} mode={'write' if args.write else 'dry-run'}")

    if failures:
        print(f"failures={len(failures)}", file=sys.stderr)
        for failure in failures[:50]:
            print(failure, file=sys.stderr)
        return 1
    if args.check and changed:
        print("Target pages are not up to date. Run with --write.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
