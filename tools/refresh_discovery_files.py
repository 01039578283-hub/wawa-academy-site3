"""Regenerate sitemap.xml and a concise RSS feed from canonical page data."""

from __future__ import annotations

import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path


TODAY = "2026-08-11"
KST = timezone(timedelta(hours=9))
RSS_HUB_SLUGS = (
    "초등영어학원",
    "초등수학학원",
    "중등영어학원",
    "중등수학학원",
    "고등영어학원",
    "고등수학학원",
)
RSS_SUBJECT_HUB_SLUGS = (
    "영수전문학원",
    "영어전문학원",
    "수학전문학원",
)


def read_tag(text: str, pattern: str) -> str:
    match = re.search(pattern, text, re.I | re.S)
    if not match:
        raise ValueError(f"Required tag not found: {pattern}")
    return html.unescape(match.group(1)).strip()


def structured_modified(text: str) -> str | None:
    """Return the newest valid dateModified exposed by page JSON-LD."""
    dates: list[str] = []
    for raw in re.findall(
        r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        text,
        re.I | re.S,
    ):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        stack: list[object] = [data]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                value = node.get("dateModified")
                if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                    dates.append(value)
                stack.extend(node.values())
            elif isinstance(node, list):
                stack.extend(node)
    return max(dates) if dates else None


def canonical_data(path: Path, existing_lastmod: dict[str, str]) -> tuple[str, str, str, str]:
    text = path.read_text(encoding="utf-8")
    canonical = read_tag(text, r'<link\b(?=[^>]*rel=["\']canonical["\'])[^>]*href=["\']([^"\']+)["\']')
    title = read_tag(text, r"<title>(.*?)</title>")
    description = read_tag(text, r'<meta\b(?=[^>]*name=["\']description["\'])[^>]*content=["\']([^"\']*)["\']')
    lastmod = structured_modified(text) or existing_lastmod.get(canonical, TODAY)
    return canonical, title, description, lastmod


def existing_sitemap_dates(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    result: dict[str, str] = {}
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return result
    for node in root.findall("sm:url", namespace):
        loc = node.findtext("sm:loc", default="", namespaces=namespace).strip()
        lastmod = node.findtext("sm:lastmod", default="", namespaces=namespace).strip()
        if loc and re.fullmatch(r"\d{4}-\d{2}-\d{2}", lastmod):
            result[loc] = lastmod
    return result


def rss_date(value: str) -> str:
    moment = datetime.strptime(value, "%Y-%m-%d").replace(hour=12, tzinfo=KST)
    return moment.strftime("%a, %d %b %Y %H:%M:%S %z")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    existing = existing_sitemap_dates(root / "sitemap.xml")
    pages = sorted(root.rglob("index.html"))
    data = [canonical_data(path, existing) for path in pages]
    canonicals = [item[0] for item in data]
    if len(canonicals) != len(set(canonicals)):
        raise ValueError("Duplicate canonical URLs detected")

    sitemap_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for canonical, _title, _description, lastmod in sorted(data):
        sitemap_lines.extend([
            "  <url>",
            f"    <loc>{html.escape(canonical)}</loc>",
            f"    <lastmod>{lastmod}</lastmod>",
            "  </url>",
        ])
    sitemap_lines.append("</urlset>")
    (root / "sitemap.xml").write_text("\n".join(sitemap_lines) + "\n", encoding="utf-8", newline="\n")

    feed_paths = [
        root / "index.html",
        root / "학습관리" / "index.html",
        root / "전국센터" / "index.html",
        *(root / "전국센터" / slug / "index.html" for slug in RSS_HUB_SLUGS),
        root / "과목별학원" / "index.html",
        *(root / "과목별학원" / slug / "index.html" for slug in RSS_SUBJECT_HUB_SLUGS),
    ]
    missing = [path for path in feed_paths if not path.is_file()]
    if missing:
        raise ValueError(f"RSS source pages missing: {missing}")
    items = [canonical_data(path, existing) for path in feed_paths]
    build_date = rss_date(max(item[3] for item in items))
    rss_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0">',
        "  <channel>",
        "    <title>와와학습코칭학원 학습 안내</title>",
        "    <link>https://xn--sp5b72l1taf0p.com/</link>",
        "    <description>학습 진단, 계획, 과제 실행과 지역별 영어·수학 학습관리 안내입니다.</description>",
        "    <language>ko-KR</language>",
        f"    <lastBuildDate>{build_date}</lastBuildDate>",
    ]
    for canonical, title, description, lastmod in items:
        rss_lines.extend([
            "    <item>",
            f"      <title>{html.escape(title)}</title>",
            f"      <link>{html.escape(canonical)}</link>",
            f"      <guid isPermaLink=\"true\">{html.escape(canonical)}</guid>",
            f"      <description>{html.escape(description)}</description>",
            f"      <pubDate>{rss_date(lastmod)}</pubDate>",
            "    </item>",
        ])
    rss_lines.extend(["  </channel>", "</rss>"])
    (root / "rss.xml").write_text("\n".join(rss_lines) + "\n", encoding="utf-8", newline="\n")
    print(f"sitemap_urls={len(canonicals)} rss_items={len(items)}")


if __name__ == "__main__":
    main()
