# -*- coding: utf-8 -*-
"""Build crawlable region/category hubs without changing existing local URLs.

The source of truth is the supplied centre-information CSV.  Existing 371
neighbourhood pages remain in place; this tool adds 13 regional collections,
six curriculum collections and reciprocal contextual links.
"""

from __future__ import annotations

import csv
import html
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote


DOMAIN = "xn--sp5b72l1taf0p.com"
BASE_URL = f"https://{DOMAIN}"
TODAY = "2026-07-29"
CENTER_DIR = "전국센터"
REGION_ORDER = ["서울", "경기", "인천", "대전", "충청", "대구", "울산", "부산", "경상", "광주", "전라", "강원", "제주"]
CATEGORIES = {
    "초등영어학원": ("초등 영어학원", "단어·문장 읽기·기초 문법·독해 흐름을 확인하는 초등 영어 학습 안내"),
    "초등수학학원": ("초등 수학학원", "개념·연산·문장제·풀이 기록을 확인하는 초등 수학 학습 안내"),
    "중등영어학원": ("중등 영어학원", "교과서 본문·어휘·문법·서술형을 확인하는 중등 영어 학습 안내"),
    "중등수학학원": ("중등 수학학원", "단원 개념·내신 유형·서술형·누적 오답을 확인하는 중등 수학 학습 안내"),
    "고등영어학원": ("고등 영어학원", "내신 범위·모의고사 독해·어휘·구문을 확인하는 고등 영어 학습 안내"),
    "고등수학학원": ("고등 수학학원", "단원 개념·내신 유형·수능형 접근·서술형을 확인하는 고등 수학 학습 안내"),
}
CONSULT_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdb2oE5Qk5YS0TfYDxyV1w-IOTkhkjOCmmpAKTI9FmqpVj6Yg/viewform"


def normalize(value: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value or "")).strip()


def page_url(*parts: str) -> str:
    encoded = "/".join(quote(part, safe="") for part in parts)
    return f"{BASE_URL}/{encoded}/" if encoded else BASE_URL + "/"


def load_manifest(root: Path) -> list[dict[str, str]]:
    csv_path = root.parent / "참고자료" / "공통자료" / "센터정보 정리.csv"
    folders = {
        normalize(path.name): path.name
        for path in (root / CENTER_DIR).iterdir()
        if path.is_dir() and all((path / slug / "index.html").is_file() for slug in CATEGORIES)
    }
    rows: list[dict[str, str]] = []
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        for raw in csv.DictReader(handle):
            locality = str(raw.get("근처 수업가능 동네", "")).strip()
            folder = folders.get(normalize(locality))
            if not folder:
                raise ValueError(f"No existing neighbourhood folder for CSV row: {locality}")
            rows.append({
                "display": locality,
                "folder": folder,
                "region": str(raw.get("지역", "")).strip(),
                "district": str(raw.get("시or구", "")).strip() or "지역 안내",
            })
    if len(rows) != 371 or len({row["folder"] for row in rows}) != 371:
        raise ValueError(f"Expected 371 unique neighbourhoods, got rows={len(rows)} folders={len({row['folder'] for row in rows})}")
    unknown = sorted({row["region"] for row in rows} - set(REGION_ORDER))
    if unknown:
        raise ValueError(f"Unknown regions: {unknown}")
    return rows


def schema_graph(*, url: str, title: str, description: str, crumbs: list[tuple[str, str]], items: list[tuple[str, str]], about: dict[str, str]) -> dict:
    breadcrumb_id = url + "#breadcrumb"
    list_id = url + "#item-list"
    return {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebSite", "@id": BASE_URL + "/#website", "url": BASE_URL + "/", "name": "와와학습코칭학원", "inLanguage": "ko-KR"},
            {
                "@type": "CollectionPage", "@id": url + "#webpage", "url": url, "name": title,
                "description": description, "inLanguage": "ko-KR", "isPartOf": {"@id": BASE_URL + "/#website"},
                "publisher": {"@id": BASE_URL + "/#organization"}, "about": about,
                "breadcrumb": {"@id": breadcrumb_id}, "mainEntity": {"@id": list_id}, "dateModified": TODAY,
            },
            {
                "@type": "BreadcrumbList", "@id": breadcrumb_id,
                "itemListElement": [
                    {"@type": "ListItem", "position": index, "name": name, "item": item_url}
                    for index, (name, item_url) in enumerate(crumbs, 1)
                ],
            },
            {
                "@type": "ItemList", "@id": list_id, "name": title + " 페이지 목록", "numberOfItems": len(items),
                "itemListElement": [
                    {"@type": "ListItem", "position": index, "name": name, "url": item_url}
                    for index, (name, item_url) in enumerate(items, 1)
                ],
            },
        ],
    }


def shell(*, depth: int, title: str, description: str, canonical: str, h1: str, eyebrow: str, intro: str,
          metric: str, metric_label: str, crumbs: list[tuple[str, str | None]], body: str,
          schema: dict, extra_script: str = "") -> str:
    home = "../" * depth
    crumb_html = "".join(
        f'<span><a href="{html.escape(href, quote=True)}">{html.escape(name)}</a></span>' if href else f"<span>{html.escape(name)}</span>"
        for name, href in crumbs
    )
    compact_schema = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
    return f'''<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(description, quote=True)}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{html.escape(canonical, quote=True)}">
  <link rel="alternate" type="application/rss+xml" title="와와학습코칭학원 RSS" href="{BASE_URL}/rss.xml">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{html.escape(canonical, quote=True)}">
  <meta property="og:title" content="{html.escape(title, quote=True)}">
  <meta property="og:description" content="{html.escape(description, quote=True)}">
  <meta property="og:image" content="{BASE_URL}/assets/generated/site3-hero.webp">
  <link rel="icon" type="image/png" href="{home}assets/favicon.png">
  <link rel="apple-touch-icon" href="{home}assets/favicon.png">
  <link rel="stylesheet" href="{home}assets/site.css">
  <script type="application/ld+json">{compact_schema}</script>
</head>
<body class="center-page">
<a class="skip-link" href="#main">본문 바로가기</a>
  <header class="site-header">
    <nav class="nav wrap" aria-label="주요 메뉴">
      <a class="brand" href="{home}" aria-label="와와학습코칭학원 홈"><span class="brand-mark">W</span><span><small>STUDY COACHING</small>와와학습코칭학원</span></a>
      <div class="nav-links"><a href="{home}">홈</a><a href="{home}학습관리/">학습관리</a><a class="active" href="{home}전국센터/">전국센터</a><a href="{home}상담문의/">상담문의</a></div>
      <a class="nav-cta" href="{CONSULT_URL}" target="_blank" rel="noopener">상담 신청</a>
    </nav>
  </header>
  <main id="main">
    <section class="center-hero">
      <div class="wrap">
        <div class="crumbs">{crumb_html}</div>
        <div class="center-hero-card"><div class="center-hero-inner">
          <div><p class="eyebrow">{html.escape(eyebrow)}</p><h1>{html.escape(h1)}</h1><p>{html.escape(intro)}</p>
            <div class="local-actions"><a class="btn btn-primary" href="{CONSULT_URL}" target="_blank" rel="noopener">상담 신청</a><a class="btn btn-ghost" href="tel:010-3957-8283">전화 문의</a></div>
          </div>
          <aside class="hero-mini-panel"><span>{html.escape(metric_label)}</span><strong>{html.escape(metric)}</strong><span>확인된 안내 페이지</span></aside>
        </div></div>
      </div>
    </section>
{body}
  </main>
  <footer class="site-footer" id="contact"><div class="wrap footer-inner"><div><a class="brand footer-brand" href="{home}"><span class="brand-mark">W</span><span><small>STUDY COACHING</small>와와학습코칭학원</span></a><p>초중고 영어수학 학습코칭 · 진단상담 · 플래너 관리</p></div><div class="footer-links"><a href="{home}학습관리/">학습관리</a><a href="{home}전국센터/">전국센터</a><a href="tel:010-3957-8283">010-3957-8283</a></div></div></footer>
  <div class="floating-actions" aria-label="빠른 상담 메뉴"><a class="fab-call" href="tel:010-3957-8283">전화문의</a><a class="fab-sms" href="https://blogsms.net/01039578283" target="_blank" rel="noopener">문자문의</a><a class="fab-consult" href="{CONSULT_URL}" target="_blank" rel="noopener">상담신청</a></div>
{extra_script}</body>
</html>
'''


def card_links(links: list[tuple[str, str, str]]) -> str:
    return "".join(
        f'<a class="hub-link" href="{html.escape(href, quote=True)}"><strong>{html.escape(label)}</strong><small>{html.escape(note)}</small></a>'
        for label, href, note in links
    )


def faq_section(title: str, faqs: list[tuple[str, str]]) -> str:
    items = "".join(
        f'<details><summary>{html.escape(question)}</summary><p>{html.escape(answer)}</p></details>'
        for question, answer in faqs
    )
    return (
        '    <section id="faq-section" class="local-section">'
        f'<div class="wrap faq-local"><h2>{html.escape(title)}</h2>{items}</div></section>'
    )


def root_body(rows: list[dict[str, str]]) -> tuple[str, str]:
    region_links = []
    for region in REGION_ORDER:
        regional = [row for row in rows if row["region"] == region]
        districts = len({row["district"] for row in regional})
        region_links.append((region, f"{region}/", f"{districts}개 시·군·구 · {len(regional)}개 동네"))
    category_links = [(label, f"{slug}/", note) for slug, (label, note) in CATEGORIES.items()]
    options = "".join(f'<option value="{html.escape(row["display"], quote=True)}"></option>' for row in rows)
    mapping = {normalize(row["display"]): row["folder"] + "/" for row in rows}
    body = f'''    <section class="local-section"><div class="wrap">
      <article class="local-card"><p class="eyebrow">REGION DIRECTORY</p><h2>광역지역에서 동네 안내 찾기</h2><p>광역지역을 선택하면 시·군·구별 동네 페이지를 확인할 수 있습니다. 실제 센터명과 방문 주소는 각 동네 페이지에서 구분해 안내합니다.</p><div class="hub-districts">{card_links(region_links)}</div></article>
    </div></section>
    <section class="local-section"><div class="wrap">
      <article class="local-card"><p class="eyebrow">CURRICULUM DIRECTORY</p><h2>학년·과목 기준으로 비교하기</h2><p>학생이 필요한 학년과 과목을 먼저 고르면 같은 기준의 지역 안내를 한곳에서 비교할 수 있습니다.</p><div class="hub-districts">{card_links(category_links)}</div></article>
    </div></section>
    <section class="local-section"><div class="wrap"><article class="center-search-card" aria-label="동네 안내 검색">
      <div class="center-search-head"><div><p class="eyebrow">LOCAL SEARCH</p><h2>동네명으로 바로 찾기</h2><p>동네명을 입력한 뒤 이동 버튼을 누르면 기존 371개 안내 페이지로 이동합니다.</p></div>
      <form class="center-search-form" id="hubSearch"><label class="skip-link" for="hubSearchInput">동네명 검색</label><input id="hubSearchInput" list="hubLocalities" type="search" placeholder="예: 명일동, 화명동" autocomplete="off"><button type="submit">페이지 이동</button><datalist id="hubLocalities">{options}</datalist></form></div>
      <div class="center-search-meta"><span>전체 371개 동네</span><span id="hubSearchMessage">정확한 동네명을 선택해 주세요.</span></div>
    </article></div></section>'''
    script = f'''  <script>
  (() => {{
    const pages = {json.dumps(mapping, ensure_ascii=False, separators=(",", ":"))};
    const form = document.getElementById("hubSearch");
    const input = document.getElementById("hubSearchInput");
    const message = document.getElementById("hubSearchMessage");
    form.addEventListener("submit", (event) => {{
      event.preventDefault();
      const key = input.value.normalize("NFKC").replace(/\\s+/g, "");
      if (pages[key]) {{ window.location.href = pages[key]; return; }}
      message.textContent = "목록에서 정확한 동네명을 선택해 주세요.";
    }});
  }})();
  </script>
'''
    return body, script


def region_body(region: str, rows: list[dict[str, str]]) -> str:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[row["district"]].append(row)
    cards = []
    for district in sorted(groups):
        links = [(row["display"], f"../{row['folder']}/", "동네 종합 안내") for row in sorted(groups[district], key=lambda item: item["display"])]
        cards.append(f'<article class="hub-card"><h3>{html.escape(district)}</h3><div class="hub-links">{card_links(links)}</div></article>')
    categories = [(label, f"../{slug}/", note) for slug, (label, note) in CATEGORIES.items()]
    return f'''    <section class="local-section"><div class="wrap"><article class="local-card"><h2>{html.escape(region)} 지역 학습 안내 기준</h2><p>{html.escape(region)} 지역은 {len(groups)}개 시·군·구의 {len(rows)}개 동네 페이지로 구분했습니다. 동네 페이지에서 실제 안내 센터와 주소, 가능 학년, 참고 학교를 확인한 뒤 상담 범위를 비교하세요.</p><div class="hub-districts">{card_links(categories)}</div></article></div></section>
    <section class="local-section"><div class="wrap"><p class="eyebrow">{html.escape(region)} LOCAL DIRECTORY</p><h2>{html.escape(region)} 시·군·구별 동네 바로가기</h2><div class="hub-districts">{"".join(cards)}</div></div></section>'''


def category_body(slug: str, rows: list[dict[str, str]]) -> str:
    label, note = CATEGORIES[slug]
    sections = []
    for region in REGION_ORDER:
        regional = [row for row in rows if row["region"] == region]
        groups: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in regional:
            groups[row["district"]].append(row)
        cards = []
        for district in sorted(groups):
            links = [(f"{row['display']} {label}", f"../{row['folder']}/{slug}/", note) for row in sorted(groups[district], key=lambda item: item["display"])]
            cards.append(f'<article class="hub-card"><h3>{html.escape(district)}</h3><div class="hub-links">{card_links(links)}</div></article>')
        sections.append(f'<section class="hub-region"><h2>{html.escape(region)} {html.escape(label)}</h2><div class="hub-districts">{"".join(cards)}</div></section>')
    return f'''    <section class="local-section"><div class="wrap"><article class="local-card"><h2>{html.escape(label)} 선택 전 확인할 기준</h2><p>{html.escape(note)}입니다. 각 지역 페이지는 제공된 센터정보에 있는 가능 학년과 실제 안내 센터를 기준으로 작성했으며, 학교명이나 개설 정보를 임의로 추가하지 않았습니다.</p><ul class="summary-list"><li>현재 교재와 최근 평가 자료</li><li>학교 진도와 시험 일정</li><li>반복되는 오답과 공부 가능 시간</li><li>실제 센터 주소와 현재 개설 시간</li></ul></article></div></section>
    <section class="local-section"><div class="wrap"><p class="eyebrow">LOCAL {html.escape(label.upper())}</p><h2>지역별 {html.escape(label)} 바로가기</h2>{"".join(sections)}</div></section>'''


def update_context_links(root: Path, rows: list[dict[str, str]]) -> int:
    center = root / CENTER_DIR
    # Do not consume indentation before the marker.  Replacing only the marker
    # body makes repeated runs byte-for-byte stable instead of accumulating
    # whitespace changes across thousands of pages.
    marker_re = re.compile(r'<!-- academy-hub-links:start -->.*?<!-- academy-hub-links:end -->\n[ \t]*', re.S)
    changed = 0
    for row in rows:
        parent = center / row["folder"] / "index.html"
        targets = [(parent, None)] + [(center / row["folder"] / slug / "index.html", slug) for slug in CATEGORIES]
        for path, category in targets:
            original = path.read_text(encoding="utf-8")
            if category:
                links = [
                    (f"../../{row['region']}/", f"{row['region']} 지역 안내"),
                    (f"../../{category}/", f"전국 {CATEGORIES[category][0]} 안내"),
                ]
            else:
                links = [(f"../{row['region']}/", f"{row['region']} 지역 안내")]
            marker = '<!-- academy-hub-links:start -->\n        <div class="local-actions" aria-label="지역과 학년 과목 허브 이동">' + "".join(
                f'<a class="btn btn-ghost" href="{html.escape(href, quote=True)}">{html.escape(label)}</a>' for href, label in links
            ) + '</div>\n        <!-- academy-hub-links:end -->\n        '
            needle = '<div class="family-link-grid"'
            if marker_re.search(original):
                text = marker_re.sub(marker, original, count=1)
            elif needle in original:
                text = original.replace(needle, marker + needle, 1)
            else:
                raise ValueError(f"Family navigation not found: {path}")

            script = re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)
            if not script:
                raise ValueError(f"JSON-LD missing: {path}")
            data = json.loads(script.group(1))
            graph = data.get("@graph", [])
            item_list = next((node for node in graph if isinstance(node, dict) and node.get("@type") == "ItemList"), None)
            if item_list is not None:
                items = [item for item in item_list.get("itemListElement", []) if "지역 안내 허브" not in str(item.get("name", "")) and "전국 과정 허브" not in str(item.get("name", ""))]
                hub_urls = [(f"{row['region']} 지역 안내 허브", page_url(CENTER_DIR, row["region"]))]
                if category:
                    hub_urls.append((f"{CATEGORIES[category][0]} 전국 과정 허브", page_url(CENTER_DIR, category)))
                for name, url in hub_urls:
                    items.append({"@type": "ListItem", "position": len(items) + 1, "name": name, "url": url})
                for position, item in enumerate(items, 1):
                    item["position"] = position
                item_list["itemListElement"] = items
            compact = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
            text = text[:script.start(1)] + compact + text[script.end(1):]
            if text != original:
                path.write_text(text, encoding="utf-8", newline="\n")
                changed += 1
    return changed


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    rows = load_manifest(root)
    center = root / CENTER_DIR

    root_items = [(f"{region} 지역 안내", page_url(CENTER_DIR, region)) for region in REGION_ORDER]
    root_items.extend((label, page_url(CENTER_DIR, slug)) for slug, (label, _note) in CATEGORIES.items())
    root_faqs = [
        (
            "전국센터에서 원하는 동네 페이지는 어떻게 찾나요?",
            "광역지역을 먼저 고르거나 동네명 검색을 이용하면 기존 371개 동네 안내로 이동할 수 있습니다. 학년과 과목이 정해졌다면 과정별 안내에서 비교할 수도 있습니다.",
        ),
        (
            "동네명 페이지가 해당 동네 안의 독립 센터를 뜻하나요?",
            "항상 그렇지는 않습니다. 각 페이지는 상담 가능 생활권을 설명하며, 방문할 실제 센터명과 주소는 페이지의 ‘확인된 센터 정보’ 또는 ‘인근 실제 센터 정보’에서 구분해 안내합니다.",
        ),
        (
            "영어와 수학의 수업 가능 학년은 모두 같은가요?",
            "센터와 과목에 따라 현재 확인되는 학년 범위가 다를 수 있습니다. 동네별 페이지에 표시된 제공 자료를 확인한 뒤 정확한 개설 시간과 수업 가능 여부를 문의해 주세요.",
        ),
        (
            "첫 상담 전에 준비하면 좋은 자료는 무엇인가요?",
            "현재 교재, 최근 시험지나 평가 자료, 반복되는 오답 기록, 학교 시험 일정과 주간 공부 가능 시간을 준비하면 우선순위를 더 구체적으로 정할 수 있습니다.",
        ),
    ]
    body, script = root_body(rows)
    body += "\n" + faq_section("전국 학습코칭 안내 자주 묻는 질문", root_faqs)
    root_url = page_url(CENTER_DIR)
    root_schema = schema_graph(
        url=root_url, title="전국 371개 동네별 학습 안내", description="전국 371개 동네의 영어·수학 학습관리 안내를 광역지역과 학년·과목 기준으로 찾는 페이지입니다.",
        crumbs=[("와와학습코칭학원", BASE_URL + "/"), ("전국센터", root_url)], items=root_items,
        about={"@type": "Thing", "name": "전국 초중고 영어수학 학습관리"},
    )
    root_schema["@graph"].append({
        "@type": "FAQPage",
        "@id": root_url + "#faq",
        "mainEntity": [
            {
                "@type": "Question",
                "name": question,
                "acceptedAnswer": {"@type": "Answer", "text": answer},
            }
            for question, answer in root_faqs
        ],
    })
    (center / "index.html").write_text(shell(
        depth=1, title="전국 371개 동네별 학습 안내 | 와와학습코칭학원", description="전국 371개 동네의 영어·수학 학습관리 안내를 광역지역과 학년·과목 기준으로 찾아보세요.", canonical=root_url,
        h1="전국 371개 동네 학습코칭 안내", eyebrow="REGION & CURRICULUM HUB", intro="광역지역이나 학년·과목을 먼저 선택한 뒤 실제 센터 정보가 연결된 동네 안내를 확인할 수 있습니다.", metric="371개", metric_label="LOCAL PAGES",
        crumbs=[("홈", "../"), ("전국센터", None)], body=body, schema=root_schema, extra_script=script,
    ), encoding="utf-8", newline="\n")

    for region in REGION_ORDER:
        regional = [row for row in rows if row["region"] == region]
        url = page_url(CENTER_DIR, region)
        items = [(f"{row['display']} 학원", page_url(CENTER_DIR, row["folder"])) for row in regional]
        schema = schema_graph(url=url, title=f"{region} 지역 학습코칭 안내", description=f"{region} {len(regional)}개 동네의 영어·수학 학습관리와 실제 안내 센터 정보를 시·군·구별로 확인하세요.", crumbs=[("와와학습코칭학원", BASE_URL + "/"), ("전국센터", root_url), (region, url)], items=items, about={"@type": "Place", "name": region})
        path = center / region / "index.html"; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(shell(depth=2, title=f"{region} 지역 학원 안내 | 와와학습코칭학원", description=f"{region} {len(regional)}개 동네의 영어·수학 학습관리와 실제 안내 센터 정보를 시·군·구별로 확인하세요.", canonical=url, h1=f"{region} 지역 학습코칭 안내", eyebrow="REGIONAL ACADEMY DIRECTORY", intro=f"{region} 지역의 {len(regional)}개 동네를 시·군·구별로 정리했습니다. 각 페이지에서 실제 센터 주소와 가능 학년을 확인하세요.", metric=f"{len(regional)}개", metric_label="LOCAL PAGES", crumbs=[("홈", "../../"), ("전국센터", "../"), (region, None)], body=region_body(region, regional), schema=schema), encoding="utf-8", newline="\n")

    for slug, (label, note) in CATEGORIES.items():
        url = page_url(CENTER_DIR, slug)
        items = [(f"{row['display']} {label}", page_url(CENTER_DIR, row["folder"], slug)) for row in rows]
        schema = schema_graph(url=url, title=f"전국 {label} 안내", description=f"전국 371개 동네의 {note}를 지역별로 확인하세요.", crumbs=[("와와학습코칭학원", BASE_URL + "/"), ("전국센터", root_url), (label, url)], items=items, about={"@type": "Thing", "name": label})
        path = center / slug / "index.html"; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(shell(depth=2, title=f"전국 {label} 안내 | 와와학습코칭학원", description=f"전국 371개 동네의 {note}를 실제 센터 정보와 함께 지역별로 확인하세요.", canonical=url, h1=f"전국 {label} 안내", eyebrow="CURRICULUM ACADEMY DIRECTORY", intro=f"{note}입니다. 동네별 페이지에서 현재 교재와 학생 상황, 실제 센터의 가능 학년을 함께 확인하세요.", metric="371개", metric_label="LOCAL PAGES", crumbs=[("홈", "../../"), ("전국센터", "../"), (label, None)], body=category_body(slug, rows), schema=schema), encoding="utf-8", newline="\n")

    updated = update_context_links(root, rows)
    print(f"neighbourhoods={len(rows)} regions={len(REGION_ORDER)} categories={len(CATEGORIES)} context_pages_updated={updated}")


if __name__ == "__main__":
    main()
