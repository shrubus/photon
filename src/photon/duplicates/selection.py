"""
Define functions that implement the selection rules

A select function receives a collection of paths and apply a specified criterium
to decide which duplicated files should be kept. If a selection step criterum
do not retrieve any file to keep, it returns the full collection (no decision).
"""

from typing import Callable
import re

from photon.model import FileGroup

type SelectFn = Callable[[FileGroup], FileGroup]


def make_selection_pipeline(steps: list[SelectFn]) -> SelectFn:
    """
    Compose a list of selection steps into a single meta-Step.

    Each Step is a function that receives an ImgGroup and returns an ImgGroup,
    mutating it in place by staging files for removal. The pipeline
    stops early if the group becomes exhausted.
    """

    def pipeline(img_group: FileGroup) -> FileGroup:
        img_group.lock()
        for step in steps:
            if img_group.is_exhausted:
                break
            img_group = step(img_group)
        return img_group

    return pipeline


def remove_filename_with(pattern: str, flags: re.RegexFlag = re.IGNORECASE) -> SelectFn:
    """
    Keep files with the minimal number of occurrences of `pattern` (case-insensitive by default),
    and stage all others for removal.

    Accepts standard library re flags.
    """

    pat = re.compile(pattern, flags=flags)

    def step(img_group: FileGroup) -> FileGroup:
        if img_group.is_exhausted:
            return img_group

        survivors = img_group.survivors
        counts = {path: len(pat.findall(path.name)) for path in survivors}
        min_count = min(counts.values())
        to_remove = {p for p in survivors if counts[p] != min_count}
        img_group.stage_for_removal(files=to_remove)
        return img_group

    return step


def ask_user(auto_select: bool) -> SelectFn:
    """
    Interactively select which file to keep among duplicates.

    User options:
    - number: keep that file
    - 's': skip this group
    - 'a': skip all remaining groups
    """

    def step(img_group: FileGroup) -> FileGroup:

        nonlocal auto_select

        if auto_select or img_group.is_exhausted:
            return img_group

        survivors = list(img_group.survivors)
        msg = "\nFound the following duplicated images:\n"
        msg += "\n".join(f"{i}: {p}" for i, p in enumerate(survivors))
        msg += "\nType the number to keep, 's' to skip, or 'a' to skip all: "

        choice = input(msg).strip().lower()

        if choice == "s":
            return img_group

        if choice == "a":
            auto_select = True
            return img_group

        try:
            idx = int(choice)
            file_to_keep = survivors[idx]
        except (ValueError, IndexError):
            return img_group

        print(f"keeping: {file_to_keep}")
        survivors.remove(file_to_keep)
        img_group.stage_for_removal(set(survivors))
        return img_group

    return step
