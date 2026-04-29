# normal.docx — Expected 해설

정상 SOP 패턴: 다단계 자동 번호 + 캡션 정상 부여 + 단일 portrait 섹션.

## 주요 단언

| index | 의미 | 검증 포인트 |
|---|---|---|
| 0 | 문서 제목 (Heading 1) | `style_name == "Heading 1"`, `numbering == null` |
| 1 | 일반 본문 | `numbering == null` |
| 2 | 자동 번호 ilvl=0 (decimal) | `numbering.is_auto == true`, `numId/ilvl/format` 일치 |
| 3 | 자동 번호 ilvl=1 (decimal) | 다단계 번호의 두 번째 레벨 |
| 4 | 자동 번호 ilvl=2 (lowerLetter) | 세 번째 레벨, 형식 다름 |
| 5 | 자동 번호 ilvl=0 (decimal) | 1단 위계로 복귀 — 후속 로직에서 번호 흐름 추적 가능 |
| 6 | 그림 임베드 단락 | `runs == []` 또는 빈 텍스트, anchor 대상 |
| 7 | 그림 캡션 | `style_name == "Caption"`, 캡션 매칭 대상 |
| 8 | 표 캡션 | `style_name == "Caption"`, anchor 단락은 표 직전(=index 7)이지만 매칭은 직후 paragraph 8 |

## 구조적 약속

- 그림은 단 1개 → `images[0].anchor_paragraph_index == 6`
- 표는 단 1개 → `tables[0].anchor_paragraph_index == 7`
  (표는 paragraph 인덱스를 증가시키지 않으므로 직전 단락 인덱스로 anchor 부여)
- 캡션 매칭은 anchor ±1, ±2 범위 검색 — 첫 매칭에서 종료
- 섹션은 1개. `page_orientation == "portrait"`

## 후속 로직 힌트

- index 5의 ilvl=0이 index 2와 같은 numId라도, 워드는 "동일 시퀀스"로 보고 번호를 이어간다
  (numId가 같으면 카운터가 공유됨). 정규화 시 이 규칙을 보존해야 함.
- 표의 caption anchor = 표 직전 단락이지만 캡션은 표 **직후** paragraph 8에 위치.
  안전하게 매칭하려면 anchor ±N 범위 양방향 탐색이 필요.
