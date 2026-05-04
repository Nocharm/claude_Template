# Template Setup Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize `claude-code-template` so the copy-and-start flow becomes `copy → /init → /setup-from-template`, with single-source inventory and audience-split meta docs.

**Architecture:** Documentation/template repo, no executable pipeline. Three streams of work: (1) move existing meta docs into `docs/template/`, (2) reduce hub `CLAUDE.md` to a minimal seed and turn root `README.md` into a placeholder, (3) add `/setup-from-template` slash command and rewrite the meta docs per the writing rules in §4.5 of the spec.

**Tech Stack:** Markdown + bash verification (file existence, grep). No automated test suite — verification = structural checks via shell.

**Spec:** [`docs/superpowers/specs/2026-05-04-template-setup-flow-design.md`](../specs/2026-05-04-template-setup-flow-design.md)

---

## File Structure

| Path | Status | Responsibility |
|---|---|---|
| `CLAUDE.md` | Modify | Minimal seed: `@import` blocks only |
| `README.md` | Modify | Placeholder for downstream project name |
| `.claude/commands/setup-from-template.md` | Create | Slash command instructions for setup automation |
| `docs/template/README.md` | Move + rewrite | Template overview + quick start (개발자/인수인계 관점) |
| `docs/template/USAGE.md` | Move + rewrite | Operating manual (사용자 관점), only inventory in repo |
| `rules/` | Untouched | Existing rule files |
| `templates/` | Untouched | Design token templates and concept references |
| `.claude/settings.local.json` | Untouched | Local Claude Code settings |

---

### Task 1: Move existing meta docs into docs/template/

**Files:**
- Move: `README.md` → `docs/template/README.md`
- Move: `USAGE.md` → `docs/template/USAGE.md`
- Create: `docs/template/` directory

- [ ] **Step 1.1: Create the docs/template directory**

```bash
mkdir -p docs/template
```

- [ ] **Step 1.2: Move with git mv to preserve history**

```bash
git mv README.md docs/template/README.md
git mv USAGE.md docs/template/USAGE.md
```

- [ ] **Step 1.3: Verify the moves**

```bash
test ! -f README.md && echo "root README.md gone: OK" || echo "FAIL"
test ! -f USAGE.md && echo "root USAGE.md gone: OK" || echo "FAIL"
test -f docs/template/README.md && echo "moved README: OK" || echo "FAIL"
test -f docs/template/USAGE.md && echo "moved USAGE: OK" || echo "FAIL"
```

Expected: four `OK` lines.

- [ ] **Step 1.4: Commit**

```bash
git add -A
git commit -m "refactor: move meta docs into docs/template/"
```

---

### Task 2: Replace root README.md with a placeholder

**Files:**
- Create: `README.md`

- [ ] **Step 2.1: Write the placeholder file with this exact content**

```markdown
# <project name>

_TODO: 프로젝트 설명_
```

- [ ] **Step 2.2: Verify**

```bash
test -f README.md && wc -l README.md
grep -c "TODO: 프로젝트 설명" README.md
```

Expected: 3 lines, grep count = 1.

- [ ] **Step 2.3: Commit**

```bash
git add README.md
git commit -m "feat: add root README placeholder for downstream project name"
```

---

### Task 3: Reduce CLAUDE.md to a minimal seed

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 3.1: Replace `CLAUDE.md` content (full file overwrite)**

```markdown
<!-- 사용법: /init 실행 후 /setup-from-template 으로 정리 -->

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

## Language-Specific Rules

@rules/languages/python.md
@rules/languages/typescript.md

## Frontend Rules (프론트엔드 프로젝트만)

@rules/languages/nextjs.md
@rules/styling/css.md
```

- [ ] **Step 3.2: Verify all `@import` paths resolve**

```bash
grep -E '^@rules/' CLAUDE.md | sed 's/^@//' | while read p; do
  test -f "$p" && echo "OK $p" || echo "MISSING $p"
done
```

Expected: every line prefixed with `OK`. No `MISSING`.

- [ ] **Step 3.3: Verify no Project / Commands sections leaked through**

```bash
grep -c "^## Project" CLAUDE.md
grep -c "^## Commands" CLAUDE.md
```

Expected: both `0`.

- [ ] **Step 3.4: Commit**

```bash
git add CLAUDE.md
git commit -m "refactor: reduce CLAUDE.md to minimal seed (import blocks only)"
```

---

### Task 4: Create the /setup-from-template slash command

**Files:**
- Create: `.claude/commands/setup-from-template.md`

- [ ] **Step 4.1: Create the directory**

```bash
mkdir -p .claude/commands
```

- [ ] **Step 4.2: Write the slash command file with this exact content**

````markdown
---
description: claude-code-template 으로 시작한 새 프로젝트를 setup — 스택 감지, @import 가지치기, 디자인 토큰 배치, 메타 문서 정리
---

이 슬래시 커맨드는 claude-code-template 을 새 프로젝트 루트로 복사한 직후 한 번 실행하는 setup automation 이다. 각 단계는 사용자 확인을 받은 뒤 진행하고, 파괴적 작업(파일 삭제·이동·`CLAUDE.md` 편집)은 명시적 Y 응답 없이 실행하지 말 것.

## Step 1 — 스택 감지 (자동)

다음 파일/폴더의 존재로 스택을 추론하고 결과를 사용자에게 표로 보여준다.

- `package.json` → JS/TS 프로젝트
- `next.config.*` 또는 `app/` + React → Next.js
- `tailwind.config.*` 또는 `package.json` 의 `tailwindcss` 의존성 → Tailwind
- `pyproject.toml` 또는 `requirements.txt` → Python

어느 것도 감지되지 않으면 "스택을 감지할 수 없습니다. 수동으로 진행하세요." 메시지 후 종료.

## Step 2 — Language / Frontend imports 가지치기

`CLAUDE.md` 의 `## Language-Specific Rules` / `## Frontend Rules` 섹션에서 감지 결과와 일치하지 않는 `@import` 라인을 제거한다.

규칙:
- Python 미감지 → `@rules/languages/python.md` 라인 제거
- TS/JS 미감지 → `@rules/languages/typescript.md` 라인 제거
- Next.js 미감지 → `@rules/languages/nextjs.md` 라인 제거
- 프론트엔드 미감지 → `## Frontend Rules` 섹션 통째 제거 (`@rules/styling/css.md` 포함)

제거할 라인 diff 를 보여주고 사용자 Y/N 확인 후 적용.

## Step 3 — `## Rules` 블록 복원

`CLAUDE.md` 의 `## Rules` 섹션에 다음 9 개 라인이 모두 존재하는지 확인:

```
@rules/comments.md
@rules/config.md
@rules/docker.md
@rules/testing.md
@rules/git.md
@rules/security.md
@rules/dependencies.md
@rules/sync-checklist.md
@rules/error-handling.md
```

누락된 라인이 있거나 `## Rules` 섹션 자체가 없으면 위 canonical block 을 적절한 위치(보통 파일 상단 또는 `## Language-Specific Rules` 위)에 추가. diff 를 보여주고 사용자 Y/N 확인 후 적용.

## Step 4 — 디자인 토큰 배치 (프론트엔드만)

Step 1 에서 프론트엔드 미감지면 이 단계 건너뛴다.

사용자에게 묻기: "Tailwind 와 vanilla CSS / CSS Modules 중 무엇을 사용하시나요? (T / V)"

- **T (Tailwind):**
  - `templates/tailwind.theme.ts` → 프로젝트 루트로 이동
  - `templates/design-tokens.css` 삭제
- **V (vanilla):**
  - `templates/design-tokens.css` → `styles/design-tokens.css` 로 이동 (`styles/` 디렉터리 자동 생성)
  - `templates/tailwind.theme.ts` 삭제

이동/삭제 전 사용자 Y/N 확인.

## Step 5 — 디자인 컨셉 레퍼런스 정리 (프론트엔드만)

사용자에게 묻기: "`templates/design_concept/` 5 개 레퍼런스를 유지하시겠어요? (Y/N, 기본 N)"

기본은 삭제. Y 응답 시에만 유지.

## Step 6 — 메타 문서 정리

사용자에게 묻기: "`docs/template/` 의 템플릿 사용 가이드를 삭제하시겠어요? (Y/N, 기본 Y)"

기본은 삭제. 유지를 원하면 N.

## Step 7 — 검증 (자동)

- `CLAUDE.md` 의 모든 `@import` 라인을 grep 으로 추출
- 각 경로가 실제 파일을 가리키는지 확인
- 깨진 import 가 있으면 사용자에게 보고
- 최종 요약 출력:
  - 적용된 규칙 N 개
  - 디자인 토큰 위치 (또는 "프론트엔드 아님")
  - `templates/design_concept/` 유지/삭제
  - `docs/template/` 유지/삭제
  - 깨진 import 개수
````

- [ ] **Step 4.3: Verify the file**

```bash
test -f .claude/commands/setup-from-template.md && echo "exists: OK"
head -3 .claude/commands/setup-from-template.md
grep -c "^## Step 1 — 스택 감지" .claude/commands/setup-from-template.md
grep -c "^## Step 7 — 검증" .claude/commands/setup-from-template.md
```

Expected: `exists: OK`, frontmatter visible, both grep counts = 1.

- [ ] **Step 4.4: Commit**

```bash
git add .claude/commands/setup-from-template.md
git commit -m "feat: add /setup-from-template slash command"
```

---

### Task 5: Rewrite docs/template/README.md per the writing rules

**Files:**
- Modify: `docs/template/README.md`

- [ ] **Step 5.1: Replace the file content (full overwrite)**

```markdown
# Claude Code 템플릿

Claude Code 프로젝트를 위한 hub-and-spoke 규칙 템플릿. 새 프로젝트 루트에 복사 → `/init` → `/setup-from-template` 으로 setup 한다.

## 실행 방법

**1. 템플릿 복사**

```bash
# macOS / Linux
cp -r /path/to/claude-code-template ~/new-project
cd ~/new-project
```

```powershell
# Windows (PowerShell)
Copy-Item -Recurse C:\path\to\claude-code-template C:\Users\<you>\new-project
cd C:\Users\<you>\new-project
```

**2. Claude Code 에서 `/init` 실행**

현재 폴더 구조를 분석해 프로젝트 맞춤 hub `CLAUDE.md` 가 생성된다.

**3. `/setup-from-template` 실행**

스택 감지 → 불필요한 `@import` 제거 → 디자인 토큰 배치 → 메타 문서 정리. 자세한 동작은 [`USAGE.md`](USAGE.md) 참고.

## 왜 hub-and-spoke 인가

- `CLAUDE.md` 가 짧게 유지된다 → 프로젝트 overview 가 한눈에 들어옴
- 규칙을 바꿔도 hub 는 그대로, `rules/*.md` 만 수정
- 규칙을 끄려면 `@import` 한 줄만 지움
- 언어별 규칙을 시각적으로 분리

상세 사용법, 파일 구성, FAQ → [`USAGE.md`](USAGE.md).
```

- [ ] **Step 5.2: Verify (no inventory, has OS split, links to USAGE)**

```bash
# Should NOT contain a rules/* inventory
echo -n "rule mentions in README (should be 0): "
grep -c "comments.md\|docker.md\|testing.md" docs/template/README.md

# Has macOS and Windows blocks
echo -n "macOS lines: "
grep -c "macOS / Linux" docs/template/README.md
echo -n "Windows lines: "
grep -c "Windows (PowerShell)" docs/template/README.md

# Links to USAGE
echo -n "USAGE links: "
grep -c "USAGE.md" docs/template/README.md

# Length
wc -l docs/template/README.md
```

Expected: rule mentions = 0, macOS = 1, Windows = 1, USAGE links ≥ 2.

- [ ] **Step 5.3: Commit**

```bash
git add docs/template/README.md
git commit -m "docs: rewrite template README per audience-split writing rules"
```

---

### Task 6: Rewrite docs/template/USAGE.md per the writing rules

**Files:**
- Modify: `docs/template/USAGE.md`

- [ ] **Step 6.1: Replace the file content (full overwrite)**

````markdown
# Claude Code 템플릿 사용 가이드

이 가이드는 `claude-code-template` 을 새 프로젝트로 복사한 뒤 사용하는 방법을 설명한다. **사용자(end user) 관점** — 템플릿을 받아 자신의 프로젝트를 시작하려는 사람을 대상으로 한다.

---

## 파일 구성

본 템플릿이 ship 하는 파일 / 폴더는 다음과 같다. **이 인벤토리가 본 레포의 단일 출처다** — 다른 곳에 중복 표기되지 않는다.

```
CLAUDE.md                       # 허브 (최소 seed — @import 블록만)
README.md                       # 다운스트림 프로젝트의 placeholder
.claude/
  commands/
    setup-from-template.md      # 본 setup 슬래시 커맨드
  settings.local.json           # 로컬 Claude Code 설정
docs/
  template/
    README.md                   # 템플릿 overview (개발자/인수인계 관점)
    USAGE.md                    # 본 파일 (사용자 관점)
rules/
  comments.md                   # 주석 규칙
  config.md                     # 설정 관리
  docker.md                     # Docker
  testing.md                    # 테스트
  git.md                        # Git 컨벤션
  security.md                   # 보안
  dependencies.md               # 의존성 관리
  sync-checklist.md             # 코드 변경 동기화 체크리스트
  error-handling.md             # 에러 처리
  languages/
    python.md                   # Python 전용
    typescript.md               # TypeScript / JavaScript 전용
    nextjs.md                   # Next.js (App Router) 전용
  styling/
    css.md                      # CSS / Tailwind 공통 + 토큰 강제
templates/
  design-tokens.css             # vanilla CSS 디자인 토큰
  tailwind.theme.ts             # Tailwind 디자인 토큰
  design_concept/               # 5 개 디자인 컨셉 레퍼런스 (01_minimal ~ 05_apple)
```

`rules/*.md` 는 `CLAUDE.md` 가 `@import` 로 자동 로드한다. `templates/` 는 import 대상이 아니다 — 프로젝트 시작 시 복사해서 채우는 파일 템플릿이다.

---

## 사용 흐름

세 단계로 끝난다.

**1. 템플릿 복사**

```bash
# macOS / Linux
cp -r /path/to/claude-code-template ~/new-project
cd ~/new-project
```

```powershell
# Windows (PowerShell)
Copy-Item -Recurse C:\path\to\claude-code-template C:\Users\<you>\new-project
cd C:\Users\<you>\new-project
```

**2. `/init` 실행**

Claude Code 에서 `/init` 을 실행하면, 현재 폴더 상태를 분석해 프로젝트 성격(스택, 빌드 / 테스트 명령, 핵심 디렉터리 구조)을 정리한 hub `CLAUDE.md` 가 자동 생성된다.

빈 placeholder 대신 `/init` 결과물을 그대로 쓴다.

**3. `/setup-from-template` 실행**

같은 Claude Code 세션에서 슬래시 커맨드를 실행한다. 스택 감지 → 불필요한 `@import` 제거 → 디자인 토큰 배치 → 메타 문서 정리까지 자동화된다.

---

## `/setup-from-template` 동작

7 단계 순차 실행. 각 파괴적 단계는 명시적 Y/N 확인 후 적용된다.

| # | 단계 | 동작 | 사용자 입력 |
|---|---|---|---|
| 1 | 스택 감지 | `package.json`, `next.config.*`, `tailwind.config.*`, `pyproject.toml`, `requirements.txt` 의 존재로 추론 | 자동 |
| 2 | Language / Frontend imports 가지치기 | 감지 결과와 무관한 `@rules/languages/*.md` 와 `## Frontend Rules` 섹션 라인 제거 | Y/N |
| 3 | `## Rules` 블록 복원 | `/init` 이 제거했을 수 있는 9 개 일반 규칙 import 를 canonical block 으로 보강 | Y/N |
| 4 | 디자인 토큰 배치 | Tailwind 면 `tailwind.theme.ts` 를 루트로, vanilla 면 `design-tokens.css` 를 `styles/` 로. 미사용 템플릿 삭제 | T / V |
| 5 | 디자인 컨셉 레퍼런스 정리 | `templates/design_concept/` 유지 여부 | Y/N (기본 N) |
| 6 | 메타 문서 정리 | `docs/template/` 삭제 여부 | Y/N (기본 Y) |
| 7 | 검증 | 모든 `@import` 경로 resolve 확인 + 요약 | 자동 |

---

## 수동 조정

슬래시 커맨드가 적합하지 않은 경우(모노레포, 다중 언어 동시 사용 등)는 직접 수행한다.

- **`@import` 가지치기**: `CLAUDE.md` 의 `## Language-Specific Rules` / `## Frontend Rules` 섹션에서 사용 안 하는 라인을 직접 삭제. 줄을 안 지워도 동작은 하지만 컨텍스트를 차지한다.
- **디자인 토큰**: `templates/tailwind.theme.ts` 또는 `templates/design-tokens.css` 중 하나를 골라 `tailwind.config.ts` 의 `theme.extend` 또는 `app/layout.tsx` import 로 연결. 자세한 규칙은 `rules/styling/css.md` 참고.
- **프로젝트 특화 규칙 추가**: `rules/<name>.md` 새 파일 작성 → `CLAUDE.md` 의 `## Rules` 섹션에 `@rules/<name>.md` 한 줄 추가. 짧은 규칙이면 `CLAUDE.md` 의 `## Rules` 위쪽에 직접 섹션을 만들어도 된다.

Python 프로젝트의 의존성 설치 명령은 항상 두 가지를 함께 표기:

```bash
# uv (preferred)
uv pip install -r requirements.txt

# pip (fallback)
pip install -r requirements.txt
```

---

## 새 규칙 추가하기

본 템플릿에 새 규칙을 contribute 하는 절차.

1. `rules/<name>.md` 작성. 단일 책임, 200 줄 이하, terse imperative 영어.
2. `CLAUDE.md` 의 `## Rules` 섹션에 `@rules/<name>.md` 추가.
3. 본 USAGE 의 「파일 구성」 트리에 새 파일 한 줄 추가 (인벤토리 단일 출처).
4. `docs/template/README.md` 는 건드리지 않는다 (인벤토리 미보유).

언어 추가 시 동일 절차를 `rules/languages/` 와 `## Language-Specific Rules` 섹션에 적용.

---

## 업데이트 주기

- **트리거 기반**: 위 「새 규칙 추가하기」 절차의 변경이 발생하면 같은 PR 에서 즉시 갱신.
- **주기 검토**: 분기 1 회. 실행 명령이 현재 환경에서 동작하는가, 인벤토리가 실제 파일과 일치하는가, 죽은 링크 없는가.
- **이벤트 트리거**: 메이저 릴리즈, 신규 팀원 온보딩, OS / 툴체인 메이저 버전 변경 시 분기 검토를 앞당긴다.

---

## FAQ

**Q. `CLAUDE.md` 위치가 프로젝트 루트가 아니면?**
A. Claude Code 는 프로젝트 루트의 `CLAUDE.md` 를 자동 로드한다. 또는 `.claude/CLAUDE.md` 도 동작.

**Q. `/init` 가 본 템플릿의 `## Rules` 블록을 지워버리면?**
A. `/setup-from-template` Step 3 가 누락된 라인을 canonical block 으로 복원한다.

**Q. 본 템플릿을 쓰지 않고 hub 만 베끼면 안 되나?**
A. 가능. `CLAUDE.md` 의 `@import` 블록과 필요한 `rules/*.md` 만 수동 복사하면 된다. 슬래시 커맨드의 자동화 이득은 포기.

**Q. 팀원이 다른 AI 도구를 쓰면?**
A. `CLAUDE.md` 는 Claude Code 전용. 다른 도구는 자체 설정 파일을 쓴다 (Cursor: `.cursorrules`, Copilot: `.github/copilot-instructions.md`). 같은 내용을 파일명만 바꿔 복제.

**Q. `CLAUDE.md` 와 `.claude/settings.json` 의 차이?**
A. `CLAUDE.md` = "이렇게 해줘" (권장, Claude 가 판단). `settings.json` = "이것만 허용" (시스템이 강제). 예: "테스트는 mock 으로" → `CLAUDE.md`, "pytest 명령 허용" → `settings.json`.

**Q. 규칙이 너무 많으면 Claude 가 무시하나?**
A. Anthropic 공식 권장은 파일당 200 줄 이하, 전체 규칙 150 개 이하. 넘으면 준수율이 균일하게 하락. hub 구조 덕분에 분리되어 있지만 총량은 관리할 것.
````

- [ ] **Step 6.2: Verify required sections, OS split, uv+pip pairing, length**

```bash
# All required sections (heading-prefix exact match)
for s in "파일 구성" "사용 흐름" "수동 조정" "새 규칙 추가하기" "업데이트 주기" "FAQ"; do
  c=$(grep -c "^## $s" docs/template/USAGE.md)
  echo "$s: $c"
done
echo -n "/setup-from-template 동작: "
grep -c "^## \`/setup-from-template\` 동작" docs/template/USAGE.md

# Python uv + pip pairing
echo -n "uv pip install lines: "
grep -c "uv pip install" docs/template/USAGE.md
echo -n "pip install (non-uv) lines: "
grep -c "^pip install" docs/template/USAGE.md

# OS split
echo -n "macOS / Linux lines: "
grep -c "macOS / Linux" docs/template/USAGE.md
echo -n "Windows (PowerShell) lines: "
grep -c "Windows (PowerShell)" docs/template/USAGE.md

# Length cap
wc -l docs/template/USAGE.md
```

Expected: every section count ≥ 1, uv & pip ≥ 1 each, macOS & Windows ≥ 1 each, total lines ≤ 300.

- [ ] **Step 6.3: Commit**

```bash
git add docs/template/USAGE.md
git commit -m "docs: rewrite USAGE for new flow with single-source inventory"
```

---

### Task 7: Final integration verification

**Files:** None modified — verification only. If something is wrong, fix in place and commit.

- [ ] **Step 7.1: Verify all `@import` paths in CLAUDE.md still resolve**

```bash
grep -E '^@rules/' CLAUDE.md | sed 's/^@//' | while read p; do
  test -f "$p" && echo "OK $p" || echo "MISSING $p"
done | grep MISSING
```

Expected: empty output.

- [ ] **Step 7.2: Verify single-source inventory (rule names only in USAGE)**

```bash
echo -n "rule names in docs/template/README.md (must be 0): "
grep -cE "^\s+(comments|config|docker|testing|git|security|dependencies|sync-checklist|error-handling)\.md" docs/template/README.md

echo -n "rule names in docs/template/USAGE.md (must be ≥ 9): "
grep -cE "^\s+(comments|config|docker|testing|git|security|dependencies|sync-checklist|error-handling)\.md" docs/template/USAGE.md

echo -n "@imports in CLAUDE.md (must be 13): "
grep -cE "^@rules/" CLAUDE.md
```

Expected: README count = 0, USAGE count ≥ 9, CLAUDE.md @imports = 13.

- [ ] **Step 7.3: Verify slash command references correct paths**

```bash
test -f .claude/commands/setup-from-template.md && echo "exists: OK"
for ref in "templates/tailwind.theme.ts" "templates/design-tokens.css" "templates/design_concept/" "docs/template/" "@rules/" "## Frontend Rules" "## Language-Specific Rules"; do
  c=$(grep -c "$ref" .claude/commands/setup-from-template.md)
  echo "$ref: $c"
done
```

Expected: all references ≥ 1.

- [ ] **Step 7.4: Verify root README.md is a placeholder, not the old content**

```bash
wc -l README.md
grep -c "TODO: 프로젝트 설명" README.md
grep -c "Claude Code Template" README.md
```

Expected: ≤ 5 lines, TODO grep = 1, "Claude Code Template" grep = 0 (the title moved to docs/template/README.md).

- [ ] **Step 7.5: Commit any verification fixes**

```bash
git status
# If clean: skip the commit step
# If dirty: git add -A && git commit -m "fix: resolve verification findings"
```

- [ ] **Step 7.6: Final repo overview**

```bash
git log --oneline -10
ls -la
ls docs/template/
ls .claude/commands/
```

Expected: 6–7 new commits since starting, `docs/template/` contains README.md + USAGE.md, `.claude/commands/` contains setup-from-template.md, root contains the placeholder README.md and seed CLAUDE.md.

---

## Self-Review

| Spec section | Implementing task |
|---|---|
| §4.1 file reorganization | Tasks 1, 2 |
| §4.2 CLAUDE.md seed | Task 3 |
| §4.3 root README placeholder | Task 2 |
| §4.4 slash command (7 steps) | Task 4 |
| §4.5 README writing rules | Task 5 |
| §4.5 USAGE writing rules + 업데이트 주기 | Task 6 |
| §5 acceptance criteria | Task 7 verification |
| §6 trade-offs (no rollout/migration scripts) | n/a — accepted |

Placeholder scan: every step contains complete content (full file bodies, exact bash commands, expected outputs). No "TBD", no "implement later".

Type/path consistency: `.claude/commands/setup-from-template.md`, `docs/template/README.md`, `docs/template/USAGE.md`, `templates/tailwind.theme.ts`, `templates/design-tokens.css`, `templates/design_concept/` — all consistent across tasks.
