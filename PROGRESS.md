# Progress

프로젝트 진행 현황 로그. 커밋 직전 갱신한다 (`rules/common/git.md` 규칙).

## 2026-05-24

- **refactor(rules)**: rules를 tier 폴더(`common`/`backend`/`languages`)로 재편. 범용/도메인 중복 제거(입력검증·dev-deps), sync는 요청 기반으로 변경. 함수 verb 테이블을 `common/naming.md`로 공통화. 행동 가이드를 `guidelines.md` 단일 소스로 두고 CLAUDE.md 최상단 링크. 커밋 규칙(영/한 병기, 커밋 전 PROGRESS 갱신) 추가. 프론트엔드(nextjs·css·styling·templates) 전체 제거.
- **refactor(commands)**: `setup-from-template`를 새 rules 구조(common/backend 경로)에 맞게 갱신, 프론트엔드 감지·디자인 토큰 배치 로직 제거, Step 재번호.
- **feat(commands)**: `/sync`(변경 기반)·`/sync-all`(전체 점검) 슬래시 커맨드 추가. 체크리스트 표는 `backend/sync-checklist.md` 단일 소스를 참조.
- **docs(template)**: 메타 문서(README·USAGE)를 새 폴더 구조·프론트 제거·`guidelines.md`·`/sync`·`/sync-all`에 맞게 동기화.
