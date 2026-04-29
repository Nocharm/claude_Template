"""섹션, 머리글/꼬리글 추출.

섹션 경계: paragraph의 w:pPr/w:sectPr가 있으면 그 단락이 해당 섹션의 마지막.
마지막 섹션은 body 직속 w:sectPr.
"""

from docx_parser.ns import qn


def extract_sections(body_elem, doc_part, para_extractor) -> list[dict]:
    """본문 순서대로 섹션 경계를 찾아 sectPr 메타와 머리글/꼬리글을 채워 반환.

    para_extractor: 머리글/꼬리글 단락 추출용 함수 (p_elem, index) -> dict.
    """
    # 본문 직접 자식 순회: 단락(w:p)·표(w:tbl) 카운트, sectPr 등장 위치 기록
    sections: list[dict] = []
    paragraph_counter = -1  # 0-based
    section_start = 0

    children = list(body_elem)
    body_sectPr = None
    for child in children:
        if child.tag == qn("w:p"):
            paragraph_counter += 1
            pPr = child.find(qn("w:pPr"))
            sectPr = pPr.find(qn("w:sectPr")) if pPr is not None else None
            if sectPr is not None:
                sections.append(_build_section(
                    sectPr, section_start, paragraph_counter, doc_part, para_extractor,
                ))
                section_start = paragraph_counter + 1
        elif child.tag == qn("w:tbl"):
            # 표는 paragraph_counter 증가 안 함 (단락 인덱스 체계 유지)
            continue
        elif child.tag == qn("w:sectPr"):
            body_sectPr = child

    # 마지막 섹션
    if body_sectPr is not None:
        sections.append(_build_section(
            body_sectPr, section_start, paragraph_counter, doc_part, para_extractor,
        ))

    return sections


def _build_section(sectPr, start_idx: int, end_idx: int, doc_part, para_extractor) -> dict:
    pgSz = sectPr.find(qn("w:pgSz"))
    pgMar = sectPr.find(qn("w:pgMar"))

    page_orientation = (
        pgSz.get(qn("w:orient")) if pgSz is not None and pgSz.get(qn("w:orient")) else "portrait"
    )
    page_size = None
    if pgSz is not None:
        page_size = {
            "width": _int_attr(pgSz, "w:w"),
            "height": _int_attr(pgSz, "w:h"),
        }
    margins = None
    if pgMar is not None:
        margins = {
            k: _int_attr(pgMar, f"w:{k}")
            for k in ("top", "right", "bottom", "left", "header", "footer", "gutter")
        }

    headers = _extract_header_footer(sectPr, "headerReference", doc_part, para_extractor)
    footers = _extract_header_footer(sectPr, "footerReference", doc_part, para_extractor)

    return {
        "start_paragraph_index": start_idx,
        "end_paragraph_index": end_idx,
        "page_orientation": page_orientation,
        "page_size": page_size,
        "margins": margins,
        "header": headers,
        "footer": footers,
    }


def _extract_header_footer(sectPr, ref_tag: str, doc_part, para_extractor) -> dict:
    """default / first_page / even 별로 단락 목록을 추출."""
    out = {"default": None, "first_page": None, "even": None}
    type_map = {"default": "default", "first": "first_page", "even": "even"}

    for ref in sectPr.findall(qn(f"w:{ref_tag}")):
        ref_type = ref.get(qn("w:type")) or "default"
        rid = ref.get(qn("r:id"))
        if rid is None:
            continue
        try:
            related = doc_part.related_parts[rid]
        except KeyError:
            continue
        # 머리글/꼬리글 part의 root → w:hdr or w:ftr → 직속 w:p 들
        root = related.element
        paragraphs = []
        for i, p in enumerate(root.findall(qn("w:p"))):
            paragraphs.append(para_extractor(p, i))
        out[type_map.get(ref_type, ref_type)] = paragraphs
    return out


def _int_attr(el, attr: str) -> int | None:
    val = el.get(qn(attr))
    return int(val) if val is not None else None
