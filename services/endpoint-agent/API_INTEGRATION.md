# API integration

The API integration contract is defined in
[`../api/API_INTEGRATION.md`](../api/API_INTEGRATION.md). Version 1 provides
only the following endpoint-agent paths:

- `POST /api/v1/endpoints/enroll`, with a one-time enrollment token and the
  local inventory object, returns the per-device bearer credential once.
- `POST /api/v1/endpoints/heartbeat`, with the per-device bearer credential,
  agent version, and health data.
- `POST /api/v1/endpoints/inventory`, with the per-device bearer credential
  and complete local inventory object.

The API stores hashes of both enrollment tokens and device credentials; the
agent must protect the returned device credential locally. All requests must
use HTTPS outside local development. The HTTPX client and protected credential
storage are not yet implemented in this agent stage.
