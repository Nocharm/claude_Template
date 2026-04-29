"""그림(Image) 추출. 인라인/플로팅 구분, 캡션 매칭."""

import os
import re

from docx_parser.ns import qn

# 1 inch = 914400 EMU (DrawingML 단위)
EMU_PER_INCH = 914400


def extract_images_in_paragraph(p_elem, anchor_paragraph_index: int, rels_map) -> list[dict]:
    """단락 내 모든 drawing 요소를 인라인/플로팅 구분하여 추출."""
    images: list[dict] = []
    for drawing in p_elem.iter(qn("w:drawing")):
        for child in drawing:
            if child.tag == qn("wp:inline"):
                img = _extract_drawing(child, "inline", rels_map)
            elif child.tag == qn("wp:anchor"):
                img = _extract_drawing(child, "floating", rels_map)
            else:
                continue
            if img is not None:
                img["anchor_paragraph_index"] = anchor_paragraph_index
                images.append(img)
    return images


def _extract_drawing(wp_elem, kind: str, rels_map) -> dict | None:
    extent = wp_elem.find(qn("wp:extent"))
    width_emu = int(extent.get("cx")) if extent is not None and extent.get("cx") else None
    height_emu = int(extent.get("cy")) if extent is not None and extent.get("cy") else None

    blip = wp_elem.find(f'.//{qn("a:blip")}')
    if blip is None:
        return None
    embed = blip.get(qn("r:embed"))
    target = rels_map.get(embed) if embed else None
    file_name = os.path.basename(target) if target else None
    fmt = file_name.rsplit(".", 1)[-1].lower() if file_name and "." in file_name else None

    return {
        "file_name": file_name,
        "format": fmt,
        "width_emu": width_emu,
        "height_emu": height_emu,
        "width_in": _emu_to_inch(width_emu),
        "height_in": _emu_to_inch(height_emu),
        "kind": kind,
        "caption": None,  # 후속 매칭에서 채움
    }


def _emu_to_inch(emu: int | None) -> float | None:
    if emu is None:
        return None
    return round(emu / EMU_PER_INCH, 4)


# --- 캡션 ---

_SEQ_INSTR = re.compile(r"\bSEQ\s+(\S+)", re.IGNORECASE)


def is_caption_paragraph(paragraph: dict) -> tuple[bool, dict | None]:
    """단락이 캡션이면 (True, {seq_name, seq_number, text}) 반환.

    판별: style_name이 'Caption' 류이거나 본문에 SEQ 필드 흔적이 있을 때.
    seq_number는 캡션 단락 내 텍스트에서 첫 번째 정수를 찾아 사용.
    """
    style = (paragraph.get("style_name") or "").lower()
    text = "".join(r["text"] for r in paragraph.get("runs", []))

    is_caption_style = "caption" in style or "캡션" in style or "그림" in style or "표" in style and len(text) < 200
    seq_match = _SEQ_INSTR.search(text) if text else None

    # 텍스트만 보고도 'Figure 1:' / '그림 1.' 같은 패턴이면 캡션 후보
    looks_like_caption = bool(re.match(r"^\s*(Figure|Table|그림|표)\s*\d+", text))

    if not (is_caption_style or seq_match or looks_like_caption):
        return False, None

    seq_name = None
    if seq_match:
        seq_name = seq_match.group(1)
    else:
        m = re.match(r"^\s*(Figure|Table|그림|표)", text)
        if m:
            seq_name = m.group(1)

    num_match = re.search(r"\d+", text)
    seq_number = int(num_match.group(0)) if num_match else None

    return True, {
        "text": text.strip(),
        "seq_name": seq_name,
        "seq_number": seq_number,
    }


def attach_captions(images: list[dict], tables: list[dict], paragraphs: list[dict]) -> None:
    """그림/표의 직전 또는 직후 단락이 캡션이면 연결. 누락 시 caption=None 유지."""
    paragraph_by_index = {p["index"]: p for p in paragraphs}

    def find_caption(anchor_idx: int) -> dict | None:
        for offset in (1, -1, 2, -2):  # 직후 → 직전 → 한 칸 더
            cand = paragraph_by_index.get(anchor_idx + offset)
            if cand is None:
                continue
            ok, cap = is_caption_paragraph(cand)
            if ok:
                return cap
        return None

    for img in images:
        if img.get("caption") is None:
            img["caption"] = find_caption(img["anchor_paragraph_index"])

    for tbl in tables:
        if tbl.get("caption") is None:
            tbl["caption"] = find_caption(tbl["anchor_paragraph_index"])
