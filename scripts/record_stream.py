from datetime import datetime, timezone

from media_meter.usage_ledger import UsageEvent, UsageLedger, UsageStage


def main() -> None:
    ledger = UsageLedger()
    customer_id = "creator_42"
    now = datetime.now(timezone.utc)
    for event in (
        UsageEvent("evt_upload", customer_id, "asset_launch", UsageStage.INGESTION, 8_000_000, now),
        UsageEvent("evt_encode", customer_id, "asset_launch", UsageStage.PROCESSING, 93, now),
        UsageEvent("evt_delivery", customer_id, "asset_launch", UsageStage.DELIVERY, 24_000_000, now),
    ):
        ledger.record(event)
    print(ledger.usage_for(customer_id))


if __name__ == "__main__":
    main()

