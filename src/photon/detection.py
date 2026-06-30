"""Algorithms to find duplicated images"""

from pathlib import Path
from hashlib import md5
from collections.abc import Callable
from typing import Protocol

from .model import ImgGroup, Signature


class GroupFn(Protocol):  # pylint: disable=too-few-public-methods
    """Protocol that defines image grouping functions signature"""

    def __call__(self, images: set[Path], ref_dir: Path | None) -> list[ImgGroup]:
        pass


type ImgSigFn = Callable[[Path], Signature]


def _get_file_hash(filepath: Path, chunk_size: int = 1024 * 1024) -> int:
    """
    Compute a file hash incrementally in fixed-size chunks,
    without loading the entire file into memory.
    """

    h = md5()
    with open(filepath, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return int(h.hexdigest(), 16)


def _group_equal(images: set[Path], ref_dir: Path | None, img_sig_fn: ImgSigFn) -> list[ImgGroup]:
    """
    Group files with the same file signature computed using `img_sig_fn`.
    Each group receives the shared signature as its group identifier.
    Return only groups containing more than one file.
    """

    groups: dict[Signature, ImgGroup] = {}

    for filepath in images:
        if filepath.is_file(follow_symlinks=False):
            signature = img_sig_fn(filepath)
            groups.setdefault(signature, ImgGroup(signature, ref_dir)).add(filepath, signature)

    return [grp for grp in groups.values() if len(grp) > 1]


def group_equal_by_hash(images: set[Path], ref_dir: Path | None) -> list[ImgGroup]:
    """
    Group files with the same hash computed using the `hashlib.md5` algorithm.
    Return list of groups that contain duplicates.
    """
    return _group_equal(images, ref_dir, _get_file_hash)
