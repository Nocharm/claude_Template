# Template Setup Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the template so that "copy folder → `/init` → `/setup-from-template`" becomes the new 3-step setup flow, with metadata docs isolated under `docs/template/` and a new documentation rule that forces real project README/USAGE content.

**Architecture:** No code/build/test pipeline — this is a markdown-only rules-and-templates repo. "Tests" are **shell verifications** (file exists, `@import` paths resolve, grep for expected content). Each task ends with a focused commit. Slash command content is markdown (Claude Code reads it as an instruction prompt).

**Tech Stack:** Markdown, bash (verification), git. No language runtime needed.

**Spec:** `docs/superpowers/specs/2026-05-04-template-setup-flow-design.md`

---

## Pre-flight

Before starting, confirm working directory and clean status:

- [ ] **Step 0a: Confirm cwd**

```bash
pwd
```

Expected: `/Users/hyeonjin/Documents/claude-code-template`

- [ ] **Step 0b: Confirm clean tree (or only have the deleted plan file)**

```bash
git status --short
```

Expected: empty, OR only ` D docs/superpowers/plans/2026-05-04-template-setup-flow.md` (the file we just overwrote in this task) and nothing else.

If clean, the deletion has been replaced by this plan file's recreation — proceed. If anything else is dirty, stop and ask.

---

## Task 1: Add `rules/documentation.md`

**Files:**
- Create: `rules/documentation.md`

This rule is referenced by the new `CLAUDE.md` seed in Task 2, so create it first.

- [ ] **Step 1: Verify the file does not exist**

```bash
test ! -e rules/documentation.md && echo OK
```

Expected output: `OK`

- [ ] **Step 2: Write the rule**

Create `rules/documentation.md` with this exact content:

```markdown
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
```

- [ ] **Step 3: Verify the file**

```bash
test -e rules/documentation.md && wc -l rules/documentation.md
```

Expected: file exists, ~14 lines.

- [ ] **Step 4: Commit**

```bash
git add rules/documentation.md
git commit -m "feat(rules): add documentation rule for real README/USAGE content"
```

---

## Task 2: Refactor root `CLAUDE.md` to seed form

**Files:**
- Modify: `CLAUDE.md`

Drops `## Project` and `## Commands` placeholder sections (these will be filled by `/init` in downstream usage), adds a top HTML comment explaining the seed's intended use, and adds `@rules/documentation.md` to the `## Rules` block.

- [ ] **Step 1: Read current `CLAUDE.md`**

```bash
cat CLAUDE.md
```

Note the existing structure: hub comment, `## Project`, `## Commands`, `## Rules`, `## Language-Specific Rules`, `## Frontend Rules (프론트엔드 프로젝트만)`.

- [ ] **Step 2: Replace contents**

Overwrite `CLAUDE.md` with this exact content:

```markdown
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
```

- [ ] **Step 3: Verify all `@import` paths resolve**

```bash
grep -E '^@' CLAUDE.md | sed 's/^@//' | while read p; do
  test -e "$p" && echo "OK $p" || echo "MISSING $p"
done
```

Expected: every line prefixed `OK`, including `OK rules/documentation.md`. No `MISSING`.

- [ ] **Step 4: Verify removed sections are gone**

```bash
grep -E '^## (Project|Commands)$' CLAUDE.md && echo "FAIL: section still present" || echo "OK: sections removed"
```

Expected: `OK: sections removed`.

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md
git commit -m "refactor(claude): convert CLAUDE.md to minimal seed form

Drops Project/Commands placeholder sections (now filled by /init in
downstream projects). Adds @rules/documentation.md to Rules block."
```

---

## Task 3: Move `USAGE.md` → `docs/template/USAGE.md` and rewrite for 3-step flow

**Files:**
- Move + replace: `USAGE.md` → `docs/template/USAGE.md`

Note: `docs/template/` already exists (the spec file lives under `docs/superpowers/specs/`, but `docs/template/` itself may not exist yet — the next step handles that).

- [ ] **Step 1: Ensure `docs/template/` exists**

```bash
mkdir -p docs/template && test -d docs/template && echo OK
```

Expected: `OK`.

- [ ] **Step 2: Move the file (preserves git rename detection)**

```bash
git mv USAGE.md docs/template/USAGE.md
```

- [ ] **Step 3: Verify the move**

```bash
test ! -e USAGE.md && test -e docs/template/USAGE.md && echo OK
```

Expected: `OK`.

- [ ] **Step 4: Replace contents with the new 3-step flow**

Overwrite `docs/template/USAGE.md` with this exact content:

````markdown
# Claude Code 템플릿 사용 가이드

이 가이드는 `claude-code-template` 을 새 프로젝트의 출발점으로 사용하는 방법을 설명한다. 핵심 흐름은 **3 단계**다 — 복사 → `/init` → `/setup-from-template`.

---

## 파일 구성

```
CLAUDE.md                       # 허브 seed (## Rules / Language-Specific / Frontend 만)
README.md                       # 프로젝트 placeholder (한 줄)
.claude/
  commands/
    setup-from-template.md      # 셋업 자동화 슬래시 커맨드
docs/
  template/
    README.md                   # 이 템플릿의 README (다운스트림에서는 보통 삭제)
    USAGE.md                    # 이 가이드 (다운스트림에서는 보통 삭제)
rules/
  comments.md
  config.md
  docker.md
  testing.md
  git.md
  security.md
  dependencies.md
  sync-checklist.md
  error-handling.md
  documentation.md              # README/USAGE 작성 규칙
  languages/
    python.md
    typescript.md
    nextjs.md
  styling/
    css.md
templates/
  design-tokens.css             # vanilla CSS / CSS Modules 디자인 토큰
  tailwind.theme.ts             # Tailwind 디자인 토큰 (같은 스키마)
  design_concept/               # 디자인 컨셉 레퍼런스 (5개)
```

**관계:**
- `CLAUDE.md` 는 허브 seed. `## Rules` 블록의 `@rules/<file>.md` import 만 담는다.
- `/init` 이 Project / Commands 같은 프로젝트 메타 섹션을 자동 생성.
- `/setup-from-template` 이 사용 안 하는 언어 import, 디자인 토큰 배치, 메타 문서 정리를 자동화.
- `templates/` 는 `@import` 대상이 아니다 — 슬래시 커맨드 또는 사용자가 실제 파일로 복사하는 **파일 템플릿**.

---

## Step 1. 폴더 복사

새 프로젝트 위치로 통째로 복사한다.

```bash
# 옵션 A — 파일 복사
cp -r /path/to/claude-code-template ~/new-project
cd ~/new-project
rm -rf .git && git init                  # 템플릿 이력 제거 후 새 git 시작

# 옵션 B — 템플릿 레포 clone 후 git 초기화
git clone <template-repo-url> ~/new-project
cd ~/new-project
rm -rf .git && git init
```

> **중요:** 허브 파일은 반드시 `CLAUDE.md` 라는 이름이어야 한다. Claude Code 는 프로젝트 루트의 `CLAUDE.md` 를 자동으로 읽는다.

---

## Step 2. `/init` 실행

Claude Code 안에서:

```
/init
```

`/init` 은 폴더 내용을 분석해 다음을 생성/보강한다:
- "What this repository is" / "Project" 같은 프로젝트 설명
- "Commands" — build / test / lint / dev 명령어 (실제 의존성 파일에서 추론)
- "Architecture" / 주요 디렉터리 설명

기존의 `## Rules` / `## Language-Specific Rules` / `## Frontend Rules` 블록은 그대로 보존된다 (또는 다음 Step 의 슬래시 커맨드가 복원).

---

## Step 3. `/setup-from-template` 실행

Claude Code 안에서:

```
/setup-from-template
```

다음을 자동 수행한다:
1. 스택 감지 (`package.json`, `pyproject.toml`, `next.config.*`, `tailwind.config.*` 등)
2. `## Language-Specific Rules` / `## Frontend Rules` 의 사용 안 하는 `@import` 라인 제거
3. 디자인 토큰 템플릿을 적절한 경로로 복사 (Tailwind / vanilla CSS / 둘 다 / 안 씀 중 선택)
4. `templates/design_concept/` 유지/삭제 확인
5. 메타 문서 (`docs/template/`) 삭제 확인 — 이 프로젝트는 더 이상 템플릿이 아니므로 보통 삭제
6. 루트 `README.md` 가 placeholder 상태면 안내 (사용자 또는 `/init` 결과로 교체할 것)
7. 모든 `@import` 경로가 실제 파일을 가리키는지 검증 후 결과 요약

비가역 작업 (파일 삭제·이동) 전에는 매번 사용자 확인을 받는다.

---

## Step 4 (선택). 프로젝트 특화 규칙 추가

범용 규칙 외에 프로젝트에만 해당하는 규칙이 있다면:

**방법 A — `CLAUDE.md` 에 직접 추가:**

`## Rules` 위쪽에 프로젝트 전용 섹션을 둔다.

```markdown
## Project Structure

```
src/
├── api/          # API 라우터. 비즈니스 로직 금지.
├── services/     # 비즈니스 로직.
├── models/       # DB 모델.
└── utils/        # 공용 유틸.
```

## Gotchas
- Redis 연결은 connection pool 필수
- 파일 업로드 50MB 제한 (nginx + 앱 양쪽 설정)
```

**방법 B — `rules/` 에 새 파일 생성:**

규칙이 길거나 여러 개라면 `rules/<topic>.md` 를 만들고 `CLAUDE.md` 의 `## Rules` 목록에 `@rules/<topic>.md` 를 추가.

프로젝트별로 계속 커지는 규칙은 B 가 낫다 — 허브가 얇게 유지된다.

---

## 전체 체크리스트

- [ ] 1. 폴더 복사 + `rm -rf .git && git init`
- [ ] 2. `/init` 실행
- [ ] 3. `/setup-from-template` 실행
- [ ] 4. (선택) 프로젝트 특화 규칙 추가
- [ ] 5. 첫 의미있는 커밋 전에 루트 `README.md` 를 실제 내용으로 교체

---

## FAQ

**Q: `/init` 만 쓰고 이 템플릿 안 쓰면 안 되나?**
A: 가능하다. 다만 `rules/` 의 일반 규칙들과 `templates/` 의 디자인 토큰을 못 쓴다. 이 템플릿의 가치는 `## Rules` 블록과 `templates/` 자산.

**Q: `/setup-from-template` 을 다시 실행해도 되나?**
A: 안전. 휴리스틱으로 이미 셋업된 폴더인지 감지해 사용자에게 진행 여부를 묻는다.

**Q: 규칙이 너무 많으면 Claude 가 무시하나?**
A: Anthropic 권장은 파일당 200줄 이하, 전체 규칙 150개 이하. 넘으면 준수율이 균일하게 하락한다. 허브 구조 덕분에 분리되어 있지만 총량 관리는 필요.

**Q: 팀원이 다른 AI 도구(Cursor, Copilot)를 쓰면?**
A: `CLAUDE.md` 는 Claude Code 전용이다. Cursor 는 `.cursorrules`, Copilot 은 `.github/copilot-instructions.md` 를 쓴다. 내용은 동일하게, 파일명·형식만 맞추면 된다.

**Q: `CLAUDE.md` 와 `.claude/settings.json` 의 차이는?**
A: `CLAUDE.md` = "이렇게 해줘" (권장 사항). `settings.json` = "이것만 허용" (권한 강제). 예: "pytest 허용" → `settings.json`, "테스트는 mock 으로" → `CLAUDE.md`.

**Q: `rules/` 가 아니라 `.claude/` 에 넣으면?**
A: `.claude/` 는 하네스 설정(`settings.json`, `commands/`, `agents/`, `hooks/`) 자리. `@import` 로 읽히는 지침 문서는 `rules/` 가 의미상 맞는다. 단, `.claude/commands/` 는 슬래시 커맨드 자리로 적극 활용한다 (이 템플릿의 `setup-from-template` 처럼).
````

- [ ] **Step 5: Verify content**

```bash
grep -c "^## Step" docs/template/USAGE.md
```

Expected: `4` (Step 1, Step 2, Step 3, Step 4).

- [ ] **Step 6: Commit**

```bash
git add docs/template/USAGE.md USAGE.md
git commit -m "docs(template): move USAGE under docs/template and rewrite for 3-step flow

Replaces the manual 6-step Quick Start with cp -> /init -> /setup-from-template.
Adds /init and /setup-from-template explanations and updates FAQ."
```

---

## Task 4: Move `README.md` → `docs/template/README.md` and rewrite

**Files:**
- Move + replace: `README.md` → `docs/template/README.md`

- [ ] **Step 1: Move the file**

```bash
git mv README.md docs/template/README.md
```

- [ ] **Step 2: Verify the move**

```bash
test ! -e README.md && test -e docs/template/README.md && echo OK
```

Expected: `OK`.

- [ ] **Step 3: Replace contents**

Overwrite `docs/template/README.md` with this exact content:

````markdown
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
| `rules/styling/` | 스타일링 규칙 (CSS, Tailwind) |
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
#    프로젝트 메타 섹션 (Project, Commands, Architecture 등) 자동 생성

# 3) /setup-from-template  (Claude Code 안에서)
#    사용 안 하는 import 가지치기, 디자인 토큰 배치, 메타 문서 정리, 검증
```

## 허브 구조를 쓰는 이유

- `CLAUDE.md` 는 항상 짧다 → 프로젝트 overview 가 한눈에 들어온다
- 규칙을 바꿔도 허브는 건드리지 않는다 (`rules/*.md` 만 수정)
- 규칙을 끄려면 `@import` 한 줄만 지운다
- 언어별 규칙은 `rules/languages/` 로 분리해 일반 규칙과 시각적으로 구분
- `/init` + `/setup-from-template` 으로 수동 단계 제거 — placeholder 가 안 남는다
````

- [ ] **Step 4: Verify content**

```bash
grep -E "(setup-from-template|/init|docs/template/)" docs/template/README.md | head
```

Expected: at least 5 matches.

- [ ] **Step 5: Commit**

```bash
git add docs/template/README.md README.md
git commit -m "docs(template): move README under docs/template and update for 3-step flow"
```

---

## Task 5: Create root `README.md` placeholder

**Files:**
- Create: `README.md`

After Task 4 the root has no README. This task adds the placeholder that downstream `/init` (or the user) replaces.

- [ ] **Step 1: Verify the file is missing**

```bash
test ! -e README.md && echo OK
```

Expected: `OK`.

- [ ] **Step 2: Write the placeholder**

Create `README.md` with this exact content (3 lines including final newline):

```markdown
# <project name>

_TODO: 프로젝트 설명 — `/init` 결과나 직접 작성으로 교체하세요._
```

- [ ] **Step 3: Verify**

```bash
wc -l README.md && cat README.md
```

Expected: 3 lines, content as above.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "chore: add root README placeholder for downstream projects"
```

---

## Task 6: Create `/setup-from-template` slash command

**Files:**
- Create: `.claude/commands/setup-from-template.md`

This file IS the command — Claude Code reads its body as an instruction prompt when the user types `/setup-from-template`. The frontmatter declares command metadata.

- [ ] **Step 1: Ensure `.claude/commands/` exists**

```bash
mkdir -p .claude/commands && test -d .claude/commands && echo OK
```

Expected: `OK`.

- [ ] **Step 2: Verify the file does not exist**

```bash
test ! -e .claude/commands/setup-from-template.md && echo OK
```

Expected: `OK`.

- [ ] **Step 3: Write the command**

Create `.claude/commands/setup-from-template.md` with this exact content:

````markdown
---
description: Finish setting up a project that was started by copying claude-code-template — prune unused @import lines, place design tokens, clean metadata.
---

당신은 `/setup-from-template` 슬래시 커맨드를 수행 중입니다. 사용자는 `claude-code-template` 을 복사해 새 프로젝트를 시작했고, 이미 `/init` 으로 Project/Commands 섹션을 만든 상태입니다. 이 커맨드의 목표는 **수동 후처리 단계 (사용 안 하는 import 가지치기, 디자인 토큰 배치, 메타 문서 정리, 검증)** 를 자동화하는 것입니다.

## 원칙

- **비가역 작업 (파일 삭제·이동) 전에는 매번 사용자 확인을 받습니다.** "다음을 진행해도 될까요? Y/N" 형태로 명시적으로 묻고, Y 가 아니면 그 단계 건너뜁니다.
- 각 단계 끝에 한 줄로 결과를 요약합니다.
- 마지막에 전체 변경 요약을 출력합니다.

## Step 0: 재실행 체크

다음 휴리스틱으로 이미 셋업된 프로젝트인지 감지합니다:
- `docs/template/` 가 없다 + `README.md` 에 `<project name>` placeholder 가 없다 → 이미 셋업된 것으로 간주.

이미 셋업된 것 같으면 사용자에게 "이미 셋업이 끝난 것 같습니다. 그래도 다시 실행할까요? Y/N" 묻고, N 이면 종료.

## Step 1: 스택 감지

다음 파일들의 존재 여부를 확인합니다:

| 시그널 | 의미 |
|---|---|
| `package.json` | JS/TS 프로젝트 |
| `pyproject.toml` 또는 `requirements.txt` | Python |
| `next.config.{js,mjs,ts}` | Next.js |
| `tailwind.config.{js,ts}` | Tailwind |
| `app/`, `pages/`, `src/components/` | 프론트엔드 가능성 |

감지 결과를 사용자에게 보여줍니다:
```
감지된 스택:
- 언어: <Python | TypeScript | 둘 다 | 없음>
- Next.js: <yes/no>
- Tailwind: <yes/no>
- 프론트엔드: <yes/no/모호>
```

모호하면 사용자에게 "Python? TypeScript? 둘 다? 둘 다 아님?" 와 "프론트엔드인가요? Y/N" 으로 명시적 확인을 받습니다.

## Step 2: `## Rules` 블록 보강

`CLAUDE.md` 를 읽습니다.

- `## Rules` 블록이 없으면 → seed 의 표준 블록을 추가합니다 (`@rules/comments.md` 부터 `@rules/documentation.md` 까지).
- `## Language-Specific Rules` 블록의 import 라인 중, 감지된 언어가 아닌 것은 제거 후보로 사용자에게 확인:
  - Python 미감지 → `@rules/languages/python.md` 제거
  - JS/TS 미감지 → `@rules/languages/typescript.md` 제거
- `## Frontend Rules (프론트엔드 프로젝트만)` 블록:
  - 프론트엔드 아님 → 섹션 통째로 제거
  - 프론트엔드 + Next.js 미감지 → `@rules/languages/nextjs.md` 만 제거 (`css.md` 는 유지)
  - CSS/Tailwind 둘 다 안 씀 → `@rules/styling/css.md` 도 제거

각 제거 전에 "다음 라인을 제거할까요? Y/N" 묻습니다 (한 묶음으로 한 번만 물어도 됨).

## Step 3: 디자인 토큰 배치

프론트엔드 프로젝트면 사용자에게 묻습니다:
"디자인 토큰을 어떤 형태로 둘까요? (1) Tailwind  (2) vanilla CSS  (3) 둘 다  (4) 안 씀"

- (1) Tailwind → `templates/tailwind.theme.ts` 를 루트로 `cp` (`tailwind.theme.ts`).
- (2) vanilla CSS → `mkdir -p styles && cp templates/design-tokens.css styles/design-tokens.css`.
- (3) 둘 다 → 위 두 작업 모두.
- (4) 안 씀 → 건너뜀.

복사 후 사용자에게 `templates/` 의 사용 안 하는 토큰 파일 (`tailwind.theme.ts`, `design-tokens.css`) 을 제거할지 묻고, Y 면 제거.

## Step 4: 디자인 컨셉 레퍼런스 처리

`templates/design_concept/` 가 존재하면 묻습니다:
"`templates/design_concept/` (5개 디자인 컨셉 레퍼런스) 를 유지할까요? 새 프로젝트에서는 보통 삭제합니다. (Y=유지 / N=삭제)"

N 이면 `rm -rf templates/design_concept/`.

## Step 5: 메타 문서 정리

`docs/template/` 가 존재하면 묻습니다:
"`docs/template/` (이 템플릿의 메타 README/USAGE) 는 다운스트림 프로젝트에서 보통 삭제합니다. 삭제할까요? (Y/N)"

Y 면 `rm -rf docs/template/`.
N 이면 그대로 둠.

## Step 6: 루트 README 안내

루트 `README.md` 를 grep 합니다. `<project name>` 또는 `_TODO_` 가 보이면 사용자에게 한 번 알립니다:
"루트 `README.md` 가 placeholder 상태입니다. `/init` 결과나 직접 작성으로 교체해주세요. `rules/documentation.md` 가 이를 강제합니다 — placeholder 상태에서 첫 의미있는 커밋을 진행하지 마세요."

## Step 7: 검증

`CLAUDE.md` 의 모든 `@` 라인을 grep 으로 추출 후, 각 경로가 실제 파일인지 확인:

```bash
grep -E '^@' CLAUDE.md | sed 's/^@//' | while read p; do
  test -e "$p" && echo "OK $p" || echo "MISSING $p"
done
```

`MISSING` 이 하나라도 있으면 사용자에게 경고 후, 잘못된 라인을 제거할지 묻습니다.

## 마무리

전체 변경 사항을 한 표로 요약합니다:

```
[변경 요약]
- 제거된 import: <목록>
- 배치된 토큰: <경로>
- 삭제된 폴더: <목록>
- 검증 결과: 모두 OK / N개 경고
```

마지막으로 사용자에게:
"셋업이 끝났습니다. 다음 권장 작업: ① `README.md` 를 프로젝트 설명으로 교체 ② `git add -A && git commit -m 'chore: project bootstrap from template'`"

이 두 작업은 사용자가 직접 수행하도록 두고, 자동 커밋하지 않습니다.
````

- [ ] **Step 4: Verify the file**

```bash
test -e .claude/commands/setup-from-template.md && head -5 .claude/commands/setup-from-template.md
```

Expected: file exists, first lines show frontmatter (`---`, `description: ...`, `---`).

- [ ] **Step 5: Commit**

```bash
git add .claude/commands/setup-from-template.md
git commit -m "feat(commands): add /setup-from-template slash command

Automates the post-/init steps (prune @import, place design tokens,
clean templates/design_concept and docs/template, verify @import paths)
in a single command with explicit confirmation before destructive ops."
```

---

## Task 7: Final manual verification

These verifications mirror spec §6. Run each in this repo (the template repo itself), then in fresh scratch directories where indicated.

- [ ] **Step 1: Verify all `@import` paths in this repo's `CLAUDE.md` resolve**

```bash
grep -E '^@' CLAUDE.md | sed 's/^@//' | while read p; do
  test -e "$p" && echo "OK $p" || echo "MISSING $p"
done
```

Expected: all `OK`. No `MISSING`.

- [ ] **Step 2: Verify the file inventory**

```bash
test -e CLAUDE.md && \
test -e README.md && \
test -e docs/template/README.md && \
test -e docs/template/USAGE.md && \
test -e rules/documentation.md && \
test -e .claude/commands/setup-from-template.md && \
echo "ALL FILES PRESENT"
```

Expected: `ALL FILES PRESENT`.

- [ ] **Step 3: Verify removed sections in seed**

```bash
grep -E '^## (Project|Commands)$' CLAUDE.md && echo "FAIL" || echo "OK"
```

Expected: `OK`.

- [ ] **Step 4: Verify root README is a placeholder**

```bash
grep -q "<project name>" README.md && grep -q "_TODO" README.md && echo OK || echo "FAIL"
```

Expected: `OK`.

- [ ] **Step 5: Dry-run scenario coverage (read-only)**

For each scenario in spec §6, mentally walk through what `/setup-from-template` would do given the inputs. Check `.claude/commands/setup-from-template.md` against:

- **Empty folder**: Step 1 (스택 감지) outputs "언어: 없음, 프론트엔드: 모호" → Step 1 falls through to explicit confirmation prompts. Verify the command instructs Claude to ask "Python? TypeScript? 둘 다? 둘 다 아님?" and "프론트엔드인가요? Y/N".
- **Next.js scenario** (`package.json` + `next.config.ts` + `tailwind.config.ts`): command should detect TS+Next.js+Tailwind, propose removing `@rules/languages/python.md`, propose copying `tailwind.theme.ts`. Verify the conditional logic is in Step 2 and Step 3.
- **Python scenario** (only `pyproject.toml`): command should detect Python, propose removing `@rules/languages/typescript.md` AND the entire `## Frontend Rules` section. Verify Step 2's frontend-handling clause covers this.
- **Broken `@import` line**: Step 7 (검증) grep loop must catch it. Re-read Step 7 — the grep + ls combo is present.
- **Re-run safety**: Step 0 must short-circuit. Re-read Step 0 — the heuristic + Y/N prompt is present.

Confirm all five scenarios are covered. If any scenario is not covered, return to Task 6 and update the command.

- [ ] **Step 6: Final commit (if no further changes)**

```bash
git status
```

Expected: clean tree (all prior tasks already committed).

If clean, no commit needed for this task.

---

## Self-review notes

- Spec §3.1 file reorg: covered by Tasks 3, 4, 5 (moves) and Tasks 1, 6 (new files).
- Spec §3.2 new flow: documented in Task 3 (USAGE rewrite) and Task 4 (README rewrite).
- Spec §3.3 slash command 7-step procedure: covered by Task 6's command body — every step (0-7) is present.
- Spec §3.4 documentation rule: covered by Task 1.
- Spec §3.5 CLAUDE.md seed: covered by Task 2.
- Spec §3.6 root README placeholder: covered by Task 5.
- Spec §3.7 USAGE update: covered by Task 3.
- Spec §3.8 README update: covered by Task 4.
- Spec §6 verification scenarios: covered by Task 7 (dry-run).
