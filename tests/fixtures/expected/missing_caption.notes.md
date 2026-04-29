# missing_caption.docx — Expected 해설

캡션이 없는 그림/표가 명시적으로 `caption: null`로 표기되는지 검증.

## 입력 구조

| paragraph | 내용 | 의미 |
|---|---|---|
| 0 | "캡션 누락 검증" (Heading 1) | 제목 |
| 1 | (그림 #1 임베드) | 캡션 없음 |
| 2 | "이것은 그림에 대한 설명이 아니라 다음 본문이다." | 본문 (캡션 아님) |
| 3 | (그림 #2 임베드) | 캡션 있음 (대조) |
| 4 | "그림 1: 정상 캡션" (Caption) | 그림 #2의 캡션 |
| 5 | (그림 #3 임베드) | 캡션 없음 |
| 6 | (그림 #4 임베드) | 캡션 없음 |
| 7 | "두 그림 사이에 캡션이 없는 케이스." | 본문 |
| 8 | "표 직후 일반 본문 (캡션 아님)." | 본문 |
| (표) | 1×2 표 | 캡션 없음 (표 anchor=7) |

## 핵심 단언

> **캡션이 없는 그림은 반드시 `caption: null`이어야 한다.**

- images[0] (anchor=1): null — 직후가 본문
- images[1] (anchor=3): 매칭 성공 — 직후 paragraph 4가 캡션
- images[2] (anchor=5): null — 직후 paragraph 6은 또 다른 그림 단락
- images[3] (anchor=6): null — 직후 paragraph 7은 본문
- tables[0] (anchor=7): null — 직후 paragraph 8은 본문

## 함정 (구현이 빠질 수 있는 함정)

⚠️ **캡션 1개가 여러 그림에 잘못 매칭될 위험.**
파서 구현에 따라 anchor ±N 범위 검색 시:
- images[2] (anchor=5)의 -1 = paragraph 4 = "그림 1: 정상 캡션" ← 잘못 매칭 가능
- images[3] (anchor=6)의 -2 = paragraph 4 ← 마찬가지

→ **캡션 매칭은 (a) 가까운 anchor만 후보로 하고, (b) 이미 다른 그림/표에 소비된 캡션은 제외**해야 정확.
