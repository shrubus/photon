"""Core domain types and system‑wide utilities."""

from pathlib import Path
from dataclasses import dataclass


@dataclass(frozen=True)
class DedupPair:
    """Pairs the path of a duplicated image with the path of the original"""

    duplicated: Path
    original: Path


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
    }

    clean_fmt = f".{fmt.lstrip('.').lower()}" if fmt else None
    return suffix_map.get(clean_fmt) if clean_fmt is not None else None
