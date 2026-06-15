"""Define image file utility functions and image deduplication pipeline"""

import shutil
from pathlib import Path
import json
from hashlib import md5
from collections import Counter
from typing import Callable

# ------------------------------------------------------------------------------------------
# file utility helpers
# ------------------------------------------------------------------------------------------
type Step = Callable[[set[Path]], set[Path]]

LOGFILENAME = "log_paths.json"


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


def move_to_trash(trash: Path, dedupe_pair: dict[str, Path]) -> None:
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
    dedupe_pair : dict[str, Path]
        A mapping containing:
            - "duplicated": Path to the file being removed
            - "original":   Path to the file kept as canonical
    Returns
    -------
    Path of
    """

    duplicated = dedupe_pair.get("duplicated")
    original = dedupe_pair.get("original")

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


# -----------------------------------------------------------------------------------------
# retrieve paths of duplicated files
# -----------------------------------------------------------------------------------------


def _get_hash(file: Path, chunk_size: int = 1024 * 1024) -> str:
    """
    Helper function to hash a file incrementally in fixed-size chunks,
    without loading it fully into memory.
    """
    h = md5()
    with open(file, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def _find_duplicates(files: set[Path]) -> dict[str, set[Path]]:
    """Find duplicated files in list of paths"""

    hash_to_file_map: dict[str, set[Path]] = {}

    for path in files:
        if path.is_file(follow_symlinks=False):
            hsh = _get_hash(path)
            hash_to_file_map.setdefault(hsh, set()).add(path)

    return {hsh: files for hsh, files in hash_to_file_map.items() if len(files) > 1}


# ------------------------------------------------------------------------------------------
# functions (Steps) to select duplicated files to keep based on specified criterium
# ------------------------------------------------------------------------------------------


def get_earliest(dupl_files: set[Path]) -> set[Path]:
    """
    IMPORTANT:
    This deduplication step is not currently used in any active deduplication pipeline.
    The heuristics is intentionally weak and should only be applied for unsupervised
    cleanup of a "photo dump" directory, where filesystem metadata is irrelevant
    (e.g. directory structure, naming conventions).

    Return all filepaths with the earliest modification time"""

    if not dupl_files:
        return set()
    files = dupl_files.copy()

    mtimes: list[tuple[float, Path]]  # [<modification time epoch>,<filepath>]
    mtimes = [(p.stat(follow_symlinks=False).st_mtime, p) for p in files]

    earliest_time = min(t for t, _ in mtimes)
    return {p for t, p in mtimes if t == earliest_time}


def remove_named_copy(dupl_files: set[Path]) -> set[Path]:
    """Return paths that do not have copy in name, or all paths if all have copy in name"""

    if not dupl_files:
        return set()
    files = dupl_files.copy()

    no_named_copy = {p for p in files if "copy" not in p.name.lower()}
    return no_named_copy if no_named_copy else files


def select_by_most_common_size(pct: float) -> Step:
    """
    IMPORTANT:
    This deduplication step is not currently used in any active deduplication pipeline.
    The heuristics is intentionally weak and should only be applied for unsupervised
    cleanup of a "photo dump" directory, where filesystem metadata is irrelevant
    (e.g. directory structure, naming conventions).

    Select files whose filename length matches the dominant camera filename length,
    for the same image file format (using files extension as heuristics).

    If no dominant length exists (below pct threshold), return all files unchanged.
    """

    if pct > 1 or pct < 0.5:
        raise ValueError(f"pct threshold not in [0.5, 1]: {pct}")

    def step(dupl_files: set[Path]) -> set[Path]:

        if not dupl_files:
            return set()
        files = dupl_files.copy()

        # duplicated images should share the same file extension
        suffixes = {_clean_image_suffix(p.suffix) for p in files}
        if len(suffixes) > 1:
            return files
        suffix = next(iter(suffixes))

        parents = {p.parent for p in files}
        img_paths = [
            img for img in select_images(*parents) if _clean_image_suffix(img.suffix) == suffix
        ]

        if not img_paths:
            return files

        counter = Counter(len(p.name) for p in img_paths)
        if not counter:
            return files

        # Most common length among the duplicates
        ((length, count),) = counter.most_common(1)

        # Require dominance (e.g., 80% of duplicates share this length)
        if count < pct * counter.total():
            return files

        # Filter by dominant length
        filtered = {p for p in files if len(p.name) == length}
        return filtered if filtered else files

    return step


def select_from_album(ref_album: Path | None) -> Step:
    """
    Return the paths of a duplicated image that are in a reference directory (`ref_album`),
    or all paths if none of the paths are in the directory.
    """
    if ref_album is not None:
        if not ref_album.exists() or not ref_album.is_dir(follow_symlinks=False):
            raise ValueError(f"Reference album should be a directory: {ref_album}")

    def step(dupl_files: set[Path]) -> set[Path]:

        if ref_album is None:
            return dupl_files

        if not dupl_files:
            return set()

        files = dupl_files.copy()
        in_album = {f for f in files if f.is_relative_to(ref_album)}
        return in_album if in_album else files

    return step


def ask_user(dupl_files: set[Path]) -> set[Path]:
    """
    Return user selected path from a set of paths of duplicated images,
    or all paths if use skips deduplication
    """

    if not dupl_files:
        return set()
    files = list(dupl_files)

    msg = "Found the following duplicated images:\n"
    msg += "\n".join(f"{i}: {p}" for i, p in enumerate(files))
    msg += "\nType the number of the file to keep or 's' to skip: "

    try:
        idx = int(input(msg))
        return {files[idx]}
    except (ValueError, IndexError):
        return set(files)


# ------------------------------------------------------------------------------------------
# Pipeline
# ------------------------------------------------------------------------------------------


def make_pipeline(images: set[Path], criteria: list[Step]) -> list[dict[str, Path]]:
    """
    Make pipeline function to find duplicated images in a set of files and apply a list of steps
    to decide which image in each duplicate group should be kept (the original) and which
    should be removed (the duplicates).
    """

    duplicated: dict[str, set[Path]] = _find_duplicates(files=images)
    dedup_pairs: list[dict[str, Path]] = []

    for files in duplicated.values():
        files_to_keep = files.copy()
        for criterium in criteria:
            files_to_keep = criterium(files_to_keep)
            if len(files_to_keep) == 1:
                break

        # do not dedupe images that did not converge to a single original
        if len(files_to_keep) > 1:
            continue

        files_to_remove = files - files_to_keep
        file_to_keep = next(iter(files_to_keep))
        for file_to_remove in files_to_remove:
            dedup_pairs.append({"duplicated": file_to_remove, "original": file_to_keep})

    return dedup_pairs


def dedupe_pipeline(images: set[Path], trash: Path, ref_album: Path | None = None) -> set[Path]:
    """Move duplicates to a denominated trash directory and return list of paths removed"""

    # pipeline
    dedupe_pairs = make_pipeline(
        images=images,
        criteria=[
            select_from_album(ref_album=ref_album),
            remove_named_copy,
            ask_user,
        ],
    )

    removed = set()
    for dedupe_pair in dedupe_pairs:
        move_to_trash(trash=trash, dedupe_pair=dedupe_pair)
        if duplicated := dedupe_pair.get("duplicated"):
            removed.add(duplicated)

    return removed
