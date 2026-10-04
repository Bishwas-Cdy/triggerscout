# 2–3 minute interview demo

The demo is centered on `/compare`, so it has no dependency on a live third-party site.

## Before the call

```bash
source .venv/bin/activate
uvicorn app.main:app
```

Open `http://localhost:8000/docs`, expand `POST /compare`, and click **Try it out**.

## Talk track

### 0:00–0:30 — Frame the problem

“My other projects cover research, outbound execution, and inbound classification. TriggerScout covers the missing upstream capability: detecting when an account changes in a way that creates GTM timing.”

Point out that Swagger is the intentional interface and scans are externally scheduled rather than supported by a pretend background worker.

### 0:30–1:20 — Show a deterministic signal

Use:

```json
{
  "company_name": "Acme",
  "before": "We help small startups manage sales.",
  "after": "We're hiring 20 enterprise account executives across Europe."
}
```

Execute it and highlight:

- `SALES_TEAM_EXPANSION`, confidence `0.94`, and high significance;
- exact before/after evidence;
- a safe `RESEARCH_ACCOUNT` recommendation rather than automated outreach;
- this obvious signal requires no API key and no LLM request.

### 1:20–1:50 — Prove noise control

Change the input to:

```json
{
  "company_name": "Acme",
  "before": "Copyright 2025 Acme",
  "after": "Copyright 2026 Acme"
}
```

Execute and show `NO_MEANINGFUL_CHANGE`. Explain that live pages also remove scripts, styles, navigation, footer/cookie UI, and normalize whitespace before hashing.

### 1:50–2:30 — Explain the monitored workflow

Briefly expand `POST /companies`, `POST /companies/{id}/scan`, and `GET /companies/{id}/changes`.

“The first scan stores a baseline. Later scans hash normalized content, deterministically diff only changed lines, and classify those excerpts. An optional OpenAI-compatible model handles ambiguity behind a strict Pydantic boundary. n8n or cron owns scheduling.”

Close on the architecture diagram in the README or the importable n8n workflow.

## Backup examples

- Funding: `We raised $25M in Series B funding.`
- Enterprise: `Introducing our new enterprise plan.`
- Expansion: `Our service is now available in Germany and France.`
- Pricing: `Pricing updated: Pro now starts at $99 per month.`

All are available in `examples/comparisons.json`.

