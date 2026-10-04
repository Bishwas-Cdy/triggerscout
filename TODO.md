# TriggerScout implementation plan

- [x] Scaffold the FastAPI package, configuration, logging, database lifecycle, and tooling.
- [x] Define SQLAlchemy models and Pydantic API schemas for companies, snapshots, changes, and direct comparison.
- [x] Implement URL safety, bounded/retrying HTTP scraping, HTML normalization, stable hashing, and noise filtering.
- [x] Implement deterministic compact diffing, trigger rules, significance scoring, recommended actions, and optional validated LLM classification.
- [x] Add company, snapshot, scan, change, compare, health, and webhook endpoints.
- [x] Add representative examples, an importable n8n workflow, Docker support, and portfolio documentation.
- [x] Add endpoint and service tests covering the required success, fallback, noise, and security cases.
- [x] Run and fix `pytest`, `ruff check .`, `ruff format --check .`, and `mypy app --strict`.
- [x] Verify the FastAPI application starts and serves `/health`.
