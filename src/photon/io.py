"""Functions to manage image files and deduplication log"""

import shutil
from pathlib import Path
import json

from .core import _clean_image_suffix, DedupPair

LOGFILENAME = "log_paths.json"


def select_images(src: Path) -> set[Path]:
    """
    Return a list of image Paths in `src` (source directory), using suffix-based
    heuristics (does not open the files).

    Does not search file in sub-directories.
    """

    selected: set[Path] = set()

    if not isinstance(src, Path):
        raise TypeError("`src` must be of `pathlib.Path` type")
    if not src.is_dir(follow_symlinks=False):
        raise ValueError(f"Path is not a directory: {src}")

    for path in src.iterdir():
        if not path.is_file(follow_symlinks=False):
            continue
        if _clean_image_suffix(path.suffix) is not None:
            selected.add(path)

    return selected


def log_deduplication(dst: Path, duplicated: Path, original: Path, trash: Path) -> None:
    """Record the paths of a deduplication event in a JSON log file."""

    if not trash.is_dir():
        raise ValueError(f"Trash must be a directory: {trash}")

    if not dst.is_relative_to(trash):
        raise ValueError(f"Destination must be inside trash: {dst}")

    if not original.exists():
        raise ValueError(f"Original file does not exist: {original}")

    log_file = trash / LOGFILENAME

    if log_file.exists():
        data = json.loads(log_file.read_text())
    else:
        data = {}

    data[dst.as_posix()] = {"duplicated": duplicated.as_posix(), "original": original.as_posix()}
    log_file.write_text(json.dumps(data, indent=2))


def clean_deduplication_log(log_file: Path) -> None:
    """Remove log entries whose trash files no longer exist."""

    if not log_file.exists() or not log_file.is_file():
        return

    data = json.loads(log_file.read_text())
    clean_data = {dst: v for dst, v in data.items() if Path(dst).exists()}

    if clean_data != data:
        log_file.write_text(json.dumps(clean_data, indent=2))


def move_to_trash(trash: Path, dedupe_pair: DedupPair) -> None:
    """
    Move a duplicated file into the trash directory and log the deduplication event.

    The log entry has the structure:

        {
            "<trash_destination_path>": {
                "duplicated": "<original_duplicated_path>",
                "original": "<original_kept_path>"
            }
        }

    Parameters
    ----------
    trash : Path
        Directory where duplicates are moved.
    dedupe_pair : DedupPair

    Returns
    -------
    None
    """

    duplicated = dedupe_pair.duplicated
    original = dedupe_pair.original

    if duplicated is None or not duplicated.is_file():
        raise KeyError("A deduplication pair shall have an ('duplicated', `Path`) item")
    if original is None or not original.is_file():
        raise KeyError("A deduplication pair shall have an ('original', `Path`) item")

    if trash.is_file():
        raise ValueError(f"Trash path should not be a file: {trash}")

    trash.mkdir(parents=True, exist_ok=True)

    dst = trash / duplicated.name
    counter = 1
    while dst.exists():
        dst = trash / f"{duplicated.stem}_{counter}{duplicated.suffix}"
        counter += 1

    try:
        shutil.move(duplicated, dst)
    except Exception:  # pylint: disable=broad-exception-caught
        return

    log_deduplication(dst=dst, duplicated=duplicated, original=original, trash=trash)


def recover_from_trash(trash: Path) -> list[Path]:
    """
    Restore all files recorded in the deduplication log.

    For each entry:
        <trash_filepath> -> {"duplicated": <original_path>, "original": <kept_path>}

    The function moves <trash_filepath> back to <duplicated_path> and removes the entry
    from the log. Returns a list of restored file paths.
    """

    log_file = trash / LOGFILENAME
    if not log_file.exists() or not log_file.is_file():
        return []

    data = json.loads(log_file.read_text())
    restored: list[Path] = []
    remaining: dict[str, dict[str, str]] = {}

    for trash_str, dedup_pair in data.items():
        trash_path = Path(trash_str)
        try:
            duplicated = Path(dedup_pair["duplicated"])
        except KeyError as err:
            print(f"{err} on {dedup_pair} for {trash_str}")
            continue

        # If the trash file is missing, keep the log entry
        if not trash_path.exists():
            remaining[trash_str] = dedup_pair
            continue

        # Ensure parent directory exists
        duplicated.parent.mkdir(parents=True, exist_ok=True)

        try:
            shutil.move(trash_path, duplicated)
        except Exception:  # pylint: disable=broad-exception-caught
            # If move fails, keep the entry
            remaining[trash_str] = dedup_pair
            continue

        restored.append(duplicated)

    # Rewrite the log with only unrecovered entries
    log_file.write_text(json.dumps(remaining, indent=2))

    return restored
