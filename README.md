# docx_parser

Word(`.docx`) 문서의 구조 정보를 JSON 으로 추출하는 모듈. SOP 문서를 후속 처리(번호 정규화, 캡션 자동 생성, 참조 재연결) 하기 전 단계의 1차 추출이 목적이다.

추출만 한다. 정규화·자동 생성·승격은 비범위.

## 무엇이 나오나

- 본문 단락 — runs (글꼴/굵게/색/사이즈), 들여쓰기, 정렬, 자동/수동 번호, soft break 위치
- 그림 — 인라인/플로팅 구분, 크기 (EMU/inch), 파일명, 인접 캡션
- 표 — 셀 병합 (gridSpan/vMerge), 셀 내 단락
- 상호 참조 / 북마크 — REF 필드 (simple + complex)
- 섹션 — 시작/끝 단락 인덱스, 페이지 방향·크기·여백, default/first_page/even 머리글·꼬리글

## Quick start

```bash
pip install -r requirements.txt
python -m docx_parser input.docx -o out.json --pretty
```

```python
from docx_parser import parse_docx

doc = parse_docx("input.docx")
doc["paragraphs"]                       # 단락 리스트
doc["sections"][0]["page_orientation"]  # "portrait" | "landscape"
```

## 문서

- 사용법 / CLI / 예제 → [`docs/usage.md`](docs/usage.md)
- 출력 스키마 / 필드-원본 매핑 / 후속 작업 가이드 / FAQ → [`docs/for-developers.md`](docs/for-developers.md)
- 검증 결과 / 적용된 패치 이력 → [`REVIEW.md`](REVIEW.md)

## 테스트

```bash
pytest tests/                  # 14 개
```

6 개의 fixture(`tests/fixtures/inputs/*.docx`) 는 git 에 커밋되어 있으며 P0~P3 회귀를 막는다. 재생성은 `python tests/fixtures/generate_inputs.py`.

## 비범위

- 번호 재매김 / 자동·수동 통합 트리
- soft return → paragraph 승격
- 캡션 자동 생성 (누락 감지만)
- 상호 참조 `display_text` 재계산
- 서식 자동 수정

이 기능들은 본 모듈 위에 별도 layer 로 얹는다.

## Stack

Python 3.11+, `python-docx 1.1.x`, `lxml 5.x`.
