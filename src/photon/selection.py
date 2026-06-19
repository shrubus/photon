"""
Functions that construct (closures) or represent the selection steps.

A selection step receives a collection of paths and apply a specified criterium
to decide which duplicated files should be kept. If a selection step criterum
do not retrieve any file to keep, it returns the full collection (no decision).
"""

from typing import Callable
from pathlib import Path

type Step = Callable[[set[Path]], set[Path]]


def remove_named_copy(dupl_files: set[Path]) -> set[Path]:
    """Return paths that do not have copy in name, or all paths if all have copy in name"""

    if not dupl_files:
        return set()
    files = dupl_files.copy()

    no_named_copy = {p for p in files if "copy" not in p.name.lower()}
    return no_named_copy if no_named_copy else files


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
