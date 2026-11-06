# CUT Endpoint Agent (CUT-CEA)

CUT-CEA is the authorized university workstation inventory agent. This first
stage implements local, best-effort device discovery for Windows and Linux.
It collects inventory only when explicitly run; it does not enroll, contact a
server, run as a background service, or accept remote commands.

## Current functionality

- Host identity, operating system, CPU, memory, mounted storage, network
  interfaces, installed software, and basic system health.
- A stable, one-way hash of the Windows MachineGuid or Linux machine-id when
  the identifier is readable. The source identifier is not included in output.
- Typed Pydantic inventory models, JSON output, and explicit warnings for
  information that could not be collected.

Run locally with `uv run --directory services/endpoint-agent cut-cea inventory`.
The inventory can include machine identifiers, IP/MAC addresses, and software
names; handle the output as sensitive institutional data.

See [INSTALLATION.md](./INSTALLATION.md), [CONFIGURATION.md](./CONFIGURATION.md),
[SECURITY.md](./SECURITY.md), [DEVELOPMENT.md](./DEVELOPMENT.md),
[API_INTEGRATION.md](./API_INTEGRATION.md), and
[TROUBLESHOOTING.md](./TROUBLESHOOTING.md).

## Planned stages and current limitations

Secure enrollment, device credentials, heartbeat and inventory upload, retry
and offline buffering, protected configuration, structured agent logging,
service lifecycle integration, signed updates, and installable Windows/Linux
packages are not implemented. API paths and request/response contracts must be
coordinated with the CUT-CLMS API project before communication is added.
Serial number, manufacturer, and model collection is best effort; Linux DMI
data may be permission restricted, and Windows hardware details are not yet
collected. Unsupported platforms produce warnings where appropriate.
