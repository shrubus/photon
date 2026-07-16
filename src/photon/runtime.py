"""
Runtime configuration utilities.

Provides configuration objects and factories that translate UI or CLI arguments
into the settings required by higher-level pipeline modules. Each pipeline
domain exposes its own configuration class.
"""

from pathlib import Path
from dataclasses import dataclass
import argparse

# from .model import ImgGroup
from .duplicates.detection import GroupFn
from .duplicates.selection import SelectFn

# import defaults:
from .duplicates.detection import group_equal_by_hash
from .duplicates.selection import remove_filename_with, ask_user


@dataclass(frozen=True)
class DedupeConfig:
    """Runtime configuration for the image-deduplication settings exposed to the UI layer"""

    src: Path
    ref: Path | None
    recursive: bool
    group_fn: GroupFn
    trash: Path
    selectors: list[SelectFn]


def build_dedupe_config(args: argparse.Namespace) -> DedupeConfig:
    """
    Runtime configuration factory for image-deduplication: sets the default grouping
    method, selection criteria and trash directory for removing duplicated images
    """

    group_fn = getattr(args, "group_fn", None) or group_equal_by_hash
    trash = args.trash or (Path.cwd() / ".trash")
    default_selectors = [
        remove_filename_with("copy"),
        ask_user(args.auto_select),
    ]
    selectors = getattr(args, "selectors", None) or default_selectors

    cfg = DedupeConfig(
        src=args.src,
        ref=args.ref,
        recursive=args.recursive,
        group_fn=group_fn,
        trash=trash,
        selectors=selectors,
    )

    return cfg
