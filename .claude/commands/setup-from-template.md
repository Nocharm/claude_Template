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

이 두 작업은 사용자가 직접 수행하도록 두고, 자동 커맨드가 자동 커밋하지 않습니다.
