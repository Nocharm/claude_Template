# Dependency Management

- **Separate production and dev dependencies** (requirements.txt vs requirements-dev.txt, dependencies vs devDependencies).
- Pin exact versions in lock files.
- Verify a new dependency is truly needed before adding — prefer stdlib solutions.
- Document WHY a non-obvious dependency was chosen.
- Keep the dependency footprint minimal: this module embeds into a host app, so every added dep is a burden on the host.
