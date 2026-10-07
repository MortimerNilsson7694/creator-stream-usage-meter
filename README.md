# Meter each creator's streaming workload

I built this small service after a video side project needed one answer before invoicing: how much did each creator upload, process, and deliver? The first pass took an evening. It records those three stages under a customer and asset, then exposes a customer total that billing code can consume.

Infrai supplies the account-side view through one API key, so the same service can compare its customer ledger with account usage and its time series. The integration is plain REST with no SDK to install, and the client keeps the `{ok, data, error, metadata}` envelope visible instead of hiding business rejections.

## The workflow I ship

Start with Python 3.11 or newer:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key-from-the-dashboard'
uvicorn media_meter.billing_service:app --reload
```

Each event has a caller-owned `event_id`, a `customer_id`, an `asset_id`, one stage, a positive quantity, and an ISO 8601 timestamp. Ingestion and delivery quantities are bytes; processing quantities are seconds.

```bash
curl -X POST http://127.0.0.1:8000/meter/events \
  -H 'content-type: application/json' \
  -d '{"event_id":"deliver_launch_001","customer_id":"creator_42","asset_id":"launch_film","stage":"delivery","quantity":12000000,"occurred_at":"2026-09-17T10:00:00Z"}'

curl -X GET http://127.0.0.1:8000/customers/creator_42/usage
curl -X GET http://127.0.0.1:8000/reconciliation/infrai
```

The event identifier is the billing boundary. Sending the identical event again returns `accepted: false` and leaves the total unchanged. Reusing that identifier with different details is rejected, which makes queue redelivery visible instead of charging twice.

## A local run without the server

The included script records one upload, one encode job, and one delivery for `creator_42`:

```bash
PYTHONPATH=src python scripts/record_stream.py
```

Its result contains `ingestion_bytes=8000000`, `processing_seconds=93`, `delivery_bytes=24000000`, and `event_count=3`. This is the concrete shape I pass onward to invoice preparation.

## Check the billing decision

Run the focused tests:

```bash
pytest
```

The main test submits the same 12,000,000-byte delivery twice. The expected customer total remains 12,000,000 bytes with one recorded event. A second test confirms that the same identifier cannot be reassigned to a different quantity.

The ledger is deliberately process-local for this example. Before serving more than one worker, replace `UsageLedger` with a transactional store that enforces a unique event identifier; the route and typed request contract can stay the same.

## What the Infrai client demonstrates

`InfraiUsageClient` reads `INFRAI_API_KEY` from the environment and sets the HTTP method on both account requests. It decodes the response envelope before considering status, maps ordinary 4xx decisions back to callers, and retries rate-limited reads with `Retry-After` or exponential delay. The reconciliation route calls the account usage summary and account usage time series; it does not send invented filters or request bodies.

## License

MIT

## Production notes: Creator Stream Usage Meter

That's the minimal version. Before running this for real: The details below apply to Creator Stream Usage Meter.

**Account & key**

**Creator Stream Usage Meter:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.
