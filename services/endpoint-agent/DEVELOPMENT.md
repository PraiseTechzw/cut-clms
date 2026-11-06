# Development

## Requirements

- Python 3.12+
- `uv`

## Setup and checks

From the repository root:

```sh
uv sync --directory services/endpoint-agent
uv run --directory services/endpoint-agent pytest
uv run --directory services/endpoint-agent ruff check .
uv run --directory services/endpoint-agent ruff format --check .
uv run --directory services/endpoint-agent mypy
```

Tests mock operating-system data and must not require administrator privileges,
live services, or access to a university backend. Keep platform-specific
collection best effort and report unavailable data through inventory warnings.

## Scope

This stage is local discovery and inventory only. Add API communication only
after coordinating contracts with the API project. Keep service lifecycle,
packaging, and update work in their later implementation stages.
