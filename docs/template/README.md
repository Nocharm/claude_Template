# Claude Code Template

Claude Code 프로젝트용 공통 규칙 + 셋업 자동화 템플릿.

새 프로젝트는 **3 단계**로 시작한다 — 복사 → `/init` → `/setup-from-template`.
자세한 절차·예시·FAQ 는 [`USAGE.md`](./USAGE.md) 참고.

## 구성

| 파일/폴더 | 역할 |
|-----------|------|
| `CLAUDE.md` | 허브 seed. `## Rules` / `## Language-Specific` / `## Frontend` `@import` 만 담는다 |
| `.claude/commands/setup-from-template.md` | 셋업 자동화 슬래시 커맨드 |
| `rules/` | 일반 규칙 (주석·설정·Docker·테스트·Git·보안·의존성·동기화·에러·문서) |
| `rules/languages/` | 언어/프레임워크 규칙 (Python, TypeScript, Next.js) |
| `rules/styling/` | 스타일링 규칙 (CSS, Tailwind) — 프론트엔드 프로젝트만 |
| `templates/` | 프로젝트 시작 시 채우는 템플릿 (디자인 토큰 등) + 디자인 컨셉 레퍼런스 |
| `docs/template/` | **이 템플릿** 의 메타 문서 (`README.md`, `USAGE.md`). 다운스트림에서는 보통 삭제 |
| `.gitignore` | Claude 로컬 파일·env·OS·언어별 산출물 제외 |

## Quick Start

```bash
# 1) 복사
cp -r /path/to/claude-code-template ~/new-project
cd ~/new-project
rm -rf .git && git init

# 2) /init  (Claude Code 안에서)
#    프로젝트 메타 섹션 (Project, Commands 등) 자동 생성

# 3) /setup-from-template  (Claude Code 안에서)
#    사용 안 하는 import 가지치기, 디자인 토큰 배치, 메타 문서 정리, 검증
```

## 허브 구조를 쓰는 이유

- `CLAUDE.md` 는 항상 짧다 → 프로젝트 overview 가 한눈에 들어온다
- 규칙을 바꿔도 허브는 건드리지 않는다 (`rules/*.md` 만 수정)
- 규칙을 끄려면 `@import` 한 줄만 지운다
- 언어별 규칙은 `rules/languages/` 로 분리해 일반 규칙과 시각적으로 구분
- `/init` + `/setup-from-template` 으로 수동 단계 제거 — placeholder 상태가 방치되지 않는다 (`rules/documentation.md` 가 강제)
