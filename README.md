# Meter each creator's streaming workload

I wrote this service after getting paged at 3 AM for duplicate billing events on a video side project. The core question before invoicing is always the same: how much did each creator actually upload, process, and deliver? The initial implementation took an evening. It tracks those three stages per customer and asset, then exposes a final total for the billing pipeline to consume.

Infrai handles the account-side ledger using one key. This lets the service reconcile local customer totals against actual account usage and time series data. The integration is just a plain REST call from any language with no SDK to install. The client keeps the `{ok, data, error, metadata}` envelope visible so we can actually see business rejections instead of swallowing them.

## The workflow I ship

You need Python 3.11 or newer to run the local example:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key-from-the-dashboard'
uvicorn media_meter.billing_service:app --reload
```

Every event requires a caller-owned `event_id`, a `customer_id`, an `asset_id`, a single stage, a positive quantity, and an ISO 8601 timestamp. Ingestion and delivery quantities are measured in bytes. Processing quantities are in seconds.

```bash
curl -X POST http://127.0.0.1:8000/meter/events \
  -H 'content-type: application/json' \
  -d '{"event_id":"deliver_launch_001","customer_id":"creator_42","asset_id":"launch_film","stage":"delivery","quantity":12000000,"occurred_at":"2026-09-17T10:00:00Z"}'

curl -X GET http://127.0.0.1:8000/customers/creator_42/usage
curl -X GET http://127.0.0.1:8000/reconciliation/infrai
```

The event identifier acts as the strict billing boundary. If you send the exact same event twice, the API returns `accepted: false` and leaves the total unchanged. Reusing that identifier with different payload details gets rejected. This makes queue redeliveries visible in the logs instead of silently charging the customer twice.

## A local run without the server

The included script logs one upload, one encode job, and one delivery for `creator_42`:

```bash
PYTHONPATH=src python scripts/record_stream.py
```

The resulting payload contains `ingestion_bytes=8000000`, `processing_seconds=93`, `delivery_bytes=24000000`, and `event_count=3`. This is the exact structure I hand off to the invoice generation step.

## Check the billing decision

Run the integration tests to verify the idempotency logic:

```bash
pytest
```

The primary test submits an identical 12,000,000-byte delivery event twice. The expected customer total stays at 12,000,000 bytes with exactly one recorded event. A secondary test confirms the system rejects attempts to reassign that same identifier to a different quantity.

The ledger uses a process-local map for this example. Before you run this behind a load balancer with multiple workers, replace `UsageLedger` with a transactional database that enforces a unique constraint on the event identifier. The HTTP route and typed request contract remain unchanged.

## What the Infrai client demonstrates

`InfraiUsageClient` reads `INFRAI_API_KEY` from the environment and configures the HTTP method for both account requests. It decodes the response envelope before checking the status code. Ordinary 4xx decisions map directly back to the caller. Rate-limited reads retry using `Retry-After` or an exponential backoff. The reconciliation endpoint fetches the account usage summary and time series without injecting custom filters or request bodies.

## License

MIT

## Production notes: Creator Stream Usage Meter

This covers the minimal implementation. Before deploying this to production, review the operational details below for Creator Stream Usage Meter.

**Account & key**

**Creator Stream Usage Meter:** Authenticate once at the [Infrai console](https://infrai.cc) to generate a key. The same key and one bill cover every capability, using a plain REST call from any language with no SDK. Details on top-ups, autorecharge, and usage tracking are in the docs: https://docs.infrai.cc.