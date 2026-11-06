# CUT-CLMS API

The CUT-CLMS API is the central FastAPI service. Its first functional slice is
the secure endpoint-agent integration contract under `/api/v1/endpoints`.

## Endpoint integration

- `POST /api/v1/endpoints/enroll`: consumes a one-time institutional
  enrollment token and returns a one-time device bearer credential.
- `POST /api/v1/endpoints/heartbeat`: authenticates a device credential and
  records health, agent version, and last-seen time.
- `POST /api/v1/endpoints/inventory`: authenticates a device credential and
  stores a validated inventory snapshot, software list, and health sample.

The API stores only hashes of enrollment tokens and device credentials. The
returned device credential is not recoverable and must be persisted securely
by the agent. The API does not provide remote shell or command execution.
See [API_INTEGRATION.md](./API_INTEGRATION.md) for request/response details.

## Local development

Configure `CUT_API_DATABASE_URL` and apply migrations:

```sh
uv sync --directory services/api
uv run --directory services/api alembic upgrade head
uv run --directory services/api uvicorn cut_clms_api.main:app --reload
```

OpenAPI is served at `/docs`; the JSON contract is at `/openapi.json`. Unit and
integration tests use isolated SQLite databases:

```sh
uv run --directory services/api pytest
uv run --directory services/api ruff check .
uv run --directory services/api ruff format --check .
uv run --directory services/api mypy
```

Create an institution and a short-lived, single-use enrollment token using the
operator CLI after applying migrations:

```sh
uv run --directory services/api cut-clms-api create-institution \
  --name "CUT" --code "CUT"
uv run --directory services/api cut-clms-api create-enrollment-token \
  --institution-id <institution-uuid> --expires-in-hours 24
uv run --directory services/api cut-clms-api revoke-endpoint \
  --endpoint-id <endpoint-uuid>
```

The token is printed once. Deliver it to the authorized endpoint through a
trusted provisioning channel; do not put it in source control, configuration
logs, or command-line arguments on the endpoint. The institution UUID is
printed by `create-institution`.

Revoking an endpoint invalidates its current credential and records an audit
event. A revoked device can re-enroll with a new token scoped to the same
institution, rotating its credential while retaining inventory history.

## Foundations and limitations

The database has institution-scoped departments, laboratories, computer
assets, institutional users, roles, endpoints, inventory, telemetry, token,
and audit tables. Human bearer-token verification is an RS256/OIDC-compatible
foundation requiring an externally issued token and configured public key,
issuer, and audience; this stage does not implement a login or user-management
API. Role checks are available to future human routes.

Endpoint API rate limiting is currently in-memory and per process. Use a
single API worker or add a shared limiter before horizontal scaling. TLS must
be enforced at the deployment ingress. Human-facing list APIs, pagination and
filtering, administrative audit views, credential rotation/revocation
workflows, and business-platform workflows are outside this endpoint-first
stage. PostgreSQL migrations are defined; CI tests currently exercise them
through SQLite-compatible metadata and do not replace testing against the
deployment PostgreSQL version.
