"""Orchestration of image deduplication"""

from pathlib import Path

from .io import move_to_trash
from .detection import GroupFn
from .selection import Step


def dedupe(
    images: set[Path],
    ref_dir: Path | None,
    group_fn: GroupFn,
    selection_pipeline: Step,
    trash: Path,
) -> set[Path]:
    """
    Find duplicates, select files to remove, move selected files to a denominated
    trash directory, and return list of paths removed
    """

    removed = set()
    img_groups = group_fn(images, ref_dir)
    for img_group in img_groups:
        selection_pipeline(img_group)
        for file in img_group.files_to_remove:
            move_to_trash(trash, file)
            removed.add(file)

    return removed
