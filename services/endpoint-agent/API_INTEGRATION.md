# API integration

No API endpoint, payload contract, or authentication protocol is implemented
or assumed in this stage. The inventory output is a local Pydantic model and
is not yet an agreed backend wire format.

Before implementing enrollment or heartbeat, coordinate with the CUT-CLMS API
project on endpoint paths, schemas, device identity and credential lifecycle,
error responses, TLS requirements, timeouts, and compatibility/versioning.
Only then add the HTTPX communication layer and contract tests.
