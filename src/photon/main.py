"""Entrypoint"""

from pathlib import Path
from importlib.metadata import version
import argparse
from pprint import pprint

from photon.io import get_images
from photon.detection import group_equal_by_hash
from photon.selection import make_selection_pipeline, remove_filename_with, ask_user, Control
from photon.dedupe import dedupe


def dedupe_albums(args: argparse.Namespace) -> None:
    """
    Deduplicate images according to CLI arguments.

    - If no reference album is provided, perform intra-album deduplication on the
      source directory only, unless user pass "--recursive" flag.

    - If a reference album is provided, recursively remove files in the source directory
      that also appear in the reference album (cross-album deduplication) which remains
      untouched.
    """

    # Collect images
    images: set[Path] = set()
    if args.ref is not None:
        images.update(get_images(args.src, recursive=True))
        images.update(get_images(args.ref, recursive=True))
    else:
        images.update(get_images(args.src, recursive=args.recursive))

    # Selection
    control = Control(skip_all=False)
    selection_pipeline = make_selection_pipeline(
        steps=[
            remove_filename_with("copy"),
            ask_user(control),
        ]
    )

    # Dedupe
    removed = dedupe(
        images=images,
        ref_dir=args.ref,
        group_fn=group_equal_by_hash,
        selection_pipeline=selection_pipeline,
        trash=Path("./data/trash"),
    )

    # Console Report
    if not args.silent:
        pprint(removed)
        print(f"albums = {args.src}")
        if args.ref is not None:
            print(f"ref_album = {args.ref}")


def build_cli_argparser() -> argparse.ArgumentParser:
    """Construct the top-level CLI parser and register all command groups."""

    argparser = argparse.ArgumentParser(
        prog="photon",
        description="Photo deduplication tool",
    )

    argparser.add_argument("-v", "--version", action="version", version=version("photon"))
    domains = argparser.add_subparsers(dest="domain", required=True, metavar="COMMAND")

    dedupe_cmd = domains.add_parser("dedupe", help="Remove duplicate images")
    dedupe_cmd.add_argument("src", type=Path)
    dedupe_cmd.add_argument(
        "-s", "--silent", action="store_true", help="Do not print removed files"
    )
    recursive_group = dedupe_cmd.add_mutually_exclusive_group()
    recursive_group.add_argument(
        "--ref", nargs="?", type=Path, help="Reference album whose files must always be kept"
    )
    recursive_group.add_argument("-r", "--recursive", action="store_true")
    dedupe_cmd.set_defaults(func=dedupe_albums)

    return argparser


def main() -> None:
    """Temporary cross-directory deduplication entrypoint"""

    cli_argparser = build_cli_argparser()
    args = cli_argparser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
