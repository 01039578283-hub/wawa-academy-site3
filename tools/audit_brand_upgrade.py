"""Read-only static checks; writes an ignored audit report only."""
import hashlib
import html
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "https://xn--sp5b72l1taf0p.com"
PAGES = {"index.html": "/", "학습관리/index.html": "/학습관리/"}
errors = []


def check(condition, description):
    if not condition:
        errors.append(description)


def plain(value):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


class Parser(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.nodes = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.nodes.append((tag, dict(attrs)))


def main():
    report = {"pages": [], "assets": []}
    for filename, pagepath in PAGES.items():
        path = ROOT / filename
        source = path.read_text(encoding="utf-8")
        parser = Parser(source)
        ids = [a["id"] for _, a in parser.nodes if a.get("id")]
        check(len(ids) == len(set(ids)), f"{filename}: duplicate IDs")
        check(sum(t == "h1" for t, _ in parser.nodes) == 1, f"{filename}: H1 count")
        check(sum(t == "title" for t, _ in parser.nodes) == 1, f"{filename}: title count")
        metas = {a.get("name", a.get("property")): a.get("content") for t, a in parser.nodes if t == "meta"}
        title = plain(re.search(r"<title>(.*?)</title>", source, re.S)[1])
        canonical = [a["href"] for t, a in parser.nodes if t == "link" and a.get("rel") == "canonical"]
        check(canonical == [DOMAIN + pagepath], f"{filename}: canonical")
        check(metas["og:url"] == canonical[0], f"{filename}: og:url")
        check(metas["og:title"] == title, f"{filename}: og:title")
        check(metas["description"] == metas["og:description"], f"{filename}: description mismatch")
        graph = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', source, re.S)[1])["@graph"]
        web = next(n for n in graph if n["@type"] == "WebPage")
        check(web["name"] == title and web["url"] == canonical[0], f"{filename}: WebPage identity")
        check(web["description"] == metas["description"], f"{filename}: WebPage description")
        check(all("makesOffer" not in n for n in graph if n["@type"] == "Service"), f"{filename}: Service offers property")
        faq_schema = next(n for n in graph if n["@type"] == "FAQPage")["mainEntity"]
        faq_visible = re.findall(r'<details class="faq-item">\s*<summary><h3>(.*?)</h3></summary>\s*<p>(.*?)</p>\s*</details>', source, re.S)
        check([(q["name"], q["acceptedAnswer"]["text"]) for q in faq_schema] == [(plain(q), plain(a)) for q, a in faq_visible], f"{filename}: FAQ text differs")
        check("youtube.com/embed" not in source and "youtube-nocookie.com/embed" not in source, f"{filename}: eager video iframe")
        links_checked = 0
        for tag, attrs in parser.nodes:
            if tag == "img":
                check("alt" in attrs and "width" in attrs and "height" in attrs, f"{filename}: image semantics {attrs}")
                check(attrs.get("loading") in {"lazy", "eager"}, f"{filename}: image loading strategy")
            url = attrs.get("href") if tag in {"a", "link"} else attrs.get("src") if tag in {"img", "script"} else None
            if not url or url.startswith(("tel:", "mailto:", "sms:")):
                continue
            resolved = urlsplit(urljoin(DOMAIN + pagepath, url))
            if resolved.netloc != urlsplit(DOMAIN).netloc:
                continue
            target = ROOT / unquote(resolved.path).lstrip("/")
            if target.is_dir():
                target /= "index.html"
            check(target.is_file(), f"{filename}: missing local target {url}")
            if tag == "img" and target.is_file():
                with Image.open(target) as im:
                    check(im.size == (int(attrs["width"]), int(attrs["height"])), f"{filename}: image dimensions {url}")
            if target.is_file() and resolved.fragment and target.suffix == ".html":
                target_text = target.read_text(encoding="utf-8")
                check(f'id="{unquote(resolved.fragment)}"' in target_text, f"{filename}: broken fragment {url}")
            links_checked += 1
        # Preserve all current contact targets, locale links, and verification tags.
        before = subprocess.check_output(["git", "show", f"HEAD:{filename}"], cwd=ROOT).decode("utf-8")
        old_contacts = {a["href"] for t, a in Parser(before).nodes if t == "a" and a.get("href", "").startswith(("tel:", "https://blogsms.net/", "https://docs.google.com/forms/"))}
        new_contacts = {a["href"] for t, a in parser.nodes if t == "a" and a.get("href", "").startswith(("tel:", "https://blogsms.net/", "https://docs.google.com/forms/"))}
        check(old_contacts == new_contacts, f"{filename}: contact target changed")
        before_regions = {a["href"] for t, a in Parser(before).nodes if t == "a" and any(v in a.get("href", "") for v in ("전국센터/", "과목별학원/"))}
        after_regions = {a["href"] for t, a in parser.nodes if t == "a" and any(v in a.get("href", "") for v in ("전국센터/", "과목별학원/"))}
        check(before_regions <= after_regions, f"{filename}: removed regional link")
        for tag, attrs in Parser(before).nodes:
            if tag == "meta" and attrs.get("name", "").endswith("site-verification"):
                check(metas.get(attrs["name"]) == attrs["content"], f"{filename}: verification token changed")
        report["pages"].append({"file": filename, "h1": 1, "faq": len(faq_visible), "local_links_checked": links_checked, "title": title, "bytes": path.stat().st_size, "dateModified": web["dateModified"]})
    originals = {"brand-learning.png": "Main_CD_wawa.png", "learning-space.png": "system_03.png", "teacher-coaching.png": "system_04.png", "four-c.png": "system_05.png", "learning-planner.png": "system_06_01.png", "learning-materials.png": "system_07_01.png", "ai-english.png": "ais_step02.png", "ai-math.png": "ais_math_content02.png", "ai-korean.png": "ais_kor_content03.png", "ai-reading.png": "ais_read_portfolio.png", "ai-guide.png": "ais01.png", "video-student.jpg": "video-avpJfW7eIV0.jpg", "video-coaching.jpg": "video-f_skFu40U04.jpg", "video-exam.jpg": "video-UIXUaBZdNXU.jpg"}
    for file in sorted((ROOT / "assets/brand-upgrade-v1").iterdir()):
        data = file.read_bytes()
        with Image.open(file) as im:
            im.verify()
        original = ROOT / "tools/data/brand-upgrade" / originals[file.name]
        if original.exists():
            check(data == original.read_bytes(), f"{file.name}: differs from collected original")
        report["assets"].append({"file": file.name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    # Check XML and prove only the two edited page entries changed.
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    def sitemap_map(data):
        return {unquote(n.find("s:loc", ns).text): n.find("s:lastmod", ns).text for n in ET.fromstring(data).findall("s:url", ns)}
    oldmap = sitemap_map(subprocess.check_output(["git", "show", "HEAD:sitemap.xml"], cwd=ROOT))
    newmap = sitemap_map((ROOT / "sitemap.xml").read_bytes())
    check(set(oldmap) == set(newmap), "sitemap route set changed")
    changed_dates = {url for url in oldmap if oldmap[url] != newmap[url]}
    check(changed_dates <= {DOMAIN + v for v in PAGES.values()}, "unrelated sitemap lastmod changed")
    ET.parse(ROOT / "rss.xml")
    report["sitemap"] = {"url_count": len(newmap), "changed_entries": sorted(changed_dates)}
    report["asset_bytes"] = sum(a["bytes"] for a in report["assets"])
    report["errors"] = errors
    report["status"] = "PASS" if not errors else "FAIL"
    output = ROOT / "tools/reports/brand-upgrade/static-audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "assets"}, ensure_ascii=False, indent=2))
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
