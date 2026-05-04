# Documentation Rules

프로젝트의 `README.md` 와 (필요 시) `USAGE.md` 는 **현재 프로젝트** 를 설명한다. 템플릿 placeholder 나 메타 가이드를 그대로 두지 않는다.

**Do:**
- 루트 `README.md` 는 다음을 담는다 — 무엇을 하는 프로젝트인지 한 줄 요약, 누가 쓰는지, 시작하는 법(setup), 핵심 명령어, 주요 디렉터리 구조.
- `USAGE.md` 가 필요한 프로젝트 (CLI, 라이브러리, 별도 사용자 가이드가 있는 앱 등) 라면 **그 프로젝트** 의 사용법을 작성한다.
- 템플릿에서 시작한 프로젝트라면 첫 작업 중 하나로 루트 `README.md` 의 placeholder 를 실제 내용으로 교체한다.
- 코드/구조가 바뀌면 README 의 해당 섹션도 함께 갱신한다 (`rules/sync-checklist.md` 와 일관).

**Don't:**
- `_TODO_`, `<project name>` 같은 placeholder 가 남은 채로 `feat:` / `fix:` 커밋 누적.
- 템플릿의 메타 README/USAGE (이 템플릿이 무엇이고 어떻게 복사하는지) 를 **다운스트림 프로젝트** 에 그대로 둠.
- README 가 한 줄짜리 placeholder 인 채로 첫 의미있는 커밋 진행 — 그 커밋 전에 한 번이라도 채운다.
