"""Read-only release audit for the subject-professional page collection.

The generator creates one subject directory, four category hubs, and
4 x 371 locality detail pages.  This audit deliberately does not import the
generator: it checks the files that would actually be deployed against the
independent centre-information source and the site's existing map mapping.

Exit status is zero only when every release-blocking assertion passes.  The
script never writes to the site.
"""

from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SITE_URL = "https://xn--sp5b72l1taf0p.com"
SITE_HOSTS = {"xn--sp5b72l1taf0p.com", "코칭학원.com"}
DOMAIN_NAME = "코칭학원.com"
SITE_NAME = "와와학습코칭학원"
PHONE = "010-3957-8283"
SUBJECT_ROOT = ROOT / "과목별학원"
CENTER_CSV = ROOT.parent / "참고자료" / "공통자료" / "센터정보 정리.csv"

CATEGORIES: dict[str, dict[str, Any]] = {
    "영수전문학원": {
        "label": "영수 전문학원",
        "focus": "combined",
        "subjects": ("영어", "수학"),
    },
    "영어전문학원": {
        "label": "영어 전문학원",
        "focus": "english",
        "subjects": ("영어",),
    },
    "수학전문학원": {
        "label": "수학 전문학원",
        "focus": "math",
        "subjects": ("수학",),
    },
    "전문학원": {
        "label": "전문학원",
        "focus": "combined",
        "subjects": ("영어", "수학"),
    },
}

DETAIL_SCHEMA_TYPES = {
    "WebPage",
    "ImageObject",
    "EducationalOrganization",
    "LocalBusiness",
    "BreadcrumbList",
    "Article",
    "Service",
    "FAQPage",
    "ItemList",
    "CreativeWork",
}
HUB_SCHEMA_TYPES = {"CollectionPage", "BreadcrumbList", "ItemList", "FAQPage"}

# Production-language residue and known malformed source phrases are never
# appropriate in reader-facing detail content.
BLOCKED_TEXT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("authoring_seo_aeo_geo", re.compile(r"(?<![A-Za-z])(?:SEO|AEO|GEO|JSON-LD)(?![A-Za-z])", re.I)),
    ("authoring_manuscript", re.compile(r"(?<![가-힣])원고(?:처럼|라면|라|입니다|에서는|에서|에는|에|의|를|로|가|는|와)?(?![가-힣])")),
    ("authoring_page_intent", re.compile(r"이 페이지|페이지여야|검색 의도|검색자|참고 키워드|운영 키워드|설정한 학생")),
    ("synthetic_review_wording", re.compile(r"후기형\s*예시|후기\s*예시|형식의\s*후기|내용으로\s*정리할\s*수\s*있습니다")),
    ("source_column_wording", re.compile(r"D열|수업학교|본문에서\s*학교명|자료에\s*없는\s*학교를\s*임의로")),
    ("broken_student_particle", re.compile(r"학생(?:를|가|와|라는)")),
    ("broken_grade_particle", re.compile(r"학년(?:를|가|와)")),
    ("broken_awkward_student", re.compile(r"편\s*학생|학부모에게는\s*학부모|것이라는\s*목표")),
    ("broken_semicolon", re.compile(r"(?:합니다|입니다|있습니다);")),
    ("broken_subject_spacing", re.compile(r"영어\s+수학")),
    ("broken_address_split", re.compile(r"304\.[가-힣]|305으로")),
    (
        "broken_duplicate_noun",
        re.compile(
            r"(?<![가-힣])(?P<noun>학생|학부모|상담|관리|확인|자료|학습|수업|학교|기준|과정|"
            r"결과|계획|기록|답안|풀이|교재|영역|오답|복습|진단|설명|단원|학년)\s+(?P=noun)"
            r"(?=(?:에서|으로|은|는|이|가|을|를|과|와|의|에|도|만|부터|까지)?(?:\s|[,.!?]|$))"
        ),
    ),
    ("broken_duplicate_particle", re.compile(r"에서는는|에게는는|으로으로|에서에서|에는에는")),
    ("broken_duplicate_adverb", re.compile(r"가장\s+가장")),
    ("broken_home_check_phrase", re.compile(r"집에서도\s+무엇을\s+봐야\s+하는지\s+집에서도")),
    ("broken_combined_guide_phrase", re.compile(r"영수\s+전문학원\s+일반적인\s+안내처럼")),
    ("broken_school_material_phrase", re.compile(r"학생이\s+받은\s+제공된|자녀\s+제공된")),
    ("broken_math_instrumental", re.compile(r"수학\s+풀이으로")),
    ("broken_next_consultation", re.compile(r"다음\s+첫\s+상담")),
    ("broken_combined_reference", re.compile(r"이\s+영수\s+학습\s+과정")),
    ("broken_design_particle", re.compile(r"수업\s*설계은|피드백\s*구조은")),
    ("broken_choice_phrase", re.compile(r"선택\s*전\s*확인할\s*(?:확인\s*항목|선택\s*기준)")),
    ("authoring_source_wording", re.compile(r"자료에\s*(?:적힌|제시된)|제공된\s*주소\s*정보|구조화\s*데이터")),
    ("broken_grade_student_phrase", re.compile(r"(?:(?:초등|중등|중|고등)(?:학교)?\s*[1-6]\s*학년|해당\s*학년)\s+중\s+[^,.]{2,120}?학생")),
    ("authoring_address_wording", re.compile(r"주소\s*정보는\s*.{5,180}?\s*기준으로\s*제공되어\s*있습니다")),
    ("broken_math_solution_particle", re.compile(r"수학\s*풀이이|영어\s*답안과\s*수학\s*풀이와")),
    ("broken_repeated_school_source", re.compile(r"학생이\s*받은\s*학교에서\s*받은\s*자료|학생이\s*가져온\s*제공된\s*학교\s*자료")),
    ("broken_repeated_process", re.compile(r"과정이\s*필요한\s*과정|학습학습|시험학습\s*성과")),
    ("broken_guidance_phrase", re.compile(r"보는\s*지도가\s*확인할\s*필요|최근\s*교재\s*활용과\s*교재")),
    ("broken_repeated_student_explanation", re.compile(r"학생이\s*설명한\s*두\s*과목\s*내용을\s*학생의\s*설명")),
    ("broken_grade_list_particle", re.compile(r"[초중고][1-6](?:·[초중고][1-6])+?이\s+(?:확인된\s*수업\s*가능\s*학년|전문학원\s*상담\s*가능\s*학년)")),
    ("broken_object_particle", re.compile(r"(?:루틴|장치|구조|절차|관리)(?:가|이)\s+확인할\s+필요")),
    ("broken_repeated_consultation", re.compile(r"상담\s+첫\s+상담")),
    (
        "broken_extended_particle",
        re.compile(
            r"기준는|기준를|기준와|기록라는|예비고이|점검와|결과과|날짜과|과정를|기록를|피드백와|분위기을|"
            r"일정와|기록와|과정는|학습량와|계획와|재확인가|배분와|적용와|구조을|설계을|"
            r"교정와|해석와|대비이|과정와|준비이|누적와|정리이|분류이|복습와|연계이|테스트이|"
            r"피드백는|공유이|활용를|점검는|기록가|기록는|학습를|구성를|자기주도반를|점검가|"
            r"동선를|계획는|시간를|환경를|누적가|단기집중반를|(?:신창지구|첨단지구|청라)과"
        ),
    ),
    (
        "broken_composed_phrase",
        re.compile(
            r"예비해당\s*학년|나누는지부터\s+나누어\s+보면|설명하는\s+데\s+실제\s+계획을\s+세우는\s+데|"
            r"을\s+함께\s+서술형\s+풀이|학교\s+학생에게|오답노트를\s+학생에게|"
            r"영어\s+답안과\s+수학\s+풀이를\s+과목별\s+오답과\s+복습\s+일정을\s+나누면|"
            r"필요한\s+학생에게\s+필요한|확인\s+내용을\s+확인|학생\s+설명과\s+풀이\s+흔적과|"
            r"교재\s+진도와\s+이해도와"
            r"|[가-힣]+(?:는지|인지)부터\s+나누어\s+보면|"
            r"서술형\s+답안의\s+식과\s+설명과\s+서술형\s+풀이의\s+근거를|"
            r"문제집\s+학생에게|시험분석|이\s+행의|학교\s+칸|해당\s+학년\s+(?:이|에게)(?=\s)|"
            r"(?<![가-힣])페이지(?:이지만|는|를|가|에서)?(?![가-힣])"
            r"|이\s+문장은|이\s+목록|목록\s+안에서만\s+언급|[,，]상담에서"
            r"|센터\s+등록\s+자료에서|학교\s+참고\s+범위로|자료에\s+없는\s+학교명|"
            r"제공된\s+학교\s+범위|주소가\s+.{1,250}?으로\s+제공된\s+.{1,80}?학습\s+과정을\s+방문한다면"
            r"|(?:학교\s+)?항목에\s+기재된|(?<=[초중고])[.,](?=[가-힣])"
            r"|학생처럼\s+약점이\s+뚜렷한\s+학생|상담을\s+상담할\s+때|"
            r"(?:이\s+과정에서|상담\s+과정에서는)\s+영어\s+학습\s+과정에서|"
            r"확인(?:이|하는지가)\s+핵심\s+확인사항|확인하는\s+방식이\s+확인할\s+필요가\s+있습니다|"
            r"학습량\s+조정(?:은\s+학습량\s+조정에|을\s+학습량\s+조정과|과\s+학습량\s+조정을)|"
            r"학생에게는\s+학생별\s+계획은|학습\s+과정을\s+(?:알아보는|찾는)\s+과정(?:에서는|에서)|"
            r"수업을\s+시작하기\s+전에는\s+수업\s+위치는"
        ),
    ),
    (
        "reader_copy_residue",
        re.compile(
            r"‘[^’]{1,45}’\s*(?:학습\s*)?항목|[가-힣·0-9]+\s+단계의\s+[^,.!?]{1,50}생활권의|"
            r"제공된\s+학교\s+범위|이\s+행의|학교\s+칸|해당\s+학년|현재\s+학년\s+진단|"
            r"학생에게는[^,.!?]{0,70}학생(?:에게는|이라면|은|이)|예비고가라도|"
            r"학원을\s+고르는\s+과정은[^.!?]{0,100}학습\s+흐름을\s+찾는\s+과정|"
            r"문장\s+구조를\s+읽는\s+힘과\s+시험\s+조건을\s+해석하는\s+힘이\s+같이|"
            r"시험\s+전후의\s+변화를\s+시험\s+전후로|확인된\s+자료에는[^.!?]{1,180}?등을\s+확인할\s+수\s+있습니다|"
            r"등록\s+자료\s+기준|주소\s+항목에는[^.!?]{0,180}?정보가\s+제공|"
            r"수업\s+위치는\s+자료에\s+기재된|학생에게는\s+내신\s+대비는|상담\s+과정에서\s+상담에서|"
            r"정확히\s+다루는\s+순서로\s+상담\s+질문으로|확인하는\s+시간이\s+필요한\s+과정입니다|"
            r"추가\s+확인\s+항목|두\s+과목의\s+주간\s+계획을\s+주간\s+계획과|"
            r"어휘·문법·독해의\s+차이를\s+어휘·문법·독해로|"
            r"학생이\s+(?:문장을|말로)\s+설명한\s+내용을\s+학생의\s+설명과|"
            r"나눠\s+보는\s+것이\s+(?:필요한\s+과정|먼저\s+마련)|"
            r"현재\s+단원과\s+누적\s+빈틈과|확인\s+가능한지|"
            r"과목별\s+오답과\s+복습\s+일정이\s+수업\s+후\s+일정으로|확인된\s+자료에는|"
            r"진단\s+내용을\s+다시\s+묻는\s+것이\s+필요한\s+과정입니다|"
            r"(?:시험\s+범위와\s+남은\s+기간|숙제\s+수행과\s+오답)과|내신진도|"
            r"주소가\s+.{3,220}?로\s+제공되어\s+있으니|주소는\s+.{3,220}?로\s+제공되어\s+있습니다|"
            r"주소가\s+.{3,220}?로\s+제공된\s+.{1,80}?을\s+방문한다면|"
            r"수업\s+시작\s+전에는\s+위치를\s+자료에\s+기재된|제공된\s+학교\s+자료가\s+있다면|"
            r"주간\s+계획을\s+계획에\s+반영하는\s+순서|(?:영어\s+답안과\s+독해\s+근거|수학\s+답안과\s+풀이\s+과정)과|"
            r",\s+또한\s+|"
            r"(?:수업을\s+시작하기\s+전에는|학습\s+계획을\s+세울\s+때는)"
            r"[^.!?]{1,160}?영어[^.!?]{0,80}?찾는\s+가정은"
        ),
    ),
    (
        "reader_internal_data_wording",
        re.compile(
            r"현재\s+학년에게|등록\s+자료에|특정\s+학교명을\s+임의로|"
            r"센터\s+자료(?:\s+기준|에\s+나온)|"
            r"(?:(?:영어|수학)\s+학습\s+과정|해당\s+(?:영어|수학)\s+관리\s+방식|"
            r"지역별\s+(?:영어|수학)\s+학습\s+기준|영어·수학\s+학습\s+과정|"
            r"해당\s+영수\s+관리\s+방식|지역별\s+영수\s+학습\s+기준)"
            r"\s+(?:상담|수업|선택|기준)|"
            r"살펴보기을|점검을\s+점검|등록\s+전\s+확인하면|"
            r"것이\s+확인할\s+필요가\s+있습니다|,(?=확인된)|"
            r"학습\s+계획을\s+세울\s+때는\s+확인된\s+수업\s+위치는|"
            r"까지\s+무엇을\s+남길지까지|예비현재\s+학년|현재\s+학년(?:맞춤|과정)|"
            r"현재\s+학년의\s+학생의|(?:이)?라는\s+표현은|’\s+표현은\s+결과를\s+약속|"
            r"[가-힣 ]+\s+영어\s+(?:상담|수업)\s+(?:초등|중등|고등)\s+과정은|"
            r"상담\s+때[^.!?]{0,100}?상담에서|학습\s+운영\s+기준\s+이\s+기준|"
            r"(?:하면|보면|살펴보면|맞춰\s+보면|대조하면|정리하면),\s*"
            r"[^,.!?]{5,110}?(?:하면|보면|살펴보면|맞춰\s+보면|대조하면|정리하면),"
        ),
    ),
    (
        "broken_double_object_heading",
        re.compile(
            r"(?:을|를)\s+[^,.!?:]{1,45}?(?:을|를)\s+연결하는\s+기준|"
            r"(?:확인|점검|살펴보기)을\s+정하는\s+(?:순서|방법)"
        ),
    ),
    (
        "reader_current_grade_residue",
        # ``현재 학년 확인이 필요한 자녀`` is an intentional one-reader
        # phrase.  Other bare ``현재 학년`` wording is internal planning copy.
        re.compile(r"현재\s+학년(?!\s+확인이\s+필요한\s+자녀)"),
    ),
    (
        "reader_new_copy_residue",
        re.compile(
            r"필요한\s+과정입니다|"
            r"(?:해당|지역별)\s+(?:영어|수학|영수|과목)\s+(?:관리\s+방식|학습\s+기준)|"
            r"상담에서\s+살펴본\s+내용입니다|내용을\s+확인할\s+수\s+있습니다|"
            r"흐름이\s+자연스럽습니다|관련\s+안내를\s+학습\s+관리\s+질문|"
            r"확인된\s+학교\s+정보에는[^.!?]{0,200}?확인할\s+수|"
            r"이\s+보완\s+과정은\s+학원과\s+가정이|"
            r"설명받는지가\s+놓치지\s+말아야|"
            r"문법\s+문제를?\s+감으로\s+찍는\s+횟수가\s+많은\s+부분|"
            r"비교\s+기준\s+비교|가정\s+점검\s+내용을\s+점검|"
            r"과정이\s+우선\s+살펴볼\s+기준|합니다입니다|다음\s+수업에서\s+상담에서|"
            r"(?:학습설계|학습노트|입시준비|시험성적|학습목표설정|학습프로그램|학습반복|"
            r"학습자율성|학습\s+성과\s+점검반|학습오답\s+관리|밀착학습관리|학습문제관리|내신과제관리)|"
            r"(?:집중|자기주도|학습|입시|방학)\s*캠프|내신\s+과제\s+점검가|"
            r"학년\s+확인이\s+필요한\s+학생|예비학년|학생학생|"
            r"학생(?:학습|시험|학교|집|쉬운|수학|문제|풀이|상황|맞춤|과정)|"
            r"(?:있는|분명한|이어지는|보는|작동하는)(?:가|이)입니다|으입니다|"
            r"수업의\s+수업\s+내용을|(?:학습암기|학습심화|학습몰입도|학습부진|오답\s+반복)을?\s+잘\s+활용하려면|"
            r"고등학교\s+1학년\s+학생에게\s+학습\s+성적이\s+필요하다면|"
            r"(?:학습예습|학습실전|학습성장력|학습응용|학습암기|학습연습|학습복습|시험오답|학습정리|학습향상|학습이해|학습부진|학습심화|학습자립도|학습달성률|학습약점|학습요약|학습완성도|학습자극|학습보완)|"
            r"영어\s+답안과\s+수학\s+풀이를\s+과목별\s+오답과\s+복습\s+일정을|"
            r"서술형\s+교정과\s+가정\s+복습을\s+가정\s+복습과|"
            r"영어\s+(?:수업|상담|학습\s+기준|학습\s+과정)\s+행에는\s+학교명이|"
            r"학교명이\s+별도로\s+제공되지\s+않은|꾸며\s+쓰는\s+것이\s+아니라|"
            r"차이를\s+구체적으로\s+설명하는\s+데\s+비교\s+기준을\s+세우기\s+수월합니다|"
            r"(?:자녀|학생)의\s+두\s+과목의\s+최근\s+시험지|"
            r"먼저\s+[^.!?]{1,90}?\s+먼저\s+정리하고|주소\s+항목에는|"
            r"같은\s+운영\s+요소가\s+학습\s+지속성에\s+어떤\s+도움을|"
            r"작은\s+항목처럼\s+보여도[^.!?]{0,120}?꾸준히\s+다닐\s+수\s+있는지|"
            r"잘\s+활용하려면\s+강의\s+내용,\s*과제,\s*재확인\s+문제가|"
            r"학생에게\s+[^.!?]{1,55}?(?:이|가)\s+필요하다면\s+먼저\s+최근\s+시험지|"
            r"영어\s+학습\s+기준\s+(?:초등|중등|고등)\s+과정|영어\s+학습\s+기준\s+행|"
            r"(?:영어|수학)\s+학습\s+기준\s+커리큘럼|수학\s+학습\s+기준\s+등록\s+전(?:에는)?|"
            r"생활권의\s+(?:초등학교\s*[1-6]학년|중학교\s*[1-3]학년|고등학교\s*[1-3]학년|"
            r"초[1-6]|중[1-3]|고[1-3]|예비[초중고])[^.!?]{3,150}?학생|"
            r"기준으로\s+상담\s+질문으로|오답을\s+맞힌\s+문제처럼|문제집\s+안내\s+수|"
            r"함께\s+살펴보는[^.!?]{0,100}?(?:한\s+번에|연결하는\s+방식)|"
            r"별도\s+수업\s+가능\s+학교\s+정보가\s+제공되지\s+않았으므로|"
            r"영어\s+(?:전문학원|전문\s+수업)\s+행에는\s+학교명이|"
            r"[^.!?]{2,70}?(?:을|를)\s+먼저\s+안정시키는\s+접근|"
            r"[^.!?]{2,75}?(?:을|를)\s+현재\s+수준을\s+판단하는\s+기준으로\s+삼으면|"
            r"영어와\s+수학의\s+차이를\s+영어·수학으로\s+구분하면|"
            r"어휘·문법·독해와\s+답의\s+근거와\s+서술형\s+교정|"
            r"답의\s+근거를\s+설명하지\s+못하는\s+지점을\s+설명하고|"
            r"학부모\s+관점에서\s+보면|학생에게는\s+[^,.!?]{0,80}?(?:질문은|영어·수학은|"
            r"광고에는|등록\s+전에는|학습\s+공간은|이\s+보완은|상담\s+때는|상담\s+후에는|평일에는)"
            r"|[^.!?]{1,100}?(?:이|가)\s+제공되는지보다\s+중요한\s+점은|"
            r"학생이라는\s+가설을\s+세우고|목표는\s+작은\s+기록이\s+쌓일\s+때|"
            r"(?:영어|수학)\s+학습\s+(?:과정|기준)을\s+찾는|학생의\s+시험을\s+준비할\s+때|"
            r"학습\s+변화\s+확인을\s+보장한다는\s+표현|수학\s+(?:수업|상담|전문학원)의\s+확인된\s+주소|"
            r"수학\s+학습\s+(?:과정|기준)\s+커리큘럼|커리큘럼은\s+빠른\s+선행표보다|"
            r"먼저\s+[^.!?]{1,90}?\s+먼저\s+정리|다음\s+(?:영어|수학)\s+수업\s+전\s+실행\s+계획을\s+다음\s+점검|"
            r"다음\s+계획을\s+다음\s+(?:학습|점검)|풀이\s+과정을\s+설명하게\s+해\s+보는\s+과정|"
            r"영어\s+학생에게\s+맞는|영어\s+학습\s+(?:과정|기준)\s+안내에서|"
            r"필요한\s+부분부터\s+살펴볼\s+부분은|최근\s+학교\s+교재\s+활용과\s+교재를|"
            r"관리까지\s+확인하는\s+관리\s+포인트|수업의\s+수업\s+가능|수업에서\s+수업\s+가능한|"
            r"서술형\s+답안의\s+식과\s+설명을\s+함께[^.!?]{2,100}?하는지를\s+점검|"
            r"살펴볼\s+학생은|(?:에서는|으로는)\s+이\s+보완은|훈련이\s+비교\s+기준을\s+세우기|"
            r"부분(?:이\s+생기는|에서\s+막히는)\s+부분은|영수\s+상담의\s+상담\s+기준|"
            r"차이를\s+구체적으로\s+설명하는\s+데\s+비교\s+기준을\s+세우기\s+수월합니다|"
            r"상담\s+자리에서\s+먼저\s+상담에서"
            r"|서술형\s+답안의\s+식과\s+설명을\s+함께"
            r"|수학\s+수업에서\s+수업과\s+가정\s+복습의\s+역할"
            r"|(?:이처럼\s+약점이\s+뚜렷한|학생처럼\s+현재\s+약점이\s+분명한)\s+학생"
            r"|중등\s+내신\s+이후|단어\s+시험을\s+시험\s+전후\s+변화로"
            r"|찾는\s+가정은\s+가정에서|주소\s+정보\([^)]{3,180}\)는[^.!?]*정보입니다"
            r"|수업을\s+검토할\s+때\s+커리큘럼을\s+볼\s+때|영어\s+학습\s+기준이[^.!?]*공간인지"
            r"|학생에게는\s+수업\s+운영\s+기준은|함께\s+올라가는\s+흐름을\s+함께\s+겪는"
            r"|(?:영어|수학)\s+영역별\s+취약\s+지점을\s+(?:영어|수학)\s+영역별로"
            r"|영어·수학\s+수업의\s+(?:수학·영어|두\s+과목)\s+수업이"
            r"|상황에\s+맞게\s+적용\s+범위를\s+다시\s+조정해야\s+합니다"
            r"|(?:확인하는|확인할|물어볼)\s+질문\s*[:，,]\s*질문"
            r"|주간\s+실행\s+계획을\s+확인하고\s+주간\s+계획을"
            r"|오답\s+재확인\s+절차를\s+기준으로\s+보면[^?]{1,150}?오답\s+재확인도"
            r"|수업\s+운영\s+기준은\s+수업\s+선택의\s+부가\s+요소"
            r"|문제\s+조건을\s+표시한\s+흔적에서\s+문제\s+조건을"
            r"|(?:과목별|영어|수학)\s+현재\s+차이를\s+바탕으로\s+현재\s+수준"
            r"|학교\s+일정과\s+함께\s+살펴보면,\s*학교\s+일정과"
            r"|상담\s+과정에서는[^.!?]{1,160}?(?:확인된\s+수업\s+위치는|"
            r"확인된\s+수업\s+가능\s+학교\s+정보에는|영어\s+전문\s+수업의\s+기본은)"
            r"|학생에게는[^.!?]{0,110}?(?:시험\s+기간\s+수업은|영어·수학\s+학습은|"
            r"문제집(?:\s+선택)?은|학생일수록)"
            r"|함께\s+챙겨야\s+하는\s+준비\s+과정을\s+함께\s+겪는"
            r"|함께\s+계산해야\s+하는\s+상황도\s+함께\s+고려"
            r"|충청\s+새롬중앙로\s+(?:다정동|새롬동)"
            r"|등록된\s+학교\s+정보가\s+없는\s+경우에는\s+최근\s+학교"
            r"|어휘\s+누적\s+기록과\s+단어\s+시험을\s+시험\s+전후\s+기록으로"
            r"|상담\s+과정에서는[^.!?]{1,160}?학생은"
            r"|상담\s+후\s+실행\s+계획[^.!?]{0,100}?다음\s+실행"
            r"|문제\s+조건을\s+표시한\s+흔적[^.!?]{0,100}?문제\s+조건을\s+끝까지"
            r"|상담[^.!?]{0,160}?상담에서\s+살펴보아야\s+합니다"
            r"|과목별\s+취약\s+지점을\s+과목별로\s+나누어\s+보면"
            r"|(?<=[.!?])(?=[가-힣])"
        ),
    ),
    (
        "nested_conditional_openers",
        re.compile(
            r"(?:하면|보면|대조하면|살펴보면|맞춰\s+보면|정리하면|바꾸면|넣으면|"
            r"이어\s+보면|구체화하면|나란히\s+놓으면|놓고\s+보면|연결하면|배열하면|"
            r"삼으면|포함하면|바뀌면|찾으면|나누면|비교하면|판단하면),\s+[^.!?]{2,190}?"
            r"(?:하면|보면|대조하면|살펴보면|맞춰\s+보면|정리하면|바꾸면|넣으면|"
            r"이어\s+보면|구체화하면|나란히\s+놓으면|놓고\s+보면|연결하면|배열하면|"
            r"삼으면|포함하면|바뀌면|찾으면|나누면|비교하면|판단하면)(?:,|\s)"
        ),
    ),
    (
        "double_subject_parent_view",
        re.compile(r"학부모\s+관점에서는\s+[^.!?]{0,100}?(?:학생은|질문은|기준은|광고에는)"),
    ),
    (
        "faq_semantic_adjacent_pair",
        re.compile(
            r"학생이\s+혼자\s+다시\s+해낸\s+기록도\s+비교\s+기준입니다\.\s*"
            r"학생이\s+혼자\s+다시\s+해낸\s+기록도\s+함께\s+남겨\s+두세요\."
        ),
    ),
)

# Heading-only rules stay outside ``BLOCKED_TEXT_PATTERNS`` so prose such as
# a legitimate weekly planning example does not create a false positive.
BROKEN_STUDENT_HEADING_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "duplicate_question_heading",
        re.compile(r"질문\s*[:,，]\s*질문\s*기록"),
    ),
    (
        "broken_student_approach_heading",
        re.compile(
            r"(?:수학|영어|초등|고등학교|개념|집에서는|성실하지만)\s+학생을\s+위한\s+접근"
        ),
    ),
    (
        "broken_weekly_plan_heading",
        re.compile(r"(?:오답을|학년이|방학에는|기초가|영어)\s+학생의\s+주간\s+계획\s+예시"),
    ),
)

# These terms came from an unrelated keyword bank and cannot be asserted as
# centre services without a separate verified source.
UNVERIFIED_OPERATION_PATTERN = re.compile(
    r"입시실적|입시성공사례|입시합격(?:관리|전략)|학원창업|학원운영자|"
    r"학원차량|차량\s*운행|학원주차|셔틀|학원온라인등록|"
    r"(?:학원)?(?:온라인|화상|녹화|실시간)수업|방학캠프|입시캠프|성적향상수업"
)


class Audit:
    """Collect bounded examples while retaining exact issue totals."""

    def __init__(self) -> None:
        self.counts: Counter[str] = Counter()
        self.examples: dict[str, list[dict[str, str]]] = defaultdict(list)

    def fail(self, code: str, page: Path | str, detail: object) -> None:
        self.counts[code] += 1
        if len(self.examples[code]) >= 5:
            return
        if isinstance(page, Path):
            try:
                label = page.relative_to(ROOT).as_posix()
            except ValueError:
                label = str(page)
        else:
            label = str(page)
        self.examples[code].append({"page": label, "detail": str(detail)[:500]})


def normalize(value: object) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(value or ""))).strip()


def normalize_space(value: object) -> str:
    return " ".join(str(value or "").split())


def clean_markup(value: str) -> str:
    value = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", value, flags=re.I | re.S)
    return normalize_space(html.unescape(re.sub(r"<[^>]+>", " ", value)))


def language_check_text(value: str) -> str:
    """Flatten markup while retaining sentence boundaries between blocks."""
    bounded = re.sub(
        r"</(?:p|h[1-6]|li|summary|dt|dd|figcaption)\s*>",
        ". ",
        value,
        flags=re.I,
    )
    return clean_markup(bounded)


def match_one(value: str, pattern: str) -> str | None:
    found = re.search(pattern, value, re.I | re.S)
    return html.unescape(found.group(1)).strip() if found else None


def tag_attr(tag: str, name: str) -> str | None:
    found = re.search(rf"\b{re.escape(name)}\s*=\s*([\"'])(.*?)\1", tag, re.I | re.S)
    return html.unescape(found.group(2)).strip() if found else None


def meta_content(source: str, key: str, value: str) -> str | None:
    pattern = rf"<{key}\b(?=[^>]*\b(?:name|property)=[\"']{re.escape(value)}[\"'])[^>]*>"
    tag = match_one(source, f"({pattern})")
    return tag_attr(tag, "content") if tag else None


def canonical_value(source: str) -> str | None:
    tag = match_one(source, r"(<link\b(?=[^>]*\brel=[\"']canonical[\"'])[^>]*>)")
    return tag_attr(tag, "href") if tag else None


def encoded_url(*parts: str) -> str:
    suffix = "/".join(quote(part, safe="") for part in parts)
    return f"{SITE_URL}/{suffix}/" if suffix else SITE_URL + "/"


def split_grades(value: str) -> list[str]:
    return unique(part.strip() for part in re.split(r"[,/|\s]+", value or ""))


def split_schools(value: str) -> list[str]:
    return unique(part.strip() for part in re.split(r"[,./|\s]+", value or ""))


def unique(values: Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = str(value or "").strip(" ,·/|")
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def load_centres(audit: Audit) -> tuple[list[str], dict[str, dict[str, str]], dict[str, str]]:
    if not CENTER_CSV.is_file():
        audit.fail("missing_center_csv", CENTER_CSV, "센터정보 정리.csv가 없습니다")
        return [], {}, {}
    with CENTER_CSV.open(encoding="utf-8-sig", newline="") as handle:
        source_rows = list(csv.DictReader(handle))
    if len(source_rows) != 371:
        audit.fail("center_row_count", CENTER_CSV, f"expected=371 actual={len(source_rows)}")

    existing: dict[str, str] = {}
    centre_root = ROOT / "전국센터"
    if centre_root.is_dir():
        for folder in centre_root.iterdir():
            if folder.is_dir() and (folder / "index.html").is_file():
                existing[normalize(folder.name)] = folder.name
    aliases = {
        normalize("부천 상동"): "부천상동",
        normalize("당진 읍내동"): "당진읍내동",
        normalize("전주 장동"): "전주장동",
    }

    order: list[str] = []
    rows: dict[str, dict[str, str]] = {}
    displays: dict[str, str] = {}
    for raw in source_rows:
        row = {str(key): str(value or "").strip() for key, value in raw.items()}
        display = row.get("근처 수업가능 동네", "")
        folder = existing.get(normalize(display)) or aliases.get(normalize(display), "")
        if not folder or not (centre_root / folder / "index.html").is_file():
            audit.fail("center_locality_mapping", CENTER_CSV, display)
            continue
        if folder in rows:
            audit.fail("duplicate_center_locality", CENTER_CSV, folder)
            continue
        order.append(folder)
        rows[folder] = row
        displays[folder] = display
    if len(order) != 371 or len(set(order)) != 371:
        audit.fail("mapped_center_count", CENTER_CSV, f"mapped={len(order)} unique={len(set(order))}")
    return order, rows, displays


def expected_grades(row: dict[str, str], focus: str) -> list[str]:
    english = split_grades(row.get("가능학년\n(영어)", ""))
    math = split_grades(row.get("가능학년\n(수학)", ""))
    if focus == "english":
        return english
    if focus == "math":
        return math
    math_set = set(math)
    return [grade for grade in english if grade in math_set]


def expected_schools(row: dict[str, str]) -> list[str]:
    return unique(
        school
        for key in ("타깃학교\n(초)", "타깃학교\n(중)", "타깃학교\n(고)")
        for school in split_schools(row.get(key, ""))
        if school not in {"초등학교", "중학교", "고등학교"}
        and re.search(r"(?:초|중|고|초등학교|중학교|고등학교)$", school)
    )


def school_aliases(schools: list[str] | set[str]) -> set[str]:
    result: set[str] = set()
    for school in schools:
        result.add(school)
        shortened = (
            school.replace("초등학교", "초")
            .replace("중학교", "중")
            .replace("고등학교", "고")
        )
        if shortened not in {"초", "중", "고"}:
            result.add(shortened)
    return result


def normalize_asset_path(source: str) -> str:
    path = unquote(urlsplit(html.unescape(source)).path)
    path = "/" + path.lstrip("./").replace("../", "")
    return path


def expected_map(local: str, audit: Audit) -> str:
    reference = ROOT / "전국센터" / local / "고등수학학원" / "index.html"
    if not reference.is_file():
        audit.fail("missing_map_reference_page", reference, local)
        return ""
    source = reference.read_text(encoding="utf-8")
    images = re.findall(r"<img\b[^>]*\bsrc=([\"'])(.*?)\1", source, re.I | re.S)
    maps = [normalize_asset_path(value) for _, value in images if "/assets/maps/" in value or "assets/maps/" in value]
    if not maps:
        audit.fail("missing_reference_map", reference, local)
        return ""
    return maps[-1]


def schema_graph(source: str, page: Path, audit: Audit) -> list[dict[str, Any]]:
    scripts = re.findall(
        r"<script\b[^>]*\btype=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
        source,
        re.I | re.S,
    )
    if not scripts:
        audit.fail("missing_jsonld", page, "application/ld+json")
        return []
    graph: list[dict[str, Any]] = []
    for raw in scripts:
        try:
            data = json.loads(html.unescape(raw))
        except Exception as exc:  # noqa: BLE001 - report the malformed deployed payload
            audit.fail("invalid_jsonld", page, exc)
            continue
        values = data.get("@graph") if isinstance(data, dict) else data
        if isinstance(values, list):
            graph.extend(item for item in values if isinstance(item, dict))
        elif isinstance(data, dict):
            graph.append(data)
    ids = [str(node.get("@id", "")) for node in graph if node.get("@id")]
    if len(ids) != len(set(ids)):
        audit.fail("duplicate_schema_id", page, "duplicate @id in graph")
    return graph


def node_types(node: dict[str, Any]) -> set[str]:
    value = node.get("@type")
    if isinstance(value, list):
        return {str(item) for item in value}
    return {str(value)} if value else set()


def nodes_of_type(graph: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    return [node for node in graph if kind in node_types(node)]


def one_node(graph: list[dict[str, Any]], kind: str, page: Path, audit: Audit) -> dict[str, Any]:
    nodes = nodes_of_type(graph, kind)
    if len(nodes) != 1:
        audit.fail("schema_type_count", page, f"{kind}: expected=1 actual={len(nodes)}")
        return nodes[0] if nodes else {}
    return nodes[0]


def visible_faq(source: str) -> list[tuple[str, str]]:
    block = match_one(source, r"<section\b[^>]*\bid=[\"']faq-section[\"'][^>]*>(.*?)</section>")
    if block is None:
        return []
    result: list[tuple[str, str]] = []
    for details in re.findall(r"<details\b[^>]*>(.*?)</details>", block, re.I | re.S):
        question = match_one(details, r"<summary\b[^>]*>(.*?)</summary>")
        answer = match_one(details, r"<p\b[^>]*>(.*?)</p>")
        if question is not None and answer is not None:
            result.append((clean_markup(question), clean_markup(answer)))
    return result


def schema_faq(graph: list[dict[str, Any]]) -> list[tuple[str, str]]:
    nodes = nodes_of_type(graph, "FAQPage")
    if len(nodes) != 1:
        return []
    result: list[tuple[str, str]] = []
    entities = nodes[0].get("mainEntity", [])
    if not isinstance(entities, list):
        return result
    for item in entities:
        if not isinstance(item, dict):
            continue
        answer = item.get("acceptedAnswer", {})
        result.append(
            (
                normalize_space(item.get("name", "")),
                normalize_space(answer.get("text", "") if isinstance(answer, dict) else ""),
            )
        )
    return result


def visible_breadcrumb(source: str) -> list[str]:
    block = match_one(source, r"<div\b[^>]*\bclass=[\"'][^\"']*\bcrumbs\b[^\"']*[\"'][^>]*>(.*?)</div>")
    if block is None:
        return []
    return [clean_markup(item) for item in re.findall(r"<span\b[^>]*>(.*?)</span>", block, re.I | re.S)]


def schema_breadcrumb(graph: list[dict[str, Any]]) -> list[tuple[str, str]]:
    nodes = nodes_of_type(graph, "BreadcrumbList")
    if len(nodes) != 1:
        return []
    items = nodes[0].get("itemListElement", [])
    if not isinstance(items, list):
        return []
    ordered = sorted(
        (item for item in items if isinstance(item, dict)),
        key=lambda item: int(item.get("position", 0) or 0),
    )
    return [(normalize_space(item.get("name", "")), str(item.get("item", ""))) for item in ordered]


def href_target(page: Path, href: str, audit: Audit) -> Path | None:
    href = html.unescape(href.strip())
    if not href or href.startswith(("#", "tel:", "mailto:", "javascript:", "data:")):
        return None
    parts = urlsplit(href)
    if parts.scheme in {"http", "https"}:
        if parts.hostname not in SITE_HOSTS:
            return None
        target = ROOT / unquote(parts.path).lstrip("/")
    elif parts.scheme or href.startswith("//"):
        return None
    else:
        relative = unquote(parts.path)
        target = (page.parent / relative).resolve() if relative else page
    root = ROOT.resolve()
    try:
        target.resolve().relative_to(root)
    except ValueError:
        audit.fail("internal_link_path_escape", page, href)
        return target
    if parts.path.endswith("/") or target.is_dir():
        target = target / "index.html"
    return target


def audit_internal_links(page: Path, source: str, audit: Audit) -> None:
    for href in re.findall(r"<a\b[^>]*\bhref=([\"'])(.*?)\1", source, re.I | re.S):
        target = href_target(page, href[1], audit)
        if target is not None and not target.exists():
            audit.fail("broken_internal_link", page, href[1])


def audit_metadata(
    page: Path,
    source: str,
    expected_title: str,
    expected_h1: str,
    expected_url: str,
    audit: Audit,
    *,
    detail: bool,
) -> tuple[str, str, str]:
    titles = re.findall(r"<title\b[^>]*>(.*?)</title>", source, re.I | re.S)
    if len(titles) != 1:
        audit.fail("title_count", page, len(titles))
    title = clean_markup(titles[0]) if titles else ""
    if title != expected_title:
        audit.fail("title_mismatch", page, f"expected={expected_title!r} actual={title!r}")

    descriptions = re.findall(
        r"<meta\b(?=[^>]*\bname=[\"']description[\"'])[^>]*>", source, re.I | re.S
    )
    if len(descriptions) != 1:
        audit.fail("meta_description_count", page, len(descriptions))
    description = tag_attr(descriptions[0], "content") if descriptions else ""
    description = description or ""
    if not description:
        audit.fail("empty_meta_description", page, "")
    if detail and not 70 <= len(description) <= 100:
        audit.fail("detail_meta_length", page, len(description))

    h1_values = [clean_markup(value) for value in re.findall(r"<h1\b[^>]*>(.*?)</h1>", source, re.I | re.S)]
    if len(h1_values) != 1:
        audit.fail("h1_count", page, len(h1_values))
    h1 = h1_values[0] if h1_values else ""
    if h1 != expected_h1:
        audit.fail("h1_mismatch", page, f"expected={expected_h1!r} actual={h1!r}")

    canonical = canonical_value(source) or ""
    og_url = meta_content(source, "meta", "og:url") or ""
    if canonical != expected_url:
        audit.fail("canonical_mismatch", page, f"expected={expected_url} actual={canonical}")
    if og_url != expected_url:
        audit.fail("og_url_mismatch", page, f"expected={expected_url} actual={og_url}")
    if canonical != og_url:
        audit.fail("canonical_og_mismatch", page, f"canonical={canonical} og={og_url}")
    if canonical and any("가" <= char <= "힣" for char in canonical):
        audit.fail("canonical_not_percent_encoded", page, canonical)
    if meta_content(source, "meta", "og:title") != expected_title:
        audit.fail("og_title_mismatch", page, meta_content(source, "meta", "og:title"))
    if meta_content(source, "meta", "og:description") != description:
        audit.fail("og_description_mismatch", page, "og:description differs from meta")
    return title, description, canonical


def audit_hub(
    page: Path,
    expected_url: str,
    expected_title: str,
    expected_h1: str,
    expected_crumbs: list[str],
    expected_items: list[tuple[str, str]],
    audit: Audit,
) -> dict[str, str]:
    if not page.is_file():
        audit.fail("missing_hub", page, expected_url)
        return {"title": "", "description": "", "canonical": ""}
    source = page.read_text(encoding="utf-8")
    title, description, canonical = audit_metadata(
        page, source, expected_title, expected_h1, expected_url, audit, detail=False
    )
    graph = schema_graph(source, page, audit)
    present_types = set().union(*(node_types(node) for node in graph)) if graph else set()
    for kind in HUB_SCHEMA_TYPES - present_types:
        audit.fail("hub_missing_schema_type", page, kind)
    collection = one_node(graph, "CollectionPage", page, audit)
    if collection and collection.get("url") != expected_url:
        audit.fail("hub_collection_url", page, collection.get("url"))

    faq_visible = visible_faq(source)
    faq_structured = schema_faq(graph)
    if len(faq_visible) < 3:
        audit.fail("hub_visible_faq_count", page, len(faq_visible))
    if faq_visible != faq_structured:
        audit.fail("faq_schema_mismatch", page, f"visible={len(faq_visible)} schema={len(faq_structured)}")
    faq_answer_leads: set[str] = set()
    faq_answer_sentences: set[str] = set()
    conditional_endings = (
        r"하면|보면|살펴보면|맞춰\s+보면|대조하면|정리하면|"
        r"나란히\s+놓으면|놓고\s+보면|넣으면|바꾸면|이어\s+보면|"
        r"구체화하면|연결하면|배열하면|삼으면|포함하면"
    )
    for _question, answer in faq_visible:
        for sentence in re.split(r"(?<=[.!?])\s+", answer):
            normalized = normalize_space(sentence)
            lead = re.match(
                rf"^([^,.!?]{{8,140}}?(?:{conditional_endings})),",
                normalized,
            )
            if lead:
                lead_text = lead.group(1).strip()
                if lead_text in faq_answer_leads:
                    audit.fail("faq_repeated_answer_lead", page, lead_text)
                faq_answer_leads.add(lead_text)
            if normalized in faq_answer_sentences:
                audit.fail("faq_repeated_answer_sentence", page, normalized)
            faq_answer_sentences.add(normalized)

    review_block = match_one(
        source,
        r"<section\b[^>]*>\s*<div\b[^>]*>\s*<article\b[^>]*>\s*"
        r"<p\b[^>]*>PARENT CONSULTATION SCENARIOS</p>(.*?)</section>",
    ) or ""
    review_sentences: set[str] = set()
    for review_text in re.findall(
        r"<article\b[^>]*\bclass=[\"'][^\"']*review-card[^\"']*[\"'][^>]*>.*?<p>(.*?)</p>.*?</article>",
        review_block,
        re.I | re.S,
    ):
        for sentence in re.split(r"(?<=[.!?])\s+", clean_markup(review_text)):
            normalized = normalize_space(sentence)
            if normalized in review_sentences:
                audit.fail("review_repeated_sentence", page, normalized)
            review_sentences.add(normalized)
    faq_leads: set[str] = set()
    faq_sentences: set[str] = set()
    for question, answer in faq_visible:
        lead = question.split(",", 1)[0].strip()
        if 8 <= len(lead) <= 80 and lead.endswith(
            ("면", "보면", "살펴보면", "정리하면", "대조하면", "때")
        ):
            if lead in faq_leads:
                audit.fail("faq_repeated_context_lead", page, lead)
            faq_leads.add(lead)
        for sentence in re.split(r"(?<=[.!?])\s+", answer):
            normalized = normalize_space(sentence)
            if not normalized:
                continue
            if normalized in faq_sentences:
                audit.fail("faq_repeated_answer_sentence", page, normalized)
            faq_sentences.add(normalized)

    crumbs = visible_breadcrumb(source)
    if crumbs != expected_crumbs:
        audit.fail("visible_breadcrumb_mismatch", page, f"expected={expected_crumbs} actual={crumbs}")
    structured_crumbs = schema_breadcrumb(graph)
    if [name for name, _ in structured_crumbs] != expected_crumbs:
        audit.fail("schema_breadcrumb_names", page, structured_crumbs)
    if not structured_crumbs or structured_crumbs[-1][1] != expected_url:
        audit.fail("schema_breadcrumb_last_url", page, structured_crumbs[-1] if structured_crumbs else "missing")

    item_list = one_node(graph, "ItemList", page, audit)
    items = item_list.get("itemListElement", []) if item_list else []
    actual_items: list[tuple[str, str]] = []
    if isinstance(items, list):
        for item in sorted(
            (value for value in items if isinstance(value, dict)),
            key=lambda value: int(value.get("position", 0) or 0),
        ):
            actual_items.append((normalize_space(item.get("name", "")), str(item.get("url", ""))))
    if actual_items != expected_items:
        audit.fail("hub_itemlist_mismatch", page, f"expected={len(expected_items)} actual={len(actual_items)}")
    audit_internal_links(page, source, audit)
    return {"title": title, "description": description, "canonical": canonical}


def flatten_school_names(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for value in values:
        if isinstance(value, dict):
            result.extend(split_schools(str(value.get("name", ""))))
        else:
            result.extend(split_schools(str(value)))
    return unique(result)


def extract_explicit_grades(value: str) -> set[str]:
    grades = set(re.findall(r"(?<![가-힣0-9])([초중고][1-6])(?![0-9])", value))
    prefix = {"초등학교": "초", "초등": "초", "중학교": "중", "중등": "중", "고등학교": "고", "고등": "고"}
    for level, number in re.findall(r"(초등학교|초등|중학교|중등|고등학교|고등)\s*([1-6])\s*학년", value):
        grades.add(prefix[level] + number)
    return grades


def known_school_mentions(value: str) -> set[str]:
    """Return longest verified school-name matches from visible prose.

    Some centre rows contain a short name that is also the suffix of a longer
    school name (for example, ``중앙고``).  Keeping only non-contained longest
    matches prevents the shorter school from being reported as a foreign
    entity when the visible text contains the verified longer name.
    """
    locality_spans = [
        (match.start(), match.end())
        for locality in ALL_LOCAL_NAMES
        for match in re.finditer(re.escape(locality), value)
    ]
    candidates: list[tuple[int, int, str]] = []
    for school in ALL_SCHOOL_NAMES:
        if len(school) < 3:
            continue
        for match in re.finditer(re.escape(school), value):
            if any(start <= match.start() and match.end() <= end for start, end in locality_spans):
                continue
            candidates.append((match.start(), match.end(), school))
    return {
        school
        for start, end, school in candidates
        if not any(
            other_start <= start
            and end <= other_end
            and other_end - other_start > end - start
            for other_start, other_end, _ in candidates
        )
    }


def expected_reference_map(local: str, cache: dict[str, str], audit: Audit) -> str:
    if local not in cache:
        cache[local] = expected_map(local, audit)
    return cache[local]


def file_for_asset(source: str) -> Path:
    return ROOT / normalize_asset_path(source).lstrip("/")


def audit_media(
    page: Path,
    source: str,
    title: str,
    local: str,
    row: dict[str, str],
    map_cache: dict[str, str],
    audit: Audit,
) -> str:
    block = match_one(
        source,
        r"<section\b[^>]*\bclass=[\"'][^\"']*subject-media-section[^\"']*[\"'][^>]*>(.*?)</section>",
    )
    if block is None:
        audit.fail("missing_subject_media", page, "subject-media-section")
        return ""
    tags = re.findall(r"<img\b[^>]*>", block, re.I | re.S)
    hidden = [tag for tag in tags if re.search(r"display\s*:\s*none", tag_attr(tag, "style") or "", re.I)]
    if len(hidden) != 1:
        audit.fail("hidden_representative_count", page, len(hidden))
        representative = ""
    else:
        representative = tag_attr(hidden[0], "src") or ""
        if not normalize_asset_path(representative).startswith("/assets/representative/"):
            audit.fail("representative_path", page, representative)
        if tag_attr(hidden[0], "alt") != f"{title} {DOMAIN_NAME} 대표":
            audit.fail("representative_alt", page, tag_attr(hidden[0], "alt"))
        if not file_for_asset(representative).is_file():
            audit.fail("missing_representative_asset", page, representative)

    picture = match_one(source, r"<picture\b[^>]*\bclass=[\"'][^\"']*local-responsive-picture[^\"']*[\"'][^>]*>(.*?)</picture>")
    expected_body = "/assets/centers/common/seoul-q92.webp" if row.get("지역") == "서울" else "/assets/centers/common/local-q92.webp"
    expected_mobile = "/assets/centers/common/seoul-mobile.webp" if row.get("지역") == "서울" else "/assets/centers/common/local-mobile.webp"
    if picture is None:
        audit.fail("missing_body_picture", page, "local-responsive-picture")
    else:
        source_tag = match_one(picture, r"(<source\b[^>]*>)") or ""
        image_tag = match_one(picture, r"(<img\b[^>]*>)") or ""
        actual_mobile = normalize_asset_path(tag_attr(source_tag, "srcset") or "")
        actual_body = normalize_asset_path(tag_attr(image_tag, "src") or "")
        if actual_mobile != expected_mobile:
            audit.fail("body_mobile_mismatch", page, f"expected={expected_mobile} actual={actual_mobile}")
        if actual_body != expected_body:
            audit.fail("body_image_mismatch", page, f"expected={expected_body} actual={actual_body}")
        for asset in (actual_mobile, actual_body):
            if asset and not (ROOT / asset.lstrip("/")).is_file():
                audit.fail("missing_body_asset", page, asset)

    figure = match_one(source, r"<figure\b[^>]*\bclass=[\"'][^\"']*location-card[^\"']*[\"'][^>]*>(.*?)</figure>")
    if figure is None:
        audit.fail("missing_map_figure", page, "location-card")
    else:
        image_tag = match_one(figure, r"(<img\b[^>]*>)") or ""
        actual_map = normalize_asset_path(tag_attr(image_tag, "src") or "")
        wanted_map = expected_reference_map(local, map_cache, audit)
        if actual_map != wanted_map:
            audit.fail("map_image_mismatch", page, f"expected={wanted_map} actual={actual_map}")
        if actual_map and not (ROOT / actual_map.lstrip("/")).is_file():
            audit.fail("missing_map_asset", page, actual_map)
    return normalize_asset_path(representative) if representative else ""


def article_markup(source: str) -> str:
    return match_one(
        source,
        r"<article\b[^>]*\bclass=[\"'][^\"']*subject-article[^\"']*[\"'][^>]*>(.*?)</article>",
    ) or ""


def mask_facts(
    value: str,
    local: str,
    display: str,
    row: dict[str, str],
    category: dict[str, Any],
) -> str:
    facts = [
        local,
        display,
        str(category["label"]),
        str(row.get("지역", "")),
        str(row.get("시or구", "")),
        str(row.get("센터명", "")),
        str(row.get("교육지원청명칭", "")),
        str(row.get("교육지원청 등록번호", "")),
        str(row.get("센터 주소", "")),
        *expected_grades(row, str(category["focus"])),
        *expected_schools(row),
    ]
    result = unicodedata.normalize("NFKC", value)
    for fact in sorted(set(filter(None, facts)), key=len, reverse=True):
        result = result.replace(fact, " <FACT> ")
    result = re.sub(r"\d+", "0", result)
    return normalize_space(result)


def five_word_shingles(value: str) -> set[tuple[str, ...]]:
    tokens = re.findall(r"[가-힣A-Za-z]+|<FACT>|0", value.lower())
    if len(tokens) < 5:
        return {tuple(tokens)} if tokens else set()
    return {tuple(tokens[index:index + 5]) for index in range(len(tokens) - 4)}


def jaccard(left: set[tuple[str, ...]], right: set[tuple[str, ...]]) -> float:
    return len(left & right) / len(left | right) if left or right else 1.0


def check_blocked_text(page: Path, value: str, audit: Audit) -> None:
    for code, pattern in BLOCKED_TEXT_PATTERNS:
        match = pattern.search(value)
        if match:
            audit.fail(code, page, match.group(0))
    match = UNVERIFIED_OPERATION_PATTERN.search(value)
    if match:
        audit.fail("unverified_operation_term", page, match.group(0))


def audit_detail(
    page: Path,
    slug: str,
    category: dict[str, Any],
    local: str,
    display: str,
    row: dict[str, str],
    order: list[str],
    index: int,
    map_cache: dict[str, str],
    audit: Audit,
) -> dict[str, Any]:
    expected_title = f"{local} {category['label']}"
    expected_url = encoded_url("과목별학원", slug, local)
    if not page.is_file():
        audit.fail("missing_detail", page, expected_url)
        return {"title": "", "meta": "", "canonical": "", "representative": "", "article": ""}
    source = page.read_text(encoding="utf-8")
    title, description, canonical = audit_metadata(
        page,
        source,
        f"{expected_title} | {DOMAIN_NAME}",
        expected_title,
        expected_url,
        audit,
        detail=True,
    )
    graph = schema_graph(source, page, audit)
    present_types = set().union(*(node_types(node) for node in graph)) if graph else set()
    for kind in DETAIL_SCHEMA_TYPES - present_types:
        audit.fail("detail_missing_schema_type", page, kind)

    expected_grade_list = expected_grades(row, str(category["focus"]))
    expected_school_list = expected_schools(row)
    expected_school_set = set(expected_school_list)
    expected_school_alias_set = school_aliases(expected_school_set)
    centre_url = encoded_url("전국센터", local)
    centre_id = centre_url + "#organization"

    webpage = one_node(graph, "WebPage", page, audit)
    if webpage:
        if webpage.get("url") != expected_url or webpage.get("name") != f"{expected_title} | {DOMAIN_NAME}":
            audit.fail("webpage_identity", page, f"url={webpage.get('url')} name={webpage.get('name')}")
        if webpage.get("description") != description:
            audit.fail("webpage_description", page, webpage.get("description"))
        for key in ("about", "mentions", "breadcrumb", "mainEntity", "primaryImageOfPage"):
            if not webpage.get(key):
                audit.fail("webpage_missing_relation", page, key)

    organizations = [node for node in graph if {"EducationalOrganization", "LocalBusiness"}.issubset(node_types(node))]
    if len(organizations) != 1:
        audit.fail("combined_organization_type", page, len(organizations))
        organization = organizations[0] if organizations else {}
    else:
        organization = organizations[0]
    if organization:
        if organization.get("@id") != centre_id:
            audit.fail("organization_id", page, organization.get("@id"))
        if organization.get("name") != row.get("센터명"):
            audit.fail("organization_name", page, organization.get("name"))
        if organization.get("url") != centre_url:
            audit.fail("organization_url", page, organization.get("url"))
        if organization.get("telephone") != PHONE:
            audit.fail("organization_phone", page, organization.get("telephone"))
        address = organization.get("address", {})
        if not isinstance(address, dict) or address.get("streetAddress") != row.get("센터 주소"):
            audit.fail("organization_address", page, address)
        identifier = organization.get("identifier")
        expected_identifier = row.get("교육지원청 등록번호", "")
        actual_identifier = identifier.get("value", "") if isinstance(identifier, dict) else ""
        if actual_identifier != expected_identifier:
            audit.fail("organization_identifier", page, f"expected={expected_identifier!r} actual={actual_identifier!r}")
        levels = organization.get("educationalLevel", [])
        if levels != expected_grade_list:
            audit.fail("organization_grades", page, f"expected={expected_grade_list} actual={levels}")
        teaches = organization.get("teaches", [])
        if expected_grade_list and teaches != list(category["subjects"]):
            audit.fail("organization_teaches", page, f"expected={category['subjects']} actual={teaches}")
        if not expected_grade_list and (teaches or organization.get("makesOffer")):
            audit.fail("unverified_empty_grade_offer", page, "teaches/makesOffer must be absent")
        if expected_grade_list and row.get("센터 교습비"):
            offers = organization.get("makesOffer", [])
            offer_urls = [offer.get("url") for offer in offers if isinstance(offer, dict)] if isinstance(offers, list) else []
            if row["센터 교습비"] not in offer_urls:
                audit.fail("organization_tuition_offer", page, offer_urls)

    article = one_node(graph, "Article", page, audit)
    if article:
        if article.get("headline") != expected_title:
            audit.fail("article_headline", page, article.get("headline"))
        for key in ("about", "mentions", "hasPart", "articleSection", "mainEntityOfPage", "isBasedOn"):
            if not article.get(key):
                audit.fail("article_missing_relation", page, key)
        article_school_set = set(flatten_school_names([
            item for item in article.get("mentions", [])
            if isinstance(item, dict) and item.get("@type") == "Organization"
        ]))
        if article_school_set != expected_school_set:
            audit.fail("article_school_mentions", page, f"expected={sorted(expected_school_set)} actual={sorted(article_school_set)}")

    service = one_node(graph, "Service", page, audit)
    if service:
        provider = service.get("provider", {})
        if not isinstance(provider, dict) or provider.get("@id") != centre_id:
            audit.fail("service_provider", page, provider)
        if not service.get("about"):
            audit.fail("service_about", page, "missing")
        audience = service.get("audience")
        actual_audience = audience.get("audienceType", "") if isinstance(audience, dict) else ""
        expected_audience = " · ".join(expected_grade_list)
        if actual_audience != expected_audience:
            audit.fail("service_audience", page, f"expected={expected_audience!r} actual={actual_audience!r}")
        if not expected_grade_list and service.get("offers"):
            audit.fail("service_unverified_offer", page, "offers must be absent")

    image = one_node(graph, "ImageObject", page, audit)
    faq_visible = visible_faq(source)
    faq_structured = schema_faq(graph)
    if len(faq_visible) < 3:
        audit.fail("detail_visible_faq_count", page, len(faq_visible))
    if faq_visible != faq_structured:
        audit.fail("faq_schema_mismatch", page, f"visible={len(faq_visible)} schema={len(faq_structured)}")

    expected_crumbs = ["홈", "과목별학원", str(category["label"]), expected_title]
    crumbs = visible_breadcrumb(source)
    if crumbs != expected_crumbs:
        audit.fail("visible_breadcrumb_mismatch", page, f"expected={expected_crumbs} actual={crumbs}")
    structured_crumbs = schema_breadcrumb(graph)
    if [name for name, _ in structured_crumbs] != expected_crumbs:
        audit.fail("schema_breadcrumb_names", page, structured_crumbs)
    expected_crumb_urls = [
        SITE_URL + "/",
        encoded_url("과목별학원"),
        encoded_url("과목별학원", slug),
        expected_url,
    ]
    if [url for _, url in structured_crumbs] != expected_crumb_urls:
        audit.fail("schema_breadcrumb_urls", page, structured_crumbs)

    sections = re.findall(
        r"<section\b[^>]*\bid=[\"']section-(\d+)[\"'][^>]*>(.*?)</section>",
        article_markup(source),
        re.I | re.S,
    )
    section_headings = [clean_markup(match_one(block, r"<h2\b[^>]*>(.*?)</h2>") or "") for _, block in sections]
    if not 5 <= len(section_headings) <= 7 or any(not heading for heading in section_headings):
        audit.fail("article_section_count", page, len(section_headings))
    if article:
        has_parts = article.get("hasPart", [])
        part_pairs = [
            (normalize_space(item.get("name", "")), str(item.get("url", "")))
            for item in has_parts if isinstance(item, dict)
        ] if isinstance(has_parts, list) else []
        expected_parts = [(heading, expected_url + f"#section-{number}") for number, heading in enumerate(section_headings, 1)]
        if part_pairs != expected_parts:
            audit.fail("article_haspart_mismatch", page, f"expected={len(expected_parts)} actual={len(part_pairs)}")

    item_list = one_node(graph, "ItemList", page, audit)
    item_urls = []
    if item_list:
        items = item_list.get("itemListElement", [])
        if isinstance(items, list):
            item_urls = [str(item.get("url", "")) for item in items if isinstance(item, dict)]
    sibling_urls = [encoded_url("과목별학원", other, local) for other in CATEGORIES if other != slug]
    previous_local = order[index - 1] if index else order[-1]
    next_local = order[index + 1] if index + 1 < len(order) else order[0]
    expected_related = [
        *sibling_urls,
        encoded_url("전국센터", local),
        encoded_url("과목별학원", slug),
        encoded_url("과목별학원"),
        encoded_url("학습관리"),
        encoded_url("과목별학원", slug, previous_local),
        encoded_url("과목별학원", slug, next_local),
    ]
    if item_urls != expected_related:
        audit.fail("related_itemlist_mismatch", page, f"expected={expected_related} actual={item_urls}")

    representative = audit_media(page, source, expected_title, local, row, map_cache, audit)
    if image:
        wanted = SITE_URL + representative if representative else ""
        if image.get("contentUrl") != wanted or image.get("url") != wanted:
            audit.fail("schema_primary_image", page, f"expected={wanted} actual={image.get('contentUrl')}")

    verified = match_one(source, r"<section\b[^>]*\bid=[\"']verified-center[\"'][^>]*>(.*?)</section>") or ""
    verified_text = clean_markup(verified)
    for fact_name, fact in (
        ("center_name", row.get("센터명", "")),
        ("center_address", row.get("센터 주소", "")),
        ("center_identifier", row.get("교육지원청 등록번호", "")),
    ):
        if fact and fact not in verified_text:
            audit.fail("visible_verified_fact", page, f"{fact_name}={fact}")
    school_block = match_one(verified, r"<div\b[^>]*\bclass=[\"'][^\"']*verified-school-list[^\"']*[\"'][^>]*>(.*?)</div>") or ""
    visible_schools = unique(
        school
        for span in re.findall(r"<span\b[^>]*>(.*?)</span>", school_block, re.I | re.S)
        for school in split_schools(clean_markup(span))
    )
    if set(visible_schools) != expected_school_set:
        audit.fail("visible_verified_schools", page, f"expected={sorted(expected_school_set)} actual={sorted(visible_schools)}")
    if expected_grade_list:
        if not all(grade in verified_text for grade in expected_grade_list):
            audit.fail("visible_verified_grades", page, expected_grade_list)
    elif "상담 확인" not in verified_text:
        audit.fail("empty_grades_not_disclosed", page, "상담 확인 문구 없음")

    main = match_one(source, r"<main\b[^>]*>(.*?)</main>") or ""
    visible_main = clean_markup(main)
    # Preserve block boundaries while checking repeated words.  Flattening an
    # H2 ending in ``확인`` and the following paragraph beginning in ``확인``
    # would otherwise create a false ``확인 확인`` defect that does not occur
    # in either reader-facing sentence.
    language_main = re.sub(
        r"<section\b[^>]*\bid=[\"'](?:internal-links|verified-center)[\"'][^>]*>.*?</section>",
        "",
        main,
        flags=re.I | re.S,
    )
    check_blocked_text(page, language_check_text(language_main), audit)
    heading_repeat = re.compile(
        r"(?P<head_repeat>기준|순서|학부모|현재).{0,100}\b(?P=head_repeat)\b"
    )
    for heading_markup in re.findall(r"<h2\b[^>]*>(.*?)</h2>", article_markup(source), re.I | re.S):
        heading = clean_markup(heading_markup)
        match = heading_repeat.search(heading)
        if match:
            audit.fail("repeated_heading_head", page, match.group(0))
        for code, pattern in BROKEN_STUDENT_HEADING_PATTERNS:
            broken = pattern.search(heading)
            if broken:
                audit.fail(code, page, broken.group(0))
    if slug == "전문학원":
        generic_source_residue = re.search(
            r"자료에\s*함께\s*제시된|추가\s*확인\s*항목|같은\s*운영\s*정보는|"
            r"관련\s*안내를\s*확인|같은\s*항목을\s*체크리스트",
            visible_main,
        )
        if generic_source_residue:
            audit.fail("authoring_reference_term", page, generic_source_residue.group(0))
    unsupported_grades = extract_explicit_grades(visible_main) - set(expected_grade_list)
    if unsupported_grades:
        audit.fail("unsupported_visible_grade", page, sorted(unsupported_grades))

    # Only names occurring in the verified national source are treated as
    # school entities.  Three-or-more-syllable matching avoids Korean verb
    # endings such as "남고" being misread as school names.
    actual_school_mentions = known_school_mentions(visible_main)
    if not actual_school_mentions.issubset(expected_school_alias_set):
        audit.fail(
            "unsupported_visible_school",
            page,
            sorted(actual_school_mentions - expected_school_alias_set),
        )

    audit_internal_links(page, source, audit)
    article_text = clean_markup(article_markup(source))
    if len(article_text) < 900:
        audit.fail("article_too_short", page, len(article_text))
    return {
        "title": title,
        "meta": description,
        "canonical": canonical,
        "representative": representative,
        "article": article_text,
    }


ALL_SCHOOL_NAMES: set[str] = set()
ALL_LOCAL_NAMES: set[str] = set()


def audit_nav(audit: Audit) -> dict[str, int]:
    checked = 0
    missing = 0
    wanted = (SUBJECT_ROOT / "index.html").resolve()
    for page in sorted(ROOT.rglob("index.html")):
        if any(part in {".git", ".vercel", "node_modules"} for part in page.parts):
            continue
        source = page.read_text(encoding="utf-8")
        block = match_one(source, r"<div\b[^>]*\bclass=[\"'][^\"']*nav-links[^\"']*[\"'][^>]*>(.*?)</div>")
        if block is None:
            audit.fail("missing_nav_links", page, "nav-links")
            missing += 1
            continue
        anchors = re.findall(r"<a\b[^>]*\bhref=([\"'])(.*?)\1[^>]*>(.*?)</a>", block, re.I | re.S)
        matches = [(href, clean_markup(label)) for _, href, label in anchors if clean_markup(label) == "과목별학원"]
        if len(matches) != 1:
            audit.fail("subject_nav_count", page, len(matches))
            missing += 1
        else:
            target = href_target(page, matches[0][0], audit)
            if target is None or target.resolve() != wanted:
                audit.fail("subject_nav_target", page, matches[0][0])
                missing += 1
        checked += 1
    return {"checked": checked, "failed": missing}


def audit_sitemap(expected_urls: set[str], audit: Audit) -> dict[str, int]:
    path = ROOT / "sitemap.xml"
    if not path.is_file():
        audit.fail("missing_sitemap", path, "")
        return {"urls": 0, "unique": 0, "expected_missing": len(expected_urls)}
    try:
        tree = ET.parse(path)
    except Exception as exc:  # noqa: BLE001
        audit.fail("invalid_sitemap", path, exc)
        return {"urls": 0, "unique": 0, "expected_missing": len(expected_urls)}
    namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    values = [normalize_space(node.text) for node in tree.findall(f"{namespace}url/{namespace}loc") if node.text]
    duplicates = len(values) - len(set(values))
    if duplicates:
        audit.fail("duplicate_sitemap_url", path, duplicates)
    missing = expected_urls - set(values)
    for url in sorted(missing)[:5]:
        audit.fail("subject_url_missing_from_sitemap", path, url)
    return {"urls": len(values), "unique": len(set(values)), "expected_missing": len(missing)}


def audit_rss(audit: Audit) -> dict[str, int]:
    path = ROOT / "rss.xml"
    if not path.is_file():
        audit.fail("missing_rss", path, "")
        return {"items": 0, "unique": 0, "subject_hubs": 0, "subject_details": 0}
    try:
        channel = ET.parse(path).getroot().find("channel")
    except Exception as exc:  # noqa: BLE001
        audit.fail("invalid_rss", path, exc)
        return {"items": 0, "unique": 0, "subject_hubs": 0, "subject_details": 0}
    if channel is None:
        audit.fail("missing_rss_channel", path, "")
        return {"items": 0, "unique": 0, "subject_hubs": 0, "subject_details": 0}

    links: list[str] = []
    for item in channel.findall("item"):
        link = normalize_space(item.findtext("link"))
        guid = normalize_space(item.findtext("guid"))
        if not link or guid != link:
            audit.fail("rss_link_guid", path, f"link={link!r} guid={guid!r}")
        if link:
            links.append(link)
    if len(links) != len(set(links)):
        audit.fail("duplicate_rss_link", path, len(links) - len(set(links)))

    expected_subject = {
        encoded_url("과목별학원"),
        *[encoded_url("과목별학원", slug) for slug in CATEGORIES],
    }
    for url in expected_subject:
        if links.count(url) != 1:
            audit.fail("rss_subject_hub", path, f"{url} count={links.count(url)}")
    subject_prefix = encoded_url("과목별학원")
    subject_links = {url for url in links if url.startswith(subject_prefix)}
    detail_links = subject_links - expected_subject
    for url in sorted(detail_links)[:5]:
        audit.fail("rss_subject_detail", path, url)
    expected_count = 10 + len(CATEGORIES)
    if len(links) != expected_count:
        audit.fail("rss_item_count", path, f"expected={expected_count} actual={len(links)}")
    return {
        "items": len(links),
        "unique": len(set(links)),
        "subject_hubs": len(subject_links & expected_subject),
        "subject_details": len(detail_links),
    }


def audit_discovery(audit: Audit) -> None:
    home = ROOT / "index.html"
    if home.is_file():
        source = home.read_text(encoding="utf-8")
        target = (SUBJECT_ROOT / "index.html").resolve()
        found = False
        for _, href in re.findall(r"<a\b[^>]*\bhref=([\"'])(.*?)\1", source, re.I | re.S):
            resolved = href_target(home, href, audit)
            if resolved is not None and resolved.resolve() == target:
                found = True
                break
        if not found:
            audit.fail("homepage_subject_discovery", home, "과목별학원 링크 없음")
    llms = ROOT / "llms.txt"
    if not llms.is_file():
        audit.fail("missing_llms", llms, "")
    else:
        value = llms.read_text(encoding="utf-8")
        for url in [encoded_url("과목별학원"), *[encoded_url("과목별학원", slug) for slug in CATEGORIES]]:
            if url not in value:
                audit.fail("llms_subject_url_missing", llms, url)


def category_similarity(
    slug: str,
    records: list[tuple[str, str, str]],
    audit: Audit,
) -> dict[str, Any]:
    raw_hashes: dict[str, str] = {}
    masked_hashes: dict[str, str] = {}
    shingles: list[tuple[str, set[tuple[str, ...]]]] = []
    for local, raw, masked in records:
        raw_digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        masked_digest = hashlib.sha256(masked.encode("utf-8")).hexdigest()
        if raw_digest in raw_hashes:
            audit.fail("exact_article_duplicate", SUBJECT_ROOT / slug / local / "index.html", raw_hashes[raw_digest])
        else:
            raw_hashes[raw_digest] = local
        if masked_digest in masked_hashes:
            audit.fail("masked_exact_article_duplicate", SUBJECT_ROOT / slug / local / "index.html", masked_hashes[masked_digest])
        else:
            masked_hashes[masked_digest] = local
        shingles.append((local, five_word_shingles(masked)))

    maximum = 0.0
    pair = ("", "")
    for left_index in range(len(shingles)):
        left_name, left = shingles[left_index]
        for right_name, right in shingles[left_index + 1:]:
            score = jaccard(left, right)
            if score > maximum:
                maximum = score
                pair = (left_name, right_name)
    if maximum >= 0.75:
        audit.fail(
            "masked_five_shingle_similarity",
            SUBJECT_ROOT / slug,
            f"max={maximum:.4f} pair={pair[0]}/{pair[1]} threshold<0.75",
        )
    return {
        "raw_unique": len(raw_hashes),
        "masked_unique": len(masked_hashes),
        "masked_five_shingle_max": round(maximum, 4),
        "worst_pair": list(pair),
    }


def main() -> int:
    audit = Audit()
    order, rows, displays = load_centres(audit)
    global ALL_LOCAL_NAMES, ALL_SCHOOL_NAMES
    ALL_SCHOOL_NAMES = school_aliases({
        school
        for row in rows.values()
        for school in expected_schools(row)
    })
    ALL_LOCAL_NAMES = set(order) | set(displays.values())

    expected_urls: set[str] = {encoded_url("과목별학원")}
    metadata_titles: list[str] = []
    metadata_descriptions: list[str] = []
    metadata_canonicals: list[str] = []
    per_category: dict[str, dict[str, Any]] = {}
    map_cache: dict[str, str] = {}

    root_items = [
        (str(config["label"]), encoded_url("과목별학원", slug))
        for slug, config in CATEGORIES.items()
    ]
    root_result = audit_hub(
        SUBJECT_ROOT / "index.html",
        encoded_url("과목별학원"),
        f"과목별학원 | {DOMAIN_NAME}",
        "과목별학원",
        ["홈", "과목별학원"],
        root_items,
        audit,
    )
    metadata_titles.append(root_result["title"])
    metadata_descriptions.append(root_result["description"])
    metadata_canonicals.append(root_result["canonical"])

    for slug, category in CATEGORIES.items():
        hub_url = encoded_url("과목별학원", slug)
        expected_urls.add(hub_url)
        hub_items = [(f"{local} {category['label']}", encoded_url("과목별학원", slug, local)) for local in order]
        hub_result = audit_hub(
            SUBJECT_ROOT / slug / "index.html",
            hub_url,
            f"{category['label']} 지역 안내 | {DOMAIN_NAME}",
            f"동네별 {category['label']} 안내",
            ["홈", "과목별학원", f"{category['label']} 지역 안내"],
            hub_items,
            audit,
        )
        metadata_titles.append(hub_result["title"])
        metadata_descriptions.append(hub_result["description"])
        metadata_canonicals.append(hub_result["canonical"])

        category_root = SUBJECT_ROOT / slug
        actual_details = {
            path.parent.name
            for path in category_root.glob("*/index.html")
            if path.parent != category_root
        } if category_root.is_dir() else set()
        if actual_details != set(order):
            audit.fail(
                "category_detail_set",
                category_root,
                f"missing={sorted(set(order)-actual_details)[:5]} extra={sorted(actual_details-set(order))[:5]}",
            )

        records: list[tuple[str, str, str]] = []
        representatives: list[str] = []
        for index, local in enumerate(order):
            expected_urls.add(encoded_url("과목별학원", slug, local))
            page = category_root / local / "index.html"
            result = audit_detail(
                page,
                slug,
                category,
                local,
                displays.get(local, local),
                rows[local],
                order,
                index,
                map_cache,
                audit,
            )
            metadata_titles.append(result["title"])
            metadata_descriptions.append(result["meta"])
            metadata_canonicals.append(result["canonical"])
            if result["representative"]:
                representatives.append(result["representative"])
            if result["article"]:
                masked = mask_facts(result["article"], local, displays.get(local, local), rows[local], category)
                records.append((local, result["article"], masked))

        if len(representatives) != 371 or len(set(representatives)) != 371:
            audit.fail(
                "category_representative_uniqueness",
                category_root,
                f"count={len(representatives)} unique={len(set(representatives))}",
            )
        similarity = category_similarity(slug, records, audit) if len(records) == 371 else {
            "raw_unique": len({raw for _, raw, _ in records}),
            "masked_unique": len({masked for _, _, masked in records}),
            "masked_five_shingle_max": None,
            "worst_pair": [],
        }
        per_category[slug] = {
            "expected_details": 371,
            "audited_details": len(records),
            "representative_unique": len(set(representatives)),
            **similarity,
        }

    expected_page_count = 1 + len(CATEGORIES) + 371 * len(CATEGORIES)
    subject_pages = list(SUBJECT_ROOT.rglob("index.html")) if SUBJECT_ROOT.is_dir() else []
    if len(subject_pages) != expected_page_count:
        audit.fail("subject_page_count", SUBJECT_ROOT, f"expected={expected_page_count} actual={len(subject_pages)}")

    for name, values in (
        ("title", metadata_titles),
        ("description", metadata_descriptions),
        ("canonical", metadata_canonicals),
    ):
        nonempty = [value for value in values if value]
        if len(nonempty) != len(set(nonempty)):
            duplicates = [value for value, count in Counter(nonempty).items() if count > 1]
            audit.fail(f"duplicate_{name}", SUBJECT_ROOT, duplicates[:5])

    sitemap = audit_sitemap(expected_urls, audit)
    rss = audit_rss(audit)
    nav = audit_nav(audit)
    audit_discovery(audit)

    report = {
        "status": "PASS" if not audit.counts else "FAIL",
        "expected": {
            "subject_root_hubs": 1,
            "category_hubs": len(CATEGORIES),
            "detail_pages": 371 * len(CATEGORIES),
            "total_subject_pages": expected_page_count,
            "masked_five_shingle_threshold": "<0.75",
        },
        "actual": {
            "subject_pages": len(subject_pages),
            "unique_titles": len(set(filter(None, metadata_titles))),
            "unique_descriptions": len(set(filter(None, metadata_descriptions))),
            "unique_canonicals": len(set(filter(None, metadata_canonicals))),
            "sitemap": sitemap,
            "rss": rss,
            "navigation": nav,
        },
        "categories": per_category,
        "issue_counts": dict(sorted(audit.counts.items())),
        "issue_examples": dict(sorted(audit.examples.items())),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if audit.counts else 0


if __name__ == "__main__":
    sys.exit(main())
