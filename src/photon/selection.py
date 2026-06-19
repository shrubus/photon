"""
Functions that construct (closures) or represent the selection steps.

A selection step receives a collection of paths and apply a specified criterium
to decide which duplicated files should be kept. If a selection step criterum
do not retrieve any file to keep, it returns the full collection (no decision).
"""

from collections import Counter
from typing import Callable
from pathlib import Path

from .core import _clean_image_suffix
from .io import select_images

type Step = Callable[[set[Path]], set[Path]]


def get_earliest(dupl_files: set[Path]) -> set[Path]:
    """
    IMPORTANT:
    This deduplication step is not currently used in any active deduplication pipeline.
    The heuristics is intentionally weak and should only be applied for unsupervised
    cleanup of a "photo dump" directory, where filesystem metadata is irrelevant
    (e.g. directory structure, naming conventions).

    Return all filepaths with the earliest modification time"""

    if not dupl_files:
        return set()
    files = dupl_files.copy()

    mtimes: list[tuple[float, Path]]  # [<modification time epoch>,<filepath>]
    mtimes = [(p.stat(follow_symlinks=False).st_mtime, p) for p in files]

    earliest_time = min(t for t, _ in mtimes)
    return {p for t, p in mtimes if t == earliest_time}


def remove_named_copy(dupl_files: set[Path]) -> set[Path]:
    """Return paths that do not have copy in name, or all paths if all have copy in name"""

    if not dupl_files:
        return set()
    files = dupl_files.copy()

    no_named_copy = {p for p in files if "copy" not in p.name.lower()}
    return no_named_copy if no_named_copy else files


def select_by_most_common_size(pct: float) -> Step:
    """
    IMPORTANT:
    This deduplication step is not currently used in any active deduplication pipeline.
    The heuristics is intentionally weak and should only be applied for unsupervised
    cleanup of a "photo dump" directory, where filesystem metadata is irrelevant
    (e.g. directory structure, naming conventions).

    Select files whose filename length matches the dominant camera filename length,
    for the same image file format (using files extension as heuristics).

    If no dominant length exists (below pct threshold), return all files unchanged.
    """

    if pct > 1 or pct < 0.5:
        raise ValueError(f"pct threshold not in [0.5, 1]: {pct}")

    def step(dupl_files: set[Path]) -> set[Path]:

        if not dupl_files:
            return set()
        files = dupl_files.copy()

        # duplicated images should share the same file extension
        suffixes = {_clean_image_suffix(p.suffix) for p in files}
        if len(suffixes) > 1:
            return files
        suffix = next(iter(suffixes))

        parents = {p.parent for p in files}
        img_paths = [
            img for img in select_images(*parents) if _clean_image_suffix(img.suffix) == suffix
        ]

        if not img_paths:
            return files

        counter = Counter(len(p.name) for p in img_paths)
        if not counter:
            return files

        # Most common length among the duplicates
        ((length, count),) = counter.most_common(1)

        # Require dominance (e.g., 80% of duplicates share this length)
        if count < pct * counter.total():
            return files

        # Filter by dominant length
        filtered = {p for p in files if len(p.name) == length}
        return filtered if filtered else files

    return step


def select_from_album(ref_album: Path | None) -> Step:
    """
    Return the paths of a duplicated image that are in a reference directory (`ref_album`),
    or all paths if none of the paths are in the directory.
    """
    if ref_album is not None:
        if not ref_album.exists() or not ref_album.is_dir(follow_symlinks=False):
            raise ValueError(f"Reference album should be a directory: {ref_album}")

    def step(dupl_files: set[Path]) -> set[Path]:

        if ref_album is None:
            return dupl_files

        if not dupl_files:
            return set()

        files = dupl_files.copy()
        in_album = {f for f in files if f.is_relative_to(ref_album)}
        return in_album if in_album else files

    return step


def ask_user(dupl_files: set[Path]) -> set[Path]:
    """
    Return user selected path from a set of paths of duplicated images,
    or all paths if use skips deduplication
    """

    if not dupl_files:
        return set()
    files = list(dupl_files)

    msg = "Found the following duplicated images:\n"
    msg += "\n".join(f"{i}: {p}" for i, p in enumerate(files))
    msg += "\nType the number of the file to keep or 's' to skip: "

    try:
        idx = int(input(msg))
        return {files[idx]}
    except (ValueError, IndexError):
        return set(files)
