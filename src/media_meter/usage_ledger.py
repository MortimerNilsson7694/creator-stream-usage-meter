from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from threading import Lock


class UsageStage(StrEnum):
    INGESTION = "ingestion"
    PROCESSING = "processing"
    DELIVERY = "delivery"


@dataclass(frozen=True)
class UsageEvent:
    event_id: str
    customer_id: str
    asset_id: str
    stage: UsageStage
    quantity: int
    occurred_at: datetime


@dataclass(frozen=True)
class CustomerUsage:
    customer_id: str
    ingestion_bytes: int
    processing_seconds: int
    delivery_bytes: int
    event_count: int


class UsageLedger:
    """An in-process ledger with idempotent event recording."""

    def __init__(self) -> None:
        self._events: dict[str, UsageEvent] = {}
        self._lock = Lock()

    def record(self, event: UsageEvent) -> tuple[UsageEvent, bool]:
        if event.quantity <= 0:
            raise ValueError("quantity must be greater than zero")
        if not event.event_id.strip():
            raise ValueError("event_id is required")

        normalized = event
        if event.occurred_at.tzinfo is None:
            normalized = UsageEvent(
                event_id=event.event_id,
                customer_id=event.customer_id,
                asset_id=event.asset_id,
                stage=event.stage,
                quantity=event.quantity,
                occurred_at=event.occurred_at.replace(tzinfo=timezone.utc),
            )

        with self._lock:
            existing = self._events.get(normalized.event_id)
            if existing is not None:
                if existing != normalized:
                    raise ValueError("event_id already belongs to a different event")
                return existing, False
            self._events[normalized.event_id] = normalized
        return normalized, True

    def usage_for(self, customer_id: str) -> CustomerUsage:
        events = [event for event in self._events.values() if event.customer_id == customer_id]
        totals = {stage: 0 for stage in UsageStage}
        for event in events:
            totals[event.stage] += event.quantity
        return CustomerUsage(
            customer_id=customer_id,
            ingestion_bytes=totals[UsageStage.INGESTION],
            processing_seconds=totals[UsageStage.PROCESSING],
            delivery_bytes=totals[UsageStage.DELIVERY],
            event_count=len(events),
        )

