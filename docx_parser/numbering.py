"""자동 번호(w:numPr)와 수동 번호(본문 타이핑) 구분 헬퍼."""

import re

from docx_parser.ns import qn

# 본문에 직접 타이핑된 번호 패턴 (단락 시작부 한정)
# 1. / 1) / (1) / ① ~ ⑳ / 가. / 가) / a. / A. / ⓐ / ⅰ. 등
_MANUAL_NUMBER_PATTERNS = [
    re.compile(r"^\s*\(\d+\)"),           # (1)
    re.compile(r"^\s*\d+\."),              # 1.
    re.compile(r"^\s*\d+\)"),              # 1)
    re.compile(r"^\s*[①-⑳]"),              # ①
    re.compile(r"^\s*[ⓐ-ⓩ]"),              # ⓐ
    re.compile(r"^\s*[Ⅰ-ⅿ][.)]?"),  # 로마숫자 Ⅰ. ⅰ.
    re.compile(r"^\s*[가-힣][.)]"),          # 가. 가)
    re.compile(r"^\s*[A-Za-z][.)]"),         # A. a) (한 글자만)
    re.compile(r"^\s*-\s+"),                 # - 대시 글머리
    re.compile(r"^\s*[•○●■□◆◇]"),  # • ○ ● ■ □ ◆ ◇
]


def get_auto_numbering(p_elem, numbering_part) -> dict | None:
    """단락의 자동 번호 정보를 추출. 없으면 None.

    numbering_part: docx 패키지 내부의 numbering.xml 루트 element (없으면 None).
    """
    pPr = p_elem.find(qn("w:pPr"))
    if pPr is None:
        return None
    numPr = pPr.find(qn("w:numPr"))
    if numPr is None:
        return None

    ilvl_el = numPr.find(qn("w:ilvl"))
    numId_el = numPr.find(qn("w:numId"))
    ilvl = int(ilvl_el.get(qn("w:val"))) if ilvl_el is not None else 0
    numId = int(numId_el.get(qn("w:val"))) if numId_el is not None else None
    if numId is None:
        return None

    fmt = _resolve_num_format(numbering_part, numId, ilvl) if numbering_part is not None else None

    return {
        "numId": numId,
        "ilvl": ilvl,
        "format": fmt,
        "is_auto": True,
    }


def detect_manual_number(text: str) -> str | None:
    """본문 타이핑 번호가 있으면 매칭된 raw 토큰(예: '(1) ', '가. ')을 반환."""
    if not text:
        return None
    for pat in _MANUAL_NUMBER_PATTERNS:
        m = pat.match(text)
        if m:
            return m.group(0)
    return None


def _resolve_num_format(numbering_root, numId: int, ilvl: int) -> str | None:
    """numbering.xml에서 numId → abstractNumId → lvl[ilvl] → numFmt 추적."""
    num_el = numbering_root.find(f'.//{qn("w:num")}[@{qn("w:numId")}="{numId}"]')
    if num_el is None:
        return None
    abs_ref = num_el.find(qn("w:abstractNumId"))
    if abs_ref is None:
        return None
    abs_id = abs_ref.get(qn("w:val"))

    abs_el = numbering_root.find(
        f'.//{qn("w:abstractNum")}[@{qn("w:abstractNumId")}="{abs_id}"]'
    )
    if abs_el is None:
        return None

    for lvl in abs_el.findall(qn("w:lvl")):
        if lvl.get(qn("w:ilvl")) == str(ilvl):
            fmt_el = lvl.find(qn("w:numFmt"))
            if fmt_el is not None:
                return fmt_el.get(qn("w:val"))
    return None
