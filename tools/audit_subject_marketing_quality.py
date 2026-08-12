"""Read-only marketing-content audit for the four subject page collections.

This audit measures the reader-facing improvements that are intentionally not
covered by the release/technical audit:

* a concrete reader in the opening body paragraph;
* an empathy -> practical conclusion sequence near the start;
* natural, reader-oriented H2 headings rather than appended keyword fragments;
* concise FAQ answers whose first sentence gives the answer immediately.

Images, external/public evidence links, and low-priority media/OG/DNS checks
are deliberately out of scope.  The script never writes or regenerates pages.
Run with ``--strict`` to use the published targets as a CI/release gate.  The
default mode is diagnostic and therefore exits successfully after reporting
the current baseline, even when a target is missed.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
SUBJECT_ROOT = ROOT / "과목별학원"
CATEGORIES: dict[str, str] = {
    "영수전문학원": "영수 전문학원",
    "영어전문학원": "영어 전문학원",
    "수학전문학원": "수학 전문학원",
    "전문학원": "전문학원",
}
EXPECTED_DETAILS_PER_CATEGORY = 371

# Targets are intentionally expressed as ratios so the report can be reused
# while copy is iterated.  Parse/scope integrity remains an exact requirement.
TARGETS: dict[str, float] = {
    "opening_reader_specific": 0.95,
    "empathy_then_conclusion": 0.95,
    "summary_answer_first": 0.95,
    "natural_h2": 0.99,
    "faq_answer_first": 0.95,
    "faq_concise": 0.95,
}

FAQ_MAX_CHARS = 240
FAQ_MAX_SENTENCES = 3
FAQ_MAX_FIRST_SENTENCE_CHARS = 100
FAQ_MAX_SENTENCE_CHARS = 120
H2_MAX_CHARS = 78

GRADE_PATTERN = re.compile(
    r"(?:초등(?:학교)?\s*[1-6]\s*학년|중(?:학교)?\s*[1-3]\s*학년|"
    r"고등(?:학교)?\s*[1-3]\s*학년|초[1-6]|중[1-3]|고[1-3])"
)
READER_PATTERN = re.compile(r"학생|자녀|아이|학부모|보호자|가정")
PROBLEM_PATTERN = re.compile(
    r"어렵|부족|막히|막힌|멈추|실수|오답|부담|고민|놓치|밀리|공백|"
    r"약하|약한|망설|끊기|따라가지만|못하|늦어|흐트러|불안|반복해|"
    r"헷갈|취약|부진|안\s*되|틀리|잃는|누적된|시간이\s*부족|재풀이|남지"
)
ACTION_PATTERN = re.compile(
    r"먼저|확인(?:하|해|할)|준비(?:하|해|할)|비교(?:하|해|할)|"
    r"점검(?:하|해|할)|나누(?:어|고|면)|살펴(?:보|볼)|정리(?:하|해|할)|"
    r"기준(?:으로|을)|필요(?:합니다|합니다|한)|권합니다|추천합니다|"
    r"가져오세요|기록하세요|질문하세요|표시하세요|정할\s*수\s*있"
)
DIRECT_ENDING_PATTERN = re.compile(
    r"(?:입니다|아닙니다|됩니다|있습니다|없습니다|좋습니다|필요합니다|"
    r"확인됩니다|준비하세요|확인하세요|살펴보세요|정리하세요|가져오세요|"
    r"기록하세요|질문하세요|표시하세요|확인합니다|준비합니다|점검합니다|해야\s*합니다|"
    r"나누어\s*봅니다|구분합니다|권합니다|추천합니다)\.?$"
)
LEADING_CONDITION_PATTERN = re.compile(
    r"^.{0,95}?(?:보면|하면|놓으면|맞추면|연결하면|정리하면|살펴보면|"
    r"비교하면|대조하면|구체화하면|배열하면|이어\s*보면),"
)

H2_FLAG_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("keyword_fragment_separator", re.compile(r"\s[·/|—]\s")),
    ("mechanical_process_phrase", re.compile(r"^이\s+(?:영수|영어|수학)\s+학습\s+과정")),
    ("authoring_term", re.compile(r"SEO|AEO|GEO|키워드|검색\s*의도|원고|페이지", re.I)),
    ("duplicate_word", re.compile(r"(?P<word>기준|확인|상담|학습|수업)\s+(?P=word)")),
    ("broken_particle", re.compile(r"에서는는|풀이으로|설계은|구조은|다음\s+첫\s+상담")),
)


@dataclass
class PageResult:
    path: str
    category: str
    local: str
    opening_reader_specific: bool
    empathy_then_conclusion: bool
    summary_answer_first: bool
    h2_total: int
    h2_natural: int
    faq_total: int
    faq_answer_first: int
    faq_concise: int
    parse_complete: bool


@dataclass
class Aggregate:
    pages: int = 0
    parse_complete: int = 0
    opening_reader_specific: int = 0
    empathy_then_conclusion: int = 0
    summary_answer_first: int = 0
    h2_total: int = 0
    h2_natural: int = 0
    faq_total: int = 0
    faq_answer_first: int = 0
    faq_concise: int = 0
    faq_lengths: list[int] = field(default_factory=list)

    def add(self, result: PageResult, faq_lengths: Iterable[int]) -> None:
        self.pages += 1
        self.parse_complete += int(result.parse_complete)
        self.opening_reader_specific += int(result.opening_reader_specific)
        self.empathy_then_conclusion += int(result.empathy_then_conclusion)
        self.summary_answer_first += int(result.summary_answer_first)
        self.h2_total += result.h2_total
        self.h2_natural += result.h2_natural
        self.faq_total += result.faq_total
        self.faq_answer_first += result.faq_answer_first
        self.faq_concise += result.faq_concise
        self.faq_lengths.extend(faq_lengths)

    def ratios(self) -> dict[str, float]:
        return {
            "parse_complete": ratio(self.parse_complete, self.pages),
            "opening_reader_specific": ratio(self.opening_reader_specific, self.pages),
            "empathy_then_conclusion": ratio(self.empathy_then_conclusion, self.pages),
            "summary_answer_first": ratio(self.summary_answer_first, self.pages),
            "natural_h2": ratio(self.h2_natural, self.h2_total),
            "faq_answer_first": ratio(self.faq_answer_first, self.faq_total),
            "faq_concise": ratio(self.faq_concise, self.faq_total),
        }

    def score(self) -> float:
        values = self.ratios()
        weighted = (
            values["opening_reader_specific"] * 0.25
            + values["empathy_then_conclusion"] * 0.20
            + values["summary_answer_first"] * 0.15
            + values["natural_h2"] * 0.15
            + values["faq_answer_first"] * 0.15
            + values["faq_concise"] * 0.10
        )
        return round(weighted * 10, 2)


class Findings:
    """Count every finding but keep only a few bounded examples."""

    def __init__(self) -> None:
        self.counts: Counter[str] = Counter()
        self.examples: dict[str, list[dict[str, str]]] = defaultdict(list)

    def add(self, code: str, path: Path, detail: str) -> None:
        self.counts[code] += 1
        if len(self.examples[code]) >= 5:
            return
        self.examples[code].append(
            {
                "page": path.relative_to(ROOT).as_posix(),
                "detail": normalize_space(detail)[:300],
            }
        )


def ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def normalize_space(value: object) -> str:
    return " ".join(str(value or "").split())


def clean_markup(value: str) -> str:
    without_scripts = re.sub(
        r"<(?:script|style)\b[^>]*>.*?</(?:script|style)>",
        " ",
        value,
        flags=re.I | re.S,
    )
    return normalize_space(html.unescape(re.sub(r"<[^>]+>", " ", without_scripts)))


def sentences(value: str) -> list[str]:
    value = normalize_space(value)
    if not value:
        return []
    parts = re.findall(r".+?(?:[.!?](?=\s|$)|$)", value)
    return [normalize_space(part) for part in parts if normalize_space(part)]


def class_block(source: str, tag: str, class_name: str) -> str | None:
    pattern = re.compile(
        rf"<{tag}\b(?=[^>]*\bclass=([\"'])[^\"']*\b{re.escape(class_name)}\b[^\"']*\1)[^>]*>"
        rf"(.*?)</{tag}>",
        re.I | re.S,
    )
    found = pattern.search(source)
    return found.group(2) if found else None


def prose_sections(source: str) -> list[str]:
    pattern = re.compile(
        r"<section\b(?=[^>]*\bclass=([\"'])[^\"']*\bsubject-prose-section\b[^\"']*\1)[^>]*>"
        r"(.*?)</section>",
        re.I | re.S,
    )
    return [found.group(2) for found in pattern.finditer(source)]


def first_content_paragraph(section: str) -> str:
    for found in re.finditer(r"(<p\b[^>]*>)(.*?)</p>", section, re.I | re.S):
        opening_tag, body = found.groups()
        if re.search(r"\bsubject-section-index\b", opening_tag, re.I):
            continue
        return clean_markup(body)
    return ""


def article_intro_paragraph(source: str) -> str:
    block = class_block(source, "div", "subject-article-intro")
    if block is None:
        return ""
    found = re.search(r"<p\b[^>]*>(.*?)</p>", block, re.I | re.S)
    return clean_markup(found.group(1)) if found else ""


def summary_paragraph(source: str) -> str:
    found = re.search(
        r"<div\b(?=[^>]*\bclass=([\"'])[^\"']*\bgeo-summary-panel\b[^\"']*\1)[^>]*>"
        r".*?<h2\b[^>]*>.*?</h2>\s*<p\b[^>]*>(.*?)</p>",
        source,
        re.I | re.S,
    )
    return clean_markup(found.group(2)) if found else ""


def faq_pairs(source: str) -> list[tuple[str, str]]:
    found = re.search(r'<section\b(?=[^>]*\bid=["\']faq-section["\'])[^>]*>(.*?)</section>', source, re.I | re.S)
    if not found:
        return []
    return [
        (clean_markup(pair.group(1)), clean_markup(pair.group(2)))
        for pair in re.finditer(
            r"<details\b[^>]*>\s*<summary\b[^>]*>(.*?)</summary>\s*<p\b[^>]*>(.*?)</p>\s*</details>",
            found.group(1),
            re.I | re.S,
        )
    ]


def reader_specific(opening: str, local: str, path: Path, findings: Findings) -> bool:
    normalized_opening = opening.replace(" ", "")
    normalized_local = local.replace(" ", "")
    checks = {
        "opening_missing_local": normalized_local in normalized_opening,
        "opening_missing_specific_grade": bool(GRADE_PATTERN.search(opening)),
        "opening_missing_reader": bool(READER_PATTERN.search(opening)),
        "opening_missing_problem": bool(PROBLEM_PATTERN.search(opening)),
    }
    for code, passed in checks.items():
        if not passed:
            findings.add(code, path, opening or "첫 본문 문단 없음")
    return all(checks.values())


def empathy_sequence(opening: str, path: Path, findings: Findings) -> bool:
    opening_sentences = sentences(opening)[:3]
    if not opening_sentences:
        findings.add("opening_missing", path, "첫 본문 문단 없음")
        return False

    empathy = bool(READER_PATTERN.search(opening_sentences[0]) and PROBLEM_PATTERN.search(opening_sentences[0]))
    if not empathy:
        findings.add("opening_empathy_not_first", path, opening_sentences[0])

    # The practical answer may complete the first sentence or follow it in the
    # next two sentences, but it must not appear before the reader's problem.
    conclusion = any(ACTION_PATTERN.search(sentence) for sentence in opening_sentences)
    if not conclusion:
        findings.add("opening_conclusion_missing", path, " ".join(opening_sentences))
    return empathy and conclusion


def direct_first_sentence(value: str) -> tuple[bool, list[str]]:
    first = sentences(value)
    if not first:
        return False, ["missing"]
    first_sentence = first[0]
    reasons: list[str] = []
    if len(first_sentence) > FAQ_MAX_FIRST_SENTENCE_CHARS:
        reasons.append("first_sentence_long")
    if LEADING_CONDITION_PATTERN.search(first_sentence):
        reasons.append("leading_condition")
    if not (DIRECT_ENDING_PATTERN.search(first_sentence) or ACTION_PATTERN.search(first_sentence)):
        reasons.append("no_direct_answer_cue")
    return not reasons, reasons


def natural_h2(heading: str) -> tuple[bool, list[str]]:
    reasons = [name for name, pattern in H2_FLAG_PATTERNS if pattern.search(heading)]
    if len(heading) > H2_MAX_CHARS:
        reasons.append("heading_long")
    if heading.count("학원") > 2:
        reasons.append("keyword_repetition")
    return not reasons, reasons


def concise_faq(answer: str) -> tuple[bool, list[str]]:
    answer_sentences = sentences(answer)
    reasons: list[str] = []
    if len(answer) > FAQ_MAX_CHARS:
        reasons.append("answer_long")
    if len(answer_sentences) > FAQ_MAX_SENTENCES:
        reasons.append("too_many_sentences")
    if any(len(sentence) > FAQ_MAX_SENTENCE_CHARS for sentence in answer_sentences):
        reasons.append("sentence_long")
    return not reasons, reasons


def detail_paths(category: str) -> list[Path]:
    category_root = SUBJECT_ROOT / category
    if not category_root.exists():
        return []
    return sorted(
        (path for path in category_root.glob("*/index.html") if path.parent != category_root),
        key=lambda path: path.parent.name,
    )


def audit_page(path: Path, category: str, findings: Findings) -> tuple[PageResult, list[int]]:
    source = path.read_text(encoding="utf-8")
    local = path.parent.name
    sections = prose_sections(source)
    opening = article_intro_paragraph(source)
    if not opening:
        opening = first_content_paragraph(sections[0]) if sections else ""
    summary = summary_paragraph(source)

    h2s: list[str] = []
    h2_natural = 0
    for section in sections:
        found = re.search(r"<h2\b[^>]*>(.*?)</h2>", section, re.I | re.S)
        if not found:
            findings.add("prose_section_missing_h2", path, clean_markup(section)[:150])
            continue
        heading = clean_markup(found.group(1))
        h2s.append(heading)
        passed, reasons = natural_h2(heading)
        h2_natural += int(passed)
        for reason in reasons:
            findings.add(f"h2_{reason}", path, heading)

    faqs = faq_pairs(source)
    faq_answer_first = 0
    faq_concise = 0
    faq_lengths: list[int] = []
    for question, answer in faqs:
        faq_lengths.append(len(answer))
        direct, direct_reasons = direct_first_sentence(answer)
        faq_answer_first += int(direct)
        for reason in direct_reasons:
            findings.add(f"faq_{reason}", path, f"{question} → {sentences(answer)[0] if sentences(answer) else ''}")
        concise, concise_reasons = concise_faq(answer)
        faq_concise += int(concise)
        for reason in concise_reasons:
            findings.add(f"faq_{reason}", path, f"{question} → {answer}")

    summary_direct, summary_reasons = direct_first_sentence(summary)
    for reason in summary_reasons:
        findings.add(f"summary_{reason}", path, sentences(summary)[0] if sentences(summary) else "핵심 안내 없음")

    structure_complete = (
        bool(opening)
        and bool(summary)
        and len(sections) >= 5
        and len(h2s) == len(sections)
        and len(faqs) >= 4
        and source.find("geo-summary-panel") < source.find("subject-prose")
    )
    if not structure_complete:
        findings.add(
            "parse_incomplete",
            path,
            f"opening={bool(opening)} summary={bool(summary)} sections={len(sections)} h2={len(h2s)} faq={len(faqs)}",
        )

    result = PageResult(
        path=path.relative_to(ROOT).as_posix(),
        category=category,
        local=local,
        opening_reader_specific=reader_specific(opening, local, path, findings),
        empathy_then_conclusion=empathy_sequence(opening, path, findings),
        summary_answer_first=summary_direct,
        h2_total=len(h2s),
        h2_natural=h2_natural,
        faq_total=len(faqs),
        faq_answer_first=faq_answer_first,
        faq_concise=faq_concise,
        parse_complete=structure_complete,
    )
    return result, faq_lengths


def percentile(values: list[int], quantile: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * quantile)))
    return ordered[index]


def aggregate_payload(aggregate: Aggregate) -> dict[str, object]:
    ratios = aggregate.ratios()
    return {
        "counts": {
            "pages": aggregate.pages,
            "parse_complete": aggregate.parse_complete,
            "h2_total": aggregate.h2_total,
            "faq_total": aggregate.faq_total,
        },
        "ratios": {name: round(value, 6) for name, value in ratios.items()},
        "score_out_of_10": aggregate.score(),
        "faq_length": {
            "mean": round(statistics.fmean(aggregate.faq_lengths), 1) if aggregate.faq_lengths else 0,
            "p95": percentile(aggregate.faq_lengths, 0.95),
            "max": max(aggregate.faq_lengths, default=0),
        },
    }


def target_failures(total: Aggregate, category_counts: dict[str, int]) -> list[str]:
    failures: list[str] = []
    for category, count in category_counts.items():
        if count != EXPECTED_DETAILS_PER_CATEGORY:
            failures.append(f"{category}: detail pages {count} != {EXPECTED_DETAILS_PER_CATEGORY}")
    expected_total = EXPECTED_DETAILS_PER_CATEGORY * len(CATEGORIES)
    if total.pages != expected_total:
        failures.append(f"total detail pages {total.pages} != {expected_total}")
    if total.parse_complete != total.pages:
        failures.append(f"parsed pages {total.parse_complete}/{total.pages}")
    for metric, target in TARGETS.items():
        actual = total.ratios()[metric]
        if actual + 1e-12 < target:
            failures.append(f"{metric}: {actual:.2%} < {target:.0%}")
    return failures


def print_report(
    by_category: dict[str, Aggregate],
    total: Aggregate,
    findings: Findings,
    failures: list[str],
) -> None:
    print("SUBJECT MARKETING QUALITY AUDIT")
    print("scope: 4 professional-academy categories; detail pages only")
    print("excluded: body-image distribution, public evidence links, low-priority technical checks")
    print()
    print(
        "category              pages  reader   empathy  summary  H2 natural  FAQ direct  FAQ concise  score"
    )
    for category, label in CATEGORIES.items():
        aggregate = by_category[category]
        values = aggregate.ratios()
        print(
            f"{label:<20} {aggregate.pages:>5}  "
            f"{values['opening_reader_specific']:>6.1%}  "
            f"{values['empathy_then_conclusion']:>7.1%}  "
            f"{values['summary_answer_first']:>7.1%}  "
            f"{values['natural_h2']:>10.1%}  "
            f"{values['faq_answer_first']:>10.1%}  "
            f"{values['faq_concise']:>11.1%}  "
            f"{aggregate.score():>4.2f}"
        )
    values = total.ratios()
    print(
        f"{'TOTAL':<20} {total.pages:>5}  "
        f"{values['opening_reader_specific']:>6.1%}  "
        f"{values['empathy_then_conclusion']:>7.1%}  "
        f"{values['summary_answer_first']:>7.1%}  "
        f"{values['natural_h2']:>10.1%}  "
        f"{values['faq_answer_first']:>10.1%}  "
        f"{values['faq_concise']:>11.1%}  "
        f"{total.score():>4.2f}"
    )
    print(
        f"parsed={total.parse_complete}/{total.pages} h2={total.h2_total} faq={total.faq_total} "
        f"FAQ chars mean/p95/max={statistics.fmean(total.faq_lengths):.1f}/"
        f"{percentile(total.faq_lengths, 0.95)}/{max(total.faq_lengths, default=0)}"
        if total.faq_lengths
        else f"parsed={total.parse_complete}/{total.pages} h2={total.h2_total} faq={total.faq_total}"
    )
    print()
    print("targets:")
    for metric, target in TARGETS.items():
        print(f"  {metric}: {target:.0%}")
    print()
    print("top findings:")
    if not findings.counts:
        print("  none")
    else:
        for code, count in findings.counts.most_common(18):
            example = findings.examples[code][0] if findings.examples[code] else {}
            suffix = f" | {example.get('page')}: {example.get('detail')}" if example else ""
            print(f"  {code}: {count}{suffix}")
    print()
    if failures:
        print("target gaps:")
        for failure in failures:
            print(f"  - {failure}")
    else:
        print("target gaps: none")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero when scope, parsing, or a published target fails",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    # PowerShell may otherwise expose its legacy Korean code page to Python,
    # while CI/log collectors expect UTF-8 bytes.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args(argv if argv is not None else sys.argv[1:])
    findings = Findings()
    by_category = {category: Aggregate() for category in CATEGORIES}
    total = Aggregate()
    results: list[PageResult] = []
    category_counts: dict[str, int] = {}

    for category in CATEGORIES:
        paths = detail_paths(category)
        category_counts[category] = len(paths)
        for path in paths:
            result, faq_lengths = audit_page(path, category, findings)
            results.append(result)
            by_category[category].add(result, faq_lengths)
            total.add(result, faq_lengths)

    failures = target_failures(total, category_counts)
    if args.json:
        payload = {
            "scope": {
                "categories": CATEGORIES,
                "expected_details_per_category": EXPECTED_DETAILS_PER_CATEGORY,
                "actual_details_per_category": category_counts,
                "excluded": [
                    "body_image_distribution",
                    "public_evidence_links",
                    "low_priority_technical_checks",
                ],
            },
            "targets": TARGETS,
            "categories": {
                category: aggregate_payload(aggregate)
                for category, aggregate in by_category.items()
            },
            "total": aggregate_payload(total),
            "finding_counts": dict(findings.counts.most_common()),
            "finding_examples": dict(findings.examples),
            "target_failures": failures,
            "strict_pass": not failures,
            "page_results": [asdict(result) for result in results],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_report(by_category, total, findings, failures)

    return 1 if args.strict and failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
