from marketplace_handoff import BuyerUpdate, OrderHandoff, SellerAsset, handoff_order


class RecordingTracker:
    def __init__(self) -> None:
        self.events: list[dict[str, str]] = []
    def capture(self, exception: str) -> dict:
        self.events.append({"exception": exception})
        return {"event_id": f"event-{len(self.events)}"}


def test_unapproved_buyer_update_is_captured_before_review() -> None:
    request = OrderHandoff(
        order_id="ord-71",
        asset=SellerAsset("asset-care-plan", "seller-4", "ready"),
        buyer_update=BuyerUpdate("buyer-9", 2, False),
    )
    tracker = RecordingTracker()

    result = handoff_order(request, tracker.capture, max_attempts=2)

    assert result.state == "review_required"
    assert result.attempt_count == 2
    assert len(tracker.events) == 2
    assert "buyer update needs approval" in tracker.events[0]["exception"]
    assert "attempt=1" in tracker.events[0]["exception"]
    assert "attempt=2" in tracker.events[1]["exception"]
