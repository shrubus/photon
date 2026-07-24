"""
Orchestration layer of the image deduplication pipelines

This layer prepares the two main execution steps:

(1) resolution of duplicate images (pure, no side effects)
(2) moving selected files to a trash directory (filesystem side effects)
"""

from pathlib import Path

from photon.io import load_files, move_to_trash
from photon.image import filter_images, by_suffix
from photon.model import ImgGroup
from photon.duplicates.detection import GroupFn
from photon.duplicates.selection import SelectFn


def resolve(
    src: Path, ref_dir: Path | None, recursive: bool, group_fn: GroupFn, select_fn: SelectFn
) -> list[ImgGroup]:
    """
    Resolve duplicate images in a source directory using a configurable pipeline.

    Images are loaded from `src` (recursively if `recursive` is True). If `ref_dir`
    is provided, all images in that directory (always loaded recursively) are added
    to the deduplication set and treated as protected: they participate in duplicate
    detection but are never deleted.

    Duplicate detection is performed by the provided `group_fn`, which groups images
    into `ImgGroup` instances according to the chosen strategy.

    Selection of files for deletion within each group of duplicated images is performed
    by `select_fn`, which may be a single function or a chained pipeline of multiple
    selection steps.

    Returns:
        A list of `ImgGroup` objects representing all detected duplicate groups,
        each annotated with survivor and removal decisions applied by `select_fn`.
    """

    paths = load_files(src, recursive)
    images = filter_images(paths, key=by_suffix)
    if ref_dir is not None:
        images.update(load_files(ref_dir, recursive=True))

    img_grps = group_fn(images, ref_dir)
    for img_grp in img_grps:
        select_fn(img_grp)

    return img_grps


def remove(img_grps: list[ImgGroup], trash: Path) -> set[Path]:
    """
    Move all files marked for removal in each `ImgGroup` to a trash directory.

    The function first asks the user for confirmation. If removal is declined,
    no filesystem changes are made and an empty set is returned.

    Returns:
        A set of `Path` objects representing all files successfully moved to trash.
    """

    removed: set[Path] = set()

    for img_grp in img_grps:
        for file in img_grp.files_to_remove:
            move_to_trash(file, trash)
            removed.add(file)

    return removed
