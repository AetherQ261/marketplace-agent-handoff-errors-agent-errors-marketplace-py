"""Send one approved marketplace handoff to the local service."""

import json

import requests


REQUEST = {
    "order_id": "ord-health-204",
    "asset": {
        "asset_id": "asset-lab-summary",
        "seller_id": "seller-17",
        "state": "ready",
    },
    "buyer_update": {
        "buyer_id": "buyer-care-team",
        "revision": 3,
        "approved": True,
    },
}


def main() -> None:
    response = requests.request(
        method="POST",
        url="http://127.0.0.1:8000/handoffs",
        json=REQUEST,
        timeout=10,
    )
    response.raise_for_status()
    print(json.dumps(response.json(), indent=2))


if __name__ == "__main__":
    main()
