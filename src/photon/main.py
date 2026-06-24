"""Entrypoint"""

from pathlib import Path
from importlib.metadata import version
import argparse
from pprint import pprint

from photon.io import get_images
from photon.pipeline import dedupe_pipeline
from photon.detection import hash_signature
from photon.selection import select_from_album, remove_named_copy, ask_user


def dedupe_albums(args: argparse.Namespace) -> None:
    """
    Deduplicate images according to CLI arguments.

    - If no reference album is provided, perform intra-album deduplication on the
      source directory only, unless user pass "--recursive" flag.

    - If a reference album is provided, first recursively remove files in the source directory
      that also appear in the reference album (cross-album deduplication). After
      cross-album removal, perform intra-album deduplication within both the source
      and the reference directories.


    """

    # Collect images
    images: set[Path] = set()
    if args.ref is not None:
        images.update(get_images(args.src, recursive=True))
        images.update(get_images(args.ref, recursive=True))
    else:
        images.update(get_images(args.src, recursive=args.recursive))

    # Dedupe
    removed = dedupe_pipeline(
        images=images,
        sig_fn=hash_signature,
        criteria=[
            select_from_album(ref_album=args.ref),
            remove_named_copy,
            ask_user,
        ],
        trash=Path("./data/trash"),
    )

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

    dedupe = domains.add_parser("dedupe", help="Remove duplicate images")
    dedupe.add_argument("src", type=Path)
    dedupe.add_argument("-s", "--silent", action="store_true", help="Do not print removed files")
    recursive_group = dedupe.add_mutually_exclusive_group()
    recursive_group.add_argument("--ref", nargs="?", type=Path)
    recursive_group.add_argument("-r", "--recursive", action="store_true")
    dedupe.set_defaults(func=dedupe_albums)

    return argparser


def main() -> None:
    """Temporary cross-directory deduplication entrypoint"""

    cli_argparser = build_cli_argparser()
    args = cli_argparser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
