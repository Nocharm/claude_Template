# Developer Guide — `docx_parser`

후속 작업자(번호 정규화, 캡션 자동 생성, 참조 재연결 등)가 이 문서만 읽고도 작업을 시작할 수 있도록 작성한 가이드.

본 모듈은 **구조 추출만** 한다. 정규화/승격/자동 생성은 의도적으로 비범위.

---

## 1. 빠른 사용

```python
from docx_parser import parse_docx

doc = parse_docx("input.docx")
# doc: dict (JSON 직렬화 가능)
```

CLI:

```bash
python -m docx_parser input.docx -o out.json --pretty
python -m docx_parser input.docx --raw-xml -o out.json   # 디버깅용 raw_xml 포함
```

---

## 2. 출력 JSON 스키마

루트 객체:

```jsonc
{
  "source_path": "string",          // 입력 경로 (그대로)
  "paragraphs": [Paragraph, ...],   // 본문 단락 (표 외부)
  "images": [Image, ...],
  "tables": [Table, ...],
  "cross_references": [Ref, ...],
  "bookmarks": [Bookmark, ...],
  "sections": [Section, ...]
}
```

### 2.1 Paragraph

```jsonc
{
  "index": 0,                        // 본문 단락 0-based 순서. 표 내부 단락은 별도 카운터.
  "style_name": "Heading 1" | null,  // python-docx style.name. 미지정이면 null.
  "outline_level": 0 | null,         // w:outlineLvl. 워드가 거의 안 씀 → 대부분 null.
  "numbering": Numbering | null,     // 자동/수동 번호 정보 (§3 참고)
  "indent": {                        // 모두 twips (1/20 pt). 값 없으면 0.
    "left": 720,
    "first_line": 0,
    "hanging": 0
  },
  "alignment": "left|center|right|both|null",  // w:jc val 그대로
  "runs": [Run, ...],
  "soft_breaks": [int, ...],         // §4 참고
  "raw_xml": "<w:p ...>..."         // include_raw_xml=True 일 때만
}
```

#### Run

```jsonc
{
  "text": "내용",
  "font": "맑은 고딕" | null,         // ascii / hAnsi / eastAsia 중 첫 매칭
  "size": 11.0 | null,                // pt 단위 (w:sz는 half-point)
  "bold": true,
  "italic": false,
  "color": "FF0000" | null,           // RGB hex, "auto"는 null
  "lang": "ko-KR" | null
}
```

### 2.2 Numbering

```jsonc
// 자동 (w:numPr)
{
  "numId": 99,
  "ilvl": 0,
  "format": "decimal" | "bullet" | "korean" | null,
  "is_auto": true,
  "raw_token": null
}

// 수동 (본문 타이핑)
{
  "numId": null,
  "ilvl": null,
  "format": null,
  "is_auto": false,
  "raw_token": "(1) "    // 매칭된 원본 토큰
}
```

자동/수동 모두 같은 키 5개를 갖는다 — `numbering.get("raw_token")` 같은 균일 접근이 보장된다.

### 2.3 Image

```jsonc
{
  "anchor_paragraph_index": 3,    // 그림이 속한 단락 인덱스
  "file_name": "image1.png",
  "format": "png",
  "width_emu": 1828800,           // EMU (914400 = 1 inch)
  "height_emu": 1371600,
  "width_in": 2.0,                // 편의 변환 (round 4)
  "height_in": 1.5,
  "kind": "inline" | "floating",
  "caption": Caption | null
}
```

### 2.4 Table

```jsonc
{
  "index": 0,
  "anchor_paragraph_index": 5 | null,  // 표 직전 단락 인덱스. 표가 첫 요소면 null.
  "rows": 3,
  "cols": 4,
  "merged_cells": [
    { "row": 0, "col": 0, "grid_span": 2, "v_merge": null },
    { "row": 1, "col": 0, "grid_span": 1, "v_merge": "restart" }
  ],
  "cells": [                          // 행 → 셀 → paragraphs 3중 배열
    [
      {
        "row": 0,
        "col": 0,
        "grid_span": 2,
        "v_merge": null,
        "paragraphs": [Paragraph, ...]
      },
      ...
    ],
    ...
  ],
  "caption": Caption | null
}
```

### 2.5 Caption

```jsonc
{
  "text": "그림 1: 시스템 구성도",   // strip된 전체 텍스트
  "seq_name": "그림" | "Figure" | "표" | "Table",
  "seq_number": 1 | null            // 텍스트 내 첫 정수
}
```

### 2.6 CrossReference

```jsonc
{
  "target_bookmark": "_Ref12345",
  "display_text": "1.2",            // 워드가 표시 시점에 채워둔 텍스트
  "paragraph_index": 7,
  "run_position": 2 | null          // 단락 내 fldSimple/field-begin run 인덱스
}
```

### 2.7 Bookmark

```jsonc
{
  "id": "1",                        // w:bookmarkStart/@w:id (string)
  "name": "_Ref12345",
  "paragraph_index": 3
}
```

### 2.8 Section

```jsonc
{
  "start_paragraph_index": 0,
  "end_paragraph_index": 4,
  "page_orientation": "portrait" | "landscape",
  "page_size":   { "width": 11906, "height": 16838 },   // twips
  "margins":     { "top": 1440, "right": 1440, "bottom": 1440,
                   "left": 1440, "header": 720, "footer": 720, "gutter": 0 },
  "header": { "default": [Paragraph, ...] | null,
              "first_page": [Paragraph, ...] | null,
              "even":       [Paragraph, ...] | null },
  "footer": { ... 동일 구조 ... }
}
```

---

## 3. 필드 → 원본 docx 요소 매핑

| 출력 필드 | 원본 위치 | 비고 |
|---|---|---|
| `paragraph.style_name` | `w:p/w:pPr/w:pStyle/@w:val` → python-docx `Styles` 룩업 | style_id → 표시명 변환 |
| `paragraph.outline_level` | `w:p/w:pPr/w:outlineLvl/@w:val` | 거의 미사용 |
| `paragraph.numbering` (auto) | `w:p/w:pPr/w:numPr` + `numbering.xml` | numId → abstractNumId → lvl[ilvl] → numFmt |
| `paragraph.numbering` (manual) | 단락 첫 텍스트의 정규식 매칭 | 본문에 직접 타이핑된 번호 |
| `paragraph.indent` | `w:p/w:pPr/w:ind/@w:left,firstLine,hanging` | twips (1/20 pt) |
| `paragraph.alignment` | `w:p/w:pPr/w:jc/@w:val` | val 그대로 |
| `run.text` | `w:t` 텍스트 + `w:tab` (`\t`로 변환) | |
| `run.font` | `w:rPr/w:rFonts/@ascii\|hAnsi\|eastAsia` | 첫 매칭 |
| `run.size` | `w:rPr/w:sz/@w:val` ÷ 2 | half-point → pt |
| `run.bold/italic` | `w:rPr/w:b`, `w:i` 존재 + val ≠ "0/false" | 토글 속성 |
| `run.color` | `w:rPr/w:color/@w:val` | "auto"는 null |
| `run.lang` | `w:rPr/w:lang/@w:val\|eastAsia` | |
| `paragraph.soft_breaks` | `w:br` (type 미지정 또는 textWrapping) 위치 | §4 |
| `image.*` | `w:drawing/wp:inline\|wp:anchor` + `a:blip/@r:embed` → rels | |
| `image.caption` | 인접 단락 텍스트/스타일 휴리스틱 | §5 |
| `table.cells` | `w:tbl/w:tr/w:tc` 순회, `w:gridSpan`/`w:vMerge` 보존 | |
| `cross_reference` | `w:fldSimple` + `w:fldChar` 상태머신 (`REF` instr) | |
| `bookmark` | `w:bookmarkStart/@id,name` | end는 무시 (range 보존 안 함) |
| `section.*` | `w:p/w:pPr/w:sectPr` (중간 섹션) + body 직속 `w:sectPr` (마지막) | |
| `section.header/footer` | `w:headerReference`/`w:footerReference/@r:id` → related part | type: default/first/even |

---

## 4. soft_breaks 의 의미와 사용법

```
soft_breaks[i] = j  →  "runs[j] 와 runs[j+1] 사이에 break 위치"
j == -1            →  "단락 시작에 break"
```

빈 placeholder run은 만들지 **않는다**. break 직전까지 누적된 텍스트가 비어 있고 직전 run 이 push된 적 없으면 `j = -1`.

### soft break 를 paragraph 로 승격하기

```python
def split_runs_by_breaks(runs, soft_breaks):
    """break 위치 기준으로 runs를 segment 리스트로 분할."""
    if not soft_breaks:
        return [runs]
    segments = []
    cursor = 0
    for j in soft_breaks:
        # j 까지 (포함) 가 한 segment
        end = j + 1
        segments.append(runs[cursor:end])
        cursor = end
    segments.append(runs[cursor:])
    return segments
```

승격 시 결정해야 할 정책:

| 항목 | 옵션 | 권장 |
|---|---|---|
| `numbering` 상속 | A) 첫 자식만 유지 / B) 모두 공유 / C) 모두 None | A) — 워드 자동 번호는 단락당 카운트되므로 B는 부작용 |
| `style_name` | 모두 동일하게 복제 | 그대로 복제 |
| `indent` / `alignment` | 모두 복제 | 그대로 복제 |
| `outline_level` | 첫 자식만 유지 | A와 동일 이유 |

---

## 5. 캡션 매칭 정책 (현 구현)

- 검색 거리: anchor ±1 단락 (직후 → 직전 순)
- 한 번 매칭된 단락 인덱스는 다른 그림/표가 재사용 불가 (`consumed` set)
- 캡션 판별 휴리스틱:
  - `style_name` 에 `caption / 캡션 / 그림 / 표` 포함 (200자 이하)
  - 본문에 `SEQ` 필드 흔적
  - `^Figure|Table|그림|표\s*\d+` 패턴

### 후속에서 자동 생성하려면

```python
# 누락된 그림에 임시 캡션 부여
for i, img in enumerate(doc["images"]):
    if img["caption"] is None:
        img["caption"] = {
            "text": f"그림 {i+1} (자동)",
            "seq_name": "그림",
            "seq_number": i + 1,
        }
```

⚠ `seq_number` 의 전역 재매김은 본 모듈 책임이 아니다. 자동 캡션 생성과 번호 재매김 정책은 후속 로직에서 일관되게 결정.

---

## 6. 후속 로직이 자주 만나는 패턴

### 6.1 자동/수동 번호 혼재

`mixed_numbering.docx` 같은 케이스: paragraphs[1..2] 자동, [3..8] 수동.

```python
def normalize(n: dict | None) -> str | None:
    if n is None: return None
    if n["is_auto"]:
        return f"auto:{n['numId']}.{n['ilvl']}"
    return f"manual:{n['raw_token'].strip()}"
```

자동/수동을 같은 트리로 합치려면 `ilvl` 추정이 필요. 수동은 `raw_token` 패턴(`(1)` vs `1.` vs `가.`) 으로 레벨을 추론.

### 6.2 캡션 위/아래

워드 관행상 표는 **위**, 그림은 **아래** 가 일반적이지만 강제는 아니다. 본 모듈은 위/아래를 구분하지 않고 인접만 본다 — 후속에서 위치를 알아야 하면 `image.anchor_paragraph_index` 와 매칭된 caption 단락의 인덱스 차이로 판별.

캡션 단락 인덱스를 알고 싶으면 `attach_captions` 직후의 `consumed` 정보가 필요한데 외부에서 얻을 수 없다. 필요하면 별도 헬퍼를 구현해 `caption_paragraph_index` 필드를 사후 추가하라.

### 6.3 표 내부 단락의 인덱스 체계

표 내부 단락은 본문 `paragraphs` 리스트에 들어가지 **않는다**. 표 셀의 `paragraphs` 안에 별도 카운터(`cell_para_index`)로 0부터 매겨진다. 본문 인덱스와 표 인덱스를 섞어 쓰지 말 것.

### 6.4 섹션 경계의 단락 카운트

`paragraph_counter` 는 **본문 단락만** 센다. 표는 카운트하지 않으므로 `start/end_paragraph_index` 가 본문 인덱스와 1:1 일치.

마지막 섹션의 `end_paragraph_index` 는 **마지막 본문 단락 인덱스**. 본문에 단락이 0개면 -1 이 될 수 있다 (드문 경우).

### 6.5 cross_reference 매칭

```python
bookmarks_by_name = {b["name"]: b for b in doc["bookmarks"]}
for ref in doc["cross_references"]:
    target = bookmarks_by_name.get(ref["target_bookmark"])
    if target is None:
        # 외부 참조 또는 깨진 참조
        continue
    # target["paragraph_index"] 가 참조 대상 단락
```

`display_text` 는 워드가 마지막 업데이트 시 계산해 박아둔 값. 본문 변경 후 재계산이 필요하면 후속 로직에서 직접 채워 넣어야 한다.

---

## 7. 건드리면 안 되는 것 (구조 보존 원칙)

| 필드 | 이유 |
|---|---|
| `paragraph.index` | 다른 모든 인덱스 참조의 기준. 재매김 시 cross_reference / image / table / section 까지 함께 갱신 필수 |
| `image.anchor_paragraph_index` | 캡션 매칭과 본문 위치 추적의 키 |
| `table.anchor_paragraph_index` | 동일 |
| `bookmark.name` | cross_reference 의 키. 변경 시 모든 ref 의 `target_bookmark` 도 일괄 변경 |
| `section.start/end_paragraph_index` | 섹션 경계 — 페이지 방향/크기/머리글 적용 범위 |
| `numbering.numId / ilvl` | numbering.xml 트리의 키. 단순 재매김 금지 (numbering.xml 도 함께 변경해야 의미 있음) |
| `runs` 의 순서와 개수 | `soft_breaks` 의 인덱스가 깨진다. run 분리/병합 시 `soft_breaks` 동기 갱신 |

---

## 8. FAQ / 함정

**Q. `paragraph.numbering.format` 이 None 인 경우가 있다.**
A. `numbering.xml` 이 없거나 `numId` 가 잘못되어 룩업 실패. 자동 번호 자체는 살아 있으므로 (`numId`/`ilvl` 존재) 처리 정책은 따로.

**Q. `outline_level` 이 거의 항상 None.**
A. 워드는 헤딩 스타일(`Heading 1` 등)에는 `outlineLvl` 을 안 박는다. 대신 `style_name` 으로 판별하라.

**Q. soft_breaks 인덱스가 -1 이다.**
A. 단락 시작에 `<w:br/>` 가 있다는 뜻. 첫 자식으로 빈 paragraph 를 만들어야 할지는 후속 정책.

**Q. `image.kind` 가 floating 인데 anchor_paragraph_index 가 정확한가?**
A. 워드는 floating 도 어떤 단락의 child 로 직렬화한다. 시각적 위치는 다를 수 있지만 anchor 는 그 host 단락 인덱스다.

**Q. 표 내부의 그림이 두 번 매칭된다?**
A. 표 내부 그림도 `images` 에 추가되며 anchor 는 표의 `anchor_paragraph_index` 와 같다. 셀 단락 안에 또 들어가 있지는 않다 — 본문 그림 리스트에서만 한 번 등장.

**Q. 표가 문서 첫 요소면 anchor 가 None.**
A. 의도된 동작. -1 은 위험하므로 None 으로 두고, 후속에서 명시적으로 처리하라.

**Q. cross_reference 의 `display_text` 가 비어 있다.**
A. complex field 인데 `<w:fldChar w:fldCharType="separate"/>` 이전에 값이 캐싱되어 있지 않은 경우. 워드가 한 번도 필드 업데이트를 안 한 문서.

**Q. `caption.seq_number` 가 None 이다.**
A. 캡션 텍스트에 정수가 없음 (예: "그림" 만 적힌 케이스). 해석은 후속 정책.

**Q. soft break 가 page break / column break 도 잡나?**
A. 안 잡는다. `w:br/@w:type` 가 `page` 나 `column` 이면 무시. textWrapping(또는 미지정)만 soft return.

**Q. raw_xml 이 필요한 경우?**
A. 본 모듈이 보존하지 않는 속성(예: 글자 간격, 강조점, 한자 음운 정보 등)을 후속에서 다뤄야 할 때. CLI 는 `--raw-xml` 옵션으로 켠다.

---

## 9. 비범위 (이 모듈이 의도적으로 안 하는 일)

- **번호 재매김 / 정규화** — 자동/수동 통합 트리 생성, ilvl 추론
- **soft return → paragraph 승격** — 위치 정보만 보존, 분리는 후속
- **캡션 자동 생성** — 누락 감지만, 생성은 후속
- **상호 참조 재계산** — `display_text` 재계산은 후속
- **양식(서식) 자동 수정** — 폰트 통일, 들여쓰기 정렬 등

각 기능을 추가할 때는 본 모듈을 수정하지 말고 위에 별도 layer 를 얹는다 — 추출과 변환의 책임 분리를 유지한다.

---

## 10. 단위 정리

| 단위 | 변환 | 사용 필드 |
|---|---|---|
| twips | 1 twip = 1/20 pt = 1/1440 inch | `indent.*`, `page_size.*`, `margins.*` |
| EMU | 1 inch = 914400 EMU | `image.width_emu`, `image.height_emu` |
| half-point | size_pt = val ÷ 2 | `run.size` 계산 직전 (출력은 pt) |

---

## 11. 동작 검증

```bash
pytest tests/                                    # 전체
pytest tests/test_fixtures.py -v                 # 6개 fixture 회귀 테스트
python -m docx_parser tests/fixtures/inputs/normal.docx --pretty
```

테스트 픽스처는 `tests/fixtures/generate_inputs.py` 에서 생성. 기대값은 `tests/fixtures/expected/*.expected.json` 와 같은 경로의 `*.notes.md` 에 해설.
