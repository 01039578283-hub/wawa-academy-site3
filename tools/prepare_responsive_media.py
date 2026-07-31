# -*- coding: utf-8 -*-
"""Prepare mobile body images and responsive ``picture`` markup.

The default mode is read-only and reports the exact number of assets/pages that
would change.  Pass ``--apply`` only after reviewing the plan.  This keeps the
bulk HTML operation explicit and repeatable.

Run this post-processor after any tool that regenerates complete local-page
HTML.  Tools that only replace text or image attributes can run afterward
without removing the surrounding ``picture`` element.

Examples
--------
    python tools/prepare_responsive_media.py
    python tools/prepare_responsive_media.py --write-assets
    python tools/prepare_responsive_media.py --apply
    python tools/prepare_responsive_media.py --apply --mobile-width 640 --quality 92
"""

from __future__ import annotations

import argparse
import io
import json
import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
CENTER_ROOT = ROOT / "전국센터"
COMMON = ROOT / "assets" / "centers" / "common"
STEMS = ("seoul", "local")

IMAGE_RE = re.compile(
    r"(?P<indent>^[ \t]*)(?P<tag><img\b[^>]*"
    r"\bsrc=[\"'][^\"']*/(?P<stem>seoul|local)-q92\.webp[\"'][^>]*>)",
    re.IGNORECASE | re.MULTILINE,
)
RESPONSIVE_PICTURE_RE = re.compile(
    r'<picture\b[^>]*class=["\'][^"\']*\blocal-responsive-picture\b[^"\']*["\'][^>]*>'
    r"(?:(?!</picture>).)*"
    r'<source\b[^>]*\bsrcset=["\'][^"\']*/(?:seoul|local)-mobile\.webp["\'][^>]*>'
    r"(?:(?!</picture>).)*"
    r'<img\b[^>]*\bsrc=["\'][^"\']*/(?:seoul|local)-q92\.webp["\'][^>]*>'
    r"(?:(?!</picture>).)*</picture>",
    re.IGNORECASE | re.DOTALL,
)


@dataclass
class PagePlan:
    path: Path
    candidates: int
    wrapped: int
    updated_text: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write the two mobile WebP assets and update matching HTML",
    )
    parser.add_argument(
        "--write-assets",
        action="store_true",
        help="write only the two mobile WebP assets; do not touch HTML",
    )
    parser.add_argument("--mobile-width", type=int, default=640)
    parser.add_argument("--quality", type=int, default=92)
    return parser.parse_args()


def inside_picture(text: str, position: int) -> bool:
    """Return True when ``position`` is already inside an open picture tag."""

    return text.rfind("<picture", 0, position) > text.rfind("</picture>", 0, position)


def plan_page(path: Path) -> PagePlan:
    original = path.read_text(encoding="utf-8")
    candidates = 0
    wrapped = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal candidates, wrapped
        candidates += 1
        if inside_picture(original, match.start()):
            return match.group(0)

        indent = match.group("indent")
        tag = match.group("tag")
        stem = match.group("stem").lower()
        src_match = re.search(r'\bsrc=(["\'])([^"\']+)\1', tag, re.IGNORECASE)
        if not src_match:
            return match.group(0)
        mobile_src = src_match.group(2).replace(
            f"{stem}-q92.webp", f"{stem}-mobile.webp"
        )
        wrapped += 1
        return (
            f'{indent}<picture class="local-responsive-picture">\n'
            f'{indent}  <source media="(max-width: 720px)" '
            f'type="image/webp" srcset="{mobile_src}">\n'
            f"{indent}  {tag}\n"
            f"{indent}</picture>"
        )

    updated = IMAGE_RE.sub(replace, original)
    return PagePlan(path=path, candidates=candidates, wrapped=wrapped, updated_text=updated)


def source_for(stem: str) -> Path:
    original = COMMON / f"{stem}.jpg"
    if original.is_file():
        return original
    fallback = COMMON / f"{stem}-q92.webp"
    if fallback.is_file():
        return fallback
    raise FileNotFoundError(f"No source image for {stem}: {original} / {fallback}")


def prepare_asset(
    stem: str, *, width: int, quality: int, apply: bool
) -> dict[str, int | str]:
    source = source_for(stem)
    target = COMMON / f"{stem}-mobile.webp"
    with Image.open(source) as image:
        source_width, source_height = image.size
        target_width = min(width, source_width)
        target_height = round(source_height * target_width / source_width)
        resized = image.resize(
            (target_width, target_height), Image.Resampling.LANCZOS
        )
        if resized.mode not in ("RGB", "RGBA"):
            resized = resized.convert("RGB")

        buffer = io.BytesIO()
        resized.save(buffer, "WEBP", quality=quality, method=6, exif=b"")
        payload = buffer.getvalue()
        if apply:
            target.write_bytes(payload)

    return {
        "stem": stem,
        "source": source.relative_to(ROOT).as_posix(),
        "target": target.relative_to(ROOT).as_posix(),
        "width": target_width,
        "height": target_height,
        "estimated_bytes": len(payload),
    }


def validate(applied_pages: list[Path]) -> dict[str, int]:
    q92_tags = 0
    responsive_pictures = 0
    missing_mobile_assets = 0
    for stem in STEMS:
        if not (COMMON / f"{stem}-mobile.webp").is_file():
            missing_mobile_assets += 1

    for path in applied_pages:
        text = path.read_text(encoding="utf-8")
        q92_tags += len(IMAGE_RE.findall(text))
        responsive_pictures += len(RESPONSIVE_PICTURE_RE.findall(text))

    if missing_mobile_assets:
        raise RuntimeError(f"missing_mobile_assets={missing_mobile_assets}")
    if q92_tags != responsive_pictures:
        raise RuntimeError(
            "Responsive picture validation failed: "
            f"q92_tags={q92_tags} pictures={responsive_pictures}"
        )
    return {
        "q92_tags": q92_tags,
        "responsive_pictures": responsive_pictures,
        "missing_mobile_assets": missing_mobile_assets,
    }


def main() -> None:
    args = parse_args()
    if args.mobile_width < 320:
        raise SystemExit("--mobile-width must be at least 320")
    if not 1 <= args.quality <= 100:
        raise SystemExit("--quality must be between 1 and 100")

    assets = [
        prepare_asset(
            stem,
            width=args.mobile_width,
            quality=args.quality,
            apply=args.apply or args.write_assets,
        )
        for stem in STEMS
    ]

    plans = [
        plan_page(path)
        for path in sorted(CENTER_ROOT.rglob("*.html"))
        if "-q92.webp" in path.read_text(encoding="utf-8")
    ]
    pages_to_change = [plan for plan in plans if plan.wrapped]

    if args.apply:
        for plan in pages_to_change:
            plan.path.write_text(plan.updated_text, encoding="utf-8", newline="\n")
        validation = validate([plan.path for plan in plans])
    else:
        validation = {
            "q92_tags_found": sum(plan.candidates for plan in plans),
            "already_wrapped": sum(
                len(RESPONSIVE_PICTURE_RE.findall(
                    plan.path.read_text(encoding="utf-8")
                ))
                for plan in plans
            ),
        }

    report = {
        "mode": (
            "apply"
            if args.apply
            else "write-assets"
            if args.write_assets
            else "plan"
        ),
        "assets": assets,
        "html_pages_scanned": len(plans),
        "html_pages_to_change": len(pages_to_change),
        "image_tags_to_wrap": sum(plan.wrapped for plan in plans),
        "validation": validation,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
