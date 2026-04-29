"""상호 참조(Cross-reference) 및 북마크 추출.

REF 필드는 두 가지 형태:
- Simple: <w:fldSimple w:instr=" REF _Ref123 \\h ">...</w:fldSimple>
- Complex: <w:fldChar begin> ... <w:instrText> REF _Ref123 \\h </w:instrText> ... <w:fldChar end>
"""

import re

from docx_parser.ns import qn

_REF_INSTR = re.compile(r"\bREF\s+(\S+)", re.IGNORECASE)


def extract_refs_in_paragraph(p_elem, paragraph_index: int) -> list[dict]:
    refs: list[dict] = []

    # Simple field
    for fld in p_elem.iter(qn("w:fldSimple")):
        instr = fld.get(qn("w:instr")) or ""
        m = _REF_INSTR.search(instr)
        if not m:
            continue
        display = "".join(t.text or "" for t in fld.iter(qn("w:t")))
        refs.append({
            "ref_id": None,
            "target_bookmark": m.group(1),
            "display_text": display,
            "paragraph_index": paragraph_index,
            "run_position": _find_run_position(p_elem, fld),
        })

    # Complex field — fldChar begin → instrText → separate → display runs → end
    refs.extend(_extract_complex_refs(p_elem, paragraph_index))

    return refs


def _extract_complex_refs(p_elem, paragraph_index: int) -> list[dict]:
    """w:r 시퀀스에서 fldChar 상태 머신으로 REF 필드 추출."""
    refs: list[dict] = []
    state = "outside"  # outside | collecting_instr | collecting_display
    instr_buf: list[str] = []
    display_buf: list[str] = []
    field_start_run_idx = None

    runs = list(p_elem.iter(qn("w:r")))
    for run_idx, r in enumerate(runs):
        for sub in r:
            tag = sub.tag
            if tag == qn("w:fldChar"):
                t = sub.get(qn("w:fldCharType"))
                if t == "begin":
                    state = "collecting_instr"
                    instr_buf = []
                    display_buf = []
                    field_start_run_idx = run_idx
                elif t == "separate" and state == "collecting_instr":
                    state = "collecting_display"
                elif t == "end":
                    instr = "".join(instr_buf)
                    m = _REF_INSTR.search(instr)
                    if m:
                        refs.append({
                            "ref_id": None,
                            "target_bookmark": m.group(1),
                            "display_text": "".join(display_buf),
                            "paragraph_index": paragraph_index,
                            "run_position": field_start_run_idx,
                        })
                    state = "outside"
                    instr_buf = []
                    display_buf = []
                    field_start_run_idx = None
            elif tag == qn("w:instrText") and state == "collecting_instr":
                instr_buf.append(sub.text or "")
            elif tag == qn("w:t") and state == "collecting_display":
                display_buf.append(sub.text or "")
    return refs


def _find_run_position(p_elem, target_fld) -> int | None:
    """fldSimple 요소가 단락 내 몇 번째 run 위치에 있는지 (가까운 인덱스)."""
    runs = list(p_elem.iter(qn("w:r")))
    # fldSimple 안의 run을 찾으면 그 인덱스 반환
    for child in target_fld.iter(qn("w:r")):
        if child in runs:
            return runs.index(child)
    return None


def extract_bookmarks(p_elem, paragraph_index: int) -> list[dict]:
    """단락 내 bookmarkStart 수집 (id/name)."""
    bms: list[dict] = []
    for bm in p_elem.iter(qn("w:bookmarkStart")):
        bms.append({
            "id": bm.get(qn("w:id")),
            "name": bm.get(qn("w:name")),
            "paragraph_index": paragraph_index,
        })
    return bms
