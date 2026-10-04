# n8n scheduling workflow

TriggerScout exposes explicit scan APIs and does not run a hidden background scheduler. The scheduler can therefore restart, retry, and report errors independently of the API.

## Import

1. Start TriggerScout where n8n can reach it.
2. In n8n, choose **Import from File** and select `examples/triggerscout-n8n-workflow.json`.
3. Replace `http://host.docker.internal:8000` if your API uses another address.
4. Replace the disabled notification placeholder with a Slack, CRM, or signed webhook node and credentials.
5. Test manually before activating the six-hour schedule.

When both services run in the same Compose network, use the TriggerScout service name instead of `localhost`. On Linux, `host.docker.internal` may require an explicit host-gateway mapping.

## Flow

```text
Schedule Trigger (every 6 hours)
  ↓
GET /companies
  ↓
Filter active companies
  ↓
Loop Over Items
  ↓
POST /companies/{id}/scan
  ↓
IF meaningful_changes > 0
  ├─ yes → Slack / CRM / signed webhook (human review)
  └─ no  → stop
```

The bundled JSON uses generic HTTP Request, Filter, Split in Batches, and IF nodes and contains no real credentials.

## Cron alternative

For a fixed company ID:

```cron
0 */6 * * * curl -fsS --retry 2 -X POST http://127.0.0.1:8000/companies/1/scan >> /var/log/triggerscout.log 2>&1
```

For multiple companies, a small operator script can call `GET /companies`, select records where `active` is true, and call the scan endpoint for each ID.

## Operational recommendations

- Keep concurrency modest and respect each website’s terms and crawl policies.
- Configure n8n retry/backoff for transient `502` scan responses.
- Alert on repeated failures rather than silently dropping a company.
- Send only meaningful results to downstream systems.
- Preserve human approval before any customer-facing action.
- Add an authentication layer and signed webhook verification before public deployment.

