import argparse
import json

from cut_clms_endpoint_agent.inventory import collect_inventory


def main() -> int:
    parser = argparse.ArgumentParser(description="CUT-CLMS endpoint inventory agent")
    parser.add_argument(
        "command",
        choices=["inventory"],
        help="Collect local device inventory and print it as JSON",
    )
    args = parser.parse_args()

    if args.command == "inventory":
        inventory = collect_inventory()
        print(json.dumps(inventory.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0
