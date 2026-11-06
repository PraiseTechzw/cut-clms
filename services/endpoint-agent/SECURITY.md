# Security

## Current behavior

- Inventory is collected only after a local operator invokes the command.
- The agent performs no network communication, enrollment, or remote execution.
- It does not collect passwords, keystrokes, or personal files.
- The machine identifier is hashed before inclusion in inventory; the raw
  Windows MachineGuid/Linux machine-id is not emitted.
- Collector failures are represented as warnings instead of preventing the
  remaining local inventory from being returned.

Inventory includes potentially sensitive host, network, and installed-software
metadata. Protect the JSON output according to university policy and do not
publish it in logs or source control. The hashed device identifier is stable
and remains linkable across inventory runs.

## Required before deployment

Secure enrollment and per-device credentials, protected local configuration,
HTTPS API communication with validated responses and request timeouts, retry
and offline recovery, signed updates, administrative-action logging, and
allowlisted non-shell command handling are not implemented. No shared
university secret may be embedded in the agent. Remote shell execution is not
part of the design.
