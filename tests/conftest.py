"""Tests configurations"""

# pylint: disable=missing-function-docstring

from pathlib import Path

import pytest


@pytest.fixture
def img_file(tmp_path: Path) -> Path:
    path = tmp_path / "photo.jpg"
    path.write_bytes(b"photo content")
    return path


@pytest.fixture
def dup_file(img_file: Path) -> Path:  # pylint: disable=redefined-outer-name
    path = img_file.with_stem("dupli")
    path.write_bytes(img_file.read_bytes())
    return path


@pytest.fixture
def ref_dir(tmp_path: Path) -> Path:
    ref = tmp_path / "reference"
    ref.mkdir()
    return ref


@pytest.fixture
def ref_file(img_file: Path, ref_dir: Path) -> Path:  # pylint: disable=redefined-outer-name
    ref = ref_dir / "img_ref.jpg"
    ref.write_bytes(img_file.read_bytes())
    return ref
