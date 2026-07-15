# -*- coding: utf-8 -*-
"""Diversify the single sentence that was identical on every 전국센터 page.

The "ANSWER READY" section's geo-mini-faq answer paragraph was 100% the
same wording on all 2,597 dong/leaf pages (only the <summary> question
already varied). This rewrites just that <p> using a template bank keyed
by each page's own path, so the sentence itself becomes unique everywhere.
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from randomize_coaching_faq_reviews import get_title, page_context, sentence, stable_rng  # noqa: E402

ANSWER_TEMPLATES = [
    "{title} 상담 전에는 최근 시험지, 사용 중인 교재, 학교 진도, 평소 공부 가능한 시간을 정리해 오시면 상담이 더 구체적으로 진행됩니다.",
    "{dong} 학생의 상담에서는 오답노트, 최근 성적표, 숙제 수행 정도를 함께 확인할수록 필요한 관리 방향이 더 분명해집니다.",
    "{title}을 상담받기 전에는 자주 틀리는 단원, 현재 학교 진도, 하루 중 공부 가능한 시간대를 미리 정리해 두면 좋습니다.",
    "{dong}에서 {topic} 상담을 받을 때는 최근 시험 결과와 사용 중인 교재를 함께 보여주시면 진단이 더 정확해집니다.",
    "상담 전에 최근 시험지, 숙제 노트, 학교 진도표를 챙겨 오시면 {title} 상담에서 바로 활용할 수 있습니다.",
    "{title} 상담에서는 성적표뿐 아니라 자주 틀리는 유형과 평소 학습 시간을 함께 확인해야 정확한 계획이 나옵니다.",
    "{dong} 학생이라면 최근 오답노트와 현재 교재, 학교 수업 진도를 미리 정리해 상담에 가져오시는 것을 권합니다.",
    "{dong}에서 {topic} 상담을 준비할 때는 최근 시험지와 숙제 이행 정도, 집에서 공부 가능한 시간을 함께 확인하면 도움이 됩니다.",
    "{title} 상담에서 가장 먼저 보는 것은 최근 시험 결과와 교재 진도이니, 관련 자료를 준비해 오시면 좋습니다.",
    "{dong}에서 상담을 준비하신다면 최근 성적, 자주 틀리는 문제 유형, 평소 공부 습관을 함께 정리해 주세요.",
    "{title} 상담 전 최근 시험지와 오답노트, 현재 진도를 확인할 수 있는 자료를 챙겨 오시면 상담 시간을 아낄 수 있습니다.",
    "학교 진도와 최근 시험 범위, 평소 숙제 수행 정도를 알려주시면 {title} 상담에서 더 정확한 학습 방향을 안내해 드립니다.",
    "{dong} 학생의 경우 최근 시험지와 교재, 하루 공부 가능 시간을 미리 정리해 두면 상담이 한결 수월해집니다.",
    "{title}을 고민 중이라면 최근 오답 유형과 학교 진도, 평소 공부 시간을 먼저 확인해 상담에 임하시는 것이 좋습니다.",
    "상담 전 최근 시험 결과지와 현재 사용 중인 교재를 준비해 오시면 {title} 상담에서 더 구체적인 계획을 세울 수 있습니다.",
    "{dong}에서 {topic} 상담을 계획 중이라면 학교 진도표와 최근 오답노트를 함께 확인하는 것이 좋습니다.",
    "{title} 상담에서는 학생의 공부 시간, 최근 시험지, 자주 틀리는 단원을 함께 살펴야 필요한 관리 범위가 정해집니다.",
]


def build_answer(rng, ctx: dict[str, str]) -> str:
    template = rng.choice(ANSWER_TEMPLATES)
    return sentence(template.format(title=ctx["title"], dong=ctx["dong"], topic=ctx["topic"]))


PATTERN = re.compile(
    r'(<div class="geo-mini-faq">\s*<details open>\s*<summary>.*?</summary>\s*<p>)(.*?)(</p>\s*</details>\s*</div>)',
    re.S,
)


def update_page(path: Path, root: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    match = PATTERN.search(text)
    if not match:
        return False

    ctx = page_context(path, root, text)
    rng = stable_rng(path, root)
    new_answer = html.escape(build_answer(rng, ctx))

    new_text = text[: match.start()] + match.group(1) + new_answer + match.group(3) + text[match.end() :]
    if new_text != text:
        path.write_text(new_text, encoding="utf-8", newline="\n")
        return True
    return False


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    center_dir = root / "전국센터"
    pages = [
        p
        for p in sorted(center_dir.rglob("index.html"))
        if len(p.relative_to(root).parts) >= 3
    ]

    updated = 0
    skipped = []
    for path in pages:
        if update_page(path, root):
            updated += 1
        else:
            skipped.append(path.relative_to(root).as_posix())

    print(f"target pages: {len(pages)}")
    print(f"updated: {updated}")
    print(f"skipped (no match): {len(skipped)}")
    for rel in skipped[:10]:
        print(" -", rel)


if __name__ == "__main__":
    main()
