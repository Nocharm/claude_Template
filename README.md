# Phrasebook Study

회화책 PDF를 한 번 OCR·구조화해 표현 관계 그래프로 정리하고, iPhone(PWA)에서 읽기·문장 카드·표현 맵으로 외우는 개인 학습 앱. 설계는 [`docs/DESIGN.md`](docs/DESIGN.md), UI는 [`docs/UI.md`](docs/UI.md).

> 상태: 1단계 완료 — 책 처리 파이프라인 + 읽기 · 표현 상세 · 표현 맵 화면. 퀴즈·TTS·웹툰·도장 달력은 다음 단계.

## 구성

- **backend/** — FastAPI + SQLite. PDF 업로드 → Claude로 페이지 분류 → DAY별 추출 → 표현 연결 (책당 1회, 단계별 캐시로 이어서 처리).
- **frontend/** — React + Vite PWA. iPhone 사파리에서 홈 화면에 추가해 앱처럼 사용.
- **data/** — SQLite와 책별 캐시·원본 PDF (git 제외). 서버를 옮길 때 이 폴더만 복사하면 된다.

## 실행 (Docker)

```bash
cp .env.example .env          # ANTHROPIC_API_KEY 입력
docker compose up -d --build  # http://localhost:8000
```

### iPhone에서 접속 (Tailscale)

PWA 설치에는 HTTPS가 필요하다. PC와 iPhone에 Tailscale을 설치·로그인한 뒤:

```bash
tailscale serve --bg 8000     # https://<pc-이름>.<tailnet>.ts.net
```

iPhone 사파리로 위 주소 접속 → 공유 → **홈 화면에 추가**.

## 개발

```bash
# backend
cd backend
uv venv && uv pip install -r requirements-dev.txt
.venv/bin/uvicorn app.main:create_app --factory --reload   # :8000
.venv/bin/python -m pytest
.venv/bin/ruff check . && .venv/bin/ruff format --check .

# frontend (다른 터미널, /api는 :8000으로 프록시)
cd frontend
npm ci
npm run dev        # :5173
npm test
npm run lint
npm run build      # dist/ → backend가 함께 서빙
```

## 비용

Claude Opus 5.5 기준 책 1권(약 500쪽) 처리 약 $5–15, 1회. 같은 PDF를 다시 올리면 기존 결과를 돌려주고 재처리하지 않는다.
