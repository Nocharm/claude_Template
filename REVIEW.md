# Parser Implementation Review

**검토 대상**: `docx_parser/` (initial: `c81d00d`)
**검증 기반**: `tests/fixtures/inputs/*.docx` 6건 vs `tests/fixtures/expected/*.expected.json`
**검토일**: 2026-04-29
**상태**: 모든 권고 사항 적용 완료 (commit `8332624`)

> 본문의 §1~§9 는 패치 **이전** 상태에서 작성된 분석이다. 각 항목 상단에 적용 여부 마커(✅ 적용됨 / ❌ 미적용)를 붙였다. 적용 결과 요약은 하단 [적용된 패치](#적용된-패치-사용자-승인-후) 표 참조.

---

## 검증 결과 요약

| 검증 항목 | 결과 |
|---|---|
| 자동 vs 수동 번호 구분 | ✅ 동작 |
| soft break 위치 보존 | ✅ 동작 (구현 quirk 있음, P2) |
| 캡션 누락 → null | ❌ **P0 버그** — 잘못된 매칭 발생 |
| 섹션별 페이지 방향 | ✅ 동작 |
| 머리글/꼬리글 섹션별 분리 | ✅ 동작 |
| 비범위 항목 (번호 정규화/soft 승격/캡션 자동 생성) 누락 | ✅ 코드에 섞이지 않음 |

---

## P0 — Critical (수정 권장)

### 1. 캡션이 엉뚱한 그림으로 잘못 매칭됨 ✅ 적용됨

**증상** (`missing_caption.docx`):
- paragraph 4 "그림 1: 정상 캡션"은 paragraph 3의 그림 #2의 캡션
- 그러나 paragraph 5, 6에 있는 그림 #3, #4(둘 다 캡션 없음)도 paragraph 4를 자기 캡션으로 가져감

```
실제 출력:
  images[0] (anchor=1): caption=null     ✓
  images[1] (anchor=3): caption="그림 1"  ✓
  images[2] (anchor=5): caption="그림 1"  ✗ 잘못 — null이어야 함
  images[3] (anchor=6): caption="그림 1"  ✗ 잘못 — null이어야 함
```

**원인**: `images.attach_captions()`가 anchor ±1, ±2 범위 검색만 함. 각 캡션이 여러 그림에 중복 할당될 수 있음.

```python
# docx_parser/images.py:
for offset in (1, -1, 2, -2):  # ← 다른 그림이 끼어 있어도 계속 탐색
    cand = paragraph_by_index.get(anchor_idx + offset)
    if ok: return cap
```

**영향**: 검증 기준 "캡션 누락된 그림이 caption: null로 명시되는가" 위반.

**수정 방안 (택1, 결정 필요)**:
- (A) **소비 추적**: 한 번 매칭된 캡션 paragraph_index를 set에 기록 → 재사용 금지.
- (B) **거리를 ±1로 축소**: 표/그림 캡션은 워드 관행상 인접 단락에만 위치. 보수적이나 안전.
- (C) **anchor 사이에 다른 image/table이 끼어 있으면 탐색 중단**: 가장 정확하나 구현 복잡.

→ **추천: (A) + (B) 조합** — 거리 ±1로 축소하면서 소비 추적도 함께. 구현 약 10줄.

---

## P1 — High (스키마/계약 일관성)

### 2. 자동/수동 numbering 스키마 비대칭 ✅ 적용됨

**현 출력**:
```json
// 자동
{"numId": 99, "ilvl": 0, "format": "decimal", "is_auto": true}
// 수동
{"numId": null, "ilvl": null, "format": null, "is_auto": false, "raw_token": "(1)"}
```

수동에는 `raw_token`이 있지만 자동에는 없음 → 후속 로직이 `numbering.get("raw_token")`로 일관 접근 불가.

**수정 방안**: 자동에도 `"raw_token": null` 명시 추가.

→ **결정 필요**: 동의 시 한 줄 변경 (`docx_parser/numbering.py:45-50`).

### 3. 캡션 매칭 거리(±2)가 비스펙·비문서화 ✅ 적용됨

스펙은 "그림 위/아래에 캡션이 올 수 있다"만 명시. ±2까지 확장한 것은 임의 설계.
P0 수정 시 거리 정책을 함께 결정·문서화 필요.

→ 거리 ±1 + 소비 추적 정책으로 변경, `docs/for-developers.md §5` 에 문서화.

---

## P2 — Medium (손실 없음, 가독성/사용성)

### 4. soft break 위치에 빈 run이 끼어듦 ✅ 적용됨

```
입력: "첫째"<w:br/>"둘째"
출력 runs: [
  {"text": "첫째"},
  {"text": ""},        ← 빈 run, soft_breaks[0] = 1
  {"text": "둘째"}
]
```

후속 로직이 `runs[soft_breaks[i]]`을 그대로 쓰면 빈 텍스트가 나옴.
**의미적으로는 맞음** ("soft break 직전 위치 마커"), 하지만 직관적이지 않음.

**옵션**:
- (A) 빈 run을 push하지 않음. soft_breaks 인덱스를 "이 인덱스 직후에 break 있음"으로 정의 (이미 그렇게 의도됨).
- (B) 현 동작 유지하고 docs에 명시.

→ **추천: (A)**. `paragraphs._extract_runs_and_breaks()`에서 break 직전 텍스트 누적이 비어 있고 직전 run이 이미 push되었다면 빈 run을 만들지 않음.

### 5. 표 anchor가 음수가 될 수 있음 ✅ 적용됨

표가 문서 첫 요소면 `anchor_paragraph_index = -1`. 후속 로직 안전장치 필요.

→ 명시적으로 `null`로 두는 것이 더 안전. 결정 필요.

---

## P3 — Low (품질)

### 6. 예외 처리 broad-stroke ✅ 적용됨 (CLI 단)

- `_get_numbering_root()` 가 `except (AttributeError, KeyError)` 만 잡음.
- 손상된 docx, 빈 섹션, 중첩 표 등에 대한 명시적 가드 없음.
- 현 코드는 lxml/python-docx가 던지는 다양한 예외를 윗 단까지 전파 — 라이브러리 사용자에게 친숙한 메시지로 변환 안 됨.

→ 보수적 수정 권장. CLI 단에서만 사용자 친화 메시지로 변환.

### 7. 타입 힌트 일부 누락 ❌ 미적용

- `p_elem`, `tbl_elem` 등 lxml element 인자에 타입 미지정. `etree._Element` 명시 가능.
- `numbering_part` 등은 None 가능성이 있는데 `Optional` 명시 안 됨.

### 8. 단위 명시 부족 ✅ 적용됨 (docs)

- `indent.left/first_line/hanging`: twips (1/20 pt). 코드 주석은 있지만 출력 JSON에는 단위 정보 없음.
- `page_size.width/height`: twips. 마찬가지.
- `image.width_emu/height_emu`: EMU. 별도 `width_in/height_in` 도 함께 나와 친화적이지만 page_size에는 inch 변환 없음.

→ 단위는 docs(`for-developers.md`)에서 통일 설명.

### 9. REF 필드의 `ref_id` 항상 null ✅ 적용됨 (필드 제거)

스펙에 `ref_id`가 적혀 있으나, 워드 REF 필드는 자체 ID를 갖지 않음 (북마크 이름이 식별자 역할).
→ `ref_id` 필드를 제거하거나 의미 재정의 필요.

---

## 비범위 항목 누락 검증

| 비범위 항목 | 상태 |
|---|---|
| 번호 재매김 / 정규화 | ✅ 코드 없음 |
| soft return의 paragraph 승격 | ✅ 코드 없음 (위치만 보존) |
| 캡션 자동 생성 | ✅ 코드 없음 (감지만 함) |
| 양식 자동 수정 | ✅ 코드 없음 |

---

## 출력 스키마 vs 원 스펙

| 스펙 항목 | 구현 | 비고 |
|---|---|---|
| paragraph.index | ✅ | |
| paragraph.style_name | ✅ | python-docx Styles로 lookup |
| paragraph.outline_level | ✅ | 대부분 None (워드가 잘 안 씀) |
| paragraph.numbering | ✅ | P1 — auto/manual 스키마 통일됨 (`raw_token` 공통) |
| paragraph.indent | ✅ | twips |
| paragraph.alignment | ✅ | jc val |
| paragraph.runs | ✅ | |
| paragraph.soft_breaks | ✅ | P2 — 빈 run 제거됨 |
| paragraph.raw_xml | ✅ | `--raw-xml` 옵션 |
| image.{anchor, file_name, format, width, height, kind} | ✅ | |
| image.caption | ✅ | P0 — 거리 ±1 + 소비 추적으로 수정됨 |
| table.{rows, cols, merged_cells, cells, caption} | ✅ | |
| cross_reference.{target_bookmark, display_text, paragraph_index, run_position} | ✅ | P3 — ref_id 필드 제거됨 |
| bookmarks (스펙 외 추가) | ✅ | |
| section.{start/end_paragraph_index, page_orientation, page_size, margins, header, footer} | ✅ | |

---

## 권장 수정 우선순위

1. **P0**: 캡션 중복 매칭 수정 (사용자 결정 후 패치)
2. **P1**: `raw_token: null` 자동 numbering에 추가
3. **P2**: soft break 빈 run 제거
4. **P3**: 항목별 결정 후 일괄 정리

---

## 적용된 패치 (사용자 승인 후)

| 항목 | 결정 | 적용 |
|---|---|---|
| P0 캡션 매칭 정책 | (A)+(B) 채택 — 소비 추적 + 거리 ±1 | `docx_parser/images.py:attach_captions()` |
| P1 자동 numbering raw_token | null 추가 | `docx_parser/numbering.py:get_auto_numbering()` |
| P2 soft break 빈 run | 제거 | `docx_parser/paragraphs.py:_extract_runs_and_breaks()` |
| P2 표 anchor 음수 | null 채택 | `docx_parser/parser.py` |
| P3 ref_id 필드 | 제거 | `docx_parser/refs.py` |
| P3 CLI 예외 처리 | try/except + 친화 메시지 | `docx_parser/__main__.py` |
| P3 단위 명시 | docs(`for-developers.md`)에서 설명 | (Task 2에서 처리) |

## 검증

`tests/test_fixtures.py` 추가 — 6개 fixture 기반 P0~P3 회귀 방지 단언 포함.
전체 테스트: 14 passed.
