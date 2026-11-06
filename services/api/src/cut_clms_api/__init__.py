"""CUT-CLMS API package."""

__version__ = "0.1.0"


def main() -> None:
    from cut_clms_api.cli import main as cli_main

    cli_main()
