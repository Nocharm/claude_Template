# CLAUDE.md

기존 프로젝트에 임베딩하기 위한 소규모 독립 기능 모듈 템플릿.
호스트 앱의 의존성 체계를 따르며, 단일 책임 원칙으로 범위를 좁게 유지한다.

> **이 폴더를 다른 프로젝트에 적용하려면 → [`docs/template-usage.md`](docs/template-usage.md)**

---

## Project

<한 줄 설명 — 이 모듈이 무엇을 하고 어느 호스트 앱에 삽입되는지>

---

## Commands

```bash
# Test
<your test command here>              # full suite
<your single test command here>       # single test

# Lint / Format
<your lint command here>
<your format command here>
```

---

## Rules

@rules/comments.md
@rules/config.md
@rules/testing.md
@rules/git.md
@rules/security.md
@rules/dependencies.md
@rules/error-handling.md

---

## Language-Specific Rules

프로젝트에서 사용하는 언어만 남기고 나머지 줄은 삭제한다.

@rules/languages/python.md
@rules/languages/typescript.md
