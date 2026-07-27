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
TODAY = "2026-07-27"
CENTER_DIRNAME = "전국센터"


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
    return " / ".join(values) if values else "현재 개설 학년 상담 확인"


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
    return "·".join(schools[:limit]) if schools else "학교별 진도 상담 확인"


def meta_description(ctx: PageContext) -> str:
    school = actual_school_phrase(ctx, 2)
    if ctx.category:
        value = f"{ctx.title} 안내입니다. {school} 학생의 {ctx.config['meta_focus']}, 가능 학년과 {actual_center_name(ctx)} 위치를 확인하세요."
    else:
        value = f"{ctx.title} 안내입니다. {school} 인근 영어·수학 학습관리, 가능 학년과 {actual_center_name(ctx)} 위치를 확인하세요."
    if len(value) <= 95:
        return value
    shortened = value[:94]
    if " " in shortened:
        shortened = shortened.rsplit(" ", 1)[0]
    return shortened.rstrip("., ") + "…"


def hero_intro(ctx: PageContext) -> str:
    templates = [
        "{title}을 알아볼 때는 {checks} 등의 항목을 함께 확인해야 합니다. {center} 상담에서는 현재 교재와 최근 학습 자료를 바탕으로 시작 범위를 정리합니다.",
        "{title} 선택 전에는 성적만 비교하기보다 {checks} 등의 항목을 나누어 보는 것이 좋습니다. {center}에서 학생에게 필요한 관리 순서를 상담할 수 있습니다.",
        "{title} 상담의 출발점은 학생이 막히는 지점을 구체적으로 찾는 것입니다. {checks} 등을 확인한 뒤 학습 순서와 점검 방식을 안내합니다.",
        "{title}을 찾는 학생이라면 먼저 {checks} 등의 항목을 점검해 보세요. {center}는 확인된 자료를 기준으로 무리하지 않는 학습 계획을 세웁니다.",
    ]
    return choose(ctx, templates).format(title=ctx.title, checks=ctx.config["checks"], center=actual_center_name(ctx))


def method_intro(ctx: PageContext) -> tuple[str, str, str]:
    headings = [
        f"{ctx.title}, 무엇부터 확인해야 할까요?",
        f"{ctx.title} 상담 전 살펴볼 학습 기준",
        f"{ctx.title}에서 중요한 관리 순서",
        f"{ctx.title} 학습 방향을 정하는 방법",
    ]
    first = [
        f"{ctx.config['label']}에서는 학습량을 늘리기 전에 {ctx.config['checks']} 중 어디에서 어려움이 생기는지 구분하는 과정이 먼저입니다.",
        f"학생마다 필요한 보완 범위가 다르므로 {ctx.config['checks']} 항목을 한 번에 점검한 뒤 우선순위를 정하는 것이 좋습니다.",
        f"상담에서는 현재 결과만 평가하지 않고 {ctx.config['checks']} 항목을 살펴 실제로 이어갈 수 있는 계획을 정합니다.",
        f"같은 학년이라도 막히는 지점은 다를 수 있어 {ctx.config['checks']} 항목을 나누어 확인해야 합니다.",
    ]
    school = actual_school_phrase(ctx)
    center_name = actual_center_name(ctx)
    second = [
        f"이 페이지에는 {school} 학생이 참고할 수 있는 상담 범위와 {center_name} 위치 정보를 함께 정리했습니다.",
        f"{school} 관련 상담을 준비한다면 현재 교재와 최근 시험 자료를 가져오면 필요한 범위를 더 구체적으로 확인할 수 있습니다.",
        f"센터 정보와 학교 참고 목록은 상담 범위를 이해하기 위한 자료이며, 실제 개설 여부는 학년과 시간표에 따라 확인합니다.",
        f"{center_name}의 주소와 학교 참고 정보를 확인한 뒤 방문 전 상담 시간을 먼저 맞추는 것을 권합니다.",
    ]
    return choose(ctx, headings), choose(ctx, first), choose(ctx, second)


def process_items(ctx: PageContext) -> list[tuple[str, str]]:
    return [(label, choose(ctx, variants)) for label, variants in ctx.config["process"]]


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
                     if school_values else "<span>학교별 진도 상담 확인</span>")
    tuition = (f'<a class="text-link" href="{html.escape(ctx.info.tuition_url, quote=True)}" target="_blank" rel="noopener noreferrer">센터 교습비 자료 확인</a>'
               if ctx.info.tuition_url else "")
    tuition_block = f"          {tuition}\n" if tuition else ""
    verified_note = choose(ctx, [
        "학교명은 상담 범위를 이해하기 위한 참고 정보입니다. 실제 개설 여부는 학생의 학년·과목과 센터 시간표를 함께 확인해 안내합니다.",
        "표시된 학교는 통학권 참고 자료이며 수업 개설을 의미하지 않습니다. 등록 전 학년·과목과 현재 시간표를 확인해 주세요.",
        "참고 학교와 별개로 학생의 현재 진도와 센터 시간표를 대조한 뒤 실제 수업 가능 여부를 안내합니다.",
        "학교 정보는 상담 준비를 위한 기준입니다. 수업 여부는 학년, 선택 과목, 센터의 현재 개설 시간을 확인한 후 결정됩니다.",
    ])
    return f'''    <section id="verified-center" class="local-section verified-center-section">
      <div class="wrap verified-center-grid">
        <article class="verified-center-card">
          <p class="eyebrow">확인된 센터 정보</p>
          <h2>{html.escape(actual_center_name(ctx))}</h2>
          <dl class="verified-data-list">
            <div><dt>수업 가능 학년</dt><dd>{html.escape(available_grade_text(ctx))}</dd></div>
            <div><dt>주소</dt><dd>{html.escape(actual_address(ctx))}</dd></div>
            <div><dt>등록 정보</dt><dd>{html.escape(registration_value(ctx))}</dd></div>
          </dl>
{tuition_block}          <div class="verified-school-list" aria-label="상담 참고 학교">{school_markup}</div>
          <p class="verified-note">{html.escape(verified_note)}</p>
        </article>
        <figure class="verified-map-card">
          {ctx.map_image}
          <figcaption>{html.escape(ctx.locality)} 생활권에서 방문할 때 참고할 센터 위치 이미지입니다.</figcaption>
        </figure>
      </div>
    </section>'''


def build_quality_section(ctx: PageContext) -> str:
    students = ctx.rng.sample(ctx.config["students"], 3)
    student_bodies = ctx.rng.sample([
        "현재 자료를 확인한 뒤 필요한 단원과 학습량을 정합니다.",
        "상담에서 원인을 나누어 보고 실행 가능한 계획부터 세웁니다.",
        "최근 시험과 과제 기록을 바탕으로 우선 보완할 내용을 확인합니다.",
        "풀이가 멈춘 지점을 확인하고 복습할 개념과 적용 문제를 구분합니다.",
        "과제 완료 기록을 살펴 분량과 난도를 현실적으로 다시 맞춥니다.",
        "시험 범위와 남은 기간을 나누어 우선순위가 높은 학습부터 정합니다.",
        "반복되는 오답을 유형별로 묶고 다음 확인 시점을 계획합니다.",
        "공부 가능한 시간을 기준으로 주중과 주말의 역할을 다르게 잡습니다.",
        "현재 진도에 필요한 이전 개념을 찾아 짧은 복습 단계를 먼저 둡니다.",
        "정답보다 풀이 과정을 살펴 개념, 계산, 해석 중 원인을 구분합니다.",
        "학생이 스스로 설명할 수 있는 범위와 추가 지도가 필요한 범위를 나눕니다.",
        "완료할 수 있는 작은 목표를 정하고 다음 상담에서 실행 결과를 확인합니다.",
    ], 3)
    student_cards = "\n".join(
        f'''            <article class="geo-answer-card">
              <strong>{html.escape(student)}</strong>
              <p>{html.escape(body)}</p>
            </article>'''
        for student, body in zip(students, student_bodies)
    )
    school = actual_school_phrase(ctx)
    fit_intro = choose(ctx, [
        f"{ctx.config['label']}에서는 학생의 현재 상태를 확인하고 우선순위를 정하는 것부터 시작합니다.",
        f"{ctx.config['label']} 상담은 결과보다 막힌 원인과 실행 습관을 먼저 구분합니다.",
        f"{ctx.config['label']} 과정은 같은 학년이라도 교재·진도·오답 유형에 따라 점검 순서가 달라집니다.",
        f"{ctx.config['label']} 상담을 시작하기 전 현재 자료와 실제 공부 시간을 함께 살펴봅니다.",
    ])
    school_check = (choose(ctx, [
        f"{school}의 현재 진도와 다음 시험 일정을 확인합니다.",
        f"{school}에서 사용하는 교재와 시험 범위를 정리합니다.",
        f"{school}의 진도 차이를 고려해 필요한 복습 범위를 확인합니다.",
        f"{school}의 시험 일정과 센터 수업 가능 시간을 함께 대조합니다.",
    ]) if school != "학교별 진도 상담 확인" else choose(ctx, [
        "재학 중인 학교의 현재 진도와 다음 시험 일정을 확인합니다.",
        "학교에서 사용하는 교재와 최근 시험 범위를 준비합니다.",
        "학교 진도와 시험 일정을 알려주면 상담 범위를 정하기 좋습니다.",
        "재학 학교의 수업 진도와 센터 시간표를 함께 대조합니다.",
    ]))
    recent_check = choose(ctx, [
        "현재 교재와 최근 시험지, 자주 틀리는 문제를 준비합니다.",
        "사용 중인 교재와 최근 평가 자료에서 막힌 문제를 표시해 둡니다.",
        "최근 시험지와 과제 기록을 모아 반복되는 어려움을 확인합니다.",
        "현재 진도와 오답이 남은 단원을 알 수 있는 자료를 챙깁니다.",
    ])
    time_check = choose(ctx, [
        "주중과 주말에 실제로 실행할 수 있는 학습 시간을 정리합니다.",
        "학교와 다른 일정까지 고려해 꾸준히 확보할 수 있는 시간을 적어 봅니다.",
        "과제와 복습에 사용할 수 있는 요일별 시간을 현실적으로 계산합니다.",
        "계획이 무너지지 않도록 평일과 주말의 공부 가능 시간을 나누어 봅니다.",
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
    first_answers = [
        f"현재 교재와 최근 시험 자료를 보고 {ctx.config['checks']} 중 우선 확인할 부분을 정합니다. 상담 결과에 따라 시작 단원과 학습량을 안내합니다.",
        f"학생의 현재 진도와 과제 기록, 오답을 함께 확인합니다. {ctx.config['label']}에서 먼저 보완할 내용을 정한 뒤 실행 가능한 계획을 세웁니다.",
        f"성적만으로 반을 정하지 않고 최근 풀이 과정과 학습 시간을 함께 봅니다. {ctx.config['checks']} 항목을 기준으로 상담 범위를 좁힙니다.",
    ]
    school_answer = (choose(ctx, [
        f"{school} 등은 상담 범위를 이해하기 위한 참고 학교입니다. 학교명만으로 수업이 확정되지는 않으며, 현재 진도와 시험 일정, 센터 시간표를 확인한 뒤 가능한 범위를 안내합니다.",
        f"{school} 등의 진도와 시험 일정은 상담 자료로 활용합니다. 실제 수업 여부는 학생의 학년·과목과 센터 시간표를 대조해 확인합니다.",
        f"{school} 등 학교별 자료를 참고할 수 있습니다. 사용 교재와 시험 범위를 알려주시면 현재 개설 수업과 맞는지 확인해 안내합니다.",
        f"{school} 등 재학 학교의 일정은 학습 계획에 반영할 수 있습니다. 다만 학교명만으로 반이 정해지지 않으므로 현재 진도도 함께 살펴봅니다.",
    ]) if school != "학교별 진도 상담 확인" else choose(ctx, [
        "학교별 진도와 시험 범위는 상담에서 확인합니다. 현재 교재와 시험 일정을 알려주시면 센터 시간표와 함께 가능한 범위를 안내합니다.",
        "재학 학교의 교재와 시험 일정을 준비해 주시면 현재 개설 수업과 연결할 수 있는 범위를 확인합니다.",
        "학교 진도는 학생마다 다를 수 있어 최근 시험 범위와 사용 교재를 먼저 살펴본 뒤 학습 순서를 정합니다.",
        "상담에서 재학 학교와 현재 진도를 확인하고 센터 시간표에 맞는 수업 범위를 안내합니다.",
    ]))
    if available_grade_items(ctx):
        grade_answer = choose(ctx, [
            f"센터 정보에 확인된 학년은 {grades}입니다. 같은 학년이라도 과목과 시간표에 따라 달라질 수 있으므로 등록 전 현재 개설 반을 다시 확인해 주세요.",
            f"제공된 센터 자료에는 {grades} 수업이 표시되어 있습니다. 등록 시점의 개설 반과 잔여 시간은 상담에서 다시 확인합니다.",
            f"현재 자료상 가능한 학년은 {grades}입니다. 과목별 개설 시간은 달라질 수 있어 학생 일정과 함께 대조해야 합니다.",
            f"{grades} 학년이 센터 정보에 포함되어 있습니다. 정확한 수업 요일과 시간은 방문 전 확인해 주세요.",
        ])
    else:
        grade_answer = choose(ctx, [
            "제공된 센터 정보에서 이 과목·학년의 개설 범위가 확인되지 않았습니다. 실제 수업 가능 여부는 등록 전 센터 시간표를 기준으로 상담해 주세요.",
            "현재 센터 자료만으로는 해당 학년과 과목의 개설 여부를 확정하기 어렵습니다. 방문 전 최신 시간표를 확인해 주세요.",
            "표시된 자료에 이 학년의 수업 범위가 없어 임의로 안내하지 않습니다. 센터 상담에서 현재 개설 반을 확인해 주세요.",
            "해당 학년·과목은 제공된 자료에서 확인되지 않습니다. 등록 가능 여부는 최신 센터 일정으로 다시 확인해야 합니다.",
        ])
    grade_question = choose(ctx, [
        "센터 자료에서 확인되는 수업 가능 학년은 어떻게 되나요?",
        f"{label} 상담이 가능한 학년 범위는 어디까지인가요?",
        "현재 안내 자료에 표시된 개설 학년을 알 수 있나요?",
        "학년별 수업 가능 여부는 어떤 기준으로 확인하나요?",
        "학생 학년에 맞는 수업이 있는지 어떻게 확인하나요?",
        "등록 전에 확인해야 할 학년별 개설 정보는 무엇인가요?",
    ])
    school_question = choose(ctx, [
        f"{school} 등 학교 진도와 시험 일정을 반영할 수 있나요?",
        f"{school} 등의 교재와 시험 범위는 학습 계획에 어떻게 반영하나요?",
        f"{school} 등 재학 학교에 맞춘 {label} 상담이 가능한가요?",
        f"{school} 등의 학사 일정을 고려해 공부 계획을 조정할 수 있나요?",
    ]) if school != "학교별 진도 상담 확인" else choose(ctx, [
        "학교 진도와 시험 일정은 어떻게 반영하나요?",
        "재학 학교의 교재와 시험 범위도 상담에서 확인하나요?",
        f"학교별 일정에 맞춰 {label} 계획을 조정할 수 있나요?",
        "학교마다 다른 진도는 어떤 자료로 확인하나요?",
    ])
    visit_question = choose(ctx, [
        "방문 상담 전에는 어떤 자료를 준비하면 좋나요?",
        "첫 상담을 효율적으로 진행하려면 무엇을 가져가야 하나요?",
        "학생의 현재 상태를 확인하려면 어떤 기록이 필요한가요?",
        f"{label} 상담 전에 미리 정리할 내용이 있나요?",
        "센터 방문 전에 확인하면 좋은 항목은 무엇인가요?",
        "상담 예약과 준비 자료는 어떻게 확인하면 되나요?",
    ])
    visit_answer = choose(ctx, [
        f"현재 교재와 최근 시험지, 오답 기록을 준비해 주세요. 실제 안내 센터는 {actual_center_name(ctx)}이며 주소는 {actual_address(ctx)}입니다. 방문 전 상담 시간을 확인하는 것이 좋습니다.",
        f"사용 중인 교재, 최근 평가 자료, 평소 공부 가능한 시간을 정리해 오면 좋습니다. {actual_center_name(ctx)} 방문 전에는 {actual_address(ctx)} 위치와 예약 시간을 확인해 주세요.",
        f"최근 시험 결과와 틀린 문제, 과제 수행 기록을 함께 준비하면 상담 범위를 구체화할 수 있습니다. 상담 장소는 {actual_center_name(ctx)}이며 주소는 {actual_address(ctx)}입니다.",
        f"현재 진도와 어려운 단원, 주중 학습 가능 시간을 메모해 주세요. {actual_center_name(ctx)}의 최신 수업 시간과 {actual_address(ctx)} 방문 일정을 먼저 확인하는 것이 좋습니다.",
        f"교재와 시험 범위표, 반복해서 틀리는 문제를 표시해 오면 시작점을 정하는 데 도움이 됩니다. 실제 상담은 {actual_center_name(ctx)}에서 진행하며 주소는 {actual_address(ctx)}입니다.",
        f"학년·과목·현재 진도와 원하는 상담 시간을 먼저 알려주세요. {actual_center_name(ctx)}의 개설 시간 확인 후 {actual_address(ctx)} 방문 일정을 정할 수 있습니다.",
    ])
    return [
        {"q": f"{ctx.title} 상담에서는 무엇을 가장 먼저 확인하나요?", "a": choose(ctx, first_answers)},
        {"q": grade_question, "a": grade_answer},
        {"q": school_question, "a": school_answer},
        {"q": visit_question, "a": visit_answer},
    ]


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
    graph = [node for node in data["@graph"] if not (isinstance(node, dict) and node_has_type(node, "Article"))]
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
            node["description"] = description
            node["isPartOf"] = {"@id": BASE_URL + "/#website"}
            node["dateModified"] = TODAY
            node["about"] = [
                {"@type": "Place", "name": ctx.region},
                {"@type": "Thing", "name": ctx.config["label"]},
            ]
            schools = actual_school_phrase(ctx)
            node["mentions"] = ([{"@type": "Organization", "name": school} for school in schools.split("·") if is_specific_school(school)]
                                if schools != "학교별 진도 상담 확인" else [])
            node["hasPart"] = [
                {"@type": "WebPageElement", "name": "학습관리 방법", "url": ctx.page_url + "#learning-plan"},
                {"@type": "WebPageElement", "name": "확인된 센터 정보", "url": ctx.page_url + "#verified-center"},
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
            }
            node.clear()
            node.update(rebuilt)
        elif node_type == "FAQPage":
            node.clear()
            node.update({"@type": "FAQPage", "@id": ctx.page_url + "#faq", "mainEntity": faq_entities})
        elif node_type == "BreadcrumbList" or node_type == "ItemList":
            pass
    data = normalize_machine_urls(data)
    compact = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    _, match = parse_jsonld(ctx.text)
    return ctx.text[:match.start(1)] + compact + ctx.text[match.end(1):]


def transform_page(ctx: PageContext) -> str:
    description = meta_description(ctx)
    faqs = build_faqs(ctx)

    # Start with JSON-LD because its replacement offsets are based on the original page.
    text = update_jsonld(ctx, faqs, description)
    text = text.replace("https://코칭학원.com", BASE_URL)
    text = replace_meta(text, key="description", value=description, attr_name="name")
    text = replace_meta(text, key="og:description", value=description, attr_name="property")
    text = replace_meta(text, key="og:type", value="article", attr_name="property")
    if 'type="application/rss+xml"' not in text:
        canonical = re.search(r'<link\b[^>]*rel=["\']canonical["\'][^>]*>', text, re.I)
        if not canonical:
            raise ValueError(f"Canonical not found: {ctx.path}")
        rss_link = f'\n  <link rel="alternate" type="application/rss+xml" title="와와학습코칭학원 RSS" href="{BASE_URL}/rss.xml">'
        text = text[:canonical.end()] + rss_link + text[canonical.end():]

    hero_pattern = re.compile(r'(<section class="local-hero">.*?<h1>.*?</h1>)\s*<p>.*?</p>', re.S)
    text, count = hero_pattern.subn(lambda match: match.group(1) + "\n              <p>" + html.escape(hero_intro(ctx)) + "</p>", text, count=1)
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
    text = text.replace("수학는", "수학은").replace("수학를", "수학을").replace("관리을", "관리를")
    text = text.replace("SEO GEO 학습 안내", "학습 및 상담 안내")
    return text


def validate_transformed(ctx: PageContext, text: str) -> list[str]:
    errors: list[str] = []
    if text.count("<h1") != 1:
        errors.append("H1 count")
    for bad in ("수학는", "수학를", "관리을", "SEO GEO", "KEY SUMMARY", "ANSWER READY", "Local Search Guide", "친구와 함께 등록하면 할인", "parent-reviews"):
        if bad in text:
            errors.append(f"remaining token: {bad}")
    if ctx.image_block not in text:
        errors.append("image block changed")
    if ctx.map_image not in text:
        errors.append("map image changed")
    try:
        data, _ = parse_jsonld(text)
        json.dumps(data, ensure_ascii=False)
    except Exception as exc:  # noqa: BLE001 - validator collects diagnostics
        errors.append(f"JSON-LD: {exc}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    center = root / CENTER_DIRNAME
    local_pages = sorted(center.glob("*/index.html"))
    child_pages = sorted(center.glob("*/*/index.html"))
    records, locality_to_key = build_center_records(root, local_pages)
    center_info = load_center_info(root)
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
