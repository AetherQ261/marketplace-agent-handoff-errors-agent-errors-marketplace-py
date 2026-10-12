"""Typed service for seller-to-buyer AI order handoff."""

from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from infrai import InfraiClient, InfraiError, InfraiTransportError
from marketplace_handoff import (
    BuyerUpdate as DomainBuyerUpdate,
    OrderHandoff,
    SellerAsset as DomainSellerAsset,
    handoff_order,
)


class SellerAsset(BaseModel):
    asset_id: str = Field(min_length=1)
    seller_id: str = Field(min_length=1)
    state: Literal["ready", "quarantined"]


class BuyerUpdate(BaseModel):
    buyer_id: str = Field(min_length=1)
    revision: int = Field(ge=1)
    approved: bool


class OrderHandoffRequest(BaseModel):
    order_id: str = Field(min_length=1)
    asset: SellerAsset
    buyer_update: BuyerUpdate


class OrderHandoffResult(BaseModel):
    order_id: str
    state: Literal["handed_off", "review_required"]
    attempt_count: int


app = FastAPI(title="Marketplace agent handoff")


@app.post("/handoffs", response_model=OrderHandoffResult)
def create_handoff(request: OrderHandoffRequest) -> OrderHandoffResult:
    try:
        domain_request = OrderHandoff(
            order_id=request.order_id,
            asset=DomainSellerAsset(**request.asset.model_dump()),
            buyer_update=DomainBuyerUpdate(**request.buyer_update.model_dump()),
        )
        infrai = InfraiClient()
        result = handoff_order(
            domain_request,
            lambda exception: infrai.errors.capture(exception=exception),
        )
        return OrderHandoffResult(
            order_id=result.order_id,
            state=result.state,
            attempt_count=result.attempt_count,
        )
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=client_status, detail=exc.detail) from exc
    except InfraiTransportError as exc:
        raise HTTPException(status_code=502, detail="failure tracking request failed") from exc
