from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .infrai_usage import InfraiError, InfraiUsageClient
from .usage_ledger import UsageEvent, UsageLedger, UsageStage


class MeterEventRequest(BaseModel):
    event_id: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    asset_id: str = Field(min_length=1)
    stage: UsageStage
    quantity: int = Field(gt=0)
    occurred_at: datetime


class MeterEventResponse(BaseModel):
    accepted: bool
    event_id: str


class CustomerUsageResponse(BaseModel):
    customer_id: str
    ingestion_bytes: int
    processing_seconds: int
    delivery_bytes: int
    event_count: int


class ReconciliationResponse(BaseModel):
    account_usage: dict[str, Any]
    account_timeseries: dict[str, Any]


ledger = UsageLedger()
app = FastAPI(title="Media customer usage meter")


@app.post("/meter/events", response_model=MeterEventResponse)
def meter_event(payload: MeterEventRequest) -> MeterEventResponse:
    try:
        event, accepted = ledger.record(UsageEvent(**payload.model_dump()))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return MeterEventResponse(accepted=accepted, event_id=event.event_id)


@app.get("/customers/{customer_id}/usage", response_model=CustomerUsageResponse)
def customer_usage(customer_id: str) -> CustomerUsageResponse:
    return CustomerUsageResponse(**ledger.usage_for(customer_id).__dict__)


@app.get("/reconciliation/infrai", response_model=ReconciliationResponse)
def reconcile_infrai() -> ReconciliationResponse:
    try:
        client = InfraiUsageClient()
        return ReconciliationResponse(
            account_usage=client.account_usage(),
            account_timeseries=client.account_usage_timeseries(),
        )
    except KeyError as exc:
        raise HTTPException(status_code=503, detail="INFRAI_API_KEY is required") from exc
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=client_status, detail=exc.detail) from exc
    except (ConnectionError, RuntimeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail="Usage reconciliation could not complete") from exc
