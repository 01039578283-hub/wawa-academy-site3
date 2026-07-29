# -*- coding: utf-8 -*-
"""Improve the non-image search quality of coaching-academy local pages.

The site is a static export. This script deliberately preserves every image
element byte-for-byte while replacing repetitive/generated copy, rebuilding
FAQ markup and aligning the JSON-LD entity graph with the physical centers.

Run with ``--dry-run`` first. The transformation is deterministic and
idempotent so the generated pages can be audited and regenerated safely.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import random
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlsplit, urlunsplit


DOMAIN = "xn--sp5b72l1taf0p.com"
BASE_URL = f"https://{DOMAIN}"
TODAY = "2026-07-29"
CENTER_DIRNAME = "전국센터"
SCHOOL_FALLBACK = "학교별 진도 상담 확인"
GRADE_FALLBACK = "상담 시 학년 범위 확인"


CATEGORIES: dict[str, dict[str, Any]] = {
    "": {
        "stage": "초등·중등·고등",
        "subject": "영어·수학",
        "label": "영어·수학 학습관리",
        "meta_focus": "초중고 영어·수학 진단과 학습관리",
        "checks": "현재 진도, 과제 실행, 오답 기록, 시험 일정",
        "process": [
            ("학습 진단", [
                "현재 교재와 최근 시험 자료를 함께 살펴 우선 보완할 내용을 정합니다.",
                "성적표만 보지 않고 풀이 과정과 과제 습관까지 확인해 시작점을 찾습니다.",
                "과목별 진도와 자주 막히는 유형을 나누어 학습 순서를 정리합니다.",
            ]),
            ("주간 계획", [
                "학교 일정과 실제 공부 가능한 시간을 기준으로 한 주 계획을 세웁니다.",
                "과목별 우선순위와 숙제 분량을 학생이 실행할 수 있는 수준으로 조정합니다.",
                "시험 일정과 평소 학습 시간을 구분해 주간 계획의 밀도를 맞춥니다.",
            ]),
            ("실행 확인", [
                "계획한 분량의 완료 여부와 막힌 지점을 확인해 다음 학습에 반영합니다.",
                "과제 수행 결과를 확인하고 미완료 원인을 분량·난도·시간으로 나누어 봅니다.",
                "수업과 자습에서 정한 계획이 실제로 이어졌는지 주기적으로 점검합니다.",
            ]),
            ("오답 재학습", [
                "틀린 문제는 정답만 고치지 않고 원인을 기록한 뒤 다시 풀어 확인합니다.",
                "개념 부족과 실수, 문제 해석 오류를 구분해 필요한 방식으로 복습합니다.",
                "오답이 반복되는 단원은 풀이 과정을 다시 설명하고 유사 문제로 확인합니다.",
            ]),
        ],
        "students": [
            "과제는 하지만 틀린 이유를 기록하지 않는 학생",
            "시험 계획을 매번 늦게 시작하는 학생",
            "영어와 수학의 우선순위를 정하기 어려운 학생",
            "공부 시간은 길지만 완료한 분량이 분명하지 않은 학생",
            "선행보다 기초 단원 복습이 먼저 필요한 학생",
            "혼자 세운 계획을 꾸준히 실행하기 어려운 학생",
        ],
    },
    "초등영어학원": {
        "stage": "초등", "subject": "영어", "label": "초등 영어 학습관리",
        "meta_focus": "단어·문장 읽기·기초 문법과 독해 관리",
        "checks": "단어 기억, 문장 읽기, 기초 문법, 짧은 글 이해",
        "process": [
            ("읽기 기초", ["알파벳과 소리 연결부터 문장 단위 읽기까지 현재 단계를 확인합니다.", "낱말을 읽는 수준과 문장 의미를 이해하는 수준을 나누어 점검합니다.", "소리 내어 읽기와 의미 확인을 함께 진행해 읽기 기초를 살펴봅니다."]),
            ("어휘 반복", ["외운 단어를 문장 안에서 다시 만나도록 짧게 반복합니다.", "단어의 뜻만 암기하지 않고 예문과 함께 기억하는지 확인합니다.", "학습한 어휘를 읽기와 쓰기에 다시 활용하며 기억 상태를 점검합니다."]),
            ("문장 구조", ["주어와 동사 등 기초 구조를 실제 문장에서 구분하도록 돕습니다.", "기초 문법을 규칙 암기에 그치지 않고 짧은 문장 해석에 연결합니다.", "문장의 기본 순서를 익힌 뒤 읽기와 쓰기에 적용하는지 확인합니다."]),
            ("복습 기록", ["틀린 단어와 문장은 이유를 표시하고 일정 뒤 다시 확인합니다.", "읽기에서 막힌 표현을 기록해 다음 복습 범위에 포함합니다.", "반복해서 틀리는 철자와 문장을 모아 짧은 주기로 재확인합니다."]),
        ],
        "students": ["단어는 외우지만 문장 해석에서 멈추는 학생", "영어 읽기를 부담스러워하는 학생", "기초 문법과 독해 연결이 필요한 학생", "외운 단어를 자주 잊는 학생", "영어 공부 순서를 잡기 어려운 학생", "짧은 문장을 정확히 쓰는 연습이 필요한 학생"],
    },
    "초등수학학원": {
        "stage": "초등", "subject": "수학", "label": "초등 수학 학습관리",
        "meta_focus": "개념·연산·문장제와 오답 관리",
        "checks": "개념 이해, 연산 정확도, 문장제 해석, 풀이 기록",
        "process": [
            ("개념 확인", ["공식보다 개념이 만들어지는 과정을 설명할 수 있는지 확인합니다.", "교과서 개념을 예와 그림으로 이해했는지 먼저 살펴봅니다.", "새 단원을 풀기 전 필요한 이전 개념이 연결되는지 점검합니다."]),
            ("연산 정확도", ["속도만 높이기보다 반복되는 계산 실수의 원인을 구분합니다.", "연산 과정에서 자리값과 부호를 정확히 처리하는지 확인합니다.", "정확도를 먼저 확보한 뒤 학생 수준에 맞춰 풀이 속도를 조정합니다."]),
            ("문장제 해석", ["조건과 질문을 나누어 읽고 필요한 식을 스스로 세우도록 연습합니다.", "문장 속 수학 정보를 표시한 뒤 풀이 순서를 말로 정리합니다.", "문제의 조건을 빠뜨리지 않고 식으로 옮기는 과정을 확인합니다."]),
            ("오답 점검", ["개념·계산·해석 오류를 구분해 같은 실수가 반복되지 않게 합니다.", "틀린 답보다 풀이 중 어느 단계에서 어긋났는지 기록합니다.", "오답을 다시 풀고 비슷한 문제에서도 적용되는지 확인합니다."]),
        ],
        "students": ["연산 실수가 반복되는 학생", "문장제를 읽고 식을 세우기 어려운 학생", "개념은 알지만 응용 문제에서 멈추는 학생", "풀이 과정을 적지 않는 학생", "이전 학년의 빈 단원을 확인해야 하는 학생", "수학 숙제를 미루는 습관을 바꾸고 싶은 학생"],
    },
    "중등영어학원": {
        "stage": "중등", "subject": "영어", "label": "중등 영어 학습관리",
        "meta_focus": "교과서 본문·어휘·문법·서술형 관리",
        "checks": "교과서 본문, 시험 어휘, 문법 적용, 서술형 표현",
        "process": [
            ("본문 이해", ["교과서 본문의 핵심 문장과 연결 표현을 해석할 수 있는지 확인합니다.", "본문을 암기하기 전 문장 구조와 내용 흐름을 먼저 정리합니다.", "시험 범위 본문을 문단별로 나누어 의미와 구조를 점검합니다."]),
            ("어휘 관리", ["시험 범위 어휘를 뜻·철자·문장 활용으로 나누어 반복합니다.", "단어를 한 번 외우는 데 그치지 않고 누적 범위로 다시 확인합니다.", "본문과 문제에서 반복되는 어휘를 중심으로 기억 상태를 점검합니다."]),
            ("문법 적용", ["문법 규칙을 실제 내신 문장과 선택지에서 구분하도록 연습합니다.", "개념 설명 뒤 변형 문제와 서술형 문장에 적용되는지 확인합니다.", "자주 혼동하는 문법을 비교하고 틀린 이유를 설명하도록 합니다."]),
            ("서술형 대비", ["주어진 조건에 맞춰 문장을 완성하고 철자와 어순을 점검합니다.", "본문 표현을 활용해 서술형 답안을 만드는 과정을 연습합니다.", "감점이 잦은 어순·시제·철자를 답안 작성 뒤 다시 확인합니다."]),
        ],
        "students": ["본문은 외우지만 문법 문제에서 자주 틀리는 학생", "어휘 누적 복습이 필요한 학생", "서술형 답안을 만드는 데 시간이 오래 걸리는 학생", "학교 시험 범위 정리가 늦는 학생", "독해 속도와 정확도를 함께 높여야 하는 학생", "오답을 시험 직전에만 확인하는 학생"],
    },
    "중등수학학원": {
        "stage": "중등", "subject": "수학", "label": "중등 수학 학습관리",
        "meta_focus": "개념 연결·내신 유형·서술형과 오답 관리",
        "checks": "단원 개념, 내신 유형, 서술형 과정, 누적 오답",
        "process": [
            ("개념 연결", ["앞 단원의 개념이 새 단원에 어떻게 이어지는지 확인합니다.", "공식의 의미와 적용 조건을 설명한 뒤 문제에 연결합니다.", "개념 사이의 관계를 정리해 유형이 달라져도 적용하도록 돕습니다."]),
            ("내신 유형", ["학교 시험 범위에서 자주 출제되는 기본·변형 유형을 구분합니다.", "시험 범위와 현재 진도에 맞춰 우선 풀어야 할 유형을 정합니다.", "기본 문제의 정확도를 확인한 뒤 변형 문제로 범위를 넓힙니다."]),
            ("서술형 과정", ["답뿐 아니라 식을 세운 이유와 중간 과정을 남기도록 연습합니다.", "서술형에서 필요한 조건과 풀이 근거를 순서대로 적게 합니다.", "감점될 수 있는 생략과 계산 과정을 답안 작성 뒤 확인합니다."]),
            ("오답 누적", ["틀린 문제를 단원과 원인별로 모아 시험 전에 다시 확인합니다.", "개념 부족과 계산 실수를 구분해 서로 다른 방식으로 복습합니다.", "오답 풀이 뒤 유사 문제를 통해 같은 오류가 남아 있는지 살펴봅니다."]),
        ],
        "students": ["기본 문제는 풀지만 변형 유형에서 멈추는 학생", "계산 실수와 개념 오류를 구분하지 못하는 학생", "서술형 풀이를 생략하는 학생", "이전 단원의 빈틈이 다음 단원에 이어진 학생", "시험 범위별 복습 계획이 필요한 학생", "오답노트를 만들지만 다시 보지 않는 학생"],
    },
    "고등영어학원": {
        "stage": "고등", "subject": "영어", "label": "고등 영어 학습관리",
        "meta_focus": "내신·모의고사·어휘·구문과 오답 관리",
        "checks": "내신 범위, 모의고사 독해, 어휘 누적, 구문 분석",
        "process": [
            ("내신 범위", ["교과서와 부교재 범위를 나누어 핵심 문장과 변형 포인트를 확인합니다.", "학교 시험 자료를 기준으로 본문·어휘·문법의 우선순위를 정합니다.", "시험 범위별로 암기할 내용과 적용할 내용을 구분해 정리합니다."]),
            ("어휘·구문", ["어휘를 누적 복습하고 긴 문장의 핵심 구조를 정확히 찾도록 합니다.", "문장 성분과 수식 관계를 구분해 해석이 흔들리는 이유를 확인합니다.", "빈출 어휘와 구문을 독해 지문 안에서 다시 적용하도록 연습합니다."]),
            ("모의고사 독해", ["유형별 풀이 시간과 오답 원인을 기록해 독해 순서를 조정합니다.", "지문 구조와 근거 문장을 찾는 과정을 유형별로 점검합니다.", "시간 부족과 해석 오류를 나누어 필요한 독해 훈련을 정합니다."]),
            ("오답 분석", ["정답 근거를 다시 찾고 어휘·구문·추론 중 원인을 구분합니다.", "틀린 선택지를 고른 이유를 확인해 같은 판단 오류를 줄입니다.", "오답 지문을 다시 읽고 근거 문장을 설명할 수 있는지 확인합니다."]),
        ],
        "students": ["내신과 모의고사 공부 순서를 정하기 어려운 학생", "어휘는 알지만 긴 문장 해석이 흔들리는 학생", "독해 시간이 부족한 학생", "오답의 근거를 다시 찾지 않는 학생", "학교별 시험 자료 정리가 필요한 학생", "서술형에서 어순과 문법 감점이 잦은 학생"],
    },
    "고등수학학원": {
        "stage": "고등", "subject": "수학", "label": "고등 수학 학습관리",
        "meta_focus": "내신·수능형 문제·서술형과 오답 관리",
        "checks": "단원 개념, 내신 유형, 수능형 접근, 서술형 풀이",
        "process": [
            ("개념 조건", ["공식을 외우는 데 그치지 않고 적용 조건과 단원 연결을 확인합니다.", "개념의 정의와 성질을 문제 상황에서 구분해 쓰는지 살펴봅니다.", "문제 풀이 전 필요한 개념과 조건을 스스로 찾도록 연습합니다."]),
            ("내신 유형", ["학교 시험 범위와 기출 경향을 기준으로 우선 유형을 정합니다.", "기본·변형·서술형 문제를 나누어 범위별 완성도를 확인합니다.", "시험 범위에서 자주 틀리는 유형과 계산 과정을 집중 점검합니다."]),
            ("수능형 접근", ["조건 해석과 풀이 발상을 구분해 막힌 지점을 기록합니다.", "문제의 조건을 식과 그림으로 정리한 뒤 접근 순서를 설명하게 합니다.", "시간 안에 풀 문제와 충분히 분석할 문제를 나누어 학습합니다."]),
            ("오답 재풀이", ["개념·계산·조건 해석·발상 오류를 나누어 다시 풀게 합니다.", "해설을 본 문제는 일정 뒤 풀이를 재현할 수 있는지 확인합니다.", "오답의 첫 오류 지점을 표시하고 유사 문제로 적용 여부를 살펴봅니다."]),
        ],
        "students": ["개념은 알지만 문제 접근을 시작하기 어려운 학생", "내신과 수능형 문제의 균형을 잡아야 하는 학생", "계산 실수가 반복되는 학생", "해설을 본 뒤 혼자 다시 풀지 못하는 학생", "서술형 풀이 과정에서 감점이 잦은 학생", "시험 범위 복습을 체계적으로 나눠야 하는 학생"],
    },
}


@dataclass
class CenterRecord:
    key: tuple[str, str, str]
    primary_url: str
    name: str
    address: str
    telephone: str
    identifier: dict[str, Any] | None
    alternate_name: Any
    contact_point: Any
    areas: list[str]


@dataclass
class CenterInfo:
    locality: str
    region: str
    district: str
    center_name: str
    tuition_url: str
    registration_name: str
    registration_number: str
    address: str
    schools: dict[str, list[str]]
    grades: dict[str, list[str]]


@dataclass
class PageContext:
    path: Path
    text: str
    data: dict[str, Any]
    graph: list[dict[str, Any]]
    title: str
    locality: str
    category: str
    config: dict[str, Any]
    region: str
    center: CenterRecord
    info: CenterInfo
    schools: list[str]
    rng: random.Random
    page_url: str
    parent_url: str
    image_block: str
    map_image: str


def strip_tags(value: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value)).split())


def normalize_locality(value: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value)).strip()


def split_csv_values(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"[,，]", value or "") if part.strip()]


def is_specific_school(value: str) -> bool:
    return bool(re.fullmatch(r"\S+(?:초|중|고)", value.strip()))


def split_school_values(value: str) -> list[str]:
    """Split comma-delimited cells and legacy whitespace-delimited school lists."""
    result: list[str] = []
    for group in split_csv_values(value):
        tokens = group.split()
        if len(tokens) > 1 and all(is_specific_school(token) for token in tokens):
            result.extend(tokens)
        else:
            result.append(group)
    return list(dict.fromkeys(result))


def locality_without_district_prefix(info: CenterInfo) -> str:
    locality = info.locality.strip()
    district_stem = re.sub(r"(?:특별자치시|광역시|특별시|시|군|구)$", "", info.district.strip())
    if district_stem:
        shortened = re.sub(rf"^\s*{re.escape(district_stem)}\s*", "", locality, count=1)
        if shortened.strip():
            return shortened.strip()
    return locality


def full_region(info: CenterInfo) -> str:
    locality = locality_without_district_prefix(info)
    return " ".join(part for part in (info.region, info.district, locality) if part).strip()


def load_center_info(root: Path) -> dict[str, CenterInfo]:
    csv_path = root.parent / "참고자료" / "공통자료" / "센터정보 정리.csv"
    if not csv_path.is_file():
        raise FileNotFoundError(f"Center information CSV not found: {csv_path}")
    result: dict[str, CenterInfo] = {}
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            locality = str(row.get("근처 수업가능 동네", "")).strip()
            key = normalize_locality(locality)
            if not key:
                continue
            result[key] = CenterInfo(
                locality=locality,
                region=str(row.get("지역", "")).strip(),
                district=str(row.get("시or구", "")).strip(),
                center_name=str(row.get("센터명", "")).strip(),
                tuition_url=str(row.get("센터 교습비", "")).strip(),
                registration_name=str(row.get("교육지원청명칭", "")).strip(),
                registration_number=str(row.get("교육지원청 등록번호", "")).strip(),
                address=str(row.get("센터 주소", "")).strip(),
                schools={
                    "초등": split_school_values(str(row.get("타깃학교\n(초)", ""))),
                    "중등": split_school_values(str(row.get("타깃학교\n(중)", ""))),
                    "고등": split_school_values(str(row.get("타깃학교\n(고)", ""))),
                },
                grades={
                    "국어": split_csv_values(str(row.get("가능학년\n(국어)", ""))),
                    "영어": split_csv_values(str(row.get("가능학년\n(영어)", ""))),
                    "수학": split_csv_values(str(row.get("가능학년\n(수학)", ""))),
                    "과학": split_csv_values(str(row.get("가능학년\n(과학)", ""))),
                    "사회": split_csv_values(str(row.get("가능학년\n(사회)", ""))),
                },
            )
    return result


def node_has_type(node: dict[str, Any], kind: str) -> bool:
    value = node.get("@type")
    return kind in value if isinstance(value, list) else value == kind


def find_node(graph: list[dict[str, Any]], kind: str) -> dict[str, Any] | None:
    return next((node for node in graph if isinstance(node, dict) and node_has_type(node, kind)), None)


def page_url(path: Path, root: Path) -> str:
    rel = path.relative_to(root)
    if rel.as_posix() == "index.html":
        return BASE_URL + "/"
    encoded = "/".join(quote(part) for part in rel.parts[:-1])
    return f"{BASE_URL}/{encoded}/"


def stable_rng(path: Path, root: Path) -> random.Random:
    digest = hashlib.sha256(path.relative_to(root).as_posix().encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def parse_jsonld(text: str) -> tuple[dict[str, Any], re.Match[str]]:
    match = re.search(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', text, re.I | re.S)
    if not match:
        raise ValueError("JSON-LD script not found")
    data = json.loads(html.unescape(match.group(1)))
    if not isinstance(data, dict) or not isinstance(data.get("@graph"), list):
        raise ValueError("JSON-LD @graph not found")
    return data, match


def org_key(org: dict[str, Any]) -> tuple[str, str, str]:
    identifier = org.get("identifier") if isinstance(org.get("identifier"), dict) else {}
    address = org.get("address") if isinstance(org.get("address"), dict) else {}
    return (
        str(identifier.get("value", "")).strip(),
        str(org.get("name", "")).strip(),
        str(address.get("streetAddress", "")).strip(),
    )


def build_center_records(root: Path, local_pages: list[Path]) -> tuple[dict[tuple[str, str, str], CenterRecord], dict[str, tuple[str, str, str]]]:
    raw: dict[tuple[str, str, str], dict[str, Any]] = {}
    locality_to_key: dict[str, tuple[str, str, str]] = {}
    for path in local_pages:
        text = path.read_text(encoding="utf-8")
        data, _ = parse_jsonld(text)
        graph = data["@graph"]
        org = find_node(graph, "EducationalOrganization")
        if not org:
            raise ValueError(f"Organization missing: {path}")
        key = org_key(org)
        locality = path.parent.name
        locality_to_key[locality] = key
        area = org.get("areaServed") if isinstance(org.get("areaServed"), dict) else {}
        area_name = str(area.get("name", locality)).strip()
        entry = raw.setdefault(key, {"paths": [], "areas": set(), "org": org})
        entry["paths"].append(path)
        entry["areas"].add(area_name)

    records: dict[tuple[str, str, str], CenterRecord] = {}
    for key, entry in raw.items():
        paths = sorted(entry["paths"], key=lambda value: value.parent.name)
        org = entry["org"]
        address = org.get("address") if isinstance(org.get("address"), dict) else {}
        primary = page_url(paths[0], root)
        records[key] = CenterRecord(
            key=key,
            primary_url=primary,
            name=str(org.get("name", "와와학습코칭센터")),
            address=str(address.get("streetAddress", "")),
            telephone=str(org.get("telephone", "010-3957-8283")),
            identifier=org.get("identifier") if isinstance(org.get("identifier"), dict) else None,
            alternate_name=org.get("alternateName"),
            contact_point=org.get("contactPoint"),
            areas=sorted(entry["areas"]),
        )
    return records, locality_to_key


def extract_schools(text: str) -> list[str]:
    block = re.search(r'<div class="wrap school-card">(.*?)</section>', text, re.S)
    if not block:
        return []
    values = [strip_tags(value) for value in re.findall(r"<span>(.*?)</span>", block.group(1), re.S)]
    return list(dict.fromkeys(value for value in values if value and value != "상담 시 확인"))


def context_for(
    path: Path,
    root: Path,
    records: dict[tuple[str, str, str], CenterRecord],
    locality_to_key: dict[str, tuple[str, str, str]],
    center_info: dict[str, CenterInfo],
) -> PageContext:
    text = path.read_text(encoding="utf-8")
    data, _ = parse_jsonld(text)
    graph = data["@graph"]
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.I | re.S)
    if not h1:
        raise ValueError(f"H1 missing: {path}")
    title = strip_tags(h1.group(1))
    parts = path.relative_to(root).parts
    locality = parts[1]
    info_key = normalize_locality(locality)
    if info_key not in center_info:
        raise ValueError(f"Center information missing: {locality} ({path})")
    info = center_info[info_key]
    category = parts[2] if len(parts) == 4 else ""
    config = CATEGORIES[category]
    region = full_region(info) or locality
    key = locality_to_key[locality]
    image_match = re.search(r'<div class="local-image-pair local-media-section">.*?</div>', text, re.S)
    if not image_match:
        raise ValueError(f"Image block missing: {path}")
    map_match = re.search(r'<div class="wrap location-card">.*?(<img\b[^>]*>)\s*</div>', text, re.I | re.S)
    if not map_match:
        map_match = re.search(r'<figure class="verified-map-card">\s*(<img\b[^>]*>)', text, re.I | re.S)
    if not map_match:
        raise ValueError(f"Map image missing: {path}")
    current_url = page_url(path, root)
    parent_path = root / CENTER_DIRNAME / locality / "index.html"
    return PageContext(
        path=path, text=text, data=data, graph=graph, title=title, locality=locality,
        category=category, config=config, region=region, center=records[key], info=info,
        schools=extract_schools(text), rng=stable_rng(path, root), page_url=current_url,
        parent_url=page_url(parent_path, root), image_block=image_match.group(0), map_image=map_match.group(1),
    )


def choose(ctx: PageContext, values: list[str]) -> str:
    return values[ctx.rng.randrange(len(values))]


def keyed_choose(ctx: PageContext, namespace: str, values: list[str]) -> str:
    """Choose a variant independently of the other generated sections.

    Using an independent key keeps title/snippet variants stable even when a
    new content block is inserted elsewhere in the generator.
    """
    key = f"{ctx.path.as_posix()}|{namespace}".encode("utf-8")
    index = int.from_bytes(hashlib.sha256(key).digest()[:8], "big") % len(values)
    return values[index]


def school_phrase(ctx: PageContext, limit: int = 3) -> str:
    if ctx.schools:
        return "·".join(ctx.schools[:limit])
    return "학교·학년별 개설 여부"


def registration_value(ctx: PageContext) -> str:
    if ctx.info.registration_number:
        return ctx.info.registration_number
    if ctx.center.identifier:
        return str(ctx.center.identifier.get("value", "")).strip()
    return "센터 상담 시 확인"


def available_grade_items(ctx: PageContext) -> list[str]:
    stage_prefix = {"초등": "초", "중등": "중", "고등": "고"}
    if not ctx.category:
        values: list[str] = []
        for subject in ("영어", "수학"):
            grades = ctx.info.grades.get(subject, [])
            if grades:
                values.append(f"{subject} {'·'.join(grades)}")
        return values
    prefix = stage_prefix.get(ctx.config["stage"], "")
    return [grade for grade in ctx.info.grades.get(ctx.config["subject"], []) if grade.startswith(prefix)]


def available_grade_text(ctx: PageContext) -> str:
    values = available_grade_items(ctx)
    return " / ".join(values) if values else GRADE_FALLBACK


def actual_center_name(ctx: PageContext) -> str:
    return ctx.info.center_name or ctx.center.name


def actual_address(ctx: PageContext) -> str:
    return ctx.info.address or ctx.center.address


def actual_school_phrase(ctx: PageContext, limit: int = 4) -> str:
    if not ctx.category:
        schools = list(dict.fromkeys(ctx.info.schools["초등"] + ctx.info.schools["중등"] + ctx.info.schools["고등"]))
    else:
        schools = ctx.info.schools.get(ctx.config["stage"], [])
    schools = [school for school in schools if is_specific_school(school)]
    if not schools:
        schools = [school for school in ctx.schools if is_specific_school(school)]
    return "·".join(schools[:limit]) if schools else SCHOOL_FALLBACK


def locality_stem(value: str) -> str:
    """Return a conservative stem used only to explain service-area pages.

    The CSV contains both physical-centre neighbourhoods and nearby service
    areas.  A missing stem match is not treated as an error or a distance
    claim; it only triggers clearer wording about the actual visit address.
    """
    # Some manifest labels contain a regional prefix (for example
    # ``울산 삼산동`` or ``부천 상동``).  The last token is the actual
    # neighbourhood and is the part that should be compared with the centre
    # name/address.
    tokens = re.findall(r"[^\s]+", unicodedata.normalize("NFKC", value or "").strip())
    compact = normalize_locality(tokens[-1] if tokens else value)
    compact = re.sub(r"(?:국제도시|신도시|중앙|마을|지구|동|읍|면|리)$", "", compact)
    return compact


def is_service_area_page(ctx: PageContext) -> bool:
    stem = locality_stem(ctx.info.locality or ctx.locality)
    if len(stem) < 2:
        return False
    physical = normalize_locality(f"{actual_center_name(ctx)} {actual_address(ctx)}")
    return stem not in physical


def source_basis(ctx: PageContext) -> str:
    parts = ["학원 제공 센터정보", "교육지원청 등록정보"]
    if ctx.info.tuition_url:
        parts.append("연결된 교습비 공개자료")
    return " · ".join(parts)


def check_items(ctx: PageContext) -> list[str]:
    return [item.strip() for item in ctx.config["checks"].split(",") if item.strip()]


def seo_title(ctx: PageContext) -> str:
    suffixes = {
        "": "영어·수학 진단·계획·오답관리",
        "초등영어학원": "기초 독해·문법 학습관리",
        "초등수학학원": "개념·연산·오답 학습관리",
        "중등영어학원": "내신·서술형 학습관리",
        "중등수학학원": "내신·서술형 학습관리",
        "고등영어학원": "내신·모의고사 학습관리",
        "고등수학학원": "내신·수능형 학습관리",
    }
    return f"{ctx.title} | {suffixes[ctx.category]}"


def _complete_sentence(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().rstrip(".。 ") + "."


def short_center_name(ctx: PageContext) -> str:
    value = actual_center_name(ctx)
    value = re.sub(r"^와와학습코칭(?:센터|학원)\s*", "", value).strip()
    return value or actual_center_name(ctx)


def meta_description(ctx: PageContext) -> str:
    school = actual_school_phrase(ctx, 1)
    center = short_center_name(ctx)
    focus = ctx.config["meta_focus"]
    school_known = school != SCHOOL_FALLBACK
    service_area = is_service_area_page(ctx)
    if service_area:
        candidates = [
            f"{ctx.title}: {focus}를 점검하고 연결 센터 {center}의 실제 방문 주소와 가능 학년을 안내합니다",
            f"{ctx.title}: {center} 상담권역에서 {focus}와 학생 일정, 실제 방문 위치를 함께 확인합니다",
            f"{ctx.title}: {school + ' 등 재학 학교 자료' if school_known else '최근 학습자료'}로 {focus}를 살피고 연결 센터 주소를 안내합니다",
            f"{ctx.title}: {focus} 범위를 확인한 뒤 플래너 실행과 오답 재학습, {center} 방문 정보를 안내합니다",
            f"{ctx.title}: {ctx.locality} 학생의 {focus}와 연결 센터 {center}의 개설 학년·위치를 확인합니다",
            f"{ctx.title}: {school if school_known else '재학 학교'} 진도에 맞춘 {focus}와 실제 상담 센터 위치를 정리했습니다",
        ]
    else:
        candidates = [
            f"{ctx.title}: {school if school_known else '현재 교재'} 기준 {focus}를 점검하고 {center}의 가능 학년·위치를 안내합니다",
            f"{ctx.title}: {center}에서 {focus}를 확인하고 학생에게 맞는 진단·계획·오답관리 순서를 정리합니다",
            f"{ctx.title}: {school + ' 등 재학 학교 자료' if school_known else '최근 학습자료'}와 {focus}, 실제 센터 주소·개설 학년을 확인합니다",
            f"{ctx.title}: 최근 교재와 평가자료로 {focus}를 살피고 {center}의 상담 기준과 방문 정보를 안내합니다",
            f"{ctx.title}: {focus} 범위를 확인한 뒤 플래너 실행과 오답 재학습까지 이어지는 관리 기준을 안내합니다",
            f"{ctx.title}: {school if school_known else '재학 학교'} 진도에 맞춘 {focus}와 {center}의 실제 상담 정보를 정리했습니다",
        ]
    complete = [_complete_sentence(value) for value in candidates]
    eligible = [value for value in complete if 60 <= len(value) <= 80]
    if eligible:
        return keyed_choose(ctx, "meta-description", eligible)

    fallback = _complete_sentence(
        f"{ctx.title}: {focus}를 점검하고 {center}의 실제 방문 위치와 가능 학년, 상담 준비 자료를 안내합니다"
    )
    if len(fallback) < 60:
        fallback = fallback.rstrip(".") + " 최근 교재와 시간표도 함께 확인합니다."
    if len(fallback) > 80:
        fallback = _complete_sentence(
            f"{ctx.title}: {ctx.config['label']}의 진단·계획·오답관리와 실제 센터 위치, 가능 학년을 안내합니다"
        )
    if not 60 <= len(fallback) <= 80:
        raise ValueError(f"Unable to fit meta description ({len(fallback)}): {ctx.path}")
    return fallback


def hero_intro(ctx: PageContext) -> str:
    if is_service_area_page(ctx):
        templates = [
            "{title}에서는 {checks} 기록을 먼저 살펴 학습 우선순위를 정합니다. 이 지역은 {center} 상담권역이며 실제 방문 주소는 아래 센터 정보에서 구분해 안내합니다.",
            "{title} 상담은 현재 성적만 비교하지 않고 {checks} 상태를 나누어 확인합니다. 수업 상담은 {center}로 연결되므로 방문 전에 실제 주소와 시간표를 확인해 주세요.",
            "{title}을 찾는 학생은 최근 교재에서 {checks} 중 막힌 지점을 표시해 두는 것이 좋습니다. 이 페이지의 실제 안내 센터는 {center}입니다.",
            "{title} 학습 방향은 {checks} 기록과 학교 일정을 함께 보고 정합니다. {locality} 상담권역은 {center}로 연결되며 센터 위치를 별도로 명시했습니다.",
            "{title} 선택 전에는 {checks} 상태와 실행 가능한 시간을 먼저 구분해야 합니다. 실제 상담 장소는 {center}이므로 페이지의 주소를 확인해 주세요.",
            "{title}은 진단에서 끝나지 않고 계획 실행과 오답 재학습까지 연결해야 합니다. {locality} 안내는 {center}의 확인된 센터정보를 기준으로 작성했습니다.",
            "{title} 상담에서는 최근 자료로 {checks} 상태를 확인한 뒤 가능한 관리 순서를 정합니다. {locality} 학생의 방문 센터는 {center}입니다.",
            "{title} 페이지는 {checks} 중 우선 보완할 항목과 실제 수업 가능 범위를 구분합니다. 연결 상담 센터는 {center}이며 주소는 아래에서 확인할 수 있습니다.",
        ]
    else:
        templates = [
            "{title}에서는 {checks} 중 반복해서 막히는 지점을 먼저 찾습니다. {center}의 실제 개설 정보와 학생 일정을 대조해 학습 순서를 정합니다.",
            "{title} 상담은 현재 교재와 최근 평가자료에서 {checks} 상태를 확인하는 것부터 시작합니다. {center}에서 진단·계획·오답관리 순서를 안내합니다.",
            "{title}을 선택할 때는 성적만 보지 않고 {checks} 기록을 함께 확인해야 합니다. 실제 상담 장소는 {center}이며 가능 학년은 센터 자료를 기준으로 안내합니다.",
            "{title} 학습 방향은 학생이 막힌 원인과 실행 가능한 시간을 구분해 정합니다. {center}의 시간표와 맞춰 계획 실행과 재학습 범위를 확인합니다.",
            "{title}에서는 학습량보다 {checks} 가운데 먼저 바꿀 항목을 구체적으로 찾습니다. {center} 상담에서 학생별 시작 범위를 확인할 수 있습니다.",
            "{title} 상담 전 최근 교재와 오답 기록을 준비하면 {checks} 상태를 더 정확히 구분할 수 있습니다. 안내 정보는 {center}의 확인 자료를 기준으로 합니다.",
            "{title}은 진단·주간계획·실행확인·오답 재학습이 한 흐름으로 이어져야 합니다. {center}의 개설 학년과 학생 일정을 함께 확인합니다.",
            "{title} 페이지에서는 {checks} 항목을 학생 상황에 맞춰 나누고, {center}에서 실제로 이어갈 수 있는 학습 범위를 정리합니다.",
        ]
    return keyed_choose(ctx, "hero-intro", templates).format(
        title=ctx.title,
        checks=ctx.config["checks"],
        center=actual_center_name(ctx),
        locality=ctx.locality,
    )


def hero_center_fact(ctx: PageContext) -> str:
    label = "상담권역의 실제 방문 센터" if is_service_area_page(ctx) else "확인된 상담 장소"
    note = f"{ctx.locality} 상담권역" if is_service_area_page(ctx) else f"{ctx.locality} 센터 안내"
    return f'''              <div class="hero-center-fact">
                <span>{html.escape(label)}</span>
                <strong>{html.escape(actual_center_name(ctx))}</strong>
                <small>{html.escape(actual_address(ctx))} · {html.escape(note)}</small>
              </div>'''


def representative_image_url(ctx: PageContext) -> str:
    match = re.search(
        r'<img\b[^>]*data-role=["\']representative-image["\'][^>]*\bsrc=["\']([^"\']+)',
        ctx.image_block,
        re.I,
    )
    if not match:
        match = re.search(r'<meta\b[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)', ctx.text, re.I)
    return html.unescape(match.group(1)) if match else BASE_URL + "/assets/generated/site3-hero.webp"


def method_intro(ctx: PageContext) -> tuple[str, str, str]:
    headings = [
        f"{ctx.title}, 무엇부터 확인해야 할까요?",
        f"{ctx.title} 상담 전 살펴볼 학습 기준",
        f"{ctx.title}에서 중요한 관리 순서",
        f"{ctx.title} 학습 방향을 정하는 방법",
    ]
    first = [
        f"{ctx.locality} {ctx.config['label']}에서는 학습량을 늘리기 전에 {ctx.config['checks']} 중 어디에서 어려움이 생기는지 구분하는 과정이 먼저입니다.",
        f"{ctx.locality} 학생마다 필요한 보완 범위가 다르므로 {ctx.config['checks']} 항목을 한 번에 점검한 뒤 우선순위를 정하는 것이 좋습니다.",
        f"{actual_center_name(ctx)} 상담에서는 현재 결과만 평가하지 않고 {ctx.config['checks']} 항목을 살펴 실제로 이어갈 수 있는 계획을 정합니다.",
        f"{ctx.locality}의 같은 학년 학생이라도 막히는 지점은 다를 수 있어 {ctx.config['checks']} 항목을 나누어 확인해야 합니다.",
        f"{ctx.config['label']}의 시작점은 {ctx.locality} 학생이 가져온 교재와 최근 기록에서 {ctx.config['checks']} 상태를 구분하는 것입니다.",
        f"{ctx.locality}에서 {ctx.config['label']} 상담을 알아볼 때에는 {ctx.config['checks']} 가운데 먼저 바꿀 항목과 오래 관리할 항목을 나누어야 합니다.",
    ]
    school = actual_school_phrase(ctx)
    center_name = actual_center_name(ctx)
    if school == SCHOOL_FALLBACK:
        second = [
            f"재학 학교의 진도와 시험 범위는 {center_name} 상담에서 현재 교재와 함께 확인합니다.",
            f"학교명이 제공된 자료에 없을 때는 임의로 넣지 않고 현재 교재와 최근 시험 자료로 필요한 범위를 정합니다.",
            f"{ctx.locality} 학생의 재학 학교 일정과 공부 가능 시간을 알려주면 {ctx.config['label']}의 시작 범위를 더 구체적으로 조정할 수 있습니다.",
            f"학교별 진도는 상담에서 확인하므로 현재 사용하는 교재와 최근 평가 자료를 {center_name} 방문 전에 준비해 주세요.",
            f"학교 정보가 따로 표시되지 않은 경우 학생의 실제 진도와 시험 일정을 기준으로 학습 순서를 정합니다.",
            f"제공 자료에 없는 학교명은 추가하지 않았습니다. 상담에서는 학생이 가져온 교재와 시험 범위부터 확인합니다.",
        ]
    else:
        second = [
            f"이 페이지에는 {school} 학생이 참고할 수 있는 상담 범위와 {center_name} 위치 정보를 함께 정리했습니다.",
            f"{school} 관련 상담을 준비한다면 현재 교재와 최근 시험 자료를 가져오면 필요한 범위를 더 구체적으로 확인할 수 있습니다.",
            f"센터 정보와 학교 참고 목록은 상담 범위를 이해하기 위한 자료이며, 실제 개설 여부는 학년과 시간표에 따라 확인합니다.",
            f"{center_name}의 주소와 학교 참고 정보를 확인한 뒤 방문 전 상담 시간을 먼저 맞추는 것을 권합니다.",
        ]
    return choose(ctx, headings), choose(ctx, first), choose(ctx, second)


def process_items(ctx: PageContext) -> list[tuple[str, str]]:
    school = actual_school_phrase(ctx, 2)
    items: list[tuple[str, str]] = []
    for index, (label, variants) in enumerate(ctx.config["process"]):
        body = choose(ctx, variants).rstrip(".。")
        frames = [
            f"{ctx.locality} {ctx.config['label']}의 {label} 단계에서는 {body}.",
            f"학생의 현재 자료를 기준으로 {body}. 이후 {actual_center_name(ctx)} 상담에서 다음 확인 범위를 정합니다.",
            f"{ctx.config['checks']} 상태를 함께 살피면서 {body}.",
            (f"{school}의 교재·일정을 참고할 때에도 {body}." if school != SCHOOL_FALLBACK
             else f"재학 학교의 교재와 일정을 확인하면서 {body}."),
            f"{ctx.locality} 학생이 실제로 이어갈 수 있도록 {body}.",
        ]
        items.append((label, frames[(ctx.rng.randrange(len(frames)) + index) % len(frames)]))
    return items


def build_primary_section(ctx: PageContext) -> str:
    heading, paragraph1, paragraph2 = method_intro(ctx)
    items = "\n".join(f"            <li><strong>{html.escape(label)}</strong>{html.escape(body)}</li>" for label, body in process_items(ctx))
    schools = actual_school_phrase(ctx)
    grades = available_grade_text(ctx)
    center_name = actual_center_name(ctx)
    target = f"{ctx.config['stage']} {ctx.config['subject']} 학습 방향을 구체적으로 정리하려는 학생"
    return f'''    <section id="learning-plan" class="local-section">
      <div class="wrap local-grid">
        <article class="local-card">
          <h2>{html.escape(heading)}</h2>
          <p>{html.escape(paragraph1)}</p>
          <p>{html.escape(paragraph2)}</p>
          <h3>{html.escape(ctx.config['label'])} 핵심</h3>
          <ul class="process-list">
{items}
          </ul>
          {ctx.image_block}
        </article>
        <aside class="local-card">
          <h2>상담 요약</h2>
          <ul class="summary-list">
            <li>대상: {html.escape(target)}</li>
            <li>확인: {html.escape(ctx.config['checks'])}</li>
            <li>가능 학년: {html.escape(grades)}</li>
            <li>학교 참고: {html.escape(schools)}</li>
            <li>실제 안내 센터: {html.escape(center_name)}</li>
            <li>상담: 전화 · 문자 · 온라인 신청 가능</li>
          </ul>
        </aside>
      </div>
    </section>'''


def build_verified_section(ctx: PageContext) -> str:
    school_values = []
    if not ctx.category:
        school_values = list(dict.fromkeys(ctx.info.schools["초등"] + ctx.info.schools["중등"] + ctx.info.schools["고등"]))
    else:
        school_values = ctx.info.schools.get(ctx.config["stage"], [])
    school_markup = ("".join(f"<span>{html.escape(school)}</span>" for school in school_values)
                     if school_values else "<span>재학 학교 진도는 상담 시 확인</span>")
    tuition = (f'<a class="text-link" href="{html.escape(ctx.info.tuition_url, quote=True)}" target="_blank" rel="noopener noreferrer">센터 교습비 자료 확인</a>'
               if ctx.info.tuition_url else "")
    tuition_block = f"          {tuition}\n" if tuition else ""
    if is_service_area_page(ctx):
        relationship_label = "연결 상담 센터 정보"
        relationship_note = (
            f"{ctx.locality} 페이지는 제공된 상담권역 자료에 따라 {actual_center_name(ctx)}로 연결됩니다. "
            "페이지의 지역명과 실제 센터 위치가 다를 수 있으므로 방문 위치는 아래 센터명과 주소를 기준으로 확인해 주세요."
        )
    else:
        relationship_label = "확인된 센터 정보"
        if available_grade_items(ctx):
            relationship_note = (
                f"{ctx.locality} 페이지에 연결된 실제 상담 센터입니다. 등록 전 {available_grade_text(ctx)} 개설 여부와 "
                "현재 시간표를 다시 확인해 주세요."
            )
        else:
            relationship_note = (
                f"{ctx.locality} 페이지에 연결된 실제 상담 센터입니다. 제공 자료에 학년 범위가 따로 표시되지 않아 "
                "학생의 현재 학년과 센터 시간표를 상담에서 확인해야 합니다."
            )
    school_context = actual_school_phrase(ctx)
    school_statement = (
        f"{school_context} 등 표시된 학교명은 상담 범위를 이해하기 위한 참고 정보입니다."
        if school_context != SCHOOL_FALLBACK
        else "재학 학교 정보는 상담 범위를 이해하기 위한 참고 정보입니다."
    )
    verified_note = choose(ctx, [
        f"{school_statement} 실제 개설 여부는 학생의 학년·과목과 {actual_center_name(ctx)} 시간표를 함께 확인합니다.",
        f"표시된 학교는 {ctx.locality} 상담 준비를 위한 참고 자료이며 수업 개설을 뜻하지 않습니다. 등록 전 {ctx.config['stage']} 학년과 {ctx.config['subject']} 개설 시간을 확인해 주세요.",
        f"참고 학교와 별개로 학생의 현재 진도와 {actual_center_name(ctx)} 시간표를 대조한 뒤 실제 수업 가능 여부를 안내합니다.",
        f"학교 정보는 {ctx.config['label']} 상담 준비를 위한 기준입니다. 수업 여부는 학년, 선택 과목, 센터의 현재 개설 시간을 확인한 후 결정됩니다.",
        f"{ctx.locality} 학생은 재학 학교의 교재와 시험 일정을 준비하되, 수업 가능 여부는 {actual_center_name(ctx)}의 최신 시간표로 확인해야 합니다.",
    ])
    source_notes = [
        f"확인 자료: {source_basis(ctx)} · 정리일 {TODAY}",
        f"안내 근거: {source_basis(ctx)} · 최종 확인 {TODAY}",
        f"센터 정보 출처: {source_basis(ctx)} · 페이지 확인일 {TODAY}",
        f"페이지 작성 기준: {source_basis(ctx)} · 정보 정리 {TODAY}",
    ]
    source_note = keyed_choose(ctx, "source-note", source_notes)
    return f'''    <section id="verified-center" class="local-section verified-center-section">
      <div class="wrap verified-center-grid">
        <article class="verified-center-card">
          <p class="eyebrow">{html.escape(relationship_label)}</p>
          <h2>{html.escape(actual_center_name(ctx))}</h2>
          <p class="verified-note">{html.escape(relationship_note)}</p>
          <dl class="verified-data-list">
            <div><dt>수업 가능 학년</dt><dd>{html.escape(available_grade_text(ctx))}</dd></div>
            <div><dt>주소</dt><dd>{html.escape(actual_address(ctx))}</dd></div>
            <div><dt>등록 정보</dt><dd>{html.escape(registration_value(ctx))}</dd></div>
          </dl>
{tuition_block}          <div class="verified-school-list" aria-label="상담 참고 학교">{school_markup}</div>
          <p class="verified-note">{html.escape(verified_note)}</p>
          <p class="verified-note source-note">{html.escape(source_note)}</p>
        </article>
        <figure class="verified-map-card">
          {ctx.map_image}
          <figcaption>{html.escape(ctx.locality)} 생활권에서 방문할 때 참고할 센터 위치 이미지입니다.</figcaption>
        </figure>
      </div>
    </section>'''


def student_answer(ctx: PageContext, student: str, index: int) -> str:
    focuses = check_items(ctx)
    focus = focuses[(ctx.rng.randrange(len(focuses)) + index) % len(focuses)]
    process_count = len(ctx.config["process"])
    process_label, process_variants = ctx.config["process"][(ctx.rng.randrange(process_count) + index) % process_count]
    action = choose(ctx, process_variants)
    school = actual_school_phrase(ctx, 2)
    grades = available_grade_text(ctx)
    evidence = [
        f"{ctx.locality} 학생의 최근 교재에서 ‘{focus}’ 항목이 막힌 지점을 먼저 표시합니다.",
        f"{student} 상황은 과제 기록과 최근 평가 자료에서 ‘{focus}’ 항목을 함께 살펴 원인을 구분합니다.",
        (f"{school}의 교재·시험 일정을 참고하되 학생 풀이에서 ‘{focus}’ 상태를 먼저 확인합니다."
         if school != SCHOOL_FALLBACK
         else f"재학 학교의 교재와 시험 일정을 준비하고 ‘{focus}’ 상태를 먼저 확인합니다."),
        (f"센터 자료에 표시된 {grades} 범위와 학생의 실제 진도를 대조해 ‘{focus}’ 항목의 시작점을 정합니다."
         if available_grade_items(ctx)
         else f"센터 자료에 학년 범위가 따로 표시되지 않아 학생의 현재 학년과 실제 진도를 상담에서 대조한 뒤 ‘{focus}’ 항목의 시작점을 정합니다."),
        f"{actual_center_name(ctx)} 상담에서는 {student} 상황을 성적만으로 판단하지 않고 최근 학습 기록으로 확인합니다.",
        f"{ctx.config['label']}에서 ‘{focus}’ 항목이 반복되는 시점과 사용 중인 교재 범위를 나누어 봅니다.",
    ]
    followups = [
        f"{action} 이후 {process_label} 결과를 다음 상담에서 다시 확인합니다.",
        f"{action} 실행 여부는 {ctx.locality} 학생의 주중·주말 가능 시간에 맞춰 점검합니다.",
        f"{action} 한 번에 많은 분량을 정하기보다 완료 기록을 보고 다음 범위를 조정합니다.",
        f"{action} 이 과정에서 확인된 내용은 {actual_center_name(ctx)}의 실제 시간표와 대조합니다.",
        f"{action} 다음 점검에서는 같은 어려움이 남아 있는지 유사한 과제로 확인합니다.",
        f"{action} 계획은 {ctx.config['checks']} 가운데 우선순위가 높은 항목부터 실행합니다.",
    ]
    return f"{choose(ctx, evidence)} {choose(ctx, followups)}"


def build_quality_section(ctx: PageContext) -> str:
    students = ctx.rng.sample(ctx.config["students"], 3)
    student_bodies = [student_answer(ctx, student, index) for index, student in enumerate(students)]
    student_cards = "\n".join(
        f'''            <article class="geo-answer-card">
              <strong>{html.escape(student)}</strong>
              <p>{html.escape(body)}</p>
            </article>'''
        for student, body in zip(students, student_bodies)
    )
    school = actual_school_phrase(ctx)
    fit_intro = choose(ctx, [
        f"{ctx.locality} {ctx.config['label']}에서는 학생의 현재 상태를 확인하고 우선순위를 정하는 것부터 시작합니다.",
        f"{actual_center_name(ctx)}의 {ctx.config['label']} 상담은 결과보다 막힌 원인과 실행 습관을 먼저 구분합니다.",
        f"{ctx.locality}의 같은 학년 학생이라도 교재·진도·오답 유형에 따라 {ctx.config['label']} 점검 순서가 달라집니다.",
        f"{ctx.title} 상담을 시작하기 전 현재 자료와 실제 공부 시간을 함께 살펴봅니다.",
        f"{ctx.locality} 학생에게 필요한 {ctx.config['label']} 범위는 {ctx.config['checks']} 기록을 대조한 뒤 정합니다.",
        (f"{available_grade_text(ctx)} 학생이라도 현재 진도는 다를 수 있어 {ctx.config['checks']} 상태를 따로 확인합니다."
         if available_grade_items(ctx)
         else f"센터 자료에 학년 범위가 따로 표시되지 않은 경우 {ctx.locality} 학생의 현재 학년과 시간표를 상담에서 확인합니다."),
    ])
    school_check = (choose(ctx, [
        f"{school}의 현재 진도와 다음 시험 일정을 확인합니다.",
        f"{school}에서 사용하는 교재와 시험 범위를 정리합니다.",
        f"{school}의 진도 차이를 고려해 필요한 복습 범위를 확인합니다.",
        f"{school}의 시험 일정과 센터 수업 가능 시간을 함께 대조합니다.",
    ]) if school != SCHOOL_FALLBACK else choose(ctx, [
        "재학 중인 학교의 현재 진도와 다음 시험 일정을 확인합니다.",
        "학교에서 사용하는 교재와 최근 시험 범위를 준비합니다.",
        "학교 진도와 시험 일정을 알려주면 상담 범위를 정하기 좋습니다.",
        "재학 학교의 수업 진도와 센터 시간표를 함께 대조합니다.",
    ]))
    focus = choose(ctx, check_items(ctx))
    recent_check = choose(ctx, [
        f"{ctx.config['label']} 상담을 위해 현재 교재와 최근 시험지에서 ‘{focus}’ 항목이 드러나는 문제를 준비합니다.",
        f"사용 중인 교재와 최근 평가 자료에서 {ctx.locality} 학생이 ‘{focus}’ 부분에서 막힌 문제를 표시해 둡니다.",
        f"최근 시험지와 과제 기록을 모아 {ctx.config['checks']} 가운데 반복되는 어려움을 확인합니다.",
        f"현재 진도와 오답이 남은 단원을 알 수 있는 자료를 챙겨 {actual_center_name(ctx)} 상담 범위를 좁힙니다.",
        f"{ctx.title} 상담 전에 교재·시험지·오답 기록을 나누어 ‘{focus}’ 상태를 확인합니다.",
    ])
    time_check = choose(ctx, [
        f"{ctx.config['stage']} {ctx.config['subject']} 과제와 복습을 주중·주말에 실제로 실행할 수 있는 시간으로 나눕니다.",
        f"학교와 다른 일정까지 고려해 {ctx.config['label']}에 꾸준히 사용할 수 있는 시간을 적어 봅니다.",
        f"‘{focus}’ 항목의 과제와 복습에 사용할 요일별 시간을 현실적으로 계산합니다.",
        f"{ctx.locality} 학생의 계획이 무너지지 않도록 평일과 주말의 공부 가능 시간을 나누어 봅니다.",
        f"{actual_center_name(ctx)} 시간표와 학생의 학교 일정을 대조해 실행 가능한 시간을 정리합니다.",
    ])
    goal_check = choose(ctx, [
        f"{ctx.config['checks']} 중 우선 해결할 내용을 한두 가지로 좁힙니다.",
        f"{ctx.config['checks']} 가운데 가장 자주 막히는 항목을 먼저 고릅니다.",
        f"{ctx.config['checks']} 항목을 살펴 이번 상담에서 정할 우선순위를 적습니다.",
        f"{ctx.config['checks']} 중 단기간에 확인할 목표와 장기 보완 항목을 나눕니다.",
    ])
    return f'''    <!-- quality-content:start -->
    <section class="local-section seo-geo-section" aria-label="{html.escape(ctx.title)} 학습 및 상담 안내">
      <div class="wrap seo-geo-enhancement">
        <article id="student-fit" class="geo-answer-panel">
          <p class="eyebrow">학습 점검</p>
          <h2>이런 학생이라면 상담에서 먼저 확인해 보세요</h2>
          <p>{html.escape(fit_intro)}</p>
          <div class="geo-answer-grid">
{student_cards}
          </div>
        </article>

        <article id="consult-checklist" class="geo-checklist-panel">
          <p class="eyebrow">상담 준비</p>
          <h2>{html.escape(ctx.title)} 상담 전 체크리스트</h2>
          <div class="geo-checklist-grid">
            <article class="geo-check-card"><b>01</b><strong>최근 학습 자료</strong><p>{html.escape(recent_check)}</p></article>
            <article class="geo-check-card"><b>02</b><strong>학교 일정</strong><p>{html.escape(school_check)}</p></article>
            <article class="geo-check-card"><b>03</b><strong>공부 가능 시간</strong><p>{html.escape(time_check)}</p></article>
            <article class="geo-check-card"><b>04</b><strong>상담 목표</strong><p>{html.escape(goal_check)}</p></article>
          </div>
        </article>
      </div>
    </section>
    <!-- quality-content:end -->'''


def build_faqs(ctx: PageContext) -> list[dict[str, str]]:
    school = actual_school_phrase(ctx)
    grades = available_grade_text(ctx)
    label = ctx.config["label"]
    center = actual_center_name(ctx)
    address = actual_address(ctx)
    focus = choose(ctx, check_items(ctx))
    process_label, process_variants = choose(ctx, ctx.config["process"])
    process_answer = choose(ctx, process_variants)
    first_question = choose(ctx, [
        f"{ctx.title} 상담에서는 무엇을 가장 먼저 확인하나요?",
        f"{ctx.title}을 알아볼 때 첫 상담에서 어떤 자료를 살펴보나요?",
        f"{ctx.title} 학습 방향은 어떤 기준으로 정하나요?",
        f"{ctx.title} 상담은 성적 외에 무엇을 확인하나요?",
        f"{ctx.title}에서 시작 단원을 정하는 방법은 무엇인가요?",
        f"{ctx.title} 상담 전에 가장 먼저 정리할 항목은 무엇인가요?",
    ])
    first_answer = choose(ctx, [
        f"{ctx.locality} 학생의 현재 교재와 최근 시험 자료를 보고 ‘{focus}’ 항목이 막힌 지점을 먼저 확인합니다. {process_answer}",
        f"성적만으로 시작 범위를 정하지 않습니다. {ctx.config['checks']} 기록을 나누어 보고 {center}의 실제 개설 학년과 시간표를 대조합니다.",
        f"최근 풀이와 과제 완료 기록에서 ‘{focus}’ 상태를 확인한 뒤 {process_label} 순서를 정합니다. 학생이 실행할 수 있는 분량인지도 함께 살펴봅니다.",
        f"{label} 상담은 현재 진도, 오답, 공부 가능 시간을 함께 확인합니다. 그중 ‘{focus}’ 항목을 우선 점검한 뒤 다음 확인 시점을 정합니다.",
        f"{ctx.locality} 학생이 가져온 교재·시험지·오답 기록을 기준으로 {ctx.config['checks']} 상태를 구분합니다. 상담 결과는 {center}의 수업 가능 범위와 함께 안내합니다.",
        f"먼저 학생이 혼자 설명할 수 있는 부분과 도움이 필요한 부분을 나눕니다. 이후 ‘{focus}’ 항목을 중심으로 {process_answer}",
    ])
    if available_grade_items(ctx):
        grade_answer = choose(ctx, [
            f"{ctx.locality} 페이지에 연결된 {center} 자료에는 {grades} 수업이 표시되어 있습니다. 등록 전 현재 개설 반과 학생 일정을 다시 대조해 주세요.",
            f"확인된 가능 학년은 {grades}입니다. 다만 {label}의 요일·시간은 달라질 수 있어 {center}의 최신 시간표를 기준으로 확인해야 합니다.",
            f"학원 제공 센터정보에서 {grades} 학년을 확인했습니다. 같은 학년이라도 현재 진도와 잔여 시간이 다르므로 {ctx.locality} 상담 시 다시 확인합니다.",
            f"{grades} 범위가 현재 자료에 포함되어 있습니다. {ctx.config['subject']} 과목의 정확한 개설 시간은 {center} 방문 전 문의해 주세요.",
            f"{ctx.title}의 자료상 학년 범위는 {grades}입니다. 수업 확정 정보가 아니라 상담 기준이므로 현재 시간표와 함께 확인해야 합니다.",
        ])
    else:
        grade_answer = choose(ctx, [
            f"제공된 {center} 정보에서 {label} 개설 범위를 확인하지 못했습니다. 임의로 학년을 안내하지 않으며 등록 전 최신 시간표를 확인해야 합니다.",
            f"현재 센터 자료만으로 {ctx.title} 개설 여부를 확정하기 어렵습니다. {address} 방문 전 학년·과목별 시간을 문의해 주세요.",
            f"{ctx.locality} 페이지에 연결된 자료에는 해당 학년 범위가 표시되지 않았습니다. {center}의 현재 개설 반을 기준으로 상담해 주세요.",
        ])
    grade_item = {
        "q": choose(ctx, [
            f"{ctx.locality} {label}에서 확인되는 수업 가능 학년은 어떻게 되나요?",
            f"{center}의 {label} 가능 학년은 어디까지인가요?",
            f"{ctx.title} 등록 전에 어떤 학년 정보를 확인해야 하나요?",
            f"{ctx.locality} 학생의 학년에 맞는 {ctx.config['subject']} 수업은 어떻게 확인하나요?",
            f"{ctx.title} 페이지에 표시된 개설 학년은 확정 정보인가요?",
        ]),
        "a": grade_answer,
    }
    school_answer = (choose(ctx, [
        f"{school} 등은 {ctx.locality} 상담 범위를 이해하기 위한 참고 학교입니다. 학교명만으로 수업이 확정되지는 않으며 {center}의 현재 시간표를 함께 확인합니다.",
        f"{school} 등의 진도와 시험 일정은 {label} 상담 자료로 활용합니다. 실제 수업 여부는 학생의 학년·과목과 {center} 시간표를 대조해 확인합니다.",
        f"{school} 등 학교별 자료를 참고할 수 있습니다. 사용 교재와 시험 범위를 알려주시면 {center}의 현재 개설 수업과 맞는지 안내합니다.",
        f"{school} 등 재학 학교의 일정은 {ctx.locality} 학생의 학습 계획에 반영할 수 있습니다. 다만 학교명만으로 반을 정하지 않고 현재 진도도 함께 살펴봅니다.",
    ]) if school != SCHOOL_FALLBACK else choose(ctx, [
        f"재학 학교의 진도와 시험 범위는 {ctx.title} 상담에서 확인합니다. 현재 교재와 시험 일정을 알려주시면 {center} 시간표와 가능한 범위를 안내합니다.",
        f"학교명이 제공된 자료에 없어 임의로 추가하지 않습니다. {ctx.locality} 학생이 실제 사용하는 교재와 시험 일정을 준비하면 {label} 범위를 구체화할 수 있습니다.",
        f"학교 진도는 학생마다 다를 수 있어 {ctx.config['checks']} 기록을 먼저 살펴봅니다. 이후 {center}의 개설 정보와 맞는 학습 순서를 정합니다.",
        f"{ctx.locality} 상담에서 재학 학교와 현재 진도를 확인하고 {center} 시간표에 맞는 수업 범위를 안내합니다.",
    ]))
    school_question = choose(ctx, [
        f"{school} 등 학교 진도와 시험 일정을 반영할 수 있나요?",
        f"{school} 등의 교재와 시험 범위는 학습 계획에 어떻게 반영하나요?",
        f"{school} 등 재학 학교에 맞춘 {label} 상담이 가능한가요?",
        f"{school} 등의 학사 일정을 고려해 공부 계획을 조정할 수 있나요?",
    ]) if school != SCHOOL_FALLBACK else choose(ctx, [
        "학교 진도와 시험 일정은 어떻게 반영하나요?",
        "재학 학교의 교재와 시험 범위도 상담에서 확인하나요?",
        f"학교별 일정에 맞춰 {label} 계획을 조정할 수 있나요?",
        "학교마다 다른 진도는 어떤 자료로 확인하나요?",
    ])
    school_item = {"q": school_question, "a": school_answer}
    preparation_item = {
        "q": choose(ctx, [
            f"{ctx.title} 상담 전에는 어떤 자료를 준비하면 좋나요?",
            f"{center}에서 {label} 상담을 받을 때 무엇을 가져가야 하나요?",
            f"{ctx.locality} 학생의 현재 상태를 확인하려면 어떤 기록이 필요한가요?",
            f"{label} 상담 전에 ‘{focus}’ 항목을 어떻게 정리하면 되나요?",
            f"{center} 방문 전 어떤 자료와 일정을 확인해야 하나요?",
        ]),
        "a": choose(ctx, [
            f"현재 교재와 최근 시험지, 오답 기록에서 ‘{focus}’ 항목을 표시해 주세요. 실제 상담 장소는 {center}이며 주소는 {address}입니다.",
            f"교재·최근 평가 자료·평소 공부 가능한 시간을 정리하면 좋습니다. {center} 방문 전에는 {address} 위치와 최신 시간표를 확인해 주세요.",
            f"최근 시험 결과와 과제 수행 기록을 준비하면 {ctx.config['checks']} 가운데 우선 확인할 부분을 구체화할 수 있습니다.",
            f"현재 진도와 어려운 단원, 주중 학습 가능 시간을 메모해 주세요. {ctx.locality} 상담 페이지의 실제 안내 센터는 {center}입니다.",
        ]),
    }
    management_item = {
        "q": choose(ctx, [
            f"{ctx.locality} {label}에서 ‘{focus}’ 관리는 어떻게 진행하나요?",
            f"{ctx.title} 수업에서 {process_label} 결과는 어떻게 다시 확인하나요?",
            f"{ctx.config['subject']} 학습 중 ‘{focus}’ 어려움이 반복되면 무엇을 점검하나요?",
            f"{ctx.locality} 학생의 {ctx.config['checks']} 우선순위는 어떻게 정하나요?",
        ]),
        "a": choose(ctx, [
            f"최근 자료에서 ‘{focus}’ 문제가 나타난 지점을 표시한 뒤 원인을 개념·실행·오답으로 나눕니다. {process_answer}",
            f"{ctx.config['checks']} 기록을 한 번에 확인하고 학생이 실행 가능한 항목부터 정합니다. 다음 점검에서는 완료 여부와 같은 오류의 반복 여부를 확인합니다.",
            f"{ctx.locality} 학생의 교재와 학습 시간을 기준으로 ‘{focus}’ 항목의 분량을 정합니다. 결과는 {center} 상담에서 다시 조정합니다.",
        ]),
    }
    center_item = {
        "q": f"{ctx.locality} 페이지에서 안내하는 실제 상담 센터는 어디인가요?",
        "a": f"이 페이지에 연결된 상담 센터는 {center}이며 주소는 {address}입니다. 페이지의 지역명과 실제 센터 위치가 다를 수 있으므로 방문 전 센터명·주소·시간표를 확인해 주세요.",
    }
    optional = [school_item, preparation_item, management_item]
    if ctx.info.tuition_url:
        optional.append({
            "q": f"{ctx.title} 교습비 정보는 어디에서 확인할 수 있나요?",
            "a": f"페이지의 ‘센터 교습비 자료 확인’ 링크에서 {center}의 공개 자료를 확인할 수 있습니다. 실제 수강 과목과 시간에 따른 금액은 등록 전 다시 확인해 주세요.",
        })
    if is_service_area_page(ctx):
        tail = [center_item, choose(ctx, optional)]
    else:
        tail = ctx.rng.sample(optional, 2)
    return [{"q": first_question, "a": first_answer}, grade_item, *tail]


def build_faq_html(ctx: PageContext, faqs: list[dict[str, str]]) -> str:
    items = "\n".join(
        f'''      <details>
        <summary>{html.escape(item['q'])}</summary>
        <p>{html.escape(item['a'])}</p>
      </details>'''
        for item in faqs
    )
    return f'''<section id="faq-section" class="local-section">
  <div class="wrap faq-local">
    <h2>{html.escape(ctx.title)} 자주 묻는 질문</h2>
{items}
  </div>
</section>'''


def replace_meta(text: str, *, key: str, value: str, attr_name: str) -> str:
    pattern = re.compile(rf'(<meta\b(?=[^>]*\b{attr_name}=["\']{re.escape(key)}["\'])[^>]*\bcontent=["\'])(.*?)(["\'][^>]*>)', re.I | re.S)
    new_text, count = pattern.subn(lambda match: match.group(1) + html.escape(value, quote=True) + match.group(3), text, count=1)
    if count != 1:
        raise ValueError(f"Meta {attr_name}={key} not found")
    return new_text


def stable_org_node(ctx: PageContext, old: dict[str, Any]) -> dict[str, Any]:
    area_nodes = [{"@type": "Place", "name": area} for area in ctx.center.areas]
    address: dict[str, Any] = {"@type": "PostalAddress", "streetAddress": actual_address(ctx), "addressCountry": "KR"}
    if ctx.info.region:
        address["addressRegion"] = ctx.info.region
    if ctx.info.district:
        address["addressLocality"] = ctx.info.district
    node: dict[str, Any] = {
        "@type": ["EducationalOrganization", "LocalBusiness"],
        "@id": ctx.center.primary_url + "#organization",
        "name": actual_center_name(ctx),
        "branchOf": {"@id": BASE_URL + "/#organization"},
        "url": ctx.center.primary_url,
        "telephone": ctx.center.telephone,
        "address": address,
        "areaServed": area_nodes if len(area_nodes) > 1 else area_nodes[0],
    }
    identifier = ({"@type": "PropertyValue", "propertyID": "교육지원청 등록번호", "value": ctx.info.registration_number}
                  if ctx.info.registration_number else ctx.center.identifier)
    for key, value in (("alternateName", ctx.center.alternate_name), ("contactPoint", ctx.center.contact_point), ("identifier", identifier)):
        if value:
            node[key] = value
    return node


def normalize_machine_urls(value: Any) -> Any:
    if isinstance(value, list):
        return [normalize_machine_urls(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_machine_urls(item) for key, item in value.items()}
    if not isinstance(value, str):
        return value
    candidate = value.replace("https://코칭학원.com", BASE_URL)
    if not candidate.startswith(BASE_URL):
        return candidate
    parts = urlsplit(candidate)
    normalized_path = quote(unquote(parts.path), safe="/")
    return urlunsplit((parts.scheme, parts.netloc, normalized_path, parts.query, parts.fragment))


def update_jsonld(ctx: PageContext, faqs: list[dict[str, str]], description: str) -> str:
    data = ctx.data
    # Rebuild the informational Article deterministically.  The page remains a
    # Service landing page, while this node describes the substantial visible
    # guidance copy.  Tuition links stay with the Service instead of being
    # misrepresented as citations for the full article.
    primary_image_id = ctx.page_url + "#primaryimage"
    primary_image_url = representative_image_url(ctx)
    graph = [
        node for node in data["@graph"]
        if not (
            isinstance(node, dict)
            and (node_has_type(node, "Article") or node.get("@id") == primary_image_id)
        )
    ]
    data["@graph"] = graph
    old_org = find_node(graph, "EducationalOrganization")
    stable_id = ctx.center.primary_url + "#organization"
    if old_org is not None:
        graph[graph.index(old_org)] = stable_org_node(ctx, old_org)

    faq_entities = [
        {"@type": "Question", "name": item["q"], "acceptedAnswer": {"@type": "Answer", "text": item["a"]}}
        for item in faqs
    ]
    for node in graph:
        if not isinstance(node, dict):
            continue
        node_type = node.get("@type")
        if node_type == "WebSite":
            node["@id"] = BASE_URL + "/#website"
            node["url"] = BASE_URL + "/"
        if node_type == "WebPage":
            node["name"] = seo_title(ctx)
            node["description"] = description
            node["isPartOf"] = {"@id": BASE_URL + "/#website"}
            node["dateModified"] = TODAY
            node["about"] = [
                {"@type": "Place", "name": ctx.region},
                {"@type": "Thing", "name": ctx.config["label"]},
            ]
            schools = actual_school_phrase(ctx)
            school_mentions = ([{"@type": "Organization", "name": school} for school in schools.split("·") if is_specific_school(school)]
                               if schools != SCHOOL_FALLBACK else [])
            node["mentions"] = [{"@id": stable_id}, *school_mentions]
            node["primaryImageOfPage"] = {"@id": primary_image_id}
            node["hasPart"] = [
                {"@type": "WebPageElement", "name": "학습관리 방법", "url": ctx.page_url + "#learning-plan"},
                {"@type": "WebPageElement", "name": "연결 상담 센터 정보" if is_service_area_page(ctx) else "확인된 센터 정보", "url": ctx.page_url + "#verified-center"},
                {"@type": "WebPageElement", "name": "추천 학생 점검", "url": ctx.page_url + "#student-fit"},
                {"@type": "WebPageElement", "name": "상담 전 체크리스트", "url": ctx.page_url + "#consult-checklist"},
                {"@type": "WebPageElement", "name": "자주 묻는 질문", "url": ctx.page_url + "#faq-section"},
                {"@type": "WebPageElement", "name": "관련 학습 페이지", "url": ctx.page_url + "#internal-links"},
            ]
        elif node_type == "Service":
            rebuilt = {
                "@type": "Service",
                "@id": ctx.page_url + "#service",
                "name": f"{ctx.title} 학습코칭",
                "serviceType": ctx.config["label"],
                "description": description,
                "provider": {"@id": stable_id},
                "areaServed": {"@type": "Place", "name": ctx.region},
                "audience": {
                    "@type": "EducationalAudience",
                    "educationalRole": "student",
                    "audienceType": ctx.config["stage"],
                },
                "image": {"@id": primary_image_id},
            }
            if ctx.info.tuition_url:
                rebuilt["offers"] = {
                    "@type": "Offer",
                    "url": ctx.info.tuition_url,
                    "category": "교습비 안내",
                    "description": "교습비와 현재 수업 가능 여부는 연결된 공개 자료와 상담에서 확인합니다.",
                }
            node.clear()
            node.update(rebuilt)
        elif node_type == "FAQPage":
            node.clear()
            node.update({"@type": "FAQPage", "@id": ctx.page_url + "#faq", "mainEntity": faq_entities})
        elif node_type == "BreadcrumbList" or node_type == "ItemList":
            pass
    article_mentions: list[dict[str, Any]] = [{"@id": stable_id}]
    article_schools = actual_school_phrase(ctx)
    if article_schools != SCHOOL_FALLBACK:
        article_mentions.extend(
            {"@type": "Organization", "name": school}
            for school in article_schools.split("·")
            if is_specific_school(school)
        )
    article: dict[str, Any] = {
        "@type": "Article",
        "@id": ctx.page_url + "#article",
        "headline": ctx.title,
        "description": description,
        "inLanguage": "ko-KR",
        "articleSection": ctx.config["label"],
        "mainEntityOfPage": {"@id": ctx.page_url + "#webpage"},
        "author": {"@id": stable_id},
        "publisher": {"@id": stable_id},
        "about": [
            {"@type": "Place", "name": ctx.region},
            {"@type": "Thing", "name": ctx.config["label"]},
        ],
        "mentions": article_mentions,
        "image": {"@id": primary_image_id},
        "dateModified": TODAY,
    }
    graph.append(article)
    graph.append({
        "@type": "ImageObject",
        "@id": primary_image_id,
        "contentUrl": primary_image_url,
        "url": primary_image_url,
        "caption": f"{ctx.title} 코칭학원.com 대표 이미지",
        "inLanguage": "ko-KR",
    })
    data = normalize_machine_urls(data)
    compact = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    _, match = parse_jsonld(ctx.text)
    return ctx.text[:match.start(1)] + compact + ctx.text[match.end(1):]


def transform_page(ctx: PageContext) -> str:
    description = meta_description(ctx)
    title_tag = seo_title(ctx)
    faqs = build_faqs(ctx)

    # Start with JSON-LD because its replacement offsets are based on the original page.
    text = update_jsonld(ctx, faqs, description)
    text = text.replace("https://코칭학원.com", BASE_URL)
    text, title_count = re.subn(
        r"<title>.*?</title>",
        f"<title>{html.escape(title_tag)}</title>",
        text,
        count=1,
        flags=re.S,
    )
    if title_count != 1:
        raise ValueError(f"Title not replaced: {ctx.path}")
    text = replace_meta(text, key="description", value=description, attr_name="name")
    text = replace_meta(text, key="og:title", value=title_tag, attr_name="property")
    text = replace_meta(text, key="og:description", value=description, attr_name="property")
    text = replace_meta(text, key="og:type", value="article", attr_name="property")
    if 'type="application/rss+xml"' not in text:
        canonical = re.search(r'<link\b[^>]*rel=["\']canonical["\'][^>]*>', text, re.I)
        if not canonical:
            raise ValueError(f"Canonical not found: {ctx.path}")
        rss_link = f'\n  <link rel="alternate" type="application/rss+xml" title="와와학습코칭학원 RSS" href="{BASE_URL}/rss.xml">'
        text = text[:canonical.end()] + rss_link + text[canonical.end():]

    text = re.sub(r'\s*<div class="hero-center-fact">.*?</div>', "", text, count=1, flags=re.S)
    hero_pattern = re.compile(r'(<section class="local-hero">.*?<h1>.*?</h1>)\s*<p>.*?</p>', re.S)
    text, count = hero_pattern.subn(
        lambda match: match.group(1)
        + "\n              <p>"
        + html.escape(hero_intro(ctx))
        + "</p>\n"
        + hero_center_fact(ctx),
        text,
        count=1,
    )
    if count != 1:
        raise ValueError(f"Hero not replaced: {ctx.path}")
    eyebrow = "지역 학습 안내" if not ctx.category else f"{ctx.config['stage']} {ctx.config['subject']} 학습 안내"
    text = re.sub(r'(<section class="local-hero">.*?<p class="eyebrow">).*?(</p>)', lambda match: match.group(1) + html.escape(eyebrow) + match.group(2), text, count=1, flags=re.S)
    tags = [ctx.title, ctx.config["label"], ctx.config["checks"], "진단·계획·오답 점검"]
    tag_html = "".join(f"<span>{html.escape(tag)}</span>" for tag in tags)
    text = re.sub(r'(<div class="keyword-row local-keywords"[^>]*>).*?(</div>)', lambda match: match.group(1) + tag_html + match.group(2), text, count=1, flags=re.S)

    primary_pattern = re.compile(r'\s*<section(?: id="learning-plan")? class="local-section">\s*<div class="wrap local-grid">.*?</section>', re.S)
    text, count = primary_pattern.subn("\n\n" + build_primary_section(ctx), text, count=1)
    if count != 1:
        raise ValueError(f"Primary content not replaced: {ctx.path}")

    text = re.sub(r'\s*<section class="local-section keyword-focus-section"[^>]*>.*?</section>', "", text, count=1, flags=re.S)
    verified_pattern = re.compile(
        r'\s*<section class="local-section">\s*<div class="wrap school-card">.*?</section>\s*'
        r'<section class="local-section">\s*<div class="wrap location-card">.*?</section>',
        re.S,
    )
    text, count = verified_pattern.subn("\n\n" + build_verified_section(ctx), text, count=1)
    if count != 1:
        current_verified_pattern = re.compile(r'\s*<section id="verified-center" class="local-section verified-center-section">.*?</section>', re.S)
        text, count = current_verified_pattern.subn("\n\n" + build_verified_section(ctx), text, count=1)
    if count != 1:
        raise ValueError(f"Verified center section not replaced: {ctx.path}")

    quality_pattern = re.compile(r'\s*<!-- (?:seo-geo-enhancement|quality-content):start -->.*?<!-- (?:seo-geo-enhancement|quality-content):end -->', re.S)
    text, count = quality_pattern.subn("\n\n" + build_quality_section(ctx), text, count=1)
    if count != 1:
        raise ValueError(f"Quality section not replaced: {ctx.path}")

    text = re.sub(r'\s*<section id="parent-reviews" class="local-section">.*?</section>\s*(?=<section id="faq-section")', "\n", text, count=1, flags=re.S)
    faq_pattern = re.compile(r'<section id="faq-section" class="local-section">.*?</section>\s*(?=<section id="internal-links")', re.S)
    text, count = faq_pattern.subn(build_faq_html(ctx, faqs) + "\n", text, count=1)
    if count != 1:
        raise ValueError(f"FAQ not replaced: {ctx.path}")

    replacements = {
        "Study Page Map": "같이 보는 학습 안내",
        "Local Search Guide": "지역 학습 안내",
        "KEY SUMMARY": "핵심 안내",
        "ANSWER READY": "학습 점검",
        "CONSULTING CHECKLIST": "상담 준비",
        "Overview": "종합 안내",
        "Elementary English": "초등 영어",
        "Elementary Math": "초등 수학",
        "Middle English": "중등 영어",
        "Middle Math": "중등 수학",
        "High English": "고등 영어",
        "High Math": "고등 수학",
        "위치, 상담 범위, 후기, 주변 학교 안내": "위치, 상담 범위, 주변 학교 안내",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    family_match = re.search(r'<section id="internal-links"[^>]*>.*?</section>', text, re.S)
    if family_match:
        family_block = family_match.group(0).replace(f"<strong>{ctx.locality} ", "<strong>")
        text = text[:family_match.start()] + family_block + text[family_match.end():]
    text = re.sub(r'aria-label="([^"]+) 부모 자식 페이지 이동"', r'aria-label="\1 학습 안내 페이지 이동"', text)
    text = text.replace(f"와와학습코칭학원 {ctx.locality} 지점", actual_center_name(ctx))
    text = text.replace(f"와와학습코칭센터 {ctx.locality} 지점", actual_center_name(ctx))
    text = (text.replace("수학는", "수학은").replace("수학를", "수학을")
            .replace("관리을", "관리를").replace("점는", "점은"))
    text = text.replace("SEO GEO 학습 안내", "학습 및 상담 안내")
    return text


def validate_transformed(ctx: PageContext, text: str) -> list[str]:
    errors: list[str] = []
    if len(re.findall(r"<h1\b", text, re.I)) != 1:
        errors.append("H1 count")
    for bad in ("수학는", "수학를", "관리을", "점는", "점와", "SEO GEO", "KEY SUMMARY", "ANSWER READY", "Local Search Guide", "친구와 함께 등록하면 할인", "parent-reviews"):
        if bad in text:
            errors.append(f"remaining token: {bad}")
    description = meta_description(ctx)
    if not 60 <= len(description) <= 80:
        errors.append(f"description length: {len(description)}")
    title_tag = seo_title(ctx)
    if not 24 <= len(title_tag) <= 30:
        errors.append(f"title length: {len(title_tag)}")
    if ctx.image_block not in text:
        errors.append("image block changed")
    if ctx.map_image not in text:
        errors.append("map image changed")
    try:
        data, _ = parse_jsonld(text)
        json.dumps(data, ensure_ascii=False)
        graph = data.get("@graph", [])
        articles = [node for node in graph if isinstance(node, dict) and node_has_type(node, "Article")]
        faq_nodes = [node for node in graph if isinstance(node, dict) and node_has_type(node, "FAQPage")]
        services = [node for node in graph if isinstance(node, dict) and node_has_type(node, "Service")]
        if len(articles) != 1:
            errors.append("Article count")
        if len(faq_nodes) != 1 or len(faq_nodes[0].get("mainEntity", [])) != 4:
            errors.append("FAQPage count")
        stable_id = ctx.center.primary_url + "#organization"
        if articles:
            article = articles[0]
            if article.get("mainEntityOfPage", {}).get("@id") != ctx.page_url + "#webpage":
                errors.append("Article mainEntityOfPage")
            if article.get("author", {}).get("@id") != stable_id or article.get("publisher", {}).get("@id") != stable_id:
                errors.append("Article entity reference")
        if len(services) != 1 or services[0].get("provider", {}).get("@id") != stable_id:
            errors.append("Service provider")

        faq_block = re.search(r'<section\b[^>]*id="faq-section"[^>]*>(.*?)</section>', text, re.I | re.S)
        visible_faqs: list[tuple[str, str]] = []
        if faq_block:
            for detail in re.findall(r"<details\b[^>]*>(.*?)</details>", faq_block.group(1), re.I | re.S):
                question = re.search(r"<summary\b[^>]*>(.*?)</summary>", detail, re.I | re.S)
                answer = re.search(r"<p\b[^>]*>(.*?)</p>", detail, re.I | re.S)
                if question and answer:
                    visible_faqs.append((strip_tags(question.group(1)), strip_tags(answer.group(1))))
        schema_faqs = [
            (str(item.get("name", "")).strip(), str(item.get("acceptedAnswer", {}).get("text", "")).strip())
            for item in (faq_nodes[0].get("mainEntity", []) if faq_nodes else [])
            if isinstance(item, dict)
        ]
        if visible_faqs != schema_faqs:
            errors.append("FAQ screen/schema mismatch")
    except Exception as exc:  # noqa: BLE001 - validator collects diagnostics
        errors.append(f"JSON-LD: {exc}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    center = root / CENTER_DIRNAME
    center_info = load_center_info(root)
    local_pages = [
        path for path in sorted(center.glob("*/index.html"))
        if normalize_locality(path.parent.name) in center_info
    ]
    local_names = {path.parent.name for path in local_pages}
    child_pages = [
        path for path in sorted(center.glob("*/*/index.html"))
        if path.parent.parent.name in local_names and path.parent.name in CATEGORIES and path.parent.name
    ]
    records, locality_to_key = build_center_records(root, local_pages)
    for record in records.values():
        record.areas = []
    for locality, key in locality_to_key.items():
        info = center_info.get(normalize_locality(locality))
        if info:
            area = full_region(info)
            if area and area not in records[key].areas:
                records[key].areas.append(area)
    for record in records.values():
        record.areas.sort()
    pages = local_pages + child_pages

    changed = 0
    failures: list[tuple[str, list[str]]] = []
    for path in pages:
        ctx = context_for(path, root, records, locality_to_key, center_info)
        new_text = transform_page(ctx)
        errors = validate_transformed(ctx, new_text)
        if errors:
            failures.append((path.relative_to(root).as_posix(), errors))
            continue
        if new_text != ctx.text:
            changed += 1
            if not args.dry_run:
                path.write_text(new_text, encoding="utf-8", newline="\n")

    mapped = len({normalize_locality(path.parent.name if path.parent.parent.name == CENTER_DIRNAME else path.parent.parent.name) for path in pages})
    print(f"pages={len(pages)} centers={len(records)} center_rows={len(center_info)} mapped_localities={mapped} changed={changed} failures={len(failures)} dry_run={args.dry_run}")
    for rel, errors in failures[:20]:
        print(f"FAIL {rel}: {', '.join(errors)}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
