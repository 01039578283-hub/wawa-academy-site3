# -*- coding: utf-8 -*-
"""Randomize FAQ and parent review sections for 코칭학원.com local pages."""

from __future__ import annotations

import hashlib
import html
import json
import random
import re
from pathlib import Path
from typing import Any


SITE_NAME = "코칭학원"
RATING_VALUES = ["5", "5", "5", "5", "5", "4"]
STARS = {"5": "★★★★★", "4": "★★★★☆"}


def strip_tags(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value, flags=re.S)
    return html.unescape(re.sub(r"\s+", " ", value).strip())


def type_contains(node: dict[str, Any], needle: str) -> bool:
    node_type = node.get("@type")
    if isinstance(node_type, list):
        return needle in node_type
    return node_type == needle


def stable_rng(path: Path, root: Path) -> random.Random:
    rel = path.relative_to(root).as_posix()
    seed = int(hashlib.sha256(rel.encode("utf-8")).hexdigest()[:16], 16)
    return random.Random(seed)


def parse_faq_bank(path: Path) -> list[tuple[str, str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    faqs: list[tuple[str, str]] = []
    current_q: str | None = None
    current_a: list[str] = []

    def flush() -> None:
        nonlocal current_q, current_a
        if current_q and current_a:
            answer = " ".join(line.strip() for line in current_a if line.strip())
            if answer:
                faqs.append((current_q.strip(), answer.strip()))
        current_q = None
        current_a = []

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("질문:"):
            flush()
            current_q = line.split(":", 1)[1].strip()
        elif line.startswith("답변:"):
            current_a = [line.split(":", 1)[1].strip()]
        elif current_q and current_a:
            current_a.append(line)
    flush()
    return faqs


def parse_review_bank(path: Path) -> list[str]:
    lines: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        clean = line.strip()
        if clean and not clean.startswith("#"):
            lines.append(clean.rstrip(".。"))
    return lines


def get_title(text: str, path: Path) -> str:
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", text, flags=re.S | re.I)
    if h1:
        title = strip_tags(h1.group(1))
    else:
        title_match = re.search(r"<title[^>]*>(.*?)</title>", text, flags=re.S | re.I)
        title = strip_tags(title_match.group(1)) if title_match else path.parent.name
    title = re.sub(r"\s*[|｜]\s*.*$", "", title).strip()
    return title or path.parent.name


def page_context(path: Path, root: Path, text: str) -> dict[str, str]:
    rel_parts = path.relative_to(root).parts
    dong = rel_parts[1] if len(rel_parts) >= 3 else ""
    child_slug = rel_parts[2] if len(rel_parts) >= 4 else ""
    title = get_title(text, path)
    topic = title.replace(dong, "", 1).strip() if dong and title.startswith(dong) else title
    topic = topic or "학습 상담"
    if topic == "학원":
        topic = "학습 관리"
    compact_topic = re.sub(r"\s+", " ", topic)
    return {"title": title, "dong": dong, "topic": compact_topic, "child_slug": child_slug}


def sentence(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    if not value:
        return value
    if value[-1] not in ".!?。":
        value += "."
    return value


def make_faqs(
    rng: random.Random,
    faq_bank: list[tuple[str, str]],
    *,
    title: str,
    dong: str,
    topic: str,
) -> list[dict[str, str]]:
    selected = rng.sample(faq_bank, 5) if len(faq_bank) >= 5 else list(faq_bank)
    while len(selected) < 5:
        selected.append(selected[-1])

    q0_options = [
        f"{title} 상담은 어떤 순서로 진행되나요?",
        f"{title}을 알아볼 때 상담에서는 무엇을 먼저 확인하나요?",
        f"{title} 상담을 받으면 어떤 부분부터 점검하나요?",
    ]
    a0_options = [
        f"{title} 상담은 학생의 현재 교재, 학교 진도, 최근 오답, 공부 가능한 시간을 먼저 확인한 뒤 필요한 관리 범위를 정합니다.",
        f"{title} 상담에서는 성적표만 보는 것이 아니라 풀이 습관, 숙제 실행력, 시험 전 계획까지 함께 살펴봅니다.",
        f"{title}을 찾는 학생에게는 현재 수준과 목표를 나누어 보고, 과목별 약점과 관리 강도를 순서대로 정리합니다.",
    ]
    q1_options = [
        f"{dong}에서 {topic}을 선택할 때 어떤 기준이 중요할까요?",
        f"{dong} 학생이 {topic}을 시작하기 전 확인하면 좋은 점은 무엇인가요?",
        f"{dong}에서 {topic} 상담을 준비할 때 무엇을 가져가면 좋나요?",
    ]
    a1_options = [
        f"{dong} 학생이라도 학년, 학교 진도, 과목별 약점이 다르기 때문에 최근 시험지와 현재 교재를 함께 보는 것이 좋습니다.",
        f"{dong} 생활권에서 수업을 알아볼 때는 이동 거리보다 학생에게 필요한 피드백 방식과 오답 관리 흐름을 먼저 확인하는 것이 좋습니다.",
        f"{dong} 학생의 상담에서는 최근 단원, 틀리는 유형, 숙제 습관, 시험 일정이 함께 정리될수록 수업 방향이 더 분명해집니다.",
    ]
    q2_options = [
        f"{topic} 수업은 학생 수준에 맞춰 조정되나요?",
        f"{topic} 관리는 내신과 기본기 보완을 함께 볼 수 있나요?",
        f"{topic}을 처음 시작하는 학생도 상담이 가능한가요?",
    ]
    a2_options = [
        "가능합니다. 학생마다 필요한 단원과 학습 속도가 다르기 때문에 진단 후 개념, 유형, 오답, 시험 대비 비중을 다르게 잡습니다.",
        "가능합니다. 기본 개념이 부족한 학생은 기초를 먼저 정리하고, 시험 대비가 필요한 학생은 범위별 계획과 반복 확인을 함께 진행합니다.",
        "가능합니다. 처음 상담에서는 현재 상태를 무리하게 판단하기보다 학습 자료와 생활 패턴을 보고 시작 가능한 범위를 정합니다.",
    ]

    generated = [
        {
            "q": rng.choice(q0_options),
            "a": sentence(rng.choice(a0_options) + " " + selected[0][1]),
        },
        {
            "q": rng.choice(q1_options),
            "a": sentence(rng.choice(a1_options) + " " + selected[1][1]),
        },
        {
            "q": rng.choice(q2_options),
            "a": sentence(rng.choice(a2_options) + " " + selected[2][1]),
        },
    ]

    for q, a in selected[3:5]:
        generated.append(
            {
                "q": q,
                "a": sentence(
                    f"{a} {title} 상담에서는 이 내용을 학생의 현재 수준과 목표에 맞춰 다시 확인합니다."
                ),
            }
        )

    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for item in generated:
        if item["q"] in seen:
            item = {
                "q": f"{title}에서 {topic}을 이어가려면 무엇이 중요하나요?",
                "a": sentence(
                    f"처음 계획보다 실제 실행 여부를 꾸준히 확인하는 것이 중요합니다. {title} 상담에서는 학생별 루틴과 오답 흐름을 함께 봅니다."
                ),
            }
        seen.add(item["q"])
        unique.append(item)
    return unique[:5]


def make_reviews(
    rng: random.Random,
    review_bank: list[str],
    *,
    title: str,
    dong: str,
    topic: str,
) -> list[dict[str, str]]:
    selected = rng.sample(review_bank, 6) if len(review_bank) >= 6 else list(review_bank)
    while len(selected) < 6:
        selected.append(selected[-1])

    templates = [
        "{title} 상담을 받은 뒤 {line}.",
        "{dong}에서 학습 관리를 알아보다가 {line}.",
        "{topic} 방향을 잡는 과정에서 {line}.",
        "아이에게 필요한 관리 범위를 설명해 주셔서 {line}.",
        "상담 후 공부 루틴을 다시 정리하면서 {line}.",
        "{title} 수업 흐름을 확인하고 나니 {line}.",
    ]

    reviews: list[dict[str, str]] = []
    for idx, line in enumerate(selected[:6]):
        body = templates[idx].format(title=title, dong=dong, topic=topic, line=line)
        body = sentence(body)
        rating = RATING_VALUES[idx]
        reviews.append({"body": body, "rating": rating, "stars": STARS[rating]})
    return reviews


def build_review_html(reviews: list[dict[str, str]], *, title: str, dong: str, topic: str) -> str:
    cards = []
    for item in reviews:
        rating = html.escape(item["rating"])
        cards.append(
            '        <article class="review-card">\n'
            f'          <div class="stars" aria-label="{rating}점 후기">{html.escape(item["stars"])}</div>\n'
            f'          <p>{html.escape(item["body"])}</p>\n'
            "        </article>"
        )
    return (
        '<section id="parent-reviews" class="local-section">\n'
        '  <div class="wrap local-card">\n'
        f"    <h2>{html.escape(title)} 학부모 후기</h2>\n"
        f"    <p>{html.escape(dong)} 학생의 {html.escape(topic)} 상담과 학습 관리 흐름을 경험한 학부모 후기입니다.</p>\n"
        '    <div class="review-grid">\n'
        + "\n".join(cards)
        + "\n"
        "    </div>\n"
        "  </div>\n"
        "</section>"
    )


def build_faq_html(faqs: list[dict[str, str]], *, title: str) -> str:
    items = []
    for item in faqs:
        items.append(
            "      <details>\n"
            f"        <summary>{html.escape(item['q'])}</summary>\n"
            f"        <p>{html.escape(item['a'])}</p>\n"
            "      </details>"
        )
    return (
        '<section id="faq-section" class="local-section">\n'
        '  <div class="wrap faq-local">\n'
        f"    <h2>{html.escape(title)} FAQ</h2>\n"
        + "\n".join(items)
        + "\n"
        "  </div>\n"
        "</section>"
    )


def update_json_ld(text: str, faqs: list[dict[str, str]], reviews: list[dict[str, str]]) -> tuple[str, bool]:
    script_re = re.compile(r'<script type="application/ld\+json">(.*?)</script>', flags=re.S)
    match = script_re.search(text)
    if not match:
        return text, False

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return text, False

    faq_entities = [
        {"@type": "Question", "name": item["q"], "acceptedAnswer": {"@type": "Answer", "text": item["a"]}}
        for item in faqs
    ]
    review_entities = [
        {
            "@type": "Review",
            "author": {"@type": "Person", "name": "학부모"},
            "reviewBody": item["body"],
            "reviewRating": {"@type": "Rating", "ratingValue": item["rating"], "bestRating": "5"},
        }
        for item in reviews
    ]

    graph = data.get("@graph") if isinstance(data, dict) else None
    nodes = graph if isinstance(graph, list) else [data] if isinstance(data, dict) else []
    changed = False
    for node in nodes:
        if not isinstance(node, dict):
            continue
        if type_contains(node, "FAQPage"):
            node["mainEntity"] = faq_entities
            changed = True
        if type_contains(node, "EducationalOrganization") or type_contains(node, "LocalBusiness"):
            node["review"] = review_entities
            node["aggregateRating"] = {
                "@type": "AggregateRating",
                "ratingValue": "4.8",
                "bestRating": "5",
                "ratingCount": "6",
                "reviewCount": "6",
            }
            changed = True

    if not changed:
        return text, False
    compact = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    replacement = f'<script type="application/ld+json">{compact}</script>'
    return text[: match.start()] + replacement + text[match.end() :], True


def update_page(path: Path, root: Path, faq_bank: list[tuple[str, str]], review_bank: list[str]) -> tuple[bool, str | None]:
    text = path.read_text(encoding="utf-8", errors="replace")
    ctx = page_context(path, root, text)
    rng = stable_rng(path, root)
    faqs = make_faqs(rng, faq_bank, title=ctx["title"], dong=ctx["dong"], topic=ctx["topic"])
    reviews = make_reviews(rng, review_bank, title=ctx["title"], dong=ctx["dong"], topic=ctx["topic"])

    new_text, json_changed = update_json_ld(text, faqs, reviews)
    review_html = build_review_html(reviews, title=ctx["title"], dong=ctx["dong"], topic=ctx["topic"])
    faq_html = build_faq_html(faqs, title=ctx["title"])

    review_pattern = re.compile(
        r'<section id="parent-reviews" class="local-section">.*?</section>\s*(?=<section id="faq-section")',
        flags=re.S,
    )
    faq_pattern = re.compile(
        r'<section id="faq-section" class="local-section">.*?</section>\s*(?=<section id="internal-links"|<footer|</main>)',
        flags=re.S,
    )

    new_text, review_count = review_pattern.subn(review_html + "\n", new_text, count=1)
    new_text, faq_count = faq_pattern.subn(faq_html + "\n", new_text, count=1)

    if review_count != 1:
        return False, "review section not replaced"
    if faq_count != 1:
        return False, "faq section not replaced"
    if not json_changed:
        return False, "json-ld not updated"

    if new_text != text:
        path.write_text(new_text, encoding="utf-8", newline="\n")
        return True, None
    return False, None


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    common = root.parent / "참고자료" / "공통자료"
    center_dir = root / "전국센터"
    faq_bank = parse_faq_bank(common / "FAQ.txt")
    review_bank = parse_review_bank(common / "학부모 후기.txt")

    if len(faq_bank) < 5:
        raise SystemExit(f"FAQ bank is too small: {len(faq_bank)}")
    if len(review_bank) < 6:
        raise SystemExit(f"Review bank is too small: {len(review_bank)}")

    pages = [
        p
        for p in sorted(center_dir.rglob("index.html"))
        if len(p.relative_to(root).parts) >= 3
    ]

    updated = 0
    failures: list[tuple[str, str]] = []
    for path in pages:
        changed, error = update_page(path, root, faq_bank, review_bank)
        if error:
            failures.append((path.relative_to(root).as_posix(), error))
        if changed:
            updated += 1

    print(f"FAQ bank: {len(faq_bank)}")
    print(f"Review bank: {len(review_bank)}")
    print(f"Target pages: {len(pages)}")
    print(f"Updated pages: {updated}")
    print(f"Failures: {len(failures)}")
    for rel, err in failures[:20]:
        print(f" - {rel}: {err}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
