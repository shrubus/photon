"""
Top-level CLI entrypoint for the `photon` command.

Constructs the main argument parser, registers all domain commands, parses
user input, and dispatches execution to the selected domain handler.
"""

from importlib.metadata import version
import argparse

from . import dedupe


def build_cli_argparser() -> argparse.ArgumentParser:
    """Construct the top-level CLI parser and register all command groups."""

    argparser = argparse.ArgumentParser(
        prog="photon",
        description="Photo organization suit",
    )

    argparser.add_argument("-v", "--version", action="version", version=version("photon"))
    domains = argparser.add_subparsers(dest="domain", required=True, metavar="COMMAND")

    dedupe.register(domains)

    return argparser


def main() -> None:
    """Temporary cross-directory deduplication entrypoint"""

    cli_argparser = build_cli_argparser()
    args = cli_argparser.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
