"""Focused regression tests for subject-professional sentence polishing."""

from __future__ import annotations

import unittest

import audit_subject_professional_site as release_audit
import generate_subject_professional_pages as engine
import generate_subject_professional_site as site


class SubjectProfessionalLanguageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = site.ENGINE_CONFIGS["영수전문학원"]

    def test_known_defects_are_repaired_after_site_substitutions(self) -> None:
        samples = {
            "집에서도 무엇을 봐야 하는지 집에서도 확인할 기준이 분명해졌습니다.":
                "집에서도 무엇을 확인해야 하는지 기준이 분명해졌습니다.",
            "영어 수업에서는는 다음 내용을 봅니다.":
                "영어 수업에서는 다음 내용을 봅니다.",
            "지역별 영어 학습 기준 기준에서 설명합니다.":
                "영어 학습 기준에서 설명합니다.",
            "가경동 영수 전문학원 일반적인 안내처럼 아이를 봅니다.":
                "가경동 영수 전문학원 안내에서 아이를 봅니다.",
            "아이 유형을 먼저 정리하는 원고라 읽기 편했습니다.":
                "아이의 학습 상황부터 정리해 상담 기준을 이해하기 쉬웠습니다.",
            "실제 적용 범위는 학생이 받은 제공된 학교 자료로 맞춥니다.":
                "실제 적용 범위는 학생이 받은 학교 자료로 맞춥니다.",
            "첫 상담에 앞서 자녀 제공된 학교 자료를 준비합니다.":
                "첫 상담에 앞서 자녀의 학교 자료를 준비합니다.",
            "가장 가장 최근 시험지를 봅니다.":
                "가장 최근 시험지를 봅니다.",
            "영어 답안과 수학 풀이으로 나누어 봅니다.":
                "영어 답안과 수학 풀이로 나누어 봅니다.",
            "다음 첫 상담에서 확인합니다.":
                "다음 상담에서 확인합니다.",
            "이 영수 학습 과정 상담에서는 확인합니다.":
                "영어·수학 상담에서는 확인합니다.",
            "학습 학습 계획 계획을 확인합니다.":
                "학습 계획을 확인합니다.",
            "현재 학년에게 맞는 과정을 확인합니다.":
                "학생에게 맞는 과정을 확인합니다.",
            "확인된 센터 자료 기준으로 수업 범위를 봅니다.":
                "확인된 정보상 수업 범위를 봅니다.",
            "확인된 센터 주소는 리더스빌딩 402으입니다.":
                "확인된 센터 주소는 리더스빌딩 402입니다.",
            "영어 답안과 수학 풀이와 복습 기록을 비교합니다.":
                "영어 답안·수학 풀이와 복습 기록을 비교합니다.",
            "영어 학습 기준 고등 과정은 학교 시험에 맞춰 봅니다.":
                "영어 고등 과정은 학교 시험에 맞춰 봅니다.",
            "명일동 생활권의 중1 개념 설명은 알지만 적용에서 막히는 학생은 복습이 필요합니다.":
                "명일동 생활권에서 개념 설명은 알지만 적용에서 막히는 중1 학생은 복습이 필요합니다.",
            "영어 답안을 현재 수준을 판단하는 기준으로 삼으면 시작점이 보입니다.":
                "영어 답안을 바탕으로 현재 수준을 판단하면 시작점이 보입니다.",
            "수학 학습 기준 등록 전 학부모 체크리스트를 확인합니다.":
                "수학 수업 등록 전 학부모 체크리스트를 확인합니다.",
            "과목별 현재 차이를 바탕으로 현재 수준을 판단합니다.":
                "과목별 차이를 바탕으로 현재 수준을 판단합니다.",
            "학교 일정과 함께 살펴보면, 학교 일정과 가정 복습 시간을 확인합니다.":
                "최근 자료와 함께 살펴보면, 학교 일정과 가정 복습 시간을 확인합니다.",
            "상담 과정에서는 확인된 수업 위치는 명일동입니다.":
                "상담 과정에서 확인된 수업 위치는 명일동입니다.",
            "학생에게는 시험 기간 수업은 평소 진도와 달라야 합니다.":
                "시험 기간 수업은 평소 진도와 달라야 합니다.",
            "충청 새롬중앙로 다정동 학부모가 확인합니다.":
                "세종 다정동 학부모가 확인합니다.",
            "함께 챙겨야 하는 준비 과정을 함께 겪는 학생입니다.":
                "챙겨야 하는 준비 과정을 겪는 학생입니다.",
            "문제 조건을 표시한 흔적에서 문제 조건을 끝까지 읽는지 봅니다.":
                "문제 조건을 표시한 흔적에서 조건을 끝까지 읽는지 봅니다.",
            "어휘 누적 기록과 단어 시험을 시험 전후 기록으로 비교하면 방향이 보입니다.":
                "어휘 누적 기록과 단어 시험 결과를 시험 전후로 비교하면 방향이 보입니다.",
            "영수 전문학원 상담 과정에서는 복습이 느린 학생은 기록이 필요합니다.":
                "영수 전문학원 상담 과정에서 복습이 느린 학생은 기록이 필요합니다.",
        }
        for source, expected in samples.items():
            with self.subTest(source=source):
                actual = engine.final_polish(
                    site.site_polish(source, "명일동", self.config),
                    "명일동",
                    self.config,
                    ["중1"],
                    [],
                )
                self.assertEqual(expected, actual)
                self.assertIsNone(site.MALFORMED_LANGUAGE_RE.search(actual))

    def test_shared_engine_repairs_doubled_particle(self) -> None:
        source = "영어 수업에서는는 다음 내용을 봅니다."
        self.assertIsNotNone(site.MALFORMED_LANGUAGE_RE.search(source))
        self.assertEqual(
            "영어 수업에서는 다음 내용을 봅니다.",
            engine.polish_known_language_defects(source),
        )

    def test_release_audit_blocks_known_raw_phrases(self) -> None:
        raw_phrases = (
            "집에서도 무엇을 봐야 하는지 집에서도 확인합니다.",
            "영어 수업에서는는 확인합니다.",
            "지역별 학습 기준 기준에서 설명합니다.",
            "영수 전문학원 일반적인 안내처럼 설명합니다.",
            "아이 유형을 정리하는 원고라 읽기 편했습니다.",
            "학생이 받은 제공된 학교 자료를 봅니다.",
            "자녀 제공된 학교 자료를 봅니다.",
            "가장 가장 최근 시험지를 봅니다.",
            "수학 풀이으로 구분합니다.",
            "다음 첫 상담에서 확인합니다.",
            "이 영수 학습 과정에서 확인합니다.",
            "학습 학습 계획을 확인합니다.",
            "현재 학년에게 맞는 과정을 확인합니다.",
            "센터 자료에 나온 학교를 봅니다.",
            "상담 계획을 오답 기록을 연결하는 기준",
            "수학 학습 기준 등록 전 학부모 체크리스트",
            "과목별 현재 차이를 바탕으로 현재 수준을 판단합니다.",
            "학교 일정과 함께 살펴보면, 학교 일정과 복습 시간을 확인합니다.",
            "충청 새롬중앙로 다정동 학부모가 확인합니다.",
            "어휘 누적 기록과 단어 시험을 시험 전후 기록으로 비교합니다.",
            "상담 과정에서는 복습이 느린 학생은 기록이 필요합니다.",
            "상담 후 실행 계획을 확인하고 다음 실행을 계획에 반영합니다.",
            "문제 조건을 표시한 흔적과 함께 문제 조건을 끝까지 읽는지 봅니다.",
            "수학 상담에서는 오답 기록을 상담에서 살펴보아야 합니다.",
            "과목별 취약 지점을 과목별로 나누어 보면 순서가 보입니다.",
        )
        for phrase in raw_phrases:
            with self.subTest(phrase=phrase):
                result = release_audit.Audit()
                release_audit.check_blocked_text("sample", phrase, result)
                self.assertTrue(result.counts, phrase)

    def test_release_audit_does_not_join_heading_and_paragraph_words(self) -> None:
        markup = "<h2>학교 자료 확인</h2><p>확인 가능한 자료를 준비합니다.</p>"
        text = release_audit.language_check_text(markup)
        result = release_audit.Audit()
        release_audit.check_blocked_text("sample", text, result)
        self.assertNotIn("broken_duplicate_noun", result.counts)

    def test_release_audit_blocks_latest_copy_batch(self) -> None:
        blocked_samples = {
            "reader_current_grade_residue": "FAQ에서는 현재 학년부터 확인하나요?",
            "reader_new_copy_residue": "진단 내용을 다시 묻는 것이 필요한 과정입니다.",
            "nested_conditional_openers": (
                "두 과목의 시험지를 학생의 설명과 나란히 놓으면, "
                "주간 계획을 가정 복습 기준으로 바꾸면, 다음 순서가 보입니다."
            ),
            "double_subject_parent_view": "학부모 관점에서는 광고에는 좋은 말이 많습니다.",
            "faq_semantic_adjacent_pair": (
                "학생이 혼자 다시 해낸 기록도 비교 기준입니다. "
                "학생이 혼자 다시 해낸 기록도 함께 남겨 두세요."
            ),
        }
        for expected_code, phrase in blocked_samples.items():
            with self.subTest(code=expected_code):
                result = release_audit.Audit()
                release_audit.check_blocked_text("sample", phrase, result)
                self.assertIn(expected_code, result.counts)

        allowed = "갈현동에서 현재 학년 확인이 필요한 자녀가 어느 과목부터 복습할지 고민합니다."
        result = release_audit.Audit()
        release_audit.check_blocked_text("sample", allowed, result)
        self.assertNotIn("reader_current_grade_residue", result.counts)

    def test_release_audit_blocks_broken_student_headings_only_in_h2(self) -> None:
        blocked_headings = {
            "duplicate_question_heading": "놓치기 쉬운 질문: 질문 기록과 상담 항목",
            "broken_student_approach_heading": "예비고와 고등 내신을 준비하는 학생 중 수학 학생을 위한 접근",
            "broken_weekly_plan_heading": "오답을 학생의 주간 계획 예시",
        }
        for expected_code, heading in blocked_headings.items():
            with self.subTest(code=expected_code):
                result = release_audit.Audit()
                for code, pattern in release_audit.BROKEN_STUDENT_HEADING_PATTERNS:
                    match = pattern.search(heading)
                    if match:
                        result.fail(code, "sample", match.group(0))
                self.assertIn(expected_code, result.counts)

        normal_heading = "고등 학생의 주간 계획 예시: 현재 학습 상태와 다음 실행"
        self.assertFalse(any(pattern.search(normal_heading) for _, pattern in release_audit.BROKEN_STUDENT_HEADING_PATTERNS))

    def test_faq_page_sentence_deduplication(self) -> None:
        faqs = [
            {
                "question": "첫 질문인가요?",
                "answer": "최근 시험지를 함께 보면, 직접 답변 하나입니다. 공통 마무리입니다.",
            },
            {
                "question": "둘째 질문인가요?",
                "answer": "최근 시험지를 함께 보면, 직접 답변 둘입니다. 공통 마무리입니다.",
            },
        ]
        polished = engine.dedupe_faq_sentences_across_page(faqs)
        joined = " ".join(item["answer"] for item in polished)
        self.assertEqual(1, joined.count("공통 마무리입니다."))
        self.assertEqual(1, joined.count("최근 시험지를 함께 보면,"))
        self.assertIn("직접 답변 둘입니다.", joined)

    def test_stacked_faq_condition_keeps_specific_clause(self) -> None:
        source = (
            "두 과목의 시험지를 상담 자료와 맞춰 보면, "
            "학생의 설명과 실제 답안을 함께 비교하면 시작점을 정하기 쉽습니다."
        )
        self.assertEqual(
            "학생의 설명과 실제 답안을 함께 비교하면 시작점을 정하기 쉽습니다.",
            engine.collapse_stacked_faq_conditionals(source),
        )

    def test_stacked_public_condition_keeps_specific_clause_without_second_comma(self) -> None:
        source = (
            "최근 기록을 함께 보면, 상담 자리에서 답안과 풀이의 시작점을 "
            "구체적으로 설명하는지 확인하면 방향을 정하기 쉽습니다."
        )
        self.assertEqual(
            "상담 자리에서 답안과 풀이의 시작점을 구체적으로 설명하는지 확인하면 방향을 정하기 쉽습니다.",
            engine.collapse_stacked_conditionals(source),
        )

    def test_verified_school_sequence_is_stably_deduplicated(self) -> None:
        source = "확인된 학교 정보에는 진흥중·신창중·진흥중 등이 포함됩니다."
        self.assertEqual(
            "확인된 학교 정보에는 진흥중·신창중 등이 포함됩니다.",
            engine.normalize_school_separators(source, ["진흥중", "신창중"]),
        )

    def test_sejong_road_name_is_not_used_as_public_city(self) -> None:
        center = site.base_center_data("다정동")
        self.assertEqual("세종", center["region"])
        self.assertEqual("세종시", center["city"])
        self.assertEqual("새롬중앙로", center["address"]["addressLocality"])


if __name__ == "__main__":
    unittest.main()
