"""Algorithms to find duplicated images"""

from pathlib import Path
from hashlib import md5
from collections.abc import Callable, Hashable

type ImgSigFn = Callable[[Path], Hashable]
type SigGroupMap = dict[Hashable, set[Path]]


def hash_signature(file: Path, chunk_size: int = 1024 * 1024) -> str:
    """
    Compute a file hash incrementally in fixed-size chunks,
    without loading the entire file into memory.
    """

    h = md5()
    with open(file, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def group_duplicates(files: set[Path], sig_fn: ImgSigFn) -> SigGroupMap:
    """
    Find duplicated files in a set of paths using `sig_fn` to compute a signature
    for each file.
    """

    sig_groups: SigGroupMap = {}

    for path in files:
        if path.is_file(follow_symlinks=False):
            sig = sig_fn(path)
            sig_groups.setdefault(sig, set()).add(path)

    return {sig: group for sig, group in sig_groups.items() if len(group) > 1}
