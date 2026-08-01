# Progress

프로젝트 진행 현황 로그. 커밋 직전 갱신한다 (`rules/common/git.md` 규칙).

## 2026-08-01

- **프론트엔드 룰 신설** — UI 요소를 디버깅·테스트·대화에서 안정적으로 특정하기 위해 `data-testid` 식별자 룰(`rules/frontend/identifiers.md`) 추가, CLAUDE.md에 선택적 프론트엔드 블록 신설.
- **guidelines Claude 5 튜닝** — Fable 5 주력 + Opus 5 병용 절충: 준-네이티브 동작(결과 먼저·배칭 등)은 한 줄 리마인더로 유지하되, 자율 진행과 충돌하는 무조건 "ask" 문구는 제거하고 질문 기준을 §1 ask-vs-proceed 표로 일원화.
- **커밋·머지 룰 확장** — 커밋 전: PROGRESS 항목 간소화(1–3줄, 맥락·결정 위주) + README 영향 섹션만 같은 커밋에서 갱신. 머지 시: 브랜치 PROGRESS 항목을 요약 하나로 압축 (브랜치별 파일 분리안은 링크·orphan 유지비용으로 기각).
