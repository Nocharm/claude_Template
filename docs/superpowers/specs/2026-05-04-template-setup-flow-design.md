# Template Setup Flow Redesign

**Date:** 2026-05-04
**Status:** Approved (brainstorming → spec)
**Repo:** `claude-code-template`

---

## 1. Problem

The repository ships hub-and-spoke Claude Code rules (`CLAUDE.md` + `rules/`) that downstream projects copy wholesale. Three issues compound:

1. **README.md / USAGE.md drift.** The rules/templates inventory is duplicated across `README.md`, `USAGE.md`, and `CLAUDE.md`'s `@import` block. Adding or renaming a rule means editing three places — easy to miss.
2. **Meta docs squat the project README slot.** Users copy this folder and start a real project in it. The template's `README.md`/`USAGE.md` describe the *template itself*, so they read awkwardly as the new project's docs and tend to be ignored rather than replaced.
3. **`/init` produces better project-specific docs.** Claude Code's built-in `/init` analyzes the codebase and generates a tailored hub `CLAUDE.md`. The template's empty placeholder hub adds little once `/init` has run.

## 2. Goal

Redesign the copy-and-start flow so that:

- The template provides only what `/init` cannot — reusable rule files, design token templates, and a setup automation.
- Inventory lives in **exactly one place**; sync drift is structurally impossible.
- New project setup collapses from six manual steps to three: **copy → `/init` → `/setup-from-template`**.

## 3. Out of Scope

- Adding new languages, frameworks, agents, or hooks.
- Translating docs to English.
- Versioning the template or propagating updates into existing downstream projects.
- CI / external validation workflows.

## 4. Design

### 4.1 File reorganization

```
claude-code-template/
├── CLAUDE.md                          # Minimal seed — @import blocks only
├── README.md                          # One-line placeholder for the new project
├── .claude/
│   ├── settings.local.json            # (existing, untouched)
│   └── commands/
│       └── setup-from-template.md     # NEW — slash command
├── docs/
│   └── template/
│       ├── README.md                  # MOVED from root
│       └── USAGE.md                   # MOVED from root
├── rules/                             # Unchanged
└── templates/                         # Unchanged
```

### 4.2 `CLAUDE.md` seed content

The hub ships only `@import` blocks. No `## Project`, no `## Commands` — `/init` generates those.

```markdown
<!-- Copy/init 후 /setup-from-template 으로 정리하세요 -->

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

### 4.3 Root `README.md` placeholder

```markdown
# <project name>

_TODO: 프로젝트 설명_
```

The user's own project description (or `/init`'s output) replaces this.

### 4.4 Slash command: `/setup-from-template`

Located at `.claude/commands/setup-from-template.md`. Instruction-style markdown that Claude Code follows step by step. Each destructive step (file delete, file move, `CLAUDE.md` edit) requires explicit Y confirmation; detection and validation steps run silently.

| # | Step | Action | User input |
|---|---|---|---|
| 1 | **Stack detection** | Probe `package.json`, `next.config.*`, `tailwind.config.*`, `pyproject.toml`, `requirements.txt`. Report findings. | auto |
| 2 | **Prune language imports** | Remove unused `@rules/languages/*.md` and `## Frontend Rules` lines from `CLAUDE.md` based on detection. Show diff. | Y/N |
| 3 | **Restore `## Rules` block** | If `/init` removed/replaced the canonical `## Rules` import block, append it back. Show diff. | Y/N |
| 4 | **Place design tokens** (frontend only) | Ask Tailwind vs vanilla CSS. Copy the matching template file (`templates/tailwind.theme.ts` → root, or `templates/design-tokens.css` → `styles/`). Delete the unused one. | Tailwind/CSS |
| 5 | **Design concept refs** (frontend only) | Ask whether to keep `templates/design_concept/`. Default: delete. | Y/N |
| 6 | **Meta docs cleanup** | Ask whether to delete `docs/template/`. Default: delete. | Y/N |
| 7 | **Validation** | Grep all `@import` paths in `CLAUDE.md`, verify each resolves. Print summary. | auto |

### 4.5 README / USAGE writing rules

Apply to **any** `README.md` or `USAGE.md` produced from or by this template — including the template's own meta docs in `docs/template/` and the downstream project READMEs that this template helps create. Documented here so the convention propagates.

#### Audience split

| File | Audience | Purpose |
|---|---|---|
| `README.md` | 개발자, 업무 인수인계자 | 프로젝트 개요 + 실행 방법 |
| `USAGE.md` | 사용자 (end user) | 사용 방법 |

A reader picking up either file cold should immediately know they're in the right place.

#### Single source of truth

Inventory of shipped files (rules, languages, templates) appears in **exactly one place**: `docs/template/USAGE.md` § "파일 구성". Nowhere else.

- `README.md` does not list rule files. It links to USAGE for the inventory.
- `CLAUDE.md`'s `@import` lines are runtime imports, not documentation — they get pruned downstream and are not authoritative.
- Any third document that needs to reference a rule file links to USAGE; it never duplicates the list.

#### `README.md` required content (≤ 80 lines)

Developer / handoff perspective. Korean prose.

Required sections, in order:

1. **프로젝트 개요** — what, why, who. ≤ 4 sentences.
2. **실행 방법** — macOS 와 Windows 를 **반드시 분리** 표기. 명령이 동일하면 동일하다고 명시 (생략 금지).
   ```bash
   # macOS / Linux
   cp -r template/ ~/new-project
   ```
   ```powershell
   # Windows (PowerShell)
   Copy-Item -Recurse template ~/new-project
   ```
3. **(Python 프로젝트의 경우)** Install / run 명령은 uv 와 pip 를 **항상 함께** 표기. uv 가 권장, pip 는 fallback.
   ```bash
   # uv (preferred)
   uv pip install -r requirements.txt

   # pip (fallback)
   pip install -r requirements.txt
   ```
4. **Link to USAGE** for end-user docs.

Forbidden in README: 파일 인벤토리, FAQ, 사용자용 how-to, 단계별 튜토리얼.

#### `USAGE.md` required content (≤ 300 lines)

End-user perspective. Korean prose. Rule bodies referenced from USAGE stay in English (that is the language of the rules themselves).

Required sections, in order:

1. **파일 구성** — the *only* inventory in the repo.
2. **사용 흐름** — 3 steps: copy → `/init` → `/setup-from-template`.
3. **`/setup-from-template` 동작** — each step's behavior and prompts (mirrors §4.4).
4. **수동 조정** — when/how to manually edit if the slash command does not fit.
5. **새 규칙 추가하기** — process for adding a rule file and updating USAGE.
6. **FAQ**.

If USAGE shows example commands for downstream stacks (e.g. Python FastAPI), those examples follow the README rules above (OS split, uv+pip pairing).

#### Update triggers

| Change | Update USAGE | Update README |
|---|---|---|
| Add/remove rule file | ✅ (인벤토리) | ❌ |
| Add/remove language | ✅ (인벤토리) | ❌ |
| Change setup flow / slash command behavior | ✅ (사용 흐름 / 동작) | ❌ |
| Change run instructions (deps, env, OS support) | ❌ | ✅ (실행 방법) |
| Change template positioning or purpose | ❌ | ✅ (프로젝트 개요) |
| Reorganize folders | ✅ (인벤토리) | ❌ |

#### Style

- Korean prose, terse imperative.
- Code blocks for commands; prose for explanation.
- Tables for inventories and decision matrices.
- One canonical example per concept.
- **Multi-OS commands**: separate, clearly labeled code blocks (`# macOS / Linux`, `# Windows (PowerShell)`). Never assume cross-platform equivalence silently.
- **Python install/run commands**: always pair uv and pip. Showing only one is forbidden.

## 5. Acceptance Criteria

- Copying the template, running `/init`, then `/setup-from-template` produces a working project with the appropriate rules, **with no manual file editing required** for common stacks: Python, TS, Next.js+Tailwind, Next.js+CSS Modules, Python+Docker.
- After cleanup, the new project root contains only files relevant to the new project — no `docs/template/`, no unused `templates/` files, no irrelevant `@import` lines.
- Every `@import` path in the final `CLAUDE.md` resolves to a real file (validated by step 7).
- Inventory drift is structurally prevented: adding a rule only requires touching the rule file itself and `docs/template/USAGE.md` § "파일 구성".

## 6. Trade-offs Accepted

- **Backwards incompatible.** Existing projects that copied the old template will not auto-receive the slash command. They keep working; they just don't benefit from the new flow unless re-templated.
- **Setup is two commands, not one.** `/init` and `/setup-from-template` are not combined; Claude Code does not expose `/init` as composable, and replicating its analysis in our slash command is not worth the maintenance cost.
- **The slash command depends on Claude Code at setup time.** Acceptable — this is a Claude Code template by definition.

## 7. Open Questions

None at spec time. Implementation may surface details around:
- Exact stack-detection heuristics (e.g., monorepo with both `package.json` and `pyproject.toml`).
- Whether `/init` reliably preserves an existing `## Rules` block. If not, step 3 of the slash command is load-bearing.
