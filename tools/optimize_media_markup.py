# -*- coding: utf-8 -*-
"""Optimize local image delivery without changing visible copy or alt text."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
COMMON = ROOT / "assets" / "centers" / "common"


def build_common_webp() -> None:
    for stem in ("seoul", "local"):
        source = COMMON / f"{stem}.jpg"
        target = COMMON / f"{stem}-q92.webp"
        with Image.open(source) as image:
            image.save(target, "WEBP", quality=92, method=6, exif=b"")


def local_image_path(page: Path, src: str) -> Path | None:
    parsed = urlsplit(src)
    if parsed.scheme or parsed.netloc or src.startswith("//") or src.startswith("data:"):
        return None
    candidate = (page.parent / unquote(parsed.path)).resolve()
    try:
        candidate.relative_to(ROOT.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def add_attribute(tag: str, name: str, value: str) -> str:
    if re.search(rf"\s{name}\s*=", tag, re.I):
        return tag
    return tag[:-1] + f' {name}="{value}">'


def optimize_tag(page: Path, tag: str, dimensions: dict[Path, tuple[int, int]]) -> str:
    src_match = re.search(r'\bsrc=["\']([^"\']+)', tag, re.I)
    if not src_match:
        return tag
    src = src_match.group(1)
    if "data-role=\"representative-image\"" in tag or "data-role='representative-image'" in tag:
        tag = add_attribute(tag, "fetchpriority", "low")
        return add_attribute(tag, "decoding", "async")
    asset = local_image_path(page, src)
    if asset is None:
        return tag
    if asset not in dimensions:
        with Image.open(asset) as image:
            dimensions[asset] = image.size
    width, height = dimensions[asset]
    tag = add_attribute(tag, "width", str(width))
    tag = add_attribute(tag, "height", str(height))
    tag = add_attribute(tag, "decoding", "async")
    if page == ROOT / "index.html" and "site3-hero.webp" in src:
        tag = add_attribute(tag, "fetchpriority", "high")
    return tag


def main() -> None:
    build_common_webp()
    dimensions: dict[Path, tuple[int, int]] = {}
    changed = 0
    image_tags = 0
    unresolved: list[str] = []
    for page in sorted(ROOT.rglob("*.html")):
        text = page.read_text(encoding="utf-8")
        text = text.replace("/assets/centers/common/seoul.jpg", "/assets/centers/common/seoul-q92.webp")
        text = text.replace("/assets/centers/common/local.jpg", "/assets/centers/common/local-q92.webp")
        text = text.replace("assets/centers/common/seoul.jpg", "assets/centers/common/seoul-q92.webp")
        text = text.replace("assets/centers/common/local.jpg", "assets/centers/common/local-q92.webp")

        def replace(match: re.Match[str]) -> str:
            nonlocal image_tags
            image_tags += 1
            return optimize_tag(page, match.group(0), dimensions)

        updated = re.sub(r"<img\b[^>]*>", replace, text, flags=re.I)
        for tag in re.findall(r"<img\b[^>]*>", updated, flags=re.I):
            src_match = re.search(r'\bsrc=["\']([^"\']+)', tag, re.I)
            if src_match and not src_match.group(1).startswith(("http://", "https://", "//", "data:")):
                if local_image_path(page, src_match.group(1)) is None:
                    unresolved.append(f"{page.relative_to(ROOT).as_posix()} :: {src_match.group(1)}")
        if updated != page.read_text(encoding="utf-8"):
            page.write_text(updated, encoding="utf-8", newline="\n")
            changed += 1
    if unresolved:
        raise SystemExit("Unresolved local images:\n" + "\n".join(unresolved[:20]))
    print(
        f"pages_changed={changed} image_tags={image_tags} "
        f"sized_assets={len(dimensions)} unresolved={len(unresolved)}"
    )


if __name__ == "__main__":
    main()
