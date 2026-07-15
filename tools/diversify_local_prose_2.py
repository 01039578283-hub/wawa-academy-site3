# -*- coding: utf-8 -*-
"""Second pass: hero lead paragraph, geo-answer's 4 generic cards, the
geo-summary "추천 학생" fact card, and the 상담 요약 bullet list.

These were the next-largest fully-static blocks left after
diversify_local_prose.py's first pass (which handled the two local-card
intro paragraphs, school/location notes, and the geo-summary/geo-answer
LEAD paragraphs). The 관리 핵심 list, keyword-focus grid, and geo-checklist
are deliberately left untouched: they're genuine subject-methodology
content that should read the same regardless of neighborhood.
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from randomize_coaching_faq_reviews import sentence, stable_rng  # noqa: E402
from diversify_local_prose import CATEGORY_META, HUB_META, category_meta, get_h1  # noqa: E402

HERO_LEAD_HUB = [
    "{dong}에서 학원을 찾는 학부모님께, 단순히 가까운 학원 목록이 아니라 아이의 현재 공부 흐름을 기준으로 상담할 수 있는 학습관리 방향을 정리했습니다.",
    "{dong} 학부모님을 위해 위치보다 학생의 현재 상태를 먼저 확인할 수 있는 학습관리 상담 기준을 정리했습니다.",
    "{dong}에서 학원을 알아보실 때 참고할 수 있도록, 상담 전 확인하면 좋은 진단·계획·오답 관리 기준을 정리했습니다.",
    "이 페이지는 {dong}에서 아이의 학습 흐름을 기준으로 학원을 비교하고 싶은 학부모님을 위해 정리했습니다.",
    "{dong} 학원을 찾는 학부모님이 상담 전에 확인하면 좋은 진단·플래너·오답 관리 기준을 여기에 정리했습니다.",
    "단순한 학원 목록이 아니라, {dong} 학생에게 필요한 학습관리 방향을 확인할 수 있도록 이 페이지를 정리했습니다.",
    "{dong}에서 아이 학습 방향을 다시 잡고 싶은 학부모님을 위해 상담 전 확인 기준을 정리했습니다.",
    "{dong} 학원 상담을 고민 중이시라면, 이 페이지에서 진단부터 오답 관리까지 이어지는 흐름을 먼저 확인해 보세요.",
]

HERO_LEAD_LEAF = [
    "{dong}에서 {grade} {subject}학원을 찾는다면, {focus} 중 아이가 어디에서 막히는지 먼저 확인하는 것이 중요합니다.",
    "{dong}에서 {grade} {subject} 공부를 다시 잡고 싶다면, {focus}를 나눠서 확인하는 것부터 시작해야 합니다.",
    "{dong} {grade} {subject}학원을 비교하신다면, {focus} 중 어디가 비어 있는지 먼저 확인하시는 것을 권합니다.",
    "이 페이지는 {dong}에서 {grade} {subject} 학습을 맡길 곳을 찾는 학부모님을 위해 {focus} 확인 기준을 정리했습니다.",
    "{dong}에서 {subject}학원을 알아보실 때는 {focus} 중 아이의 약한 지점을 먼저 짚어보는 것이 순서입니다.",
    "{dong} 학생의 {grade} {subject}는 {focus}를 따로 보지 않고 이어서 확인해야 변화가 보입니다.",
    "{dong}에서 {grade} {subject} 학원을 정하기 전에, {focus} 흐름이 실제로 이어지는지부터 확인해 보시길 권합니다.",
    "{dong} {subject}학원을 찾는 학부모님이 가장 먼저 볼 부분은 {focus} 중 아이가 반복해서 틀리는 지점입니다.",
]

GEO_RECOMMEND_STRONG = [
    "{dong}에서 {grade} {subject} 학습코칭으로 현재 수준 진단과 오답 재학습을 함께 관리하고 싶은 학생",
    "{dong} 학생 중 {grade} {subject} 성적이 오르지 않아 진단부터 다시 받아보고 싶은 학생",
    "{dong}에서 {grade} {subject} 공부 습관과 오답 관리를 함께 잡고 싶은 학생",
    "{dong}에서 학원을 옮기기 전 {grade} {subject} 학습 상태를 정확히 진단받고 싶은 학생",
    "{dong} 학생 중 {grade} {subject}에서 같은 유형의 오답이 반복되는 학생",
    "{dong}에서 {grade} {subject} 학습 계획을 세워도 실행이 잘 이어지지 않는 학생",
    "{dong} 학생 중 {grade} {subject} 기초부터 다시 점검받고 싶은 학생",
]

GEO_RECOMMEND_STRONG_HUB = [
    "{dong}에서 과목별 우선순위와 주간 학습 루틴을 함께 정리하고 싶은 학생",
    "{dong} 학생 중 영어·수학 학습 계획을 세워도 실행이 잘 이어지지 않는 학생",
    "{dong}에서 과목마다 학습 방식을 다르게 관리받고 싶은 학생",
    "{dong}에서 학원을 옮기기 전 현재 학습 상태를 정확히 진단받고 싶은 학생",
    "{dong} 학생 중 숙제와 오답 관리를 한 흐름으로 이어가고 싶은 학생",
    "{dong}에서 학습 습관과 진도 관리를 함께 잡고 싶은 학생",
    "{dong} 학생 중 상담부터 다시 받아 관리 방향을 새로 잡고 싶은 학생",
]

GEO_RECOMMEND_P = [
    "{dong} 상담 전 현재 교재, 최근 시험지, 자주 틀리는 유형을 준비하면 더 정확합니다.",
    "{dong}에서 상담받으실 때는 최근 시험지와 오답노트를 함께 가져오시면 더 구체적으로 진행됩니다.",
    "{dong} 학생이라면 현재 사용 중인 교재와 최근 성적을 준비해 오시면 진단이 더 정확해집니다.",
    "{dong} 상담 전 자주 틀리는 문제 유형과 평소 공부 시간을 미리 정리해 오시면 좋습니다.",
    "{dong}에서 상담을 예약하신다면 최근 시험 범위와 결과를 함께 확인할 자료를 준비해 주세요.",
    "{dong} 학생의 상담에서는 최근 숙제 수행 정도와 시험 범위를 함께 확인하면 좋습니다.",
]

GEO_ANSWER_P1 = [
    "{dong} 학생의 현재 과목별 수준, 공부 습관, 오답이 반복되는 지점을 먼저 확인합니다.",
    "{dong} 학생의 최근 시험 결과와 평소 공부 습관, 자주 틀리는 유형을 먼저 살펴봅니다.",
    "{dong}에서는 현재 학교 진도와 학생의 이해도, 반복되는 오답 지점을 가장 먼저 확인합니다.",
    "{dong}에서 상담을 받으면 학생의 과목별 성취도와 공부 습관을 가장 먼저 확인해 드립니다.",
    "{dong} 학생이 어느 단원에서 자주 막히는지, 공부 시간은 충분한지를 우선 확인합니다.",
    "{dong}에서는 최근 시험 성적보다 학생이 실제로 막히는 지점을 먼저 살펴봅니다.",
]

GEO_ANSWER_P2 = [
    "{dong} 학생은 진단 결과를 바탕으로 주간 플래너를 세우고, 수업 후 실행 여부와 오답 재학습을 점검합니다.",
    "{dong}에서는 진단 이후 주간 계획을 세워 실행 여부를 확인하고, 틀린 문제는 원인별로 재학습합니다.",
    "{dong} 학생의 경우 확인된 약점을 바탕으로 학습 계획을 세우고, 수업이 끝난 뒤에도 실행 여부를 계속 점검합니다.",
    "{dong}에서는 진단 결과에 맞춰 주간 학습량을 정하고, 오답은 유형별로 나눠 다시 확인합니다.",
    "{dong} 상담에서 확인한 내용을 바탕으로 계획을 세우고, 이후 실행과 오답 재학습으로 이어갑니다.",
    "{dong} 학생은 계획 실행 여부를 매주 점검하며 오답 재학습으로 연결합니다.",
]

GEO_ANSWER_P3 = [
    "{dong}에서는 수업 횟수보다 아이에게 필요한 관리 강도, 피드백 방식, 시험 전 계획표를 함께 확인하는 것이 좋습니다.",
    "{dong} 학부모님은 몇 번 수업하는지보다 아이에게 맞는 관리 강도와 피드백 주기를 확인하시는 것이 좋습니다.",
    "{dong}에서는 수업 시간표보다 오답을 어떻게 관리하는지, 학부모에게 어떻게 공유하는지를 먼저 보시길 권합니다.",
    "{dong} 학원을 비교하실 때는 규모보다 학생별 피드백이 얼마나 구체적인지, 시험 전 계획이 있는지를 확인하시면 좋습니다.",
    "{dong}에서는 수업 진행 방식보다 문제가 생겼을 때 어떻게 대응하는지를 먼저 확인하시는 것이 좋습니다.",
    "{dong} 학부모님이라면 피드백 주기와 시험 전 계획표 유무를 먼저 확인해 보시길 권합니다.",
]

GEO_ANSWER_P4 = [
    "{dong}의 초등·중등·고등 영어·수학 페이지를 함께 비교하면 상담 범위를 더 빠르게 좁힐 수 있습니다.",
    "{dong}의 다른 학년·과목 페이지도 함께 보시면 필요한 상담 범위를 더 쉽게 좁힐 수 있습니다.",
    "{dong}의 다른 학년 페이지를 참고하시면 형제자매 상담 계획도 함께 세우기 편합니다.",
    "{dong} 안의 다른 과목 페이지를 함께 확인하면 전체적인 학습 관리 방향을 잡기 쉬워집니다.",
    "{dong}의 학년별 페이지를 함께 살펴보시면 필요한 과목을 더 정확히 정할 수 있습니다.",
    "{dong} 안의 관련 페이지를 같이 확인하시면 상담 전 비교가 더 쉬워집니다.",
]

SUMMARY_LIST_HUB = [
    ["대상: {dong} 초등반 · 중등반 · 고등반", "과목: 영어 · 수학 중심 학습관리", "방식: 진단 후 계획, 과제, 오답, 피드백 순으로 진행", "상담: 전화 · 문자 · 온라인 신청 가능"],
    ["대상: {dong}의 초·중·고 전 학년", "과목: 영어와 수학을 중심으로 관리", "방식: 진단 → 학습계획 → 과제 확인 → 오답 재학습", "상담: 전화, 문자, 온라인 중 편한 방법으로 신청"],
    ["대상: {dong} 초등학생부터 고등학생까지", "과목: 영어·수학 학습관리", "방식: 진단하고 계획을 세운 뒤 과제와 오답을 관리", "문의: 전화 · 문자 · 온라인 신청 가능"],
    ["대상: {dong}에서 학습관리가 필요한 초·중·고 학생", "과목: 영어 · 수학", "방식: 진단 → 계획 → 과제 확인 → 오답 재학습", "상담: 전화 · 문자 · 온라인 신청 가능"],
    ["대상: {dong} 학생 전 학년", "과목: 영어·수학 중심", "방식: 진단 후 주간 계획을 세우고 오답을 재학습", "문의: 전화, 문자, 온라인 중 편한 방법으로 신청"],
]

SUMMARY_LIST_LEAF_TEMPLATES = [
    ["대상: {dong} {grade} {subject} 기초·심화 상담", "내용: {focus}", "방식: 진단 후 학습계획, 숙제 확인, 오답 점검 순으로 진행", "문의: 전화 · 문자 · 온라인 신청 가능"],
    ["대상: {dong}에서 {grade} {subject}가 필요한 학생", "내용: {focus} 중심 관리", "방식: 진단 → 학습계획 → 숙제 확인 → 오답 점검", "문의: 전화, 문자, 온라인 중 편한 방법으로 신청"],
    ["대상: {dong} {grade} {subject} 진단·상담", "내용: {focus}를 함께 확인", "방식: 진단하고 계획을 세운 뒤 숙제와 오답을 관리", "문의: 전화 · 문자 · 온라인 신청 가능"],
    ["대상: {dong} 학생의 {grade} {subject} 상담", "내용: {focus}", "방식: 진단 → 계획 → 숙제 확인 → 오답 재학습", "문의: 전화, 문자, 온라인 중 편한 방법으로 신청"],
    ["대상: {dong}에서 {grade} {subject}를 다시 잡고 싶은 학생", "내용: {focus} 위주 관리", "방식: 진단 후 계획을 세우고 숙제와 오답을 확인", "문의: 전화 · 문자 · 온라인 신청 가능"],
    ["대상: {dong} {grade} {subject} 진단·상담 희망 학생", "내용: {focus}를 함께 확인", "방식: 진단하고 계획을 세운 뒤 숙제와 오답을 관리", "문의: 전화 · 문자 · 온라인 신청 가능"],
]


HERO_PATTERN = re.compile(r'(<h1>.*?</h1>\s*<p>).*?(</p>\s*<div class="keyword-row local-keywords")', re.S)
GEO_RECOMMEND_PATTERN = re.compile(
    r'(<span>추천 학생</span>\s*<strong>).*?(</strong>\s*<p>).*?(</p>)', re.S
)
GEO_ANSWER_BLOCK_PATTERN = re.compile(
    r'(<strong>무엇을 먼저 확인하나요\?</strong>\s*<p>).*?(</p>\s*</article>\s*<article class="geo-answer-card">\s*<strong>관리는 어떻게 이어지나요\?</strong>\s*<p>).*?(</p>\s*</article>\s*<article class="geo-answer-card">\s*<strong>학부모는 무엇을 보면 좋나요\?</strong>\s*<p>).*?(</p>\s*</article>\s*<article class="geo-answer-card">\s*<strong>관련 페이지는 어떻게 활용하나요\?</strong>\s*<p>).*?(</p>)',
    re.S,
)
SUMMARY_LIST_PATTERN = re.compile(r'(<ul class="summary-list">).*?(</ul>)', re.S)


def build_summary_list_html(items: list[str]) -> str:
    return "\n".join(f"            <li>{html.escape(x)}</li>" for x in items)


def update_page(path: Path, root: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    rel_parts = path.relative_to(root).parts
    meta, is_leaf, _slug = category_meta(rel_parts)
    dong = rel_parts[1]
    title = get_h1(text) or dong
    ctx = {"dong": dong, "title": title, **meta}

    rng = stable_rng(path, root)
    original = text

    hero_bank = HERO_LEAD_LEAF if is_leaf else HERO_LEAD_HUB
    m = HERO_PATTERN.search(text)
    if m:
        repl = html.escape(sentence(rng.choice(hero_bank).format(**ctx)))
        text = text[: m.start()] + m.group(1) + repl + m.group(2) + text[m.end() :]

    m = GEO_RECOMMEND_PATTERN.search(text)
    if m:
        strong_bank = GEO_RECOMMEND_STRONG if is_leaf else GEO_RECOMMEND_STRONG_HUB
        strong = html.escape(rng.choice(strong_bank).format(**ctx))
        p = html.escape(sentence(rng.choice(GEO_RECOMMEND_P).format(**ctx)))
        text = text[: m.start()] + m.group(1) + strong + m.group(2) + p + m.group(3) + text[m.end() :]

    m = GEO_ANSWER_BLOCK_PATTERN.search(text)
    if m:
        p1 = html.escape(sentence(rng.choice(GEO_ANSWER_P1).format(**ctx)))
        p2 = html.escape(sentence(rng.choice(GEO_ANSWER_P2).format(**ctx)))
        p3 = html.escape(sentence(rng.choice(GEO_ANSWER_P3).format(**ctx)))
        p4 = html.escape(sentence(rng.choice(GEO_ANSWER_P4).format(**ctx)))
        text = (
            text[: m.start()]
            + m.group(1) + p1
            + m.group(2) + p2
            + m.group(3) + p3
            + m.group(4) + p4
            + m.group(5)
            + text[m.end() :]
        )

    m = SUMMARY_LIST_PATTERN.search(text)
    if m:
        bank = SUMMARY_LIST_LEAF_TEMPLATES if is_leaf else SUMMARY_LIST_HUB
        items = [x.format(**ctx) for x in rng.choice(bank)]
        text = text[: m.start()] + m.group(1) + "\n" + build_summary_list_html(items) + "\n          " + m.group(2) + text[m.end() :]

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
