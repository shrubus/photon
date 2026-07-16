"""
CLI integration for the image-deduplication pipeline.

Registers the `photon dedupe` command, parses its options, and invokes the
deduplication pipeline according to user-provided arguments. This module
is the boundary between the CLI/UI layer and the pipeline execution layer.

Usage:
  photon dedupe [options] <src> --ref <path> [--trash <path>]
  photon dedupe [options] <src> --intra [--trash <path>]

Options:
  -r, --recursive      deduplicate 'src' directory images recursively
  -a, --auto-select    do not ask user to manually resolve duplicates
  -f, --force          move duplicates to trash without confirmation
  -s, --silent         do not report removed files
      --ref <path>     reference album whose files must always be kept
      --intra          perform intra-album deduplication
      --trash <path>   user-defined trash directory
"""

import argparse
from pathlib import Path

from photon import duplicates
from photon.model import ImgGroup
from photon.duplicates.selection import make_selection_pipeline
from photon.runtime import build_dedupe_config

from .typing import DomainType


def _report_staged_for_removal(resolved: list[ImgGroup]) -> None:
    """Report duplicated files staged for removal"""
    print("\nStaged for removal:\n")
    for img_grp in resolved:
        if files := img_grp.files_to_remove:
            print("\t".join(str(f) for f in files))


def _is_removal_user_approved(resolved: list[ImgGroup]) -> bool:
    """
    Prompt the user to confirm whether duplicate images should be moved to trash.
    Returns True if the user confirms removal, False otherwise.
    """
    if not resolved:
        return False

    answer_to_bool = {"y": True, "n": False}
    usr_msg = ""
    while usr_msg not in answer_to_bool:
        input_msg = "\nDo you want to move image duplicates to trash? (y/n) "
        usr_msg = input(input_msg).strip().lower()
    return answer_to_bool[usr_msg]


def _report_deduplication(args: argparse.Namespace, removed: set[Path]) -> None:
    """Console report of the deduplication process"""
    print("\nFiles removed:\n")
    print("\n".join(str(f) for f in removed))
    print(f"\nalbum: {args.src}")
    if args.ref is not None:
        print(f"reference album: {args.ref}")


def run(args: argparse.Namespace) -> None:
    """Run deduplication pipelines according to cli use instructions"""

    if not (args.ref or args.intra):
        args._parser.error(  # pylint: disable=protected-access
            "\n\nChoose deduplication mode: either inter-album (--ref REF) or intra-album "
            "(--intra)."
            "\n\nThe src directory is always considered an unorganized repository, where image "
            "paths do not hold any information value and may be removed if duplicates exists. "
            "\n\nFiles in the reference directory are never deleted.\n"
        )

    cfg = build_dedupe_config(args)

    resolved = duplicates.resolve(
        src=cfg.src,
        ref_dir=cfg.ref,
        recursive=cfg.recursive,
        group_fn=cfg.group_fn,
        select_fn=make_selection_pipeline(cfg.selectors),
    )

    print(f"\nFound {len(resolved)} images containing duplicates.")

    if not args.silent:
        _report_staged_for_removal(resolved)

    if args.force or _is_removal_user_approved(resolved):
        removed = duplicates.remove(img_grps=resolved, trash=cfg.trash)
        if not args.silent:
            _report_deduplication(args, removed)


def register(domains: DomainType) -> None:
    """
    Register the dedupe domain into domains subparser
    """

    hlp = {
        "r": "deduplicate 'src' directory images recursively",
        "a": "do not ask user to manually resolve image duplicates",
        "f": "move images to trash without user confirmation",
        "silent": "do not report on removed files",
        "src": "source directory containing the images to deduplicate",
        "ref": "reference album directory whose files must always be kept",
        "intra": "explicitly perform intra-album deduplication",
        "trash": "user-defined trash directory",
    }

    dedupe = domains.add_parser("dedupe", help="Remove duplicated images")
    dedupe.add_argument("-r", "--recursive", action="store_true", help=hlp["r"])
    dedupe.add_argument("-a", "--auto-select", action="store_true", help=hlp["a"])
    dedupe.add_argument("-f", "--force", action="store_true", help=hlp["f"])
    dedupe.add_argument("-s", "--silent", action="store_true", help=hlp["silent"])
    dedupe.add_argument("src", type=Path, help=hlp["src"])

    mode = dedupe.add_mutually_exclusive_group()
    mode.add_argument("--ref", type=Path, help=hlp["ref"])
    mode.add_argument("--intra", action="store_true", help=hlp["intra"])

    dedupe.add_argument("--trash", type=Path, help=hlp["trash"])

    dedupe.set_defaults(run=run, _parser=dedupe)
