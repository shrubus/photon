"""Tests configurations"""

# pylint: disable=missing-function-docstring

from pathlib import Path

import pytest


@pytest.fixture
def src_dir(tmp_path: Path) -> Path:
    path = tmp_path / "src"
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture
def src_img(src_dir: Path) -> Path:
    """Image in source directory"""
    path = src_dir / "src_img.jpg"
    path.write_bytes(b"photo content")
    return path


@pytest.fixture
def src_dup(src_img: Path) -> Path:  # pylint: disable=redefined-outer-name
    """Image duplicate in source directory"""
    path = src_img.with_stem("dup_img")
    path.write_bytes(src_img.read_bytes())
    return path


@pytest.fixture
def ref_dir(tmp_path: Path) -> Path:
    path = tmp_path / "ref"
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture
def ref_img(ref_dir: Path, src_img: Path) -> Path:  # pylint: disable=redefined-outer-name
    """Image duplicate in reference directory"""
    path = ref_dir / "ref_img.jpg"
    path.write_bytes(src_img.read_bytes())
    return path


# @pytest.fixture
# def src_tree(src_img: Path) -> Path:  # pylint: disable=redefined-outer-name
#     src_dir = src_img.parent
#     sub_dir = src_dir / "sub"
#     sub_dir.mkdir(parents=True, exist_ok=True)
#     png_img = sub_dir / "img.png"
#     return src_dir
