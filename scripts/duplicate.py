"""Minimal pogram functions to create image and album duplicates"""

# pylint: disable=missing-function-docstring

from pathlib import Path
import shutil
import argparse


def duplicate_files(src: Path, suffix: str | None) -> None:

    if suffix is None:
        return

    if not src.is_dir():
        raise ValueError(f"path should be a directory: {src}")

    for filepath in src.iterdir():
        if not filepath.is_file():
            continue
        newname = f"{filepath.stem}{suffix}{filepath.suffix}"
        newpath = filepath.parent / newname
        shutil.copy(filepath, newpath)


def duplicate_album(src: Path, dst: Path | None) -> None:

    if dst is None:
        return

    shutil.copytree(src, dst, dirs_exist_ok=True)


def main() -> None:

    parser = argparse.ArgumentParser(prog="duplicate", description="duplicates folders or files")

    parser.add_argument("src", type=Path, help="directory containing images to duplicate")
    parser.add_argument("dst", type=Path, nargs="?", help="path to the duplicated directory")
    parser.add_argument("--suffix", help='duplicated images filename suffix (default: "_copy")')

    args = parser.parse_args()

    if args.dst is not None:
        duplicate_album(src=args.src, dst=args.dst)
        if args.suffix is not None:
            print("Warning: --suffix flag has no effect if passed with a destination directory")
    else:
        duplicate_files(src=args.src, suffix=args.suffix or "_copy")


if __name__ == "__main__":
    main()
