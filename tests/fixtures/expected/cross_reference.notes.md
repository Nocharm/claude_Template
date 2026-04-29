# cross_reference.docx — Expected 해설

REF 필드와 북마크 추출 검증. 후속 "참조 재연결" 로직의 핵심 입력.

## 입력 구조

| paragraph | 역할 | 북마크 |
|---|---|---|
| 0 | "참조 검증 문서" (Heading 1) | — |
| 1 | "핵심 절차" (Heading 2) | `_Ref_core_section` (id=1) |
| 2 | (그림 임베드) | — |
| 3 | "그림 1: 핵심 도식" (Caption) | `_Ref_fig_1` (id=2) |
| 4 | "표 1: 데이터 요약" (Caption) | `_Ref_tbl_1` (id=3) |
| 5 | 본문 + REF 필드 3개 | — |

## REF 필드 위치 (paragraph 5 내)

```
"자세한 내용은 " + REF→"핵심 절차" + " 절을 참고하라. " + REF→"그림 1" + " 및 " + REF→"표 1" + " 참조."
```

run_position 기준 위치:
- run 0: 자세한 내용은
- run 1: 핵심 절차 (REF)
- run 2: 절을 참고하라.
- run 3: 그림 1 (REF)
- run 4:  및
- run 5: 표 1 (REF)
- run 6: 참조.

## 후속 로직 (참조 재연결)

```python
bookmark_map = {b["name"]: b["paragraph_index"] for b in bookmarks}
for ref in cross_references:
    target_p_idx = bookmark_map.get(ref["target_bookmark"])
    # ref["paragraph_index"]에서 target_p_idx로 재연결
```

## 함정

1. **`display_text`는 캐시된 텍스트** — 실제 워드가 렌더링한 시점의 결과.
   원본 캡션 텍스트와 다를 수 있음 (예: "그림 1" → "Figure 1"로 캡션 본문이 바뀌어도 캐시 미갱신).
   참조 재연결 시 display_text를 신뢰하지 말고 target_bookmark의 caption을 다시 조회할 것.

2. **REF 필드의 두 형태**
   - Simple: `<w:fldSimple w:instr=" REF X \\h ">`
   - Complex: `<w:fldChar begin/separate/end>` + `<w:instrText>`
   둘 다 본 파서가 처리. 출력은 동일 스키마.

3. **북마크가 있는 paragraph_index가 정답**
   참조 대상이 그림이면 caption paragraph index가 답. 그림 객체로 직접 점프할 수단은 없음
   (워드의 SEQ 카운터가 caption paragraph에 위치하므로).
