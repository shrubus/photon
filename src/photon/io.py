"""Functions to manage image files and deduplication log"""

import shutil
from pathlib import Path
import json

from .core import select_images

LOGFILENAME = "log_paths.json"


def get_images(src: Path, recursive: bool) -> set[Path]:
    """
    Return a list of image Paths in `src` (source directory), using suffix-based
    heuristics (does not open the files).

    Search file in sub-directories if `recursive`=True.
    """

    if not isinstance(src, Path):
        raise TypeError("`src` must be of `pathlib.Path` type")
    if not src.is_dir(follow_symlinks=False):
        raise ValueError(f"Path is not a directory: {src}")

    paths = src.rglob("*") if recursive is True else src.iterdir()

    return select_images(paths)


def log_deduplication(dst: Path, file: Path, trash: Path) -> None:
    """Record the paths of a deduplication event in a JSON log file."""

    if not trash.is_dir():
        raise ValueError(f"Trash must be a directory: {trash}")

    if not dst.is_relative_to(trash):
        raise ValueError(f"Destination must be inside trash: {dst}")

    log_file = trash / LOGFILENAME

    if log_file.exists():
        data = json.loads(log_file.read_text())
    else:
        data = {}

    data[dst.as_posix()] = file.as_posix()
    log_file.write_text(json.dumps(data, indent=2))


def clean_deduplication_log(log_file: Path) -> None:
    """Remove log entries whose trash files no longer exist."""

    if not log_file.exists() or not log_file.is_file():
        return

    data = json.loads(log_file.read_text())
    clean_data = {dst: v for dst, v in data.items() if Path(dst).exists()}

    if clean_data != data:
        log_file.write_text(json.dumps(clean_data, indent=2))


def move_to_trash(trash: Path, file: Path) -> None:
    """
    Move a duplicated file into the trash directory and log the deduplication event.
    """

    if trash.is_file():
        raise ValueError(f"Trash path should not be a file: {trash}")

    trash.mkdir(parents=True, exist_ok=True)

    dst = trash / file.name

    # handle filename conflicts
    counter = 1
    while dst.exists():
        dst = trash / f"{file.stem}_{counter}{file.suffix}"
        counter += 1

    try:
        shutil.move(file, dst)
    except Exception:  # pylint: disable=broad-exception-caught
        return

    log_deduplication(dst=dst, file=file, trash=trash)


def recover_from_trash(trash: Path) -> list[Path]:
    """
    Restore all files recorded in the deduplication log.

    The function moves file <trash_path> back to <original_path> and removes the entry
    from the log. Returns a list of restored file paths.
    """

    log_file = trash / LOGFILENAME
    if not log_file.exists() or not log_file.is_file():
        return []

    data = json.loads(log_file.read_text())
    restored: list[Path] = []
    remaining: dict[str, str] = {}

    for trash_str, original_str in data.items():
        trash_path = Path(trash_str)
        original_path = Path(original_str)

        # If the trash file is missing, keep the log entry
        if not trash_path.exists():
            continue

        # Ensure original_path directory exists
        original_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            shutil.move(trash_path, original_path)
        except Exception:  # pylint: disable=broad-exception-caught
            # If move fails, keep the entry
            remaining[trash_str] = original_str
            continue

        restored.append(original_path)

    # Rewrite the log with only unrecovered entries
    log_file.write_text(json.dumps(remaining, indent=2))

    return restored
