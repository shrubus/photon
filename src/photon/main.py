"""Entrypoint"""

import sys
from pathlib import Path
from pprint import pprint

from photon.io import select_images
from photon.pipeline import dedupe
from photon.detection import hash_signature
from photon.selection import select_from_album, remove_named_copy, ask_user


def main() -> None:
    """Temporary cross-directory deduplication entrypoint"""

    albums = [Path(arg) for arg in sys.argv[1:]]
    ref_album = albums[-1] if len(albums) > 1 else None

    print(f"{albums = }")
    print(f"{ref_album = }")

    selected: set[Path] = set()
    for album in albums:
        selected.update(select_images(album))

    removed = dedupe(
        images=selected,
        sig_fn=hash_signature,
        criteria=[
            select_from_album(ref_album=ref_album),
            remove_named_copy,
            ask_user,
        ],
        trash=Path("./data/trash"),
    )

    pprint(removed)


if __name__ == "__main__":
    main()
