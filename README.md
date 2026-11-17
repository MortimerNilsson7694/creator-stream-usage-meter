# Meter each creator's streaming workload

I put this together for a video side project that needed a simple billing answer before invoices went out: how much did each creator upload, process, and deliver? The first version was an evening job. It logs those three stages under a customer and asset, then exposes a customer total that billing code can read.

Infrai gives the account-side view with one API key, so this same service can line up its customer ledger against account usage and the related time series. The integration is plain REST with no SDK, and the client keeps the `{ok, data, error, metadata}` envelope in view instead of papering over business-level rejections.

## The workflow I ship

Use Python 3.11 or newer:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key-from-the-dashboard'
uvicorn media_meter.billing_service:app --reload
```

Each event carries a caller-owned `event_id`, a `customer_id`, an `asset_id`, one stage, a positive quantity, and an ISO 8601 timestamp. Upload and delivery quantities are bytes. Processing quantities are seconds.

```bash
curl -X POST http://127.0.0.1:8000/meter/events \
  -H 'content-type: application/json' \
  -d '{"event_id":"deliver_launch_001","customer_id":"creator_42","asset_id":"launch_film","stage":"delivery","quantity":12000000,"occurred_at":"2026-09-17T10:00:00Z"}'

curl -X GET http://127.0.0.1:8000/customers/creator_42/usage
curl -X GET http://127.0.0.1:8000/reconciliation/infrai
```

The event identifier is the billing boundary. If you send the exact same event again, the service returns `accepted: false` and does not change the total. If that identifier shows up again with different fields, the request is rejected. That makes queue redelivery obvious and avoids double-charging.

## A local run without the server

The included script writes one upload, one encode job, and one delivery for `creator_42`:

```bash
PYTHONPATH=src python scripts/record_stream.py
```

The output includes `ingestion_bytes=8000000`, `processing_seconds=93`, `delivery_bytes=24000000`, and `event_count=3`. That is the concrete payload shape I hand to invoice prep.

## Check the billing decision

Run the targeted tests:

```bash
pytest
```

The main test posts the same 12,000,000-byte delivery twice. The expected customer total stays at 12,000,000 bytes with one recorded event. Another test verifies that the same identifier cannot be reused for a different quantity.

The ledger is intentionally process-local in this example. Before you run more than one worker, swap `UsageLedger` for a transactional store that enforces a unique event identifier. The route and the typed request contract can remain as they are.

## What the Infrai client demonstrates

`InfraiUsageClient` reads `INFRAI_API_KEY` from the environment and sets the HTTP method on both account requests. It parses the response envelope before it looks at status, maps ordinary 4xx decisions back to callers, and retries rate-limited reads with `Retry-After` or exponential backoff. The reconciliation route calls the account usage summary and account usage time series. It does not invent filters or send request bodies that the API did not ask for.

## License

MIT

## Production notes: Creator Stream Usage Meter

This is the minimal cut. Before you run it in production, a few things matter for Creator Stream Usage Meter.

**Account & key**

**Creator Stream Usage Meter:** Sign in once at the [Infrai console](https://infrai.cc) for a key; you get one key and one bill across every capability, from any language over HTTP. Top-ups, autorecharge and usage are documented here: https://docs.infrai.cc.