"""Synchronize only home/learning metadata and their discovery entries.

The visible page is the source of truth for FAQ text. No locality generation,
canonical migration, contact change or publication is performed here.
"""
import html
import json
import re
from datetime import date, datetime
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
TODAY = date.today().isoformat()
DOMAIN = "https://xn--sp5b72l1taf0p.com"
SPECS = [
    ("index.html", "/", [("coaching", "와와의 학습코칭"), ("videos", "본사 학습코칭 영상"), ("ai-preview", "AI 학습 안내"), ("featured-local-links", "지역과 과목 찾기"), ("faq", "자주 묻는 질문")]),
    ("학습관리/index.html", "/학습관리/", [("four-c", "4C 학습코칭"), ("coaching-care", "플랜·학습·생활관리"), ("ai-learning", "과목별 AI 학습"), ("learning-flow", "상담부터 피드백까지"), ("faq", "자주 묻는 질문")]),
]


def plain(value):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def sync_pages():
    metadata = {}
    for filename, urlpath, sections in SPECS:
        path = ROOT / filename
        source = path.read_text(encoding="utf-8")
        # Native details remain usable without JS and accessible to crawlers.
        source = re.sub(
            r'<article class="faq-item">\s*<h3>(.*?)</h3>\s*<p>(.*?)</p>\s*</article>',
            r'<details class="faq-item">\n            <summary><h3>\1</h3></summary>\n            <p>\2</p>\n          </details>',
            source, flags=re.S,
        )
        title = plain(re.search(r"<title>(.*?)</title>", source, re.S)[1])
        description = html.unescape(re.search(r'<meta name="description" content="([^"]+)"', source)[1])
        image = html.unescape(re.search(r'<meta property="og:image" content="([^"]+)"', source)[1])
        matched = re.search(r'(<script type="application/ld\+json">)\s*(.*?)\s*(</script>)', source, re.S)
        graph = json.loads(matched[2])
        faqs = re.findall(r'<details class="faq-item">\s*<summary><h3>(.*?)</h3></summary>\s*<p>(.*?)</p>\s*</details>', source, re.S)
        assert len(faqs) == (4 if urlpath == "/" else 6), filename
        for node in graph["@graph"]:
            kind = node["@type"]
            if kind in {"WebPage", "Service", "EducationalOrganization"}:
                node["description"] = description
            if kind == "EducationalOrganization":
                node["image"] = image
            if kind == "WebPage":
                node.update({"name": title, "dateModified": TODAY})
                node["hasPart"] = [{"@type": "WebPageElement", "@id": DOMAIN + urlpath + "#" + fragment, "name": name, "url": DOMAIN + urlpath + "#" + fragment} for fragment, name in sections if fragment != "faq"] + [{"@id": DOMAIN + urlpath + "#faq"}]
                node["about"] = [{"@type": "Thing", "name": name} for name in ("학습코칭", "4C 학습관리", "AI 학습")]
                node["primaryImageOfPage"] = {"@type": "ImageObject", "contentUrl": image}
            if kind == "Service":
                if "makesOffer" in node:
                    node["offers"] = node.pop("makesOffer")
            if kind == "FAQPage":
                node["mainEntity"] = [{"@type": "Question", "name": plain(q), "acceptedAnswer": {"@type": "Answer", "text": plain(a)}} for q, a in faqs]
        replacement = matched[1] + "\n" + json.dumps(graph, ensure_ascii=False, indent=2) + "\n  " + matched[3]
        source = source[:matched.start()] + replacement + source[matched.end():]
        path.write_text(source, encoding="utf-8", newline="\r\n")
        metadata[DOMAIN + urlpath] = {"title": title, "description": description}
    return metadata


def sync_discovery(metadata):
    sitemap = ROOT / "sitemap.xml"
    source = sitemap.read_text(encoding="utf-8")
    changed = []
    def update_url(match):
        block = match[0]
        url = unquote(re.search(r"<loc>(.*?)</loc>", block)[1])
        if url in metadata:
            changed.append(url)
            return re.sub(r"<lastmod>.*?</lastmod>", f"<lastmod>{TODAY}</lastmod>", block)
        return block
    source = re.sub(r"<url>.*?</url>", update_url, source, flags=re.S)
    assert set(changed) == set(metadata)
    sitemap.write_text(source, encoding="utf-8", newline="\r\n")
    rss = ROOT / "rss.xml"
    source = rss.read_text(encoding="utf-8")
    date_string = format_datetime(datetime.now().astimezone())
    source = re.sub(r"<lastBuildDate>.*?</lastBuildDate>", f"<lastBuildDate>{date_string}</lastBuildDate>", source)
    def update_item(match):
        block = match[0]
        url = unquote(re.search(r"<link>(.*?)</link>", block)[1])
        if url in metadata:
            values = {**metadata[url], "pubDate": date_string}
            for key, value in values.items():
                block = re.sub(fr"<{key}>.*?</{key}>", lambda _: f"<{key}>{html.escape(value, quote=False)}</{key}>", block)
        return block
    source = re.sub(r"<item>.*?</item>", update_item, source, flags=re.S)
    rss.write_text(source, encoding="utf-8", newline="\r\n")


if __name__ == "__main__":
    result = sync_pages()
    sync_discovery(result)
    print(json.dumps({"updated": list(result), "date": TODAY}, ensure_ascii=False))
