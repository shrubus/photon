"""Define image file utility functions and image deduplication pipeline"""

from pathlib import Path


from .core import DedupPair
from .io import move_to_trash
from .detection import group_duplicates, ImgSigFn, SigGroupMap
from .selection import Step


def resolve_duplicates(sig_groups: SigGroupMap, criteria: list[Step]) -> list[DedupPair]:
    """
    Select which image mapped to the same file signature should be kept (the original)
    and which should be removed (the duplicates).
    """

    dedup_pairs: list[DedupPair] = []

    for group in sig_groups.values():
        files_to_keep = group.copy()
        for criterion in criteria:
            files_to_keep = criterion(files_to_keep)
            if len(files_to_keep) == 1:
                break

        # do not dedupe images that did not converge to a single original
        if len(files_to_keep) > 1:
            continue

        file_to_keep = next(iter(files_to_keep))
        files_to_remove = group - files_to_keep

        for file_to_remove in files_to_remove:
            pair = DedupPair(duplicated=file_to_remove, original=file_to_keep)
            dedup_pairs.append(pair)

    return dedup_pairs


def dedupe_pipeline(
    images: set[Path], sig_fn: ImgSigFn, criteria: list[Step], trash: Path
) -> set[Path]:
    """Move duplicates to a denominated trash directory and return list of paths removed"""

    sig_groups = group_duplicates(files=images, sig_fn=sig_fn)
    dedupe_pairs = resolve_duplicates(sig_groups, criteria)

    removed = set()
    for pair in dedupe_pairs:
        move_to_trash(trash, pair)
        removed.add(pair.duplicated)

    return removed
