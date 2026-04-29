# Config Management

- Secrets (API keys, passwords) are NEVER hardcoded — use environment variables.
- `.env` is never committed to git (`.gitignore`).
- Tunable values go in a Settings object with defaults; expose via `.env` if the host app needs to override.
- Business constants (unchanging core logic values) stay as Settings field defaults only — no `.env` entry needed.
- No duplicate definitions between module-level constants and Settings fields.
