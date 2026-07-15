# -*- coding: utf-8 -*-
"""Reduce cross-dong text similarity on 전국센터 pages.

The core problem: every dong+category combination reuses the exact same
prose (only the dong name substituted) for the intro paragraphs, school/
location notes, and SEO-GEO lead paragraphs. Subject-specific teaching
content (the 4-item "관리 핵심" list, keyword-focus grid) is left alone
since it's genuinely different per category and not location-driven.

This rotates the location-facing sentences through a template bank keyed
by each page's own path (stable_rng from randomize_coaching_faq_reviews),
so the same sentence no longer repeats identically across all 371 dongs.
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from randomize_coaching_faq_reviews import sentence, stable_rng  # noqa: E402

CATEGORY_META = {
    "초등영어학원": {"grade": "초등", "subject": "영어", "focus": "단어·문장·독해"},
    "초등수학학원": {"grade": "초등", "subject": "수학", "focus": "개념·연산·문장제"},
    "중등영어학원": {"grade": "중등", "subject": "영어", "focus": "문법·독해·서술형"},
    "중등수학학원": {"grade": "중등", "subject": "수학", "focus": "개념·유형·서술형"},
    "고등영어학원": {"grade": "고등", "subject": "영어", "focus": "내신·모의고사 독해"},
    "고등수학학원": {"grade": "고등", "subject": "수학", "focus": "내신·수능형 문제"},
}
HUB_META = {"grade": "초등·중등·고등", "subject": "영어·수학", "focus": "진단·플래너·오답 관리"}

CARD_P1 = [
    "{dong}에서 {grade} {subject} 학원을 고를 때는 과목명보다 학생이 지금 어느 부분에서 막히는지를 먼저 확인하는 것이 중요합니다.",
    "{dong} 학원 상담에서는 위치나 시간표보다 학생의 현재 이해도와 학교 진도가 맞는지를 먼저 살펴봐야 합니다.",
    "{dong}에서 {subject} 학습을 맡기기 전에는 아이가 어떤 유형에서 자주 막히는지부터 짚어보는 것이 순서입니다.",
    "{dong} 학생의 {grade} {subject} 관리는 진도를 서두르기보다 현재 빈틈을 먼저 찾는 데서 시작합니다.",
    "{dong}에서 학원을 비교할 때는 광고 문구보다 상담 단계에서 무엇을 확인하는지를 보는 것이 더 정확합니다.",
    "{dong} 학부모님이 학원을 정할 때 가장 먼저 볼 부분은 학생의 현재 수준을 어떻게 진단하는가입니다.",
    "{dong}에서 {grade} {subject} 공부를 다시 잡으려면 무엇을 더 시키기보다 어디가 비어 있는지부터 확인해야 합니다.",
]

CARD_P2 = [
    "와와학습코칭학원은 {dong} 학생의 현재 성취도와 과제 습관, 오답 패턴을 함께 확인하고 {focus} 흐름을 현실적으로 정리합니다.",
    "{dong} 지점에서는 상담 단계부터 학생의 학교 진도와 시험 일정을 함께 살펴 {focus} 계획을 구체적으로 세웁니다.",
    "와와학습코칭학원은 {dong} 학생이 실제로 실행할 수 있는 분량인지를 기준으로 {focus} 계획을 조정합니다.",
    "{dong}에서는 학생별 학습 습관과 시험 대비 루틴을 확인한 뒤 {focus} 순서를 학생에게 맞춰 정리합니다.",
    "와와학습코칭학원 {dong} 지점은 상담에서 확인한 내용을 바탕으로 무리하지 않는 {focus} 계획을 안내합니다.",
    "{dong} 학생은 상담 이후 현재 교재와 오답 기록을 함께 확인해 {focus} 순서를 다시 조정하는 방식으로 관리합니다.",
]

SCHOOL_P = [
    "위 학교 외에도 {dong} 인근 {grade} 학생 상담이 가능하며, 실제 수업 가능 여부는 학년과 시간표에 따라 다르게 안내합니다.",
    "{dong} 인근 다른 학교 학생도 상담이 가능하니, 정확한 시간은 문의 시 학년에 맞춰 확인해 드립니다.",
    "표에 없는 학교라도 {dong} 인근이라면 상담이 가능하며, 수업 가능 시간은 학생 학년에 따라 달라질 수 있습니다.",
    "{dong} 주변 다른 학교 학생도 문의 가능하며, 실제 수업 여부는 학년별 시간표를 확인한 뒤 안내해 드립니다.",
    "위 목록 외 학교여도 {dong} 인근이면 상담을 받을 수 있고, 개설 여부는 학년과 시간대에 따라 다릅니다.",
]

LOCATION_P2 = [
    "방문 전 상담 가능 시간과 수업 개설 여부를 먼저 확인하시면 더 정확하게 안내받을 수 있습니다.",
    "직접 방문하시기 전에 전화나 온라인으로 상담 시간을 먼저 맞춰보시는 것을 권해 드립니다.",
    "센터 방문 전에는 학생 학년에 맞는 수업 시간이 있는지 먼저 확인해 주시면 좋습니다.",
    "상담을 위해 방문하실 때는 원하는 시간대에 자리가 있는지 미리 문의해 주시면 안내가 빠릅니다.",
    "방문 전 전화나 문자로 상담 가능 시간을 확인하시면 대기 없이 안내받으실 수 있습니다.",
]

GEO_SUMMARY_LEAD_HUB = [
    "{dong} 학원 페이지는 {dong}에서 영어·수학 학습코칭 상담을 준비하는 학생과 학부모가 진단, 계획, 실행 확인, 오답 재학습 흐름을 한 번에 이해할 수 있도록 정리했습니다.",
    "이 페이지는 {dong}에서 학습 관리 상담을 알아보는 학부모가 진단부터 오답 재학습까지의 흐름을 한 번에 확인할 수 있도록 정리했습니다.",
    "{dong} 학원을 비교하는 학부모가 상담 전 확인할 진단·계획·오답 관리 흐름을 이 페이지에 정리했습니다.",
    "{dong}에서 학습 상담을 준비 중인 학부모를 위해, 진단부터 피드백까지 이어지는 관리 흐름을 이 페이지에 요약했습니다.",
]

GEO_SUMMARY_LEAD_LEAF = [
    "{title} 페이지는 {dong}에서 {grade} {subject} 학습코칭 상담을 준비하는 학생과 학부모가 진단, 계획, 실행 확인, 오답 재학습 흐름을 한 번에 이해할 수 있도록 정리했습니다.",
    "이 페이지는 {dong}에서 {grade} {subject} 상담을 알아보는 학부모가 진단부터 오답 재학습까지의 흐름을 한 번에 확인할 수 있도록 정리했습니다.",
    "{title}을 비교하는 학부모가 상담 전 확인할 진단·계획·오답 관리 흐름을 이 페이지에 정리했습니다.",
    "{dong}에서 {grade} {subject} 상담을 준비 중인 학부모를 위해, 진단부터 피드백까지 이어지는 관리 흐름을 이 페이지에 요약했습니다.",
]

KEYWORD_FOCUS_P1 = [
    "{dong}에서 {grade} {subject}학원을 찾는다면 단순히 가까운 위치만 볼 것이 아니라 학생의 현재 수준, 학교 진도, 숙제 습관, 시험 준비 흐름까지 함께 확인하는 것이 좋습니다.",
    "{dong}에서 {subject}학원을 비교하실 때는 거리보다 학생의 현재 이해도와 진도, 오답 관리 방식을 먼저 살펴보시길 권합니다.",
    "{dong} {grade} {subject}학원을 알아보실 때는 위치보다 상담에서 무엇을 확인하는지, 관리 방식이 어떤지를 먼저 보는 것이 좋습니다.",
    "{dong} 학부모님이 상담을 예약하신다면 학생의 현재 수준과 학교 진도, 평소 공부 습관을 먼저 정리해 두시는 것이 좋습니다.",
    "{dong} 학부모님이 {subject}학원을 고르실 때는 시설보다 학생별 진단과 관리 흐름을 먼저 비교해 보시길 권합니다.",
]

GEO_ANSWER_LEAD = [
    "{dong}에서 학원을 알아볼 때는 위치만 보기보다 학생의 현재 과목별 상태, 학교 진도, 혼자 공부하는 시간, 오답 관리 방식까지 함께 확인하는 것이 좋습니다.",
    "{dong}에서 {subject} 학원을 정할 때는 이동 거리보다 학생에게 필요한 관리 강도와 피드백 방식을 먼저 비교하는 것이 좋습니다.",
    "{dong} 학원 상담 전에는 현재 성적표보다 학생이 자주 막히는 지점과 공부 습관을 먼저 정리해 두는 것이 도움이 됩니다.",
    "{dong}에서 학습 관리를 알아보실 때는 수업 횟수보다 진단 이후 관리가 어떻게 이어지는지를 먼저 확인하시길 권합니다.",
]


def category_meta(rel_parts: tuple[str, ...]) -> tuple[dict[str, str], bool, str]:
    if len(rel_parts) >= 4 and rel_parts[2] in CATEGORY_META:
        return CATEGORY_META[rel_parts[2]], True, rel_parts[2]
    return HUB_META, False, ""


def get_h1(text: str) -> str:
    m = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.S)
    return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""


def replace_group(text: str, pattern: re.Pattern, build) -> str:
    m = pattern.search(text)
    if not m:
        return text
    return text[: m.start()] + build(m) + text[m.end() :]


CARD_PATTERN = re.compile(
    r'(<article class="local-card">\s*<h2>.*?</h2>\s*<p>).*?(</p>\s*<p>).*?(</p>\s*<h3>)', re.S
)
SCHOOL_PATTERN = re.compile(
    r'(<div class="wrap school-card">\s*<h2>.*?</h2>\s*<p>).*?(</p>\s*<div class=")', re.S
)
LOCATION_PATTERN = re.compile(
    r'(<div class="location-copy">\s*<h2>.*?</h2>\s*<p>.*?</p>\s*<p>).*?(</p>\s*</div>)', re.S
)
GEO_SUMMARY_PATTERN = re.compile(
    r'(<article id="geo-summary" class="geo-summary-panel">\s*<p class="eyebrow">.*?</p>\s*<h2>.*?</h2>\s*<p>).*?(</p>\s*<div class="geo-fact-grid">)',
    re.S,
)
GEO_ANSWER_PATTERN = re.compile(
    r'(<article id="geo-answer" class="geo-answer-panel">\s*<p class="eyebrow">.*?</p>\s*<h2>.*?</h2>\s*<p>).*?(</p>\s*<div class="geo-answer-grid">)',
    re.S,
)
KEYWORD_FOCUS_PATTERN = re.compile(
    r'(<div class="keyword-focus-copy">\s*<p class="eyebrow">.*?</p>\s*<h2>.*?</h2>\s*<p>).*?(</p>\s*<p>)', re.S
)


def update_page(path: Path, root: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    rel_parts = path.relative_to(root).parts
    meta, is_leaf, _slug = category_meta(rel_parts)
    dong = rel_parts[1]
    title = get_h1(text) or dong
    ctx = {"dong": dong, "title": title, **meta}

    rng = stable_rng(path, root)
    original = text

    text = replace_group(text, CARD_PATTERN, lambda m: m.group(1) + html.escape(sentence(rng.choice(CARD_P1).format(**ctx))) + m.group(2) + html.escape(sentence(rng.choice(CARD_P2).format(**ctx))) + m.group(3))
    text = replace_group(text, SCHOOL_PATTERN, lambda m: m.group(1) + html.escape(sentence(rng.choice(SCHOOL_P).format(**ctx))) + m.group(2))
    text = replace_group(text, LOCATION_PATTERN, lambda m: m.group(1) + html.escape(sentence(rng.choice(LOCATION_P2).format(**ctx))) + m.group(2))

    summary_bank = GEO_SUMMARY_LEAD_LEAF if is_leaf else GEO_SUMMARY_LEAD_HUB
    text = replace_group(text, GEO_SUMMARY_PATTERN, lambda m: m.group(1) + html.escape(sentence(rng.choice(summary_bank).format(**ctx))) + m.group(2))
    text = replace_group(text, GEO_ANSWER_PATTERN, lambda m: m.group(1) + html.escape(sentence(rng.choice(GEO_ANSWER_LEAD).format(**ctx))) + m.group(2))
    if is_leaf:
        text = replace_group(text, KEYWORD_FOCUS_PATTERN, lambda m: m.group(1) + html.escape(sentence(rng.choice(KEYWORD_FOCUS_P1).format(**ctx))) + m.group(2))

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
