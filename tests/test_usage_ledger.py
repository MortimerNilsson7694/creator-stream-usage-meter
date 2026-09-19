from datetime import datetime, timezone

import pytest

from media_meter.usage_ledger import UsageEvent, UsageLedger, UsageStage


def test_retry_does_not_bill_the_same_delivery_twice() -> None:
    ledger = UsageLedger()
    event = UsageEvent(
        event_id="delivery_attempt_77",
        customer_id="creator_42",
        asset_id="launch_film",
        stage=UsageStage.DELIVERY,
        quantity=12_000_000,
        occurred_at=datetime(2026, 9, 17, tzinfo=timezone.utc),
    )

    _, first_accepted = ledger.record(event)
    _, retry_accepted = ledger.record(event)

    usage = ledger.usage_for("creator_42")
    assert first_accepted is True
    assert retry_accepted is False
    assert usage.delivery_bytes == 12_000_000
    assert usage.event_count == 1


def test_event_id_cannot_be_reused_for_another_charge() -> None:
    ledger = UsageLedger()
    timestamp = datetime(2026, 9, 17, tzinfo=timezone.utc)
    ledger.record(UsageEvent("evt_1", "creator_42", "asset_a", UsageStage.PROCESSING, 30, timestamp))

    with pytest.raises(ValueError, match="different event"):
        ledger.record(UsageEvent("evt_1", "creator_42", "asset_a", UsageStage.PROCESSING, 60, timestamp))

