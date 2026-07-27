"""Regenerate sitemap.xml and a concise RSS feed from canonical page data."""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path


LASTMOD = "2026-07-27"
KST = timezone(timedelta(hours=9))
RSS_DATE = datetime(2026, 7, 27, 12, 0, tzinfo=KST).strftime("%a, %d %b %Y %H:%M:%S %z")


def read_tag(text: str, pattern: str) -> str:
    match = re.search(pattern, text, re.I | re.S)
    if not match:
        raise ValueError(f"Required tag not found: {pattern}")
    return html.unescape(match.group(1)).strip()


def canonical_data(path: Path) -> tuple[str, str, str]:
    text = path.read_text(encoding="utf-8")
    canonical = read_tag(text, r'<link\b(?=[^>]*rel=["\']canonical["\'])[^>]*href=["\']([^"\']+)["\']')
    title = read_tag(text, r"<title>(.*?)</title>")
    description = read_tag(text, r'<meta\b(?=[^>]*name=["\']description["\'])[^>]*content=["\']([^"\']*)["\']')
    return canonical, title, description


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    pages = sorted(root.rglob("index.html"))
    data = [canonical_data(path) for path in pages]
    canonicals = [item[0] for item in data]
    if len(canonicals) != len(set(canonicals)):
        raise ValueError("Duplicate canonical URLs detected")

    sitemap_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for canonical in sorted(canonicals):
        sitemap_lines.extend([
            "  <url>",
            f"    <loc>{html.escape(canonical)}</loc>",
            f"    <lastmod>{LASTMOD}</lastmod>",
            "  </url>",
        ])
    sitemap_lines.append("</urlset>")
    (root / "sitemap.xml").write_text("\n".join(sitemap_lines) + "\n", encoding="utf-8", newline="\n")

    feed_paths = [root / "index.html", root / "학습관리" / "index.html", root / "전국센터" / "index.html"]
    items = [canonical_data(path) for path in feed_paths]
    rss_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0">',
        "  <channel>",
        "    <title>와와학습코칭학원 학습 안내</title>",
        "    <link>https://xn--sp5b72l1taf0p.com/</link>",
        "    <description>학습 진단, 계획, 과제 실행과 지역별 상담 정보를 정리한 안내입니다.</description>",
        "    <language>ko-KR</language>",
        f"    <lastBuildDate>{RSS_DATE}</lastBuildDate>",
    ]
    for canonical, title, description in items:
        rss_lines.extend([
            "    <item>",
            f"      <title>{html.escape(title)}</title>",
            f"      <link>{html.escape(canonical)}</link>",
            f"      <guid isPermaLink=\"true\">{html.escape(canonical)}</guid>",
            f"      <description>{html.escape(description)}</description>",
            f"      <pubDate>{RSS_DATE}</pubDate>",
            "    </item>",
        ])
    rss_lines.extend(["  </channel>", "</rss>"])
    (root / "rss.xml").write_text("\n".join(rss_lines) + "\n", encoding="utf-8", newline="\n")
    print(f"sitemap_urls={len(canonicals)} rss_items={len(items)}")


if __name__ == "__main__":
    main()
