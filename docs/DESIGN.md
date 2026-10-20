# Design — Phrasebook Study

회화책 PDF를 1회 처리해 표현 그래프로 정리하고, iPhone PWA에서 퀴즈·응용·억양별 음성·실제 영상·SVG 웹툰으로 학습하는 개인용 앱.

## 목표와 범위

- 사용자: 본인 1명 (개인 학습용 — 책 저작권상 공개 배포하지 않음).
- 입력: 스캔 PDF (한글 해설 + 영어 예문). 책은 여러 권 추가 가능.
- 비목표: 다중 사용자, 앱스토어 배포, 오프라인 모드.

## 아키텍처

```
iPhone (PWA, React)  ──HTTPS──▶  FastAPI (단일 컨테이너, PWA 정적 파일도 서빙)
                                   ├─▶ Claude API — OCR·구조화·퀴즈·응용·웹툰
                                   ├─▶ Azure TTS — 억양별 음성
                                   └─ SQLite + 파일 캐시 (/data 볼륨)
```

- **실행 위치: 로컬 PC (Docker) + Tailscale.** iPhone PWA 설치에는 HTTPS가 필요 → `tailscale serve`가 인증서 포함 HTTPS 제공.
- **클라우드 전환 비용 낮음:** 상태는 `/data` 볼륨(SQLite + 캐시 파일) 하나, 설정은 `.env` 하나. 같은 이미지를 Fly.io에 올리고 볼륨 복사 + secrets 등록이면 끝.
- API 키는 서버에만 둔다 (클라이언트 번들에 절대 포함하지 않음).

## 책 처리 파이프라인 (책당 1회)

```
PDF 업로드 → sha256 → 이미 처리된 책이면 skip
  → 페이지 이미지 분할
  → [Pass 0] DAY 경계 탐지 (저해상도로 각 페이지의 "DAY n" 표지 확인)
  → [Pass 1] DAY 단위 OCR + 추출 (Claude vision, structured output) → DAY JSON 저장
  → [Pass 2] 책 전체 표현 간 관계 추출 → DB 적재
```

- 결과는 DB에 영구 저장 — 학습 중에는 PDF·OCR을 다시 쓰지 않는다.
- **DAY 단위로 자르는 이유:** 샘플 확인 결과 Reading Points 해설이 페이지를 넘어 이어진다 (p.41 → p.42). 페이지 단위면 문장·표현이 잘린다.
- DAY 단위 저장으로 중간 실패 시 이어서 처리 (재시도 비용 최소화).

### 책 구조 (샘플: 가브리엘의 잉글리시 다이어리, 495쪽)

DAY마다 동일한 패턴 — 추출 스키마가 이 구조를 그대로 따른다.

1. **일기 본문** — DAY 번호 · 제목 · 영어 본문 (손글씨체).
2. **Reading Points** — 본문을 번호 문장으로 나눔. 문장마다 영어 + 핵심 표현 하이라이트 + 한글 해석.
3. **표현 해설** — 하이라이트된 표현별 한글 설명 + e.g. 예문(영/한).
4. **가브리엘 포인트** — 표현에 딸린 박스: "비슷한 표현" 또는 "다양한 쓰임" + 각자 e.g. 예문.
- 긴급하지 않으므로 Batch API(50% 할인) 사용.
- 다른 책도 같은 파이프라인으로 추가 — 데이터 모델이 `Book` 단위로 분리됨.

## 데이터 모델 (ERD 뷰의 원천)

| 엔티티 | 주요 필드 |
|---|---|
| `Book` | id, title, file_hash, status |
| `Day` | id, book_id, day_no, title, passage_en, page_range |
| `Sentence` | id, day_id, no, text_en, text_ko — Reading Points 번호 문장 |
| `Expression` | id, sentence_id?, text, meaning_ko, explanation_ko, origin (`reading_point` · `gabriel_point`) |
| `Example` | id, expression_id, text_en, text_ko, origin (`book` · `ai`) |
| `Relation` | from_id, to_id, type, note |
| `ReviewCard` | expression_id, due_at, interval, ease — 간격 반복 (interval ≥ 21일 = 마스터) |
| `DailyLog` | date, reviews_done, new_done, goal_met, rest_used — 달력·스트릭의 원천 |
| `XpEvent` | id, created_at, kind, points — XP 합계·레벨은 여기서 계산 |
| `Sticker` | code, earned_at — 스티커북 |
| `Comic` | id, expression_ids[], script, svg_panels[] |
| `AudioCache` | text_hash, voice, file_path |

`Relation.type` 출처:

| type | UI 라벨 | 출처 |
|---|---|---|
| `similar` | 유사 | 가브리엘 포인트 "비슷한 표현" + Pass 2의 DAY 간 유사 표현 |
| `sense` | 다른 쓰임 | 가브리엘 포인트 "다양한 쓰임" |
| `contrast` | 대조 | 해설 속 비교 (예: come out vs go out) — Pass 2 |
| `same_sentence` | 같은 문장 | 같은 `Sentence`의 표현끼리 — 자동 |

ERD 뷰 = `Expression` 노드 + `Relation` 엣지 그래프. 표현 탭 → 연결 표현 펼침.

## 학습 기능 (런타임)

| 기능 | 구현 | 캐시 |
|---|---|---|
| 퀴즈 | 빈칸·한→영 작문·상황 선택, 오답은 `ReviewCard`로 재출제 | 문제 생성 결과 |
| 응용 | 표현을 다른 상황으로 변형, 내 문장 첨삭 | — |
| 억양별 읽기 | Azure TTS (en-US/GB/AU/IN 등) | `AudioCache` (같은 문장·음성은 1회 합성) |
| 실제 영상 | YouGlish 억양별 검색 링크 (필요시 위젯 임베드) | — |
| 10컷 웹툰 | Claude가 고정 캐릭터 3–4명으로 콘티 + SVG 패널 생성 | `Comic` |

## 모델·비용

- Claude Opus 5.5 기본 (OCR·구조화·웹툰·첨삭). 단순 채점 등은 측정 후 Haiku 5.5 검토.
- 책 처리: 300쪽 기준 약 $5–15, 1회.
- 런타임: 월 $20–50 예상 (월 $200 크레딧 내). Azure TTS는 무료 티어 범위.

## 단계

1. 책 처리 파이프라인 + 표현 목록·ERD 그래프 뷰 + PWA 셸
2. 퀴즈 · 간격 반복 · 응용
3. 억양별 TTS · 영상 링크
4. SVG 웹툰

## UI

컨셉·화면 레이아웃은 [`docs/UI.md`](UI.md).

## 미결

- 실제 PDF 1개 DAY(약 8쪽)로 Pass 1 추출 정확도 검증.
