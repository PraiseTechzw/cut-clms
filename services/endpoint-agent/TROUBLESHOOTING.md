# Troubleshooting

## The inventory contains warnings

Collectors run without assuming administrator privileges. Missing DMI values,
restricted device identifiers, unavailable package-manager tools, inaccessible
mounts, or unsupported operating-system details may be reported as warnings.
Other collector results are still returned when one source is unavailable.

## Installed software is empty on Linux

Linux enumeration currently uses `dpkg-query` or `rpm` when available. If
neither utility is installed or its query fails, the inventory includes a
software warning instead of scanning the filesystem.

## The command is not found

Synchronize the endpoint-agent project with `uv sync --directory
services/endpoint-agent`, then invoke it with `uv run --directory
services/endpoint-agent cut-cea inventory`.

## Connectivity or service installation

The current stage has no network client or service installer. Enrollment,
heartbeat, Windows service, systemd, and packaging instructions will be added
with those later stages.
