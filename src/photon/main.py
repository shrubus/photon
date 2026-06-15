"""Entrypoint"""

import sys
from pathlib import Path
from pprint import pprint
from photon.dedup import select_images, dedupe_pipeline


def main() -> None:
    """Temporary cross-directory deduplication entrypoint"""

    albums = [Path(arg) for arg in sys.argv[1:]]
    ref_album = albums[-1] if len(albums) > 1 else None

    print(f"{albums = }")
    print(f"{ref_album = }")

    selected: set[Path] = set()
    for album in albums:
        selected.update(select_images(album))

    img_copies_removed = dedupe_pipeline(
        images=selected,
        ref_album=ref_album,
        trash=Path("./data/trash"),
    )

    pprint(img_copies_removed)


if __name__ == "__main__":
    main()
