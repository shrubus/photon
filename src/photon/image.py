"""Image-domain utilities: filter strategies and file selection."""

from pathlib import Path
from typing import Iterable, Callable


def _clean_image_suffix(fmt: str) -> str | None:
    """
    Helper function to identify and normalize common image file extensions to a single
    representation (lower case extension with preceding dot). Also, reduce ambiguous
    extensions to a single representation:

        - ".jpeg"/".jpg" as ".jpg"
        - ".tiff"/".tif" as ".tif"

    Returns None if extension does not map to a specified image file extension.
    """

    suffix_map = {
        ".jpg": ".jpg",
        ".jpeg": ".jpg",
        ".png": ".png",
        ".webp": ".webp",
        ".heic": ".heic",
        ".tif": ".tif",
        ".tiff": ".tif",
        ".bmp": ".bmp",
        ".gif": ".gif",
        ".avif": ".avif",
    }

    clean_fmt = f".{fmt.lstrip('.').lower()}" if fmt else None
    return suffix_map.get(clean_fmt) if clean_fmt is not None else None


def by_suffix(path: Path) -> bool:
    """Return True if suffix is mapped to image file suffixes"""
    return bool(_clean_image_suffix(path.suffix))


def by_magic(path: Path) -> bool:
    """Return True if file header matches known image magic bytes."""
    raise NotImplementedError


def by_mime(path: Path) -> bool:
    """Return True if file MIME type is a recognized image format."""
    raise NotImplementedError


def by_date(path: Path, after: str = "", before: str = "") -> bool:
    """Return True if EXIF capture date falls within the given range."""
    raise NotImplementedError


def filter_images(files: Iterable[Path], key: Callable[[Path], bool]) -> set[Path]:
    """
    Return a set of image Paths filtered from an Iterable of Paths, using suffix-based heuristics
    (does not open the files).
    """

    return {path for path in files if path.is_file(follow_symlinks=False) and key(path)}
