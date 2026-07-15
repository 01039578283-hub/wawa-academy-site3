# -*- coding: utf-8 -*-
"""Third pass: touch the subject-methodology blocks without rewriting the
methodology itself.

관리 핵심 (process-list), keyword-focus-grid, and geo-checklist describe
*how a subject is taught*, not anything about the neighborhood - a wawa
teacher's approach to 초등 영어 문장 읽기 doesn't change between dongs, so
rewriting the substance per dong would just make the pedagogy less
accurate for cosmetic uniqueness. Instead, each item's existing (accurate)
description gets a small dong-anchored clause appended or prepended,
picked from a generic template bank. The teaching content itself is
untouched; only the surrounding sentence changes per page.
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from randomize_coaching_faq_reviews import stable_rng  # noqa: E402
from diversify_local_prose import category_meta  # noqa: E402

# {orig} = the existing, accurate description text (kept verbatim).
# Every template embeds {dong} so no item ever falls back to the bare,
# location-agnostic original text.
WRAP_TEMPLATES = [
    "{dong} 학생 상담에서는 {orig_lower}",
    "{dong}에서는 {orig_lower}",
    "{orig} {dong} 학생 기준으로 관리 강도를 조정합니다.",
    "{dong} 학생이라면 {orig_lower}",
    "{orig} {dong}에서도 같은 기준으로 확인합니다.",
    "{dong} 상담에서 {orig_lower}",
    "{dong} 학부모님께는 {orig_lower}",
    "{orig} {dong} 학생에게도 동일하게 적용합니다.",
]


def decap_first_word(text: str) -> str:
    # Korean has no case, but templates read better if the joined clause
    # doesn't repeat a redundant subject twice; this is a no-op placeholder
    # kept for symmetry with the "{orig_lower}" slot naming.
    return text


def wrap(orig: str, dong: str, template: str) -> str:
    return template.format(orig=orig, orig_lower=decap_first_word(orig), dong=dong)


PROCESS_LIST_BLOCK = re.compile(r'<ul class="process-list">.*?</ul>', re.S)
PROCESS_LIST_ITEM = re.compile(r'(<li><strong>.*?</strong>)(.*?)(</li>)', re.S)

KEYWORD_FOCUS_BLOCK = re.compile(r'<div class="keyword-focus-grid"[^>]*>.*?</div>', re.S)
KEYWORD_FOCUS_ITEM = re.compile(r'(<article>\s*<span>\d+</span>\s*<strong>.*?</strong>\s*<p>)(.*?)(</p>\s*</article>)', re.S)

GEO_CHECKLIST_BLOCK = re.compile(r'<div class="geo-checklist-grid">.*?</div>', re.S)
GEO_CHECKLIST_ITEM = re.compile(r'(<article class="geo-check-card"><b>\d+</b><strong>.*?</strong><p>)(.*?)(</p></article>)', re.S)


def process_block(text: str, block_pattern: re.Pattern, item_pattern: re.Pattern, dong: str, rng) -> str:
    block_match = block_pattern.search(text)
    if not block_match:
        return text
    block = block_match.group(0)

    n_items = len(item_pattern.findall(block))
    if n_items == 0:
        return text
    k = min(n_items, len(WRAP_TEMPLATES))
    templates = rng.sample(WRAP_TEMPLATES, k)
    while len(templates) < n_items:
        templates.append(rng.choice(WRAP_TEMPLATES))
    template_iter = iter(templates)

    def repl(m: re.Match) -> str:
        orig = html.unescape(m.group(2)).strip()
        new = html.escape(wrap(orig, dong, next(template_iter)))
        return m.group(1) + new + m.group(3)

    new_block = item_pattern.sub(repl, block)
    if new_block == block:
        return text
    return text[: block_match.start()] + new_block + text[block_match.end() :]


def update_page(path: Path, root: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    rel_parts = path.relative_to(root).parts
    _meta, is_leaf, _slug = category_meta(rel_parts)
    dong = rel_parts[1]

    rng = stable_rng(path, root)
    original = text

    text = process_block(text, PROCESS_LIST_BLOCK, PROCESS_LIST_ITEM, dong, rng)
    if is_leaf:
        text = process_block(text, KEYWORD_FOCUS_BLOCK, KEYWORD_FOCUS_ITEM, dong, rng)
    text = process_block(text, GEO_CHECKLIST_BLOCK, GEO_CHECKLIST_ITEM, dong, rng)

    if text != original:
        path.write_text(text, encoding="utf-8", newline="\n")
        return True
    return False


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    center_dir = root / "전국센터"
    pages = [p for p in sorted(center_dir.rglob("index.html")) if len(p.relative_to(root).parts) >= 3]

    updated = 0
    for path in pages:
        if update_page(path, root):
            updated += 1

    print(f"target pages: {len(pages)}")
    print(f"updated: {updated}")


if __name__ == "__main__":
    main()
