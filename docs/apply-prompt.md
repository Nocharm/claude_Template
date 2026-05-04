# 적용 프롬프트

이 파일은 **사용자가 호스트 프로젝트의 Claude Code 세션에 복사해 붙여넣을 프롬프트**다.

## 사용 방법

1. 본 템플릿 폴더를 호스트 프로젝트가 접근 가능한 경로에 둔다 (clone, submodule, 단순 복사 등).
2. 호스트 프로젝트의 루트에서 Claude Code 를 시작한다.
3. 아래 프롬프트 블록의 `<TEMPLATE_PATH>` 를 본 폴더의 **절대경로**로 교체해, 첫 메시지로 전송한다.

---

## 프롬프트 (아래 줄부터 복사)

`<TEMPLATE_PATH>` 경로에 Claude Code 템플릿 폴더를 두었어. 이 폴더를 현재 호스트 프로젝트(현재 cwd)에 적용해줘.

폴더 구성:
- `CLAUDE.md` + `rules/` — Claude 작업 규칙 템플릿 (허브 + import 파일들)
- `docx_parser/` — Word(.docx) 구조 추출 모듈. 호스트가 필요한 경우에만 임베딩
- `docs/template-usage.md` — **적용 절차 정본**
- `docs/usage.md`, `docs/for-developers.md` — `docx_parser` 사용/개발 가이드

작업 순서:

1. `<TEMPLATE_PATH>/docs/template-usage.md` 를 먼저 읽고 절차를 파악해.
2. 호스트 프로젝트 상태 점검:
   - 기존 `CLAUDE.md` 유무 — 있으면 절대 덮어쓰지 말고 차이를 보고. 병합 방식은 사용자와 확인 후 진행.
   - 사용 언어 — `package.json` / `pyproject.toml` / `requirements.txt` / 소스 확장자로 Python / TypeScript / 둘 다 / 그 외를 판별.
   - 실제 build · test · lint · dev 명령 — 추측하지 말고 위 설정 파일과 README 에서 추출.
3. 적용 시작 전에 사용자에게 확인:
   - 기존 `CLAUDE.md` 처리 방식 (신규 / 병합 / 백업 후 교체)
   - 언어 선택 (불필요한 `@rules/languages/*.md` import 제거 대상)
   - `docx_parser/` 모듈 임베딩 여부, 임베딩한다면 호스트 어느 경로에 둘지
4. 확인된 범위로 `docs/template-usage.md` 의 Step 1~5 를 수행:
   - `CLAUDE.md`, `rules/`, `.gitignore` 복사
   - `CLAUDE.md` 의 안 쓰는 `@rules/languages/*.md` import 줄 제거
   - `Commands` 섹션의 `<placeholder>` 를 실제 호스트 명령으로 교체
5. `docx_parser/` 임베딩 시 추가 작업:
   - 호스트의 production 의존성에 `python-docx==1.1.2`, `lxml==5.3.0` 추가 (Python 3.11+ 필요)
   - 단위 테스트(`tests/test_parser.py`, `tests/test_fixtures.py`, `tests/conftest.py`, `tests/fixtures/`) 도 함께 가져갈지 사용자에게 확인
   - 사용 예시는 `<TEMPLATE_PATH>/docs/usage.md` 의 "자주 쓰는 접근" 섹션 참고
6. 변경 결과를 파일 단위로 요약 보고. **사용자의 명시 승인 전에는 `git commit` / `git push` / 호스트의 기존 파일 삭제를 하지 마.**

판단이 모호한 항목은 추측하지 말고 사용자에게 물어봐.
