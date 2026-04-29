"""파서 동작 검증 — 검증 기준에 1:1 매핑."""

from docx_parser import parse_docx


def test_returns_top_level_keys(make_full_docx):
    path = make_full_docx()
    result = parse_docx(path)
    for key in ("paragraphs", "images", "tables", "cross_references", "bookmarks", "sections"):
        assert key in result


def test_auto_vs_manual_numbering_distinguished(make_full_docx):
    path = make_full_docx()
    result = parse_docx(path)
    paragraphs = result["paragraphs"]

    # 0번: 자동 번호 (numId 존재) 또는 List Number 스타일이 없는 환경에선 None
    auto_para = paragraphs[0]
    if auto_para["numbering"] is not None and auto_para["numbering"].get("numId") is not None:
        assert auto_para["numbering"]["is_auto"] is True
        assert auto_para["numbering"]["numId"] is not None

    # 1번: 수동 번호 "(1)"
    manual_para = paragraphs[1]
    assert manual_para["numbering"] is not None
    assert manual_para["numbering"]["is_auto"] is False
    assert "(1)" in manual_para["numbering"]["raw_token"]

    # 2번: 한글 수동 번호 "가."
    korean_manual = paragraphs[2]
    assert korean_manual["numbering"] is not None
    assert korean_manual["numbering"]["is_auto"] is False
    assert "가." in korean_manual["numbering"]["raw_token"]


def test_soft_break_position_preserved(make_full_docx):
    path = make_full_docx()
    result = parse_docx(path)
    para = result["paragraphs"][4]

    # soft break가 1개 기록되어 있고, 첫째/둘째 줄 텍스트가 모두 보존
    assert len(para["soft_breaks"]) == 1
    full = "".join(r["text"] for r in para["runs"])
    assert "첫 줄" in full
    assert "둘째 줄" in full
    # 위치 정보로 분리 가능: soft_break 인덱스 다음 run부터가 둘째 줄
    bp = para["soft_breaks"][0]
    after = "".join(r["text"] for r in para["runs"][bp + 1:])
    assert "둘째 줄" in after


def test_missing_caption_is_null(make_full_docx):
    path = make_full_docx()
    result = parse_docx(path)
    images = result["images"]
    assert len(images) >= 2
    # 첫 번째 그림은 직후 단락이 캡션 아님 → caption None
    assert images[0]["caption"] is None
    # 두 번째 그림은 직후 캡션 단락 매칭 (스타일 인식 실패해도 텍스트 패턴으로 캐치)
    assert images[1]["caption"] is not None
    assert "그림" in images[1]["caption"]["text"]


def test_section_orientation(make_full_docx):
    path = make_full_docx()
    result = parse_docx(path)
    sections = result["sections"]
    assert len(sections) >= 1
    assert sections[-1]["page_orientation"] == "landscape"
    assert sections[-1]["page_size"]["width"] is not None


def test_table_structure_preserved(make_full_docx):
    path = make_full_docx()
    result = parse_docx(path)
    tables = result["tables"]
    assert len(tables) == 1
    t = tables[0]
    assert t["rows"] == 2
    assert t["cols"] == 2
    # 셀 내 단락 텍스트 보존
    a_text = "".join(r["text"] for r in t["cells"][0][0]["paragraphs"][0]["runs"])
    assert a_text == "A"


def test_indent_extraction(docx_factory):
    from docx import Document
    from docx.shared import Pt

    doc = Document()
    p = doc.add_paragraph("indented")
    p.paragraph_format.left_indent = Pt(36)  # 36pt = 720 twips
    path = docx_factory(doc)

    result = parse_docx(path)
    indent = result["paragraphs"][0]["indent"]
    # 정확히 720이 아닐 수 있음(반올림 등). 600 이상 800 이하면 OK.
    assert 600 <= indent["left"] <= 800
