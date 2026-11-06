# Installation

## Current development-stage setup

The endpoint agent currently supports local inventory collection on Python
3.12+ with `uv`. From the repository root, synchronize dependencies and run:

```sh
uv sync --directory services/endpoint-agent
uv run --directory services/endpoint-agent cut-cea inventory
```

The command prints the inventory to standard output as JSON. It does not install
a service or make a network connection. Do not deploy this development-stage
command as a managed university service.

## Not yet available

Windows service installation, Linux systemd units, startup integration,
PyInstaller builds, and operating-system package installers will be delivered
in a later stage.
