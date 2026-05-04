<!--
이 파일은 claude-code-template seed.

[다운스트림 프로젝트 시작 시]
1. `/init` 실행 — Project/Commands 섹션 자동 생성
2. `/setup-from-template` 실행 — 사용 안 하는 import 라인 정리, 디자인 토큰 배치, 메타 문서 정리

[이 템플릿 자체를 편집 중이라면]
- 레포 성격, 구조, 편집 컨벤션은 docs/template/README.md 참고.
-->

## Rules

@rules/comments.md
@rules/config.md
@rules/docker.md
@rules/testing.md
@rules/git.md
@rules/security.md
@rules/dependencies.md
@rules/sync-checklist.md
@rules/error-handling.md
@rules/documentation.md

## Language-Specific Rules

프로젝트에서 사용하는 언어만 남기고 나머지 줄은 삭제한다.

@rules/languages/python.md
@rules/languages/typescript.md

## Frontend Rules (프론트엔드 프로젝트만)

프론트엔드 프로젝트가 아니면 이 섹션을 통째로 삭제한다.
CSS 사용 시 `templates/` 의 디자인 토큰 템플릿을 먼저 채우고 시작한다 (`rules/styling/css.md` 참조).

@rules/languages/nextjs.md
@rules/styling/css.md
