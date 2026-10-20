# Phrasebook Study

회화책 PDF를 한 번 OCR·구조화해 표현 관계 그래프로 정리하고, iPhone(PWA)에서 퀴즈·응용·억양별 음성·실제 영상 링크·SVG 웹툰으로 외우는 개인 학습 앱.

> 상태: 설계 단계 — 구현 전. 설계는 [`docs/DESIGN.md`](docs/DESIGN.md).

## 구성 (예정)

- 백엔드: FastAPI + SQLite, Docker 단일 컨테이너 (로컬 실행, Tailscale로 iPhone 접속)
- 프론트: React PWA (iPhone 홈 화면 설치)
- 외부 API: Claude API (OCR·구조화·학습 기능·웹툰), Azure TTS (억양별 음성)

셋업·커맨드는 구현 단계에서 추가한다.
