"""단락 추출. run/soft break/들여쓰기/정렬/스타일/번호를 손실 없이 보존한다."""

from lxml import etree

from docx_parser.ns import qn, w
from docx_parser.numbering import detect_manual_number, get_auto_numbering


def extract_paragraph(
    p_elem,
    index: int,
    numbering_part,
    style_name_lookup,
    include_raw_xml: bool = False,
) -> dict:
    pPr = p_elem.find(qn("w:pPr"))

    style_id = _get_style_id(pPr)
    style_name = style_name_lookup.get(style_id, style_id) if style_id else None
    outline_level = _get_outline_level(pPr)
    indent = _get_indent(pPr)
    alignment = _get_alignment(pPr)
    auto_numbering = get_auto_numbering(p_elem, numbering_part)

    runs, soft_breaks = _extract_runs_and_breaks(p_elem)

    full_text = "".join(r["text"] for r in runs)
    manual_number = detect_manual_number(full_text)
    numbering = auto_numbering
    if numbering is None and manual_number is not None:
        numbering = {
            "numId": None,
            "ilvl": None,
            "format": None,
            "is_auto": False,
            "raw_token": manual_number,
        }

    para = {
        "index": index,
        "style_name": style_name,
        "outline_level": outline_level,
        "numbering": numbering,
        "indent": indent,
        "alignment": alignment,
        "runs": runs,
        "soft_breaks": soft_breaks,
    }
    if include_raw_xml:
        para["raw_xml"] = etree.tostring(p_elem, encoding="unicode")
    return para


def _get_style_id(pPr) -> str | None:
    if pPr is None:
        return None
    pStyle = pPr.find(qn("w:pStyle"))
    return pStyle.get(qn("w:val")) if pStyle is not None else None


def _get_outline_level(pPr) -> int | None:
    if pPr is None:
        return None
    ol = pPr.find(qn("w:outlineLvl"))
    if ol is None:
        return None
    val = ol.get(qn("w:val"))
    return int(val) if val is not None else None


def _get_indent(pPr) -> dict:
    """들여쓰기 (twips 단위, 1/20 pt). 값 없으면 0."""
    if pPr is None:
        return {"left": 0, "first_line": 0, "hanging": 0}
    ind = pPr.find(qn("w:ind"))
    if ind is None:
        return {"left": 0, "first_line": 0, "hanging": 0}
    return {
        "left": _int_attr(ind, "w:left") or _int_attr(ind, "w:start") or 0,
        "first_line": _int_attr(ind, "w:firstLine") or 0,
        "hanging": _int_attr(ind, "w:hanging") or 0,
    }


def _get_alignment(pPr) -> str | None:
    if pPr is None:
        return None
    jc = pPr.find(qn("w:jc"))
    return jc.get(qn("w:val")) if jc is not None else None


def _extract_runs_and_breaks(p_elem) -> tuple[list[dict], list[int]]:
    """단락 내 run을 순회하며 텍스트/서식 수집 + soft break 위치 기록.

    soft break는 `<w:br>` (type 미지정 또는 textWrapping). page/column break는 제외.
    위치는 'run 인덱스' 기준 — 해당 run *뒤에* soft break가 삽입되었음을 의미.
    """
    runs: list[dict] = []
    soft_breaks: list[int] = []

    for child in p_elem.iter():
        if child.tag != qn("w:r"):
            continue
        # nested w:r (e.g., 필드 내부)도 동일하게 처리
        rPr = child.find(qn("w:rPr"))
        run_text_parts: list[str] = []
        produced_run = False

        for sub in child:
            tag = sub.tag
            if tag == qn("w:t"):
                run_text_parts.append(sub.text or "")
            elif tag == qn("w:tab"):
                run_text_parts.append("\t")
            elif tag == qn("w:br"):
                # soft return 만 (page/column 제외)
                br_type = sub.get(qn("w:type"))
                if br_type in (None, "textWrapping"):
                    # 현재까지 누적된 텍스트로 run 1개 push 후 soft break 마킹
                    if run_text_parts or not produced_run:
                        runs.append(_make_run("".join(run_text_parts), rPr))
                        produced_run = True
                        run_text_parts = []
                    soft_breaks.append(len(runs) - 1)
                # page/column break 는 무시 (필요 시 후속 보완)

        if run_text_parts or not produced_run:
            text = "".join(run_text_parts)
            if text or rPr is not None:
                runs.append(_make_run(text, rPr))

    return runs, soft_breaks


def _make_run(text: str, rPr) -> dict:
    return {
        "text": text,
        "font": _get_font(rPr),
        "size": _get_size(rPr),
        "bold": _has_toggle(rPr, "w:b"),
        "italic": _has_toggle(rPr, "w:i"),
        "color": _get_color(rPr),
        "lang": _get_lang(rPr),
    }


def _get_font(rPr) -> str | None:
    if rPr is None:
        return None
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        return None
    # ascii / hAnsi / eastAsia 중 하나라도. eastAsia가 한글 폰트인 경우 흔함.
    return (
        rFonts.get(qn("w:ascii"))
        or rFonts.get(qn("w:hAnsi"))
        or rFonts.get(qn("w:eastAsia"))
    )


def _get_size(rPr) -> float | None:
    """w:sz는 half-point 단위. 22 → 11pt."""
    if rPr is None:
        return None
    sz = rPr.find(qn("w:sz"))
    if sz is None:
        return None
    val = sz.get(qn("w:val"))
    return float(val) / 2 if val else None


def _has_toggle(rPr, tag: str) -> bool:
    """w:b, w:i 같은 토글 속성. 존재 자체로 true, val="0"이면 false."""
    if rPr is None:
        return False
    el = rPr.find(qn(tag))
    if el is None:
        return False
    val = el.get(qn("w:val"))
    return val not in ("0", "false")


def _get_color(rPr) -> str | None:
    if rPr is None:
        return None
    color = rPr.find(qn("w:color"))
    if color is None:
        return None
    val = color.get(qn("w:val"))
    return val if val and val != "auto" else None


def _get_lang(rPr) -> str | None:
    if rPr is None:
        return None
    lang = rPr.find(qn("w:lang"))
    if lang is None:
        return None
    return lang.get(qn("w:val")) or lang.get(qn("w:eastAsia"))


def _int_attr(el, attr: str) -> int | None:
    val = el.get(qn(attr))
    return int(val) if val is not None else None
