"""
Model objects for image-deduplication state tracking.
"""

from pathlib import Path
from collections.abc import Hashable
from dataclasses import dataclass, field


@dataclass
class ImgGroup:
    """
    Mutable state machine for a set of identical images.

    - `signature` identifies the group.
    - `ref` marks a directory whose files must never be duplicated.
    - `originals` and `duplicated` track current decisions.
    - `_locked` prevents adding new files after first mutation.
    """

    signature: Hashable
    ref: Path | None = None

    originals: set[Path] = field(default_factory=set, init=False)
    duplicated: set[Path] = field(default_factory=set, init=False)
    _locked: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        """Validate reference directory if provided."""
        if self.ref is not None and not self.ref.is_dir(follow_symlinks=False):
            raise ValueError(f"Reference should be a valid directory: {self.ref}")

    def add(self, path: Path, signature: Hashable) -> None:
        """Register a file before locking; signature must match."""

        if self._locked is True:
            raise RuntimeError("Cannot add after lock()")
        if signature != self.signature:
            raise ValueError(f"Mismatch between file ({path}) and signature ({self.signature})")
        self.originals.add(path)

    def _validate(self) -> None:
        """Enforce invariants: at least one original; no overlap with duplicates."""

        # invalidate marking files for removal if no original image remains
        if not self.originals:
            raise ValueError(f"No path to the original image with signature {self.signature}")

        # invalidate marking files for removal if images are also marked as original
        if not self.originals.isdisjoint(self.duplicated):
            raise ValueError("Image simultaneously marked  as original and duplicated")

    def mark_as_duplicates(self, files: set[Path]) -> None:
        """
        Mark files as duplicates. Auto-locks on first call.
        Protected files (under `ref`) are ignored.
        """
        self._locked = True

        unprotected = {f for f in files if not f.is_relative_to(self.ref)} if self.ref else files

        remaining = self.originals - unprotected
        if not remaining:
            return

        self.duplicated.update(files)
        self.originals.difference_update(files)

        self._validate()
