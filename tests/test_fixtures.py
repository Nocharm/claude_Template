"""tests/fixtures/inputs 의 6개 .docx에 대한 통합 검증.

각 fixture가 expected JSON의 핵심 단언을 만족하는지 확인.
스펙 기반 검증이며, 모든 필드를 1:1 비교하지 않는다 (runs 디테일 등은 자유).
"""

from pathlib import Path

from docx_parser import parse_docx

FIXTURES = Path(__file__).parent / "fixtures" / "inputs"


def _parse(name: str) -> dict:
    return parse_docx(FIXTURES / f"{name}.docx")


def test_normal_structure():
    d = _parse("normal")
    assert len(d["images"]) == 1
    assert len(d["tables"]) == 1
    assert len(d["sections"]) == 1
    assert d["sections"][0]["page_orientation"] == "portrait"

    img = d["images"][0]
    assert img["caption"] is not None
    assert img["caption"]["seq_name"] == "그림"
    assert img["caption"]["seq_number"] == 1

    tbl = d["tables"][0]
    assert tbl["rows"] == 2 and tbl["cols"] == 2
    assert tbl["caption"] is not None
    assert tbl["caption"]["seq_name"] == "표"


def test_normal_auto_numbering_levels():
    d = _parse("normal")
    levels = [p["numbering"] for p in d["paragraphs"] if p["numbering"] and p["numbering"]["is_auto"]]
    assert len(levels) >= 4
    # 다단계 ilvl 0, 1, 2, 0 순서
    assert [n["ilvl"] for n in levels[:4]] == [0, 1, 2, 0]
    # 자동 번호도 raw_token 키 보유 (P1 일관성)
    assert all("raw_token" in n for n in levels)


def test_mixed_numbering():
    d = _parse("mixed_numbering")
    # paragraph[1], [2]는 자동
    assert d["paragraphs"][1]["numbering"]["is_auto"] is True
    assert d["paragraphs"][2]["numbering"]["is_auto"] is True
    # paragraph[3]~[8]은 수동
    for i in range(3, 9):
        n = d["paragraphs"][i]["numbering"]
        assert n is not None
        assert n["is_auto"] is False
        assert n["raw_token"]


def test_soft_break_clean_runs():
    d = _parse("soft_break")
    multi = d["paragraphs"][4]
    # 4 segments → 4 runs (빈 placeholder 없음)
    assert len(multi["runs"]) == 4
    assert multi["soft_breaks"] == [0, 1, 2]
    # break 위치로 분리한 결과가 4개 segment 각각 일치
    expected_segs = [
        "Step 1: Initialize the system",
        "Step 2: Validate inputs",
        "Step 3: Execute operation",
        "Step 4: Cleanup resources",
    ]
    for i, seg in enumerate(expected_segs):
        assert multi["runs"][i]["text"] == seg


def test_missing_caption_no_cross_assignment():
    """P0 회귀 방지: 캡션 1개가 여러 그림에 중복 할당되지 않는지."""
    d = _parse("missing_caption")
    captions = [img["caption"] for img in d["images"]]
    # 정확히 1개 그림만 캡션 보유
    assert sum(1 for c in captions if c is not None) == 1
    # 표는 캡션 없음
    assert d["tables"][0]["caption"] is None


def test_multi_section():
    d = _parse("multi_section")
    sections = d["sections"]
    assert len(sections) == 3
    orients = [s["page_orientation"] for s in sections]
    assert orients == ["portrait", "landscape", "portrait"]
    # 첫 페이지 헤더는 섹션 0에만
    assert sections[0]["header"]["first_page"] is not None
    assert sections[1]["header"]["first_page"] is None
    assert sections[2]["header"]["first_page"] is None
    # 섹션별 default 헤더 텍스트가 모두 다름
    headers = [
        "".join(r["text"] for p in s["header"]["default"] for r in p["runs"])
        for s in sections
    ]
    assert len(set(headers)) == 3


def test_cross_reference():
    d = _parse("cross_reference")
    assert len(d["bookmarks"]) == 3
    assert len(d["cross_references"]) == 3
    # ref_id 필드 제거 확인 (P3)
    for ref in d["cross_references"]:
        assert "ref_id" not in ref
    # target_bookmark가 bookmarks의 name과 매칭됨
    bm_names = {b["name"] for b in d["bookmarks"]}
    for ref in d["cross_references"]:
        assert ref["target_bookmark"] in bm_names
