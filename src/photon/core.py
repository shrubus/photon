"""Core domain types and system-wide utilities."""

from pathlib import Path
from typing import Iterable


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


def select_images(files: Iterable[Path]) -> set[Path]:
    """
    Return a set of image Paths filtered from an Iterable of Paths, using suffix-based heuristics
    (does not open the files).
    """

    return {
        path
        for path in files
        if path.is_file(follow_symlinks=False) and _clean_image_suffix(path.suffix) is not None
    }
