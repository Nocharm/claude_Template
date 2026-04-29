# multi_section.docx — Expected 해설

다중 섹션 + 섹션별 머리글/꼬리글 + 첫 페이지 머리글 분리 검증.

## 섹션 구조

```
[Section 0: portrait]
  - 일반 헤더, 첫 페이지 헤더 별도 지정
  - 푸터 1종
  - paragraphs: Heading 1 + 본문
[Section 1: landscape]
  - 일반 헤더만 (첫 페이지 헤더 없음)
  - 푸터 1종
[Section 2: portrait]
  - 일반 헤더만
  - 푸터 1종
```

## 핵심 단언

1. **섹션 수가 3개**
2. **각 섹션 page_orientation이 정확** — portrait/landscape/portrait
3. **section 0만 first_page 헤더 보유**
4. **각 섹션 header.default 텍스트가 다름** — `is_linked_to_previous = False` 효과

## 후속 로직 주의

- python-docx의 `add_section()`은 새 섹션을 위한 **빈 paragraph**를 본문에 삽입한다.
  → 섹션 경계의 paragraph_index에는 비어 있는 단락이 포함될 수 있음. 후속 로직이 이 빈 단락을 자동 제거하면 정확한 섹션 경계 인덱스가 어긋날 수 있음.
- 섹션의 `start_paragraph_index`/`end_paragraph_index` 는 본문 paragraph 카운터 기준.
  표는 paragraph 카운터를 증가시키지 않으므로, 표만 있는 섹션의 경계는 anchor와 동일.
- header/footer의 `paragraph` 구조는 본문과 동일한 스키마 — runs, soft_breaks, numbering 모두 보존.
