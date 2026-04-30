# Usage — `docx_parser`

Word(`.docx`) 문서의 구조를 손실 없이 JSON 으로 추출한다. 본문 단락 / 표 / 그림 / 캡션 / 상호 참조 / 북마크 / 섹션을 한 번에.

---

## Install

```bash
pip install -r requirements.txt
# (또는) uv pip install -r requirements.txt
```

요구: Python 3.11+, `python-docx 1.1.x`, `lxml 5.x`.

---

## CLI

```bash
python -m docx_parser <input.docx> [-o out.json] [--pretty] [--raw-xml]
```

| 옵션 | 의미 |
|---|---|
| `-o, --output PATH` | JSON 저장 경로. 생략 시 stdout. |
| `--pretty` | 들여쓰기 적용 (기본은 한 줄). |
| `--raw-xml` | 단락별 `raw_xml` 포함. 디버깅용. 출력 크기 큼. |

종료 코드: `0` 성공 / `1` 파싱 실패 / `2` 입력 오류 (파일 없음, 확장자 .docx 아님).

### 예시

```bash
# 기본 — stdout 으로 한 줄 JSON
python -m docx_parser report.docx

# 파일로 저장 + 들여쓰기
python -m docx_parser report.docx -o report.json --pretty

# 디버깅용 raw_xml 포함
python -m docx_parser report.docx --raw-xml -o report.debug.json --pretty

# 파이프
python -m docx_parser report.docx | jq '.paragraphs | length'
```

---

## Library

```python
from docx_parser import parse_docx

doc = parse_docx("report.docx")
# doc 은 JSON 직렬화 가능한 dict

print(len(doc["paragraphs"]))
print(doc["sections"][0]["page_orientation"])
```

`Path` 객체도 받는다:

```python
from pathlib import Path
from docx_parser import parse_docx

doc = parse_docx(Path("report.docx"), include_raw_xml=True)
```

### 자주 쓰는 접근

```python
# 본문 텍스트 추출 (단순 join)
text = "\n".join(
    "".join(r["text"] for r in p["runs"])
    for p in doc["paragraphs"]
)

# Heading 만 추출
headings = [
    p for p in doc["paragraphs"]
    if (p["style_name"] or "").startswith("Heading")
]

# 캡션 누락된 그림 찾기
missing = [img for img in doc["images"] if img["caption"] is None]

# 표 셀 텍스트 1차원으로 풀기
def cell_text(cell):
    return "\n".join(
        "".join(r["text"] for r in p["runs"])
        for p in cell["paragraphs"]
    )

for tbl in doc["tables"]:
    for row in tbl["cells"]:
        for cell in row:
            print(cell_text(cell))
```

### 북마크 ↔ 상호 참조 연결

```python
bm_by_name = {b["name"]: b for b in doc["bookmarks"]}
for ref in doc["cross_references"]:
    target = bm_by_name.get(ref["target_bookmark"])
    if target is None:
        print(f"[broken] {ref['target_bookmark']} (display='{ref['display_text']}')")
        continue
    print(f"{ref['display_text']} → paragraph {target['paragraph_index']}")
```

### 섹션별 본문 묶기

```python
def paragraphs_in_section(doc, section_idx):
    s = doc["sections"][section_idx]
    return doc["paragraphs"][s["start_paragraph_index"] : s["end_paragraph_index"] + 1]
```

---

## 출력 스키마 요약

자세한 스펙은 `docs/for-developers.md` 참고.

```
{
  source_path,
  paragraphs[]:    {index, style_name, outline_level, numbering, indent, alignment,
                    runs[], soft_breaks[], (raw_xml)},
  images[]:        {anchor_paragraph_index, file_name, format,
                    width_emu, height_emu, width_in, height_in, kind, caption},
  tables[]:        {index, anchor_paragraph_index, rows, cols,
                    merged_cells[], cells[][], caption},
  cross_references[]: {target_bookmark, display_text, paragraph_index, run_position},
  bookmarks[]:     {id, name, paragraph_index},
  sections[]:      {start_paragraph_index, end_paragraph_index,
                    page_orientation, page_size, margins, header, footer}
}
```

단위:

- 들여쓰기 / 페이지 크기 / 여백: **twips** (1/20 pt, 1/1440 inch)
- 그림 크기: **EMU** (914400 = 1 inch). 편의용 `width_in/height_in` 도 함께 제공.
- 폰트 크기 (`run.size`): **pt** (이미 변환됨).

---

## 비범위

이 모듈은 **추출만** 한다. 다음은 의도적으로 하지 않는다:

- 번호 재매김 / 정규화 (자동·수동 통합 트리)
- soft return 의 paragraph 승격
- 캡션 자동 생성 (누락 감지만 함)
- 상호 참조 `display_text` 재계산
- 서식 자동 수정 (폰트 통일, 정렬 등)

이런 변환은 본 모듈 위에 별도 layer 로 얹어서 처리한다.

---

## 트러블슈팅

| 증상 | 원인 / 해결 |
|---|---|
| `파일이 없습니다` (코드 2) | 경로 오타. 절대경로 또는 cwd 기준 상대경로 확인. |
| `확장자가 .docx가 아닙니다` (코드 2) | `.doc` (구 형식) 미지원. 워드에서 .docx 로 저장. |
| `파싱 실패: PackageNotFoundError` | 손상된 파일 또는 .docx 가 아닌 zip. |
| `image.caption` 이 모두 null | 워드에서 캡션 스타일 없이 본문 텍스트로만 적은 경우. `for-developers.md` §5 참고. |
| `numbering.format` 이 null | `numbering.xml` 의 numId 룩업 실패. `numId/ilvl` 자체는 살아 있음. |
| `display_text` 가 비어 있음 | complex field 인데 워드에서 한 번도 필드 업데이트 안 한 문서. |

---

## 테스트

```bash
pytest tests/                          # 전체
pytest tests/test_fixtures.py -v       # 6개 fixture 회귀
```

픽스처 재생성:

```bash
python tests/fixtures/generate_inputs.py
```
