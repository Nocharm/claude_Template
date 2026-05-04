# 템플릿 셋업 흐름 재설계

작성일: 2026-05-04
상태: 초안 (사용자 리뷰 대기)

---

## 1. 배경 / 문제

`claude-code-template` 의 의도된 사용 패턴은 **"이 폴더 전체를 복사 → 그 자리에서 새 프로젝트 시작"** 이다. 그런데 현재 구조는 이 패턴과 어긋나는 부분이 두 군데 있다.

1. **`README.md` / `USAGE.md` 가 "템플릿 자체의 사용법"** 이다. 새 프로젝트 입장에서는 자기 README 자리를 메타 문서가 점유하고 있어, 자연스럽게 손이 가지 않고 stale 해진다. 세 곳(`README.md` "구성" 표 / `USAGE.md` "파일 구성" 트리 / `CLAUDE.md` `@import` 목록) 의 inventory 가 어긋나도 알아채기 어렵다.

2. **`/init` 의 결과물이 더 유용하다.** Claude Code 내장 `/init` 은 현재 폴더의 실제 구조를 분석해 그 프로젝트에 맞는 `CLAUDE.md` 를 생성한다. 그에 비해 현재 템플릿의 `CLAUDE.md` 는 "Project / Commands" placeholder 만 담은 빈 허브라 정보 밀도가 낮다.

→ 결과적으로 사용자가 **수동 단계 6개** (USAGE.md 의 Step 1~6) 를 직접 수행해야 하고, 그 중 placeholder 채우기는 자주 누락된다.

---

## 2. 목표 / Non-goals

**목표**
- 복사 직후 새 프로젝트로 자연스럽게 전환되도록 메타 문서를 격리한다.
- `/init` 을 흐름의 1단계로 통합해 "Project / Commands" 영역은 자동 생성되게 한다.
- 기존 USAGE.md 의 Step 2~5 (불필요 import 제거, 디자인 토큰 배치, 메타 문서 정리, 검증) 를 슬래시 커맨드 하나로 자동화한다.
- 새 규칙 (`rules/documentation.md`) 으로 "프로젝트 README/USAGE 는 placeholder 가 아닌 실제 내용을 담아야 한다" 를 명문화한다.

**Non-goals**
- 기존 사용자에 대한 마이그레이션 자동화 (이번엔 새 흐름만 정의; 이미 복사해 쓰는 프로젝트는 영향 없음).
- 새 언어/프레임워크 규칙 추가 (별도 작업).
- CI/CD, hooks, 다른 슬래시 커맨드 (별도 작업).

---

## 3. 디자인

### 3.1 파일 재구성

```
claude-code-template/
├── CLAUDE.md                            # 최소 seed (## Rules 블록만)
├── README.md                            # 한 줄짜리 placeholder
├── .claude/
│   └── commands/
│       └── setup-from-template.md       # 신규 슬래시 커맨드
├── docs/
│   └── template/
│       ├── README.md                    # 기존 README.md 이동 + 새 흐름 반영
│       └── USAGE.md                     # 기존 USAGE.md 이동 + 새 흐름 반영
├── rules/
│   ├── comments.md
│   ├── config.md
│   ├── docker.md
│   ├── testing.md
│   ├── git.md
│   ├── security.md
│   ├── dependencies.md
│   ├── sync-checklist.md
│   ├── error-handling.md
│   ├── documentation.md                 # 신규 규칙 파일
│   ├── languages/
│   │   ├── python.md
│   │   ├── typescript.md
│   │   └── nextjs.md
│   └── styling/
│       └── css.md
└── templates/
    ├── design-tokens.css
    ├── tailwind.theme.ts
    └── design_concept/
```

**바뀌는 것**
- `README.md`, `USAGE.md` → `docs/template/` 로 이동
- 루트 `README.md` 새로 작성: `# <project name>\n\n_TODO: 프로젝트 설명_` 한 줄 placeholder
- 루트 `CLAUDE.md` 단순화: `Project` / `Commands` 섹션 제거, `## Rules` + `## Language-Specific Rules` + `## Frontend Rules` 만 남김. 맨 위에 한 줄 안내 주석
- `rules/documentation.md` 신설
- `.claude/commands/setup-from-template.md` 신설

**그대로 두는 것**
- `rules/` 의 기존 9개 파일
- `rules/languages/`, `rules/styling/` 전체
- `templates/` 전체
- `.gitignore`
- `.claude/settings.local.json`

### 3.2 새 사용 흐름

복사 후 사용자가 거치는 단계:

```bash
# 1) 복사
cp -r /path/to/claude-code-template ~/new-project && cd ~/new-project

# 2) Claude Code 안에서:
/init                       # 프로젝트 분석 → CLAUDE.md 의 Project/Commands 섹션 자동 생성
                            # (기존 ## Rules 블록은 보존되거나, 다음 단계에서 복원)

/setup-from-template        # 스택 감지 → import 가지치기 → 토큰 배치 → 메타 문서 정리 → 검증
```

기존 USAGE.md 의 Step 2~5 가 한 커맨드로 합쳐진다.

### 3.3 슬래시 커맨드: `/setup-from-template`

**위치**: `.claude/commands/setup-from-template.md` (git 커밋 대상)

**파일 형식**: Claude Code slash command 의 표준 markdown — 커맨드 본문에 절차를 자연어로 기술하고, Claude 가 이를 단계별로 실행. 비가역 작업(파일 삭제·이동) 전에는 명시적 사용자 확인을 받는다.

**절차**:

| # | 단계 | 동작 | 사용자 입력 |
|---|------|------|-----|
| 1 | 스택 감지 | 다음 파일 존재 확인하여 추론<br>• `package.json` → JS/TS<br>• `pyproject.toml` 또는 `requirements.txt` → Python<br>• `next.config.{js,mjs,ts}` → Next.js<br>• `tailwind.config.{js,ts}` → Tailwind<br>• `app/`, `pages/`, `src/components/` 등 → 프론트엔드 가능성 | 자동 |
| 2 | `## Rules` 블록 보강 | `/init` 결과 `CLAUDE.md` 에 `## Rules` 블록이 없으면 추가. 있으면 감지된 스택에 따라 사용 안 하는 `@rules/languages/*.md` / `@rules/styling/*.md` 라인 제거 | 감지 결과 보여주고 Y/N |
| 3 | 디자인 토큰 배치 | 프론트엔드면 "Tailwind / vanilla CSS / 둘 다 / 안 씀" 묻고 해당 템플릿을 적절한 경로로 복사<br>• Tailwind → `templates/tailwind.theme.ts` 를 루트 `tailwind.theme.ts` 로<br>• vanilla CSS → `templates/design-tokens.css` 를 `styles/design-tokens.css` 로<br>• 사용 안 하는 템플릿은 `templates/` 에서 제거 | 선택 |
| 4 | 디자인 컨셉 레퍼런스 처리 | `templates/design_concept/` 유지/삭제 (보통 새 프로젝트에서는 삭제) | Y/N |
| 5 | 메타 문서 정리 | `docs/template/` 삭제 여부 (이 프로젝트가 더 이상 템플릿이 아니므로 보통 삭제) | Y/N |
| 6 | 루트 README 안내 | 루트 `README.md` 가 placeholder 그대로면 "`/init` 결과나 사용자 직접 작성으로 채워야 함" 한 번 알림 | 자동 (행동 강제 아님) |
| 7 | 검증 | `CLAUDE.md` 의 모든 `@rules/...` 경로를 grep 으로 추출 → 각각 파일이 실제 존재하는지 확인 → 결과 요약 출력. 깨진 경로 있으면 경고 | 자동 |

**1회성 보장**: 커맨드 첫 부분에서 "이미 셋업이 끝난 프로젝트인지" 휴리스틱으로 체크 (예: `docs/template/` 부재 + `CLAUDE.md` 에 placeholder 없음). 끝난 것 같으면 "다시 실행하시겠습니까?" 묻고 진행.

### 3.4 신규 규칙: `rules/documentation.md`

다운스트림 프로젝트가 "템플릿 메타 문서를 그대로 두지 않고 실제 프로젝트 문서를 작성"하도록 강제하는 규칙. 허브 `CLAUDE.md` 의 `## Rules` 블록에 `@rules/documentation.md` 로 import.

**규칙 요지**:
- 루트 `README.md` 는 **현재 프로젝트** 의 설명을 담는다. 무엇을 하는 프로젝트인지, 누가 쓰는지, 어떻게 시작하는지(setup), 핵심 명령어, 주요 디렉터리. placeholder (`_TODO_`, `<project name>`) 상태로 커밋 금지.
- `USAGE.md` 가 필요한 프로젝트(CLI 도구, 라이브러리, 사용자 가이드가 별도로 필요한 앱 등) 라면 **그 프로젝트의 사용법**을 작성한다. 템플릿 메타 가이드를 그대로 두지 않는다.
- 템플릿에서 시작한 프로젝트라면 첫 작업 중 하나로 루트 `README.md` 를 실제 내용으로 교체한다.
- 코드/구조가 바뀌면 README 의 해당 섹션도 함께 갱신한다 (`rules/sync-checklist.md` 와 일관).
- README 가 placeholder 상태인 채로 `feat:` / `fix:` 커밋이 쌓이지 않게 한다 — 첫 의미있는 커밋 전에 README 를 한 번이라도 채운다.

이 규칙은 일반 규칙이므로 `## Rules` 블록 (조건부 아님) 에 추가한다.

### 3.5 루트 `CLAUDE.md` seed 의 새 형태

```markdown
<!--
이 파일은 claude-code-template seed 입니다.
복사 후 `/init` 으로 Project/Commands 섹션을 채우고,
`/setup-from-template` 으로 import 라인을 정리하세요.
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

@rules/languages/python.md
@rules/languages/typescript.md

## Frontend Rules (프론트엔드 프로젝트만)

@rules/languages/nextjs.md
@rules/styling/css.md
```

`/init` 이 이 파일을 만났을 때 동작:
- Claude Code `/init` 은 기존 `CLAUDE.md` 가 있으면 그 위에 augment 하는 동작이 권장이지만, 도구 버전에 따라 overwrite 할 수도 있다. 어느 쪽이든 `/setup-from-template` 의 단계 2 가 `## Rules` 블록의 존재/내용을 보장하므로 안전하다.

### 3.6 루트 `README.md` placeholder

```markdown
# <project name>

_TODO: 프로젝트 설명_
```

`/init` 또는 사용자가 첫 의미있는 커밋 전에 교체.

### 3.7 `docs/template/USAGE.md` 갱신 내용

기존 6단계를 새 3단계 흐름으로 다시 쓴다. FAQ 항목 일부도 바뀐다.

새 구조:
1. **Step 1.** 폴더 복사
2. **Step 2.** `/init` 실행 (Project/Commands 섹션 자동 생성)
3. **Step 3.** `/setup-from-template` 실행 (자동 정리)
4. **Step 4 (선택).** 프로젝트 특화 규칙 추가 — 기존 Step 5 와 동일

기존 Step 3 (Commands 채우기), Step 4 (디자인 토큰 채우기), Step 6 (커밋) 은 새 흐름에 흡수되거나 자명해진다. Step 2 (사용 안 하는 import 제거) 는 슬래시 커맨드가 처리.

FAQ 변경:
- "이 템플릿을 안 쓰고 그냥 `/init` 만 하면?" 질문 추가 — 답: 그래도 되지만 `rules/`, `templates/` 의 자산을 못 쓴다.
- 기존 "rules/ 가 아니라 .claude/ 에 넣으면 안 되나?" 질문은 유지하되, 이제 `.claude/commands/` 도 의미있게 사용한다는 한 줄 추가.

### 3.8 `docs/template/README.md` 갱신 내용

- 새 흐름의 "Quick Start" 를 3단계로 갱신 (cp → `/init` → `/setup-from-template`)
- "구성" 표에 `docs/template/`, `.claude/commands/`, `rules/documentation.md` 추가

---

## 4. 파일별 변경 요약

| 파일 | 변경 유형 | 비고 |
|------|----------|------|
| `README.md` | 교체 | placeholder 한 줄로 |
| `USAGE.md` | 이동 | → `docs/template/USAGE.md` 로 옮긴 뒤 새 흐름 반영해 다시 씀 |
| `CLAUDE.md` | 수정 | Project / Commands 섹션 제거, `@rules/documentation.md` 추가, 상단 안내 주석 |
| `docs/template/README.md` | 신규 (이동 + 갱신) | 기존 `README.md` 를 옮겨 새 흐름 반영해 갱신 |
| `docs/template/USAGE.md` | 신규 (이동 + 갱신) | 위와 동일 |
| `rules/documentation.md` | 신규 | 3.4 의 규칙 |
| `.claude/commands/setup-from-template.md` | 신규 | 3.3 의 슬래시 커맨드 |
| `rules/sync-checklist.md` | 미변경 검토 | "README 갱신" 항목이 이미 있음. `docs/template/` 추가 여부 검토 — 일반 다운스트림에는 `docs/template/` 가 없으므로 추가하지 않는 것이 맞음 |

---

## 5. 엣지 케이스 / 결정 사항

- **`/init` 이 `## Rules` 블록을 지운 경우**: 슬래시 커맨드 단계 2 가 항상 보강하므로 안전.
- **사용자가 `/setup-from-template` 을 두 번 실행**: 첫 실행 후 `docs/template/` 가 없거나 placeholder 가 사라진 상태를 휴리스틱으로 감지하고 재실행 의사를 묻는다.
- **언어 자동 감지 실패**: 모호하면 사용자에게 명시적으로 "Python? TypeScript? 둘 다? 둘 다 아님?" 묻는다.
- **`templates/design_concept/` 를 유지하기로 한 경우**: 이후 빌드 단계에서 `next/image` 등이 그 폴더를 보지 않도록 빌드/lint 가 자체적으로 제외하거나 사용자가 .gitignore 에 추가하도록 안내. 슬래시 커맨드는 강제하지 않고 한 줄 알림만.
- **이미 다운스트림에서 쓰고 있는 기존 프로젝트**: 영향 없음. 새 흐름은 신규 복사부터 적용.
- **루트 README 가 placeholder 인 채로 첫 커밋 시도**: `rules/documentation.md` 가 권고하지만 강제(hook) 하지는 않는다. 강제는 별도 작업.

---

## 6. 검증

스펙 자체에는 자동 테스트가 없지만 구현 후 다음을 손으로 확인한다.

1. **빈 폴더 시나리오**: 빈 디렉터리에 이 템플릿을 복사 → `/init` → `/setup-from-template` 의 단계 1 이 "스택 미감지 → 어떤 언어인가요?" 로 사용자에게 묻는지.
2. **Next.js 시나리오**: `package.json` + `next.config.ts` + `tailwind.config.ts` 가 있는 폴더에 복사 → 자동으로 Python 라인이 제거되고 Tailwind 토큰이 배치되는지.
3. **Python 시나리오**: `pyproject.toml` 만 있는 폴더에 복사 → JS/TS 라인과 Frontend 섹션 전체가 제거되는지.
4. **검증 단계 7**: 일부러 `@rules/존재안함.md` 라인을 추가한 뒤 실행 → 경고가 나는지.
5. **재실행**: `/setup-from-template` 을 마친 폴더에서 다시 실행 → "이미 셋업된 것 같음, 계속?" 묻는지.

---

## 7. 후속 작업 (이번 스코프 밖)

- pre-commit hook 으로 README placeholder 상태 차단
- 영문판 `docs/template/README.en.md` / `USAGE.en.md`
- 추가 언어 (Go, Rust 등) 규칙
- 다른 슬래시 커맨드 (`/add-rule`, `/sync-template-update` 등)
- 모노레포 / nested CLAUDE.md 가이드
