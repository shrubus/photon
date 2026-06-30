"""
Model objects for image-deduplication state tracking.
"""

from pathlib import Path
from collections.abc import Sequence, Set
from dataclasses import dataclass, field

type Signature = int | Sequence[float]


@dataclass
class ImgGroup:
    """
    Mutable state machine for managing a group of images sharing the same signature.

    Public interface:
    - `signature`: identifier for the group.
    - `ref_dir`: optional directory whose files must always be kept.
    - `signatures`: view of signatures for all files in the group.
    - `survivors`: view of non-protected files still eligible to survive.
    - `files_to_remove`: view of files currently staged for removal.
    - add(path, signature): register a file before selection begins.
    - stage_for_removal(files): apply removal rules to update state.
    - `is_exhausted`: True when no further staging is possible.

    Internal state:
    - `_protected`: files under `ref_dir` (never eligible for removal).
    - `_survivors`: non-protected files not yet staged for removal.
    - `_to_remove`: files staged for removal (not removed yet).
    - `_locked`: prevents adding new files after the first staging operation.

    The object enforces the invariant that at least one file must be kept.
    """

    signature: Signature
    ref_dir: Path | None = None

    _protected: dict[Path, Signature] = field(default_factory=dict, init=False)
    _survivors: dict[Path, Signature] = field(default_factory=dict, init=False)
    _to_remove: dict[Path, Signature] = field(default_factory=dict, init=False)
    _locked: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        """Validate reference directory if provided."""
        if self.ref_dir and not self.ref_dir.is_dir(follow_symlinks=False):
            raise ValueError(f"Reference should be a valid directory: {self.ref_dir}")

    ############################################################
    ## Views

    @property
    def signatures(self) -> frozenset[Signature]:
        """
        Return a frozenset containing the signatures of all files in the group.
        """
        return frozenset((self._protected | self._survivors | self._to_remove).values())

    @property
    def survivors(self) -> frozenset[Path]:
        """
        Return a frozenset containing non-protected files that are not yet staged for removal.
        """
        return frozenset(self._survivors.keys())

    @property
    def files_to_remove(self) -> frozenset[Path]:
        """
        Return a frozenset containing the files currently staged for removal.
        This reflects the state after any selection steps have been applied.
        """
        return frozenset(self._to_remove.keys())

    ############################################################
    ## Builder

    def add(self, path: Path, signature: Signature) -> None:
        """Register a file before locking."""

        if self._locked is True:
            raise RuntimeError("Image group is locked; cannot add new files")

        if not path.is_file(follow_symlinks=False):
            raise ValueError(f"Not a file: {path}")

        if self.ref_dir and path.is_relative_to(self.ref_dir):
            self._protected[path] = signature
        else:
            self._survivors[path] = signature

    def __len__(self) -> int:
        return len(self._protected.keys() | self._survivors.keys() | self._to_remove.keys())

    ############################################################
    ## Validation

    @property
    def _to_keep(self) -> frozenset[Path]:
        """Files currently selected to survive (protected + survivors)."""
        return frozenset(self._protected.keys() | self._survivors.keys())

    def _validate(self) -> None:
        """Ensure at least one file survives and no file is both kept and staged for removal."""

        if not self._to_keep:
            raise ValueError(f"No path to the original image with signature {self.signature}")

        if not self._to_keep.isdisjoint(self._to_remove):
            raise ValueError("Image simultaneously marked as kept and staged for removal")

    ############################################################
    ## Selection

    @property
    def is_exhausted(self) -> bool:
        """
        Return True if no more files can be staged for removal while ensuring
        that at least one file will be kept.
        """
        if self._protected:
            return not self._survivors
        return len(self._survivors) == 1

    def _apply_stage_for_removal(self, files: Set[Path]) -> None:
        """Move file paths from `survivors` to `to_remove` and validate state."""
        for file in files:
            self._to_remove[file] = self._survivors.pop(file)
        self._validate()

    def stage_for_removal(self, files: Set[Path]) -> None:
        """
        Stage files for removal according to group rules.

        - If any protected files exist, all non-protected survivors are staged.
        - Otherwise, the given `candidates` are staged only if at least one file
          would remain in `files_to_keep` after the operation.
        - If no survivors would remain, nothing is staged.

        Auto-locks on first call.
        """
        self._locked = True
        if self.is_exhausted:
            return

        if self._protected:
            self._apply_stage_for_removal(self.survivors)
            return

        remaining = self._to_keep - files
        if remaining:
            self._apply_stage_for_removal(files)
