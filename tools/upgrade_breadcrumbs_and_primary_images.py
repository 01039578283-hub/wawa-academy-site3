# -*- coding: utf-8 -*-
"""Upgrade nationwide breadcrumbs and representative images reproducibly.

This tool is intentionally a dry run unless ``--write`` is supplied.

What it does
------------
* Makes the visible breadcrumb labels and BreadcrumbList names identical while
  preserving every existing breadcrumb URL and canonical URL.
* Replaces the externally hosted hidden representative image on every
  neighbourhood parent/child page with a local WebP generated from the shared
  representative-image source folder.
* Uses deterministic, group-aware assignment.  A neighbourhood parent and its
  children receive different images whenever the source pool is large enough.
* Keeps the hidden representative image as the first element immediately
  before the visible body image inside ``.local-media-section``.
* Synchronises the representative ``img`` alt text, ``og:image`` and
  ``ImageObject`` fields.
* Optionally updates JSON-LD ``dateModified`` and only the matching sitemap
  ``lastmod`` entries for pages whose semantic markup actually changed.

Typical use
-----------
Dry run (default):

    python tools/upgrade_breadcrumbs_and_primary_images.py

Apply after reviewing the dry-run summary:

    python tools/upgrade_breadcrumbs_and_primary_images.py --write \
        --lastmod 2026-07-31
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
NATIONWIDE_SLUG = "전국센터"
DOMAIN = "https://xn--sp5b72l1taf0p.com"
SITE_NAME = "코칭학원.com"
SUPPORTED_SOURCE_EXTENSIONS = {".gif", ".jpg", ".jpeg", ".png", ".webp"}

JSONLD_RE = re.compile(
    r'(<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>)(.*?)(</script>)',
    re.I | re.S,
)
CRUMBS_RE = re.compile(
    r'(?P<open><div\b[^>]*class=["\'][^"\']*\bcrumbs\b[^"\']*["\'][^>]*>)'
    r'(?P<body>.*?)'
    r'(?P<close></div>)',
    re.I | re.S,
)
SPAN_RE = re.compile(
    r'(?P<open><span\b[^>]*>)(?P<body>.*?)(?P<close></span>)',
    re.I | re.S,
)
REPRESENTATIVE_IMG_RE = re.compile(
    r'\s*<img\b(?=[^>]*\bdata-role=["\']representative-image["\'])[^>]*>',
    re.I,
)
MEDIA_OPEN_RE = re.compile(
    r'<(?:div|section|figure)\b[^>]*'
    r'class=["\'][^"\']*\blocal-media-section\b[^"\']*["\'][^>]*>',
    re.I,
)
IMG_RE = re.compile(r"<img\b[^>]*>", re.I)


@dataclass(frozen=True)
class SourceAsset:
    source: Path
    digest: str
    width: int
    height: int

    def output_name(self, quality: int) -> str:
        return f"primary-q{quality}-{self.digest}.webp"


@dataclass
class PagePlan:
    path: Path
    original: str
    updated: str
    canonical: str
    is_local: bool
    asset: SourceAsset | None
    semantic_changed: bool
    breadcrumb_changed: bool
    representative_changed: bool


def schema_types(node: object) -> set[str]:
    if not isinstance(node, dict):
        return set()
    value = node.get("@type", [])
    return set(value if isinstance(value, list) else [value])


def find_schema_node(graph: list[object], kind: str) -> dict:
    node = next(
        (
            candidate
            for candidate in graph
            if isinstance(candidate, dict) and kind in schema_types(candidate)
        ),
        None,
    )
    if node is None:
        raise ValueError(f"JSON-LD node missing: {kind}")
    return node


def clean_text(value: str) -> str:
    return " ".join(
        html.unescape(re.sub(r"<[^>]+>", " ", value, flags=re.S)).split()
    )


def read_single_match(text: str, pattern: str, label: str) -> str:
    matches = re.findall(pattern, text, re.I | re.S)
    if len(matches) != 1:
        raise ValueError(f"{label}: expected exactly one match, found {len(matches)}")
    value = matches[0]
    if isinstance(value, tuple):
        value = value[0]
    return html.unescape(value).strip()


def canonical_url(text: str) -> str:
    return read_single_match(
        text,
        r'<link\b(?=[^>]*rel=["\']canonical["\'])'
        r'[^>]*href=["\']([^"\']+)["\']',
        "canonical",
    )


def og_url(text: str) -> str:
    return read_single_match(
        text,
        r'<meta\b(?=[^>]*property=["\']og:url["\'])'
        r'[^>]*content=["\']([^"\']+)["\']',
        "og:url",
    )


def h1_text(text: str) -> str:
    return clean_text(
        read_single_match(text, r"<h1\b[^>]*>(.*?)</h1>", "H1")
    )


def title_text(text: str) -> str:
    return clean_text(read_single_match(text, r"<title>(.*?)</title>", "title"))


def load_jsonld(text: str) -> tuple[dict, re.Match[str]]:
    matches = list(JSONLD_RE.finditer(text))
    if len(matches) != 1:
        raise ValueError(
            f"application/ld+json: expected exactly one script, found {len(matches)}"
        )
    data = json.loads(matches[0].group(2))
    if not isinstance(data, dict) or not isinstance(data.get("@graph"), list):
        raise ValueError("JSON-LD must be an object containing an @graph array")
    return data, matches[0]


def serialize_jsonld(text: str, data: dict) -> str:
    match = next(iter(JSONLD_RE.finditer(text)), None)
    if match is None or next(JSONLD_RE.finditer(text, match.end()), None) is not None:
        raise ValueError("Expected one JSON-LD script while serialising")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return text[: match.start()] + match.group(1) + payload + match.group(3) + text[match.end() :]


def image_attribute(tag: str, name: str) -> str | None:
    match = re.search(
        rf"\b{re.escape(name)}\s*=\s*([\"'])(.*?)\1",
        tag,
        re.I | re.S,
    )
    return html.unescape(match.group(2)) if match else None


def set_tag_attribute(tag: str, name: str, value: str) -> str:
    escaped = html.escape(value, quote=True)
    pattern = re.compile(
        rf"(\b{re.escape(name)}\s*=\s*)([\"'])(.*?)\2",
        re.I | re.S,
    )
    if pattern.search(tag):
        return pattern.sub(
            lambda match: f'{match.group(1)}"{escaped}"',
            tag,
            count=1,
        )
    return tag[:-1] + f' {name}="{escaped}">'


def replace_meta_content(
    text: str,
    property_name: str,
    value: str,
    *,
    required: bool,
) -> tuple[str, bool]:
    pattern = re.compile(
        rf'<meta\b(?=[^>]*property=["\']{re.escape(property_name)}["\'])[^>]*>',
        re.I,
    )
    matches = list(pattern.finditer(text))
    if not matches:
        if required:
            raise ValueError(f"Missing meta property: {property_name}")
        return text, False
    if len(matches) != 1:
        raise ValueError(
            f"{property_name}: expected one meta tag, found {len(matches)}"
        )
    old_tag = matches[0].group(0)
    new_tag = set_tag_attribute(old_tag, "content", value)
    updated = text[: matches[0].start()] + new_tag + text[matches[0].end() :]
    return updated, new_tag != old_tag


def visible_breadcrumb_parts(block_body: str) -> tuple[list[str], list[str]]:
    names: list[str] = []
    hrefs: list[str] = []
    for span in SPAN_RE.finditer(block_body):
        inner = span.group("body")
        anchor = re.search(
            r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
            inner,
            re.I | re.S,
        )
        if anchor:
            hrefs.append(html.unescape(anchor.group(1)))
            names.append(clean_text(anchor.group(2)))
        else:
            names.append(clean_text(inner))
    return names, hrefs


def replace_visible_breadcrumb_labels(
    text: str,
    labels: list[str],
) -> tuple[str, bool, list[str]]:
    match = CRUMBS_RE.search(text)
    if match is None:
        raise ValueError("Visible .crumbs block missing")
    body = match.group("body")
    spans = list(SPAN_RE.finditer(body))
    if len(spans) != len(labels):
        raise ValueError(
            "Visible/schema breadcrumb length mismatch: "
            f"{len(spans)} != {len(labels)}"
        )
    _old_names, old_hrefs = visible_breadcrumb_parts(body)
    chunks: list[str] = []
    cursor = 0
    for index, span in enumerate(spans):
        chunks.append(body[cursor : span.start()])
        inner = span.group("body")
        escaped_label = html.escape(labels[index])
        anchor = re.search(
            r"(?P<open><a\b[^>]*>)(?P<label>.*?)(?P<close></a>)",
            inner,
            re.I | re.S,
        )
        if anchor:
            new_inner = (
                inner[: anchor.start()]
                + anchor.group("open")
                + escaped_label
                + anchor.group("close")
                + inner[anchor.end() :]
            )
        else:
            new_inner = escaped_label
        chunks.append(span.group("open") + new_inner + span.group("close"))
        cursor = span.end()
    chunks.append(body[cursor:])
    new_body = "".join(chunks)
    updated = (
        text[: match.start()]
        + match.group("open")
        + new_body
        + match.group("close")
        + text[match.end() :]
    )
    return updated, new_body != body, old_hrefs


def update_breadcrumb(
    text: str,
    graph: list[object],
) -> tuple[str, bool, list[str], list[str]]:
    breadcrumb = find_schema_node(graph, "BreadcrumbList")
    items = breadcrumb.get("itemListElement")
    if not isinstance(items, list) or not items:
        raise ValueError("BreadcrumbList.itemListElement is empty")
    if any(not isinstance(item, dict) for item in items):
        raise ValueError("BreadcrumbList entries must be objects")
    original_urls = [str(item.get("item", "")) for item in items]
    labels = [str(item.get("name", "")).strip() for item in items]
    if any(not label for label in labels):
        raise ValueError("BreadcrumbList contains an empty name")
    # Keep the user-facing convention while making schema and screen identical.
    labels[0] = "홈"
    schema_changed = False
    for item, label in zip(items, labels):
        if item.get("name") != label:
            item["name"] = label
            schema_changed = True
    text, visible_changed, original_hrefs = replace_visible_breadcrumb_labels(
        text,
        labels,
    )
    return text, schema_changed or visible_changed, original_urls, original_hrefs


def discover_source_assets(source_dir: Path) -> list[SourceAsset]:
    if not source_dir.is_dir():
        raise FileNotFoundError(f"Representative image folder missing: {source_dir}")
    unique: dict[str, SourceAsset] = {}
    for source in sorted(source_dir.iterdir(), key=lambda item: item.name.casefold()):
        if not source.is_file() or source.suffix.lower() not in SUPPORTED_SOURCE_EXTENSIONS:
            continue
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if digest in unique:
            continue
        with Image.open(source) as image:
            frame_count = getattr(image, "n_frames", 1)
            if frame_count != 1:
                raise ValueError(
                    f"Animated source is not converted silently: {source} "
                    f"({frame_count} frames)"
                )
            oriented = ImageOps.exif_transpose(image)
            width, height = oriented.size
        unique[digest] = SourceAsset(source, digest, width, height)
    assets = sorted(unique.values(), key=lambda item: item.digest)
    if not assets:
        raise ValueError(f"No supported representative images in {source_dir}")
    return assets


def discover_neighbourhood_groups(
    site_root: Path,
) -> list[tuple[Path, list[Path]]]:
    nationwide = site_root / NATIONWIDE_SLUG
    if not nationwide.is_dir():
        raise FileNotFoundError(f"Nationwide directory missing: {nationwide}")
    groups: list[tuple[Path, list[Path]]] = []
    for parent_index in sorted(nationwide.glob("*/index.html")):
        children = sorted(parent_index.parent.glob("*/index.html"))
        if children:
            groups.append((parent_index.parent, [parent_index, *children]))
    if not groups:
        raise ValueError("No neighbourhood parent/child groups detected")
    return groups


def assign_assets(
    groups: list[tuple[Path, list[Path]]],
    assets: list[SourceAsset],
    site_root: Path,
) -> dict[Path, SourceAsset]:
    assignments: dict[Path, SourceAsset] = {}
    for group_dir, pages in groups:
        if len(pages) > len(assets):
            raise ValueError(
                f"Not enough unique assets for {group_dir}: "
                f"{len(pages)} pages > {len(assets)} assets"
            )
        group_key = group_dir.relative_to(site_root).as_posix()
        ranked = sorted(
            assets,
            key=lambda asset: hashlib.sha256(
                f"{group_key}\0{asset.digest}".encode("utf-8")
            ).digest(),
            reverse=True,
        )
        chosen = ranked[: len(pages)]
        if len({asset.digest for asset in chosen}) != len(pages):
            raise AssertionError(f"Duplicate image inside group: {group_key}")
        for page, asset in zip(pages, chosen):
            if page in assignments:
                raise ValueError(f"Page assigned twice: {page}")
            assignments[page] = asset
    return assignments


def representative_urls(asset: SourceAsset, quality: int) -> tuple[str, str]:
    relative = f"/assets/representative/{asset.output_name(quality)}"
    return relative, urljoin(DOMAIN + "/", relative.lstrip("/"))


def insert_representative_image(
    text: str,
    *,
    relative_url: str,
    absolute_url: str,
    alt: str,
    width: int,
    height: int,
    graph: list[object],
) -> tuple[str, bool]:
    original = text
    text, removed = REPRESENTATIVE_IMG_RE.subn("", text)
    if removed > 1:
        raise ValueError(f"Expected at most one representative img, found {removed}")

    media_open = MEDIA_OPEN_RE.search(text)
    if media_open is None:
        raise ValueError(".local-media-section missing")
    visible_image = IMG_RE.search(text, media_open.end())
    if visible_image is None:
        raise ValueError("Visible body image missing after .local-media-section")
    closing = re.search(r"</(?:div|section|figure)>", text[media_open.end() :], re.I)
    if closing is not None:
        closing_position = media_open.end() + closing.start()
        if visible_image.start() > closing_position:
            raise ValueError(".local-media-section contains no body image")

    after_media_open = text[media_open.end() :]
    whitespace_match = re.match(r"\r?\n([ \t]*)", after_media_open)
    indentation = whitespace_match.group(1) if whitespace_match else "  "
    tag = (
        f'<img data-role="representative-image" '
        f'src="{html.escape(relative_url, quote=True)}" '
        f'alt="{html.escape(alt, quote=True)}" '
        f'style="display:none;" width="{width}" height="{height}" '
        f'decoding="async">'
    )
    text = (
        text[: media_open.end()]
        + "\n"
        + indentation
        + tag
        + text[media_open.end() :]
    )

    text, _ = replace_meta_content(
        text,
        "og:image",
        absolute_url,
        required=True,
    )
    text, _ = replace_meta_content(
        text,
        "twitter:image",
        absolute_url,
        required=False,
    )

    image_object = find_schema_node(graph, "ImageObject")
    original_schema_image = (
        image_object.get("contentUrl"),
        image_object.get("url"),
        image_object.get("caption"),
        image_object.get("width"),
        image_object.get("height"),
    )
    image_object["contentUrl"] = absolute_url
    image_object["url"] = absolute_url
    image_object["caption"] = alt
    image_object["width"] = width
    image_object["height"] = height
    updated_schema_image = (
        image_object.get("contentUrl"),
        image_object.get("url"),
        image_object.get("caption"),
        image_object.get("width"),
        image_object.get("height"),
    )
    return text, text != original or updated_schema_image != original_schema_image


def set_modified_date(graph: list[object], value: str) -> None:
    for node in graph:
        if not isinstance(node, dict):
            continue
        if schema_types(node) & {"WebPage", "CollectionPage", "Article"}:
            node["dateModified"] = value


def normalise_url(value: str, base: str = DOMAIN + "/") -> str:
    parsed = urlsplit(urljoin(base, html.unescape(value)))
    path = unquote(parsed.path).rstrip("/") + "/"
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def validate_page_plan(
    plan: PagePlan,
    quality: int,
    *,
    require_local_files: bool,
    asset_dir: Path,
) -> None:
    if canonical_url(plan.updated) != canonical_url(plan.original):
        raise ValueError(f"Canonical changed unexpectedly: {plan.path}")
    if og_url(plan.updated) != og_url(plan.original):
        raise ValueError(f"og:url changed unexpectedly: {plan.path}")

    data, _match = load_jsonld(plan.updated)
    graph = data["@graph"]
    breadcrumb = find_schema_node(graph, "BreadcrumbList")
    items = breadcrumb.get("itemListElement", [])
    schema_names = [str(item.get("name", "")).strip() for item in items]
    schema_urls = [str(item.get("item", "")) for item in items]
    visible_match = CRUMBS_RE.search(plan.updated)
    if visible_match is None:
        raise ValueError(f"Visible breadcrumb missing after update: {plan.path}")
    visible_names, _visible_hrefs = visible_breadcrumb_parts(
        visible_match.group("body")
    )
    if visible_names != schema_names:
        raise ValueError(
            f"Visible/schema breadcrumb labels differ after update: {plan.path}"
        )

    original_data, _ = load_jsonld(plan.original)
    original_breadcrumb = find_schema_node(original_data["@graph"], "BreadcrumbList")
    original_urls = [
        str(item.get("item", ""))
        for item in original_breadcrumb.get("itemListElement", [])
    ]
    if schema_urls != original_urls:
        raise ValueError(f"Breadcrumb URLs changed unexpectedly: {plan.path}")

    original_visible = CRUMBS_RE.search(plan.original)
    if original_visible is None:
        raise ValueError(f"Original visible breadcrumb missing: {plan.path}")
    _names, original_hrefs = visible_breadcrumb_parts(original_visible.group("body"))
    _names, updated_hrefs = visible_breadcrumb_parts(visible_match.group("body"))
    if updated_hrefs != original_hrefs:
        raise ValueError(f"Visible breadcrumb href changed: {plan.path}")

    if not plan.is_local:
        return
    if plan.asset is None:
        raise ValueError(f"Local page has no representative assignment: {plan.path}")
    expected_relative, expected_absolute = representative_urls(plan.asset, quality)
    expected_alt = f"{h1_text(plan.updated)} {SITE_NAME} 대표"
    if h1_text(plan.updated) not in title_text(plan.updated):
        raise ValueError(f"H1 is not represented in title: {plan.path}")

    tags = REPRESENTATIVE_IMG_RE.findall(plan.updated)
    if len(tags) != 1:
        raise ValueError(
            f"Expected one representative img after update: {plan.path} ({len(tags)})"
        )
    tag = tags[0].strip()
    if image_attribute(tag, "src") != expected_relative:
        raise ValueError(f"Representative src mismatch: {plan.path}")
    if image_attribute(tag, "alt") != expected_alt:
        raise ValueError(f"Representative alt mismatch: {plan.path}")
    if image_attribute(tag, "loading") is not None:
        raise ValueError(f"Representative loading must be omitted: {plan.path}")
    if image_attribute(tag, "decoding") != "async":
        raise ValueError(f"Representative decoding mismatch: {plan.path}")
    if "display:none" not in (image_attribute(tag, "style") or "").replace(" ", ""):
        raise ValueError(f"Representative image is not hidden: {plan.path}")
    if image_attribute(tag, "width") != str(plan.asset.width):
        raise ValueError(f"Representative width mismatch: {plan.path}")
    if image_attribute(tag, "height") != str(plan.asset.height):
        raise ValueError(f"Representative height mismatch: {plan.path}")

    media_open = MEDIA_OPEN_RE.search(plan.updated)
    if media_open is None:
        raise ValueError(f".local-media-section missing: {plan.path}")
    direct_first = re.match(
        r'\s*<img\b(?=[^>]*data-role=["\']representative-image["\'])[^>]*>',
        plan.updated[media_open.end() :],
        re.I | re.S,
    )
    if direct_first is None:
        raise ValueError(
            f"Representative image is not the first direct media child: {plan.path}"
        )
    first_two = list(IMG_RE.finditer(plan.updated, media_open.end()))[:2]
    if len(first_two) < 2:
        raise ValueError(f"Representative/body image pair incomplete: {plan.path}")
    if "data-role=\"representative-image\"" not in first_two[0].group(0):
        raise ValueError(
            f"Representative image is not the first media element: {plan.path}"
        )
    if "data-role=\"representative-image\"" in first_two[1].group(0):
        raise ValueError(f"Visible body image position is invalid: {plan.path}")

    og_image = read_single_match(
        plan.updated,
        r'<meta\b(?=[^>]*property=["\']og:image["\'])'
        r'[^>]*content=["\']([^"\']+)["\']',
        "og:image",
    )
    image_object = find_schema_node(graph, "ImageObject")
    if og_image != expected_absolute:
        raise ValueError(f"og:image mismatch: {plan.path}")
    if image_object.get("contentUrl") != expected_absolute:
        raise ValueError(f"ImageObject.contentUrl mismatch: {plan.path}")
    if image_object.get("url") != expected_absolute:
        raise ValueError(f"ImageObject.url mismatch: {plan.path}")
    if image_object.get("caption") != expected_alt:
        raise ValueError(f"ImageObject.caption mismatch: {plan.path}")
    if image_object.get("width") != plan.asset.width:
        raise ValueError(f"ImageObject.width mismatch: {plan.path}")
    if image_object.get("height") != plan.asset.height:
        raise ValueError(f"ImageObject.height mismatch: {plan.path}")
    if urlsplit(og_image).netloc != urlsplit(DOMAIN).netloc:
        raise ValueError(f"Representative image is still external: {plan.path}")
    if require_local_files:
        target = asset_dir / plan.asset.output_name(quality)
        if not target.is_file():
            raise ValueError(f"Local representative file missing: {target}")
        with Image.open(target) as image:
            if image.format != "WEBP":
                raise ValueError(f"Representative is not WebP: {target}")
            if image.size != (plan.asset.width, plan.asset.height):
                raise ValueError(f"Converted representative dimensions differ: {target}")


def transform_page(
    path: Path,
    *,
    asset: SourceAsset | None,
    quality: int,
    lastmod: str | None,
) -> PagePlan:
    original = path.read_text(encoding="utf-8")
    before_canonical = canonical_url(original)
    before_og_url = og_url(original)
    data, _ = load_jsonld(original)
    graph = data["@graph"]

    updated, breadcrumb_changed, _breadcrumb_urls, _visible_hrefs = update_breadcrumb(
        original,
        graph,
    )
    representative_changed = False
    if asset is not None:
        page_h1 = h1_text(updated)
        relative_url, absolute_url = representative_urls(asset, quality)
        updated, representative_changed = insert_representative_image(
            updated,
            relative_url=relative_url,
            absolute_url=absolute_url,
            alt=f"{page_h1} {SITE_NAME} 대표",
            width=asset.width,
            height=asset.height,
            graph=graph,
        )

    semantic_changed = breadcrumb_changed or representative_changed
    if lastmod is not None and semantic_changed:
        set_modified_date(graph, lastmod)
    updated = serialize_jsonld(updated, data)

    if canonical_url(updated) != before_canonical:
        raise ValueError(f"Canonical changed during transform: {path}")
    if og_url(updated) != before_og_url:
        raise ValueError(f"og:url changed during transform: {path}")
    return PagePlan(
        path=path,
        original=original,
        updated=updated,
        canonical=before_canonical,
        is_local=asset is not None,
        asset=asset,
        semantic_changed=semantic_changed,
        breadcrumb_changed=breadcrumb_changed,
        representative_changed=representative_changed,
    )


def convert_asset(asset: SourceAsset, target: Path, quality: int) -> bool:
    if target.is_file():
        with Image.open(target) as existing:
            if existing.format == "WEBP" and existing.size == (
                asset.width,
                asset.height,
            ):
                return False
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    with Image.open(asset.source) as source:
        if getattr(source, "n_frames", 1) != 1:
            raise ValueError(f"Animated source cannot be converted safely: {asset.source}")
        oriented = ImageOps.exif_transpose(source)
        has_alpha = (
            "A" in oriented.getbands()
            or "transparency" in oriented.info
            or oriented.mode in {"LA", "PA"}
        )
        converted = oriented.convert("RGBA" if has_alpha else "RGB")
        converted.save(
            temporary,
            "WEBP",
            quality=quality,
            method=6,
            exact=has_alpha,
            exif=b"",
        )
        converted.close()
    os.replace(temporary, target)
    return True


def update_sitemap_lastmod(
    sitemap_path: Path,
    changed_canonicals: set[str],
    lastmod: str,
) -> int:
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", namespace)
    tree = ET.parse(sitemap_path)
    root = tree.getroot()
    touched = 0
    found: set[str] = set()
    for node in root.findall(f"{{{namespace}}}url"):
        loc_node = node.find(f"{{{namespace}}}loc")
        if loc_node is None or not loc_node.text:
            continue
        canonical = html.unescape(loc_node.text.strip())
        if canonical not in changed_canonicals:
            continue
        found.add(canonical)
        lastmod_node = node.find(f"{{{namespace}}}lastmod")
        if lastmod_node is None:
            lastmod_node = ET.SubElement(node, f"{{{namespace}}}lastmod")
        if lastmod_node.text != lastmod:
            lastmod_node.text = lastmod
            touched += 1
    missing = changed_canonicals - found
    if missing:
        sample = "\n".join(sorted(missing)[:10])
        raise ValueError(f"Changed canonical missing from sitemap:\n{sample}")
    ET.indent(tree, space="  ")
    tree.write(
        sitemap_path,
        encoding="utf-8",
        xml_declaration=True,
        short_empty_elements=False,
    )
    return touched


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="Apply the validated plan. Without this flag the tool is read-only.",
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=ROOT.parent / "참고자료" / "공통자료" / "대표이미지",
        help="Shared representative-image source directory.",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=90,
        help="Lossy WebP quality (default: 90).",
    )
    parser.add_argument(
        "--lastmod",
        help=(
            "Optional YYYY-MM-DD value. It is applied only to pages whose "
            "breadcrumb/image markup changed and to their sitemap entries."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not 1 <= args.quality <= 100:
        raise ValueError("--quality must be between 1 and 100")
    if args.lastmod is not None:
        date.fromisoformat(args.lastmod)

    source_dir = args.source_dir.resolve()
    asset_dir = ROOT / "assets" / "representative"
    assets = discover_source_assets(source_dir)
    groups = discover_neighbourhood_groups(ROOT)
    assignments = assign_assets(groups, assets, ROOT)
    nationwide_pages = sorted((ROOT / NATIONWIDE_SLUG).rglob("index.html"))
    if set(assignments) - set(nationwide_pages):
        raise ValueError("A local page falls outside the nationwide page set")

    plans: list[PagePlan] = []
    for page in nationwide_pages:
        plan = transform_page(
            page,
            asset=assignments.get(page),
            quality=args.quality,
            lastmod=args.lastmod,
        )
        validate_page_plan(
            plan,
            args.quality,
            require_local_files=False,
            asset_dir=asset_dir,
        )
        plans.append(plan)

    local_plans = [plan for plan in plans if plan.is_local]
    if len(local_plans) != len(assignments):
        raise ValueError("Local-page plan count does not match assignments")
    for _group, pages in groups:
        group_digests = [assignments[page].digest for page in pages]
        if len(group_digests) != len(set(group_digests)):
            raise ValueError(f"Representative collision inside group: {_group}")
    selected_assets = {
        plan.asset
        for plan in local_plans
        if plan.asset is not None
    }
    changed_plans = [plan for plan in plans if plan.updated != plan.original]
    external_representatives = sum(
        1
        for plan in local_plans
        if urlsplit(
            read_single_match(
                plan.updated,
                r'<img\b(?=[^>]*data-role=["\']representative-image["\'])'
                r'[^>]*src=["\']([^"\']+)["\']',
                "representative src",
            )
        ).netloc
    )
    if external_representatives:
        raise ValueError(
            f"External representative URLs remain: {external_representatives}"
        )

    converted = 0
    sitemap_touched = 0
    if args.write:
        for asset in sorted(selected_assets, key=lambda item: item.digest):
            target = asset_dir / asset.output_name(args.quality)
            converted += int(convert_asset(asset, target, args.quality))
        for plan in changed_plans:
            plan.path.write_text(
                plan.updated,
                encoding="utf-8",
                newline="\n",
            )
        if args.lastmod is not None:
            changed_canonicals = {
                plan.canonical
                for plan in changed_plans
                if plan.semantic_changed
            }
            sitemap_touched = update_sitemap_lastmod(
                ROOT / "sitemap.xml",
                changed_canonicals,
                args.lastmod,
            )
        for plan in plans:
            on_disk = PagePlan(
                path=plan.path,
                original=plan.original,
                updated=plan.path.read_text(encoding="utf-8"),
                canonical=plan.canonical,
                is_local=plan.is_local,
                asset=plan.asset,
                semantic_changed=plan.semantic_changed,
                breadcrumb_changed=plan.breadcrumb_changed,
                representative_changed=plan.representative_changed,
            )
            validate_page_plan(
                on_disk,
                args.quality,
                require_local_files=plan.is_local,
                asset_dir=asset_dir,
            )

    print(
        json.dumps(
            {
                "mode": "write" if args.write else "dry-run",
                "nationwide_pages": len(nationwide_pages),
                "neighbourhood_groups": len(groups),
                "local_parent_child_pages": len(local_plans),
                "source_assets_unique": len(assets),
                "selected_assets_unique": len(selected_assets),
                "same_neighbourhood_image_collisions": 0,
                "planned_changed_pages": len(changed_plans),
                "breadcrumb_changed_pages": sum(
                    plan.breadcrumb_changed for plan in plans
                ),
                "representative_changed_pages": sum(
                    plan.representative_changed for plan in local_plans
                ),
                "external_representative_urls_after_plan": 0,
                "converted_assets": converted,
                "sitemap_lastmod_entries_touched": sitemap_touched,
                "webp_quality": args.quality,
                "lastmod": args.lastmod,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not args.write:
        print("No files changed. Re-run with --write after reviewing this plan.")


if __name__ == "__main__":
    main()
