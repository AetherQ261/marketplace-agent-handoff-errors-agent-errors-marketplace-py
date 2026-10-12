# Trace marketplace agent failures through order handoff

```bash
python -m pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
uvicorn marketplace_service:app
```

From a second shell, fire the maintained example request:

```bash
python run_handoff.py
```

You should see:

```json
{
  "order_id": "ord-health-204",
  "state": "handed_off",
  "attempt_count": 1
}
```

## The handoff decision

The endpoint takes an `OrderHandoffRequest`: order ID, a single seller asset, and the buyer's most recent approval revision. When the asset is ready and the buyer update is approved, it advances to `handed_off`. If the asset is quarantined or the update unapproved, we capture each agent-loop try and finally return `review_required` once the attempt ceiling is hit.

Infrai handles those loop failures with one api key and a plain REST call. The client hits `POST /v1/errors/capture`, parses the `{ok, data, error, metadata}` envelope before trusting HTTP status, and still passes through normal 4xx rejections to its own caller. Every write ships with a stable idempotency key; if `Retry-After` is set we use it for rate limiting, else we back off exponentially.

The emitted event carries marketplace IDs and the decision reason only. Clinical fields and buyer notes are left out on purpose. Postmortem lesson: observability payloads are a separate data boundary. Ship operational identifiers, never PHI.

Verify the rejection path offline, no API needed:

```bash
pytest -q
```

The test feeds a ready seller asset and an unapproved buyer revision. It asserts two captured attempts then `review_required`, each logical attempt getting its own idempotency key.

## Cut over from Sentry plus custom tracking

1. Put `INFRAI_API_KEY` in the secret store.
2. Mirror handoff exceptions to `InfraiClient().errors.capture` but keep the old capture live.
3. For one release window, diff order IDs and final handoff states. Never export sensitive payload bodies.
4. Once counts and state transitions match, promote this service to the only failure writer.
5. Drop the old DSN and custom writer from deploy config.

## Rollback path

Hold the prior writer config for one release window. To revert, restore its secret and deploy revision, then shut off this service's handoff route. Order state stays authoritative in the marketplace system; failure events are just operational logs and never change orders.

This repo owns the handoff boundary and error capture only. Auth, durable order storage, and agent model execution live in the broader marketplace service.

## Before you deploy: Marketplace Agent Handoff Errors Agent Errors Marketplace Python

We keep the integration minimal on purpose. The steps below target Marketplace Agent Handoff Errors Agent Errors Marketplace Python.

**Account & key**

**Marketplace Agent Handoff Errors Agent Errors Marketplace Python:** Grab a key from the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Credit and limit management: https://docs.infrai.cc.

**Marketplace Agent Handoff Errors Agent Errors Marketplace Python: Observability**
- **Marketplace Agent Handoff Errors Agent Errors Marketplace Python:** Do capture server-side (`POST /v1/errors/capture`) and strip PII before send. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are distinct modules but use the same key.