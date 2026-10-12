"""Pure marketplace handoff decision used by the HTTP service and tests."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class SellerAsset:
    asset_id: str
    seller_id: str
    state: Literal["ready", "quarantined"]


@dataclass(frozen=True)
class BuyerUpdate:
    buyer_id: str
    revision: int
    approved: bool


@dataclass(frozen=True)
class OrderHandoff:
    order_id: str
    asset: SellerAsset
    buyer_update: BuyerUpdate


@dataclass(frozen=True)
class HandoffResult:
    order_id: str
    state: Literal["handed_off", "review_required"]
    attempt_count: int


def _capture_key(request: OrderHandoff) -> str:
    material = f"{request.order_id}:{request.buyer_update.revision}:handoff"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def handoff_order(
    request: OrderHandoff,
    capture: Callable[[str], dict],
    *,
    max_attempts: int = 2,
) -> HandoffResult:
    """Attempt the transition and record each rejected agent decision."""
    for attempt in range(1, max_attempts + 1):
        reason = ""
        if request.asset.state != "ready":
            reason = "seller asset is quarantined"
        elif not request.buyer_update.approved:
            reason = "buyer update needs approval"
        else:
            return HandoffResult(request.order_id, "handed_off", attempt)

        event = (
            f"marketplace handoff failed; order={request.order_id}; "
            f"asset={request.asset.asset_id}; seller={request.asset.seller_id}; "
            f"buyer={request.buyer_update.buyer_id}; "
            f"revision={request.buyer_update.revision}; attempt={attempt}; reason={reason}"
        )
        capture(f"{_capture_key(request)}; {event}")

    return HandoffResult(request.order_id, "review_required", max_attempts)
