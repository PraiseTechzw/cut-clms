import argparse
import json
from pathlib import Path
from typing import Any

from cut_clms_api.main import app


def build_schema() -> dict[str, Any]:
    return app.openapi()


def main() -> None:
    parser = argparse.ArgumentParser(description="Export CUT-CLMS API OpenAPI schema")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rendered = json.dumps(build_schema(), indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
