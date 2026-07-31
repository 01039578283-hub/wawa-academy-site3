# -*- coding: utf-8 -*-
"""Add searchable, grouped navigation to the six curriculum hub pages.

This is an idempotent post-processor for ``build_academy_hubs.py``.  Run it
after that generator whenever hub pages are rebuilt.  The default mode is
read-only; ``--apply`` is required to write the six hub HTML files.

Existing destination URLs and JSON-LD are preserved.  The 371 links remain in
the HTML DOM, while region buttons, district ``details`` and client-side search
make the directory practical on mobile.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from build_academy_hubs import (
    CATEGORIES,
    CENTER_DIR,
    REGION_ORDER,
    load_manifest,
    normalize,
)


ROOT = Path(__file__).resolve().parents[1]
CENTER_ROOT = ROOT / CENTER_DIR
BLOCK_START = "<!-- category-hub-navigation:start -->"
BLOCK_END = "<!-- category-hub-navigation:end -->"
SCRIPT_START = "<!-- category-hub-navigation-script:start -->"
SCRIPT_END = "<!-- category-hub-navigation-script:end -->"

MARKED_BLOCK_RE = re.compile(
    rf"\s*{re.escape(BLOCK_START)}.*?{re.escape(BLOCK_END)}\s*",
    re.DOTALL,
)
LEGACY_DIRECTORY_RE = re.compile(
    r'\s*<section class="local-section"><div class="wrap">'
    r'<p class="eyebrow">LOCAL .*?</div></section>\s*'
    r'(?=(?:<!-- hub-content-refinement:start -->|</main>))',
    re.DOTALL,
)
MARKED_SCRIPT_RE = re.compile(
    rf"\s*{re.escape(SCRIPT_START)}.*?{re.escape(SCRIPT_END)}\s*",
    re.DOTALL,
)
HREF_RE = re.compile(r'<a\b[^>]*class="[^"]*\bhub-link\b[^"]*"[^>]*href="([^"]+)"')


@dataclass
class HubPlan:
    path: Path
    original: str
    updated: str
    old_hrefs: set[str]
    new_hrefs: set[str]
    region_panels: int
    district_details: int
    locality_links: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write the six category hub HTML files",
    )
    return parser.parse_args()


def hub_markup(
    slug: str, rows: list[dict[str, str]]
) -> tuple[str, str, dict[str, int]]:
    label, note = CATEGORIES[slug]
    search_mapping: dict[str, str] = {}
    options: list[str] = []
    panels: list[str] = []
    district_total = 0
    link_total = 0

    for region in REGION_ORDER:
        groups: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            if row["region"] == region:
                groups[row["district"]].append(row)

        districts: list[str] = []
        for district in sorted(groups):
            district_rows = sorted(
                groups[district], key=lambda item: item["display"]
            )
            links: list[str] = []
            for row in district_rows:
                href = f"../{row['folder']}/{slug}/"
                title = f"{row['display']} {label}"
                search_text = normalize(
                    f"{region} {district} {row['display']} {label}"
                )
                search_mapping[normalize(row["display"])] = href
                options.append(
                    f'<option value="{html.escape(row["display"], quote=True)}">'
                    f"{html.escape(region)} · {html.escape(district)}</option>"
                )
                links.append(
                    f'<a class="hub-link" '
                    f'data-search="{html.escape(search_text, quote=True)}" '
                    f'href="{html.escape(href, quote=True)}">'
                    f"<strong>{html.escape(title)}</strong>"
                    f"<small>{html.escape(note)}</small></a>"
                )
                link_total += 1
            districts.append(
                '<details class="category-district">'
                f"<summary><span>{html.escape(district)}</span>"
                f"<small>{len(district_rows)}개 동네</small></summary>"
                f'<div class="hub-links">{"".join(links)}</div></details>'
            )
            district_total += 1

        panels.append(
            f'<section id="category-{html.escape(region, quote=True)}" '
            f'class="category-region-panel" '
            f'data-region="{html.escape(region, quote=True)}">'
            f"<h2>{html.escape(region)} {html.escape(label)}</h2>"
            f'<div class="category-district-list">{"".join(districts)}</div>'
            "</section>"
        )

    tabs = [
        '<button class="category-region-tab" type="button" data-region="all" '
        'aria-pressed="true" aria-controls="categoryDirectory">전체</button>'
    ]
    tabs.extend(
        '<button class="category-region-tab" type="button" '
        f'data-region="{html.escape(region, quote=True)}" '
        'aria-pressed="false" aria-controls="categoryDirectory">'
        f"{html.escape(region)}</button>"
        for region in REGION_ORDER
    )

    input_id = f"categorySearch-{slug}"
    status_id = f"categorySearchStatus-{slug}"
    list_id = f"categoryLocalities-{slug}"
    block = f'''{BLOCK_START}
    <section class="local-section"><div class="wrap">
      <article class="center-search-card category-directory-tools" aria-label="{html.escape(label)} 지역 검색">
        <div class="center-search-head">
          <div><p class="eyebrow">LOCAL SEARCH</p><h2>동네명으로 {html.escape(label)} 찾기</h2><p>동네를 검색하거나 광역지역을 선택한 뒤 시·군·구 목록을 펼쳐 확인하세요.</p></div>
          <form class="center-search-form category-search-form">
            <label class="skip-link" for="{input_id}">동네명 검색</label>
            <input id="{input_id}" list="{list_id}" type="search" placeholder="예: 명일동, 화명동" autocomplete="off">
            <button type="submit">페이지 이동</button>
            <datalist id="{list_id}">{"".join(options)}</datalist>
          </form>
        </div>
        <div class="category-region-tabs" role="group" aria-label="광역지역 선택">{"".join(tabs)}</div>
        <p class="category-search-status" id="{status_id}" aria-live="polite">전체 371개 동네를 지역별로 확인할 수 있습니다.</p>
      </article>
    </div></section>
    <section class="local-section"><div class="wrap" id="categoryDirectory">
      <p class="eyebrow">LOCAL {html.escape(label.upper())}</p>
      <h2>지역별 {html.escape(label)} 바로가기</h2>
      {"".join(panels)}
    </div></section>
{BLOCK_END}'''

    script = f'''{SCRIPT_START}
  <script>
  (() => {{
    const normalize = (value) => value.normalize("NFKC").replace(/\\s+/g, "").toLowerCase();
    const pages = {json.dumps(search_mapping, ensure_ascii=False, separators=(",", ":"))};
    const form = document.querySelector(".category-search-form");
    const input = document.getElementById({json.dumps(input_id, ensure_ascii=False)});
    const status = document.getElementById({json.dumps(status_id, ensure_ascii=False)});
    const tabs = [...document.querySelectorAll(".category-region-tab")];
    const regions = [...document.querySelectorAll(".category-region-panel")];
    let selectedRegion = "all";

    const applyFilters = () => {{
      const query = normalize(input.value);
      let visibleLinks = 0;
      regions.forEach((region) => {{
        const regionAllowed = selectedRegion === "all" ||
          region.dataset.region === selectedRegion;
        let regionMatches = 0;
        region.querySelectorAll(".category-district").forEach((district) => {{
          let districtMatches = 0;
          district.querySelectorAll(".hub-link").forEach((link) => {{
            const matches = !query ||
              normalize(link.dataset.search || "").includes(query);
            link.classList.toggle("is-hidden", !matches);
            if (matches) districtMatches += 1;
          }});
          district.classList.toggle("is-hidden", !districtMatches);
          if (query && districtMatches) district.open = true;
          regionMatches += districtMatches;
        }});
        region.hidden = !regionAllowed || !regionMatches;
        if (!region.hidden) visibleLinks += regionMatches;
      }});
      status.textContent = query
        ? `${{visibleLinks}}개 동네가 검색되었습니다.`
        : selectedRegion === "all"
          ? "전체 371개 동네를 지역별로 확인할 수 있습니다."
          : `${{selectedRegion}} 지역 동네 목록입니다.`;
    }};

    tabs.forEach((tab) => {{
      tab.addEventListener("click", () => {{
        selectedRegion = tab.dataset.region || "all";
        tabs.forEach((item) => item.setAttribute(
          "aria-pressed", String(item === tab)
        ));
        applyFilters();
        document.getElementById("categoryDirectory").scrollIntoView({{
          block: "start",
          behavior: "smooth"
        }});
      }});
    }});
    input.addEventListener("input", applyFilters);
    form.addEventListener("submit", (event) => {{
      event.preventDefault();
      const key = normalize(input.value);
      if (pages[key]) {{
        window.location.href = pages[key];
        return;
      }}
      applyFilters();
      if (!key) {{
        status.textContent = "동네명을 입력하거나 지역을 선택해 주세요.";
      }}
    }});
  }})();
  </script>
{SCRIPT_END}'''
    return block, script, {
        "region_panels": len(panels),
        "district_details": district_total,
        "locality_links": link_total,
    }


def replace_navigation(original: str, block: str, script: str) -> str:
    if MARKED_BLOCK_RE.search(original):
        updated = MARKED_BLOCK_RE.sub("\n" + block + "\n", original, count=1)
    elif LEGACY_DIRECTORY_RE.search(original):
        updated = LEGACY_DIRECTORY_RE.sub(
            "\n" + block + "\n", original, count=1
        )
    else:
        raise ValueError("Legacy category directory or enhancement marker not found")

    updated = MARKED_SCRIPT_RE.sub("\n", updated)
    if "</body>" not in updated:
        raise ValueError("Closing body tag not found")
    updated = updated.replace("</body>", script + "\n</body>", 1)
    # Keep the refinement marker indentation stable so this post-processor
    # remains byte-idempotent when ``refine_national_content.py`` runs first.
    return re.sub(
        r"(?m)^[ \t]*<!-- hub-content-refinement:start -->",
        "  <!-- hub-content-refinement:start -->",
        updated,
        count=1,
    )


def build_plan(
    slug: str, rows: list[dict[str, str]]
) -> HubPlan:
    path = CENTER_ROOT / slug / "index.html"
    original = path.read_text(encoding="utf-8")
    block, script, counts = hub_markup(slug, rows)
    updated = replace_navigation(original, block, script)

    old_hrefs = set(HREF_RE.findall(original))
    new_hrefs = set(HREF_RE.findall(updated))
    expected = {
        f"../{row['folder']}/{slug}/"
        for row in rows
    }
    if new_hrefs != expected:
        missing = sorted(expected - new_hrefs)
        unexpected = sorted(new_hrefs - expected)
        raise ValueError(
            f"{slug}: destination mismatch "
            f"missing={missing[:3]} unexpected={unexpected[:3]}"
        )
    if old_hrefs and old_hrefs != expected:
        raise ValueError(
            f"{slug}: existing destination set is already inconsistent "
            f"old={len(old_hrefs)} expected={len(expected)}"
        )
    if counts["region_panels"] != len(REGION_ORDER):
        raise ValueError(f"{slug}: invalid region panel count")
    if counts["locality_links"] != len(rows):
        raise ValueError(f"{slug}: invalid locality link count")
    if original.split("<main", 1)[0] != updated.split("<main", 1)[0]:
        raise ValueError(f"{slug}: head metadata changed unexpectedly")

    return HubPlan(
        path=path,
        original=original,
        updated=updated,
        old_hrefs=old_hrefs,
        new_hrefs=new_hrefs,
        region_panels=counts["region_panels"],
        district_details=counts["district_details"],
        locality_links=counts["locality_links"],
    )


def main() -> None:
    args = parse_args()
    rows = load_manifest(ROOT)
    plans = [build_plan(slug, rows) for slug in CATEGORIES]

    if args.apply:
        for plan in plans:
            plan.path.write_text(plan.updated, encoding="utf-8", newline="\n")

    report = {
        "mode": "apply" if args.apply else "plan",
        "pages": len(plans),
        "pages_to_change": sum(
            plan.original != plan.updated for plan in plans
        ),
        "region_panels_per_page": sorted(
            {plan.region_panels for plan in plans}
        ),
        "district_details_per_page": sorted(
            {plan.district_details for plan in plans}
        ),
        "locality_links_per_page": sorted(
            {plan.locality_links for plan in plans}
        ),
        "destination_sets_preserved": all(
            not plan.old_hrefs or plan.old_hrefs == plan.new_hrefs
            for plan in plans
        ),
        "output_hashes": {
            plan.path.parent.name: hashlib.sha256(
                plan.updated.encode("utf-8")
            ).hexdigest()[:16]
            for plan in plans
        },
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
