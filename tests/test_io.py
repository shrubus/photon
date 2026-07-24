"""Tests for io layer: path loading, trash management, and deduplication log"""

# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

from pathlib import Path

import pytest

from photon.io import load_paths


class TestLoadPaths:
    """Test io.load_paths(): generic directory walker with recursive/non-recursive modes"""

    @pytest.fixture
    def nested_images(self, tmp_path: Path):
        subdir = tmp_path / "sub"
        subdir.mkdir()
        file_1 = tmp_path / "img_1.jpg"
        file_2 = subdir / "img_2.png"
        file_1.write_bytes(b"img jpg")
        file_2.write_bytes(b"img png")
        return tmp_path, file_1, file_2

    ##############################################
    #### Valid inputs

    def test_load_src_recursively(self, nested_images: tuple[Path, ...]):
        src_dir, file_1, file_2 = nested_images

        result = set(load_paths(src_dir, recursive=True))
        assert file_1 in result
        assert file_2 in result

    def test_load_src_non_recursively(self, nested_images: tuple[Path, ...]):
        src_dir, file_1, file_2 = nested_images

        result = set(load_paths(src_dir, recursive=False))
        assert file_1 in result
        assert file_2 not in result

    def test_load_src_empty(self, tmp_path: Path):
        result = set(load_paths(tmp_path, recursive=False))
        assert result == set()

    ##############################################
    #### Invalid inputs

    def test_raise_src_path_no_exists(self):
        with pytest.raises(ValueError, match="not a directory"):
            load_paths(Path("/nonexistent"), recursive=False)

    def test_raise_src_path_is_file(self, tmp_path: Path):
        f = tmp_path / "file.txt"
        f.write_bytes(b"data")
        with pytest.raises(ValueError, match="not a directory"):
            load_paths(f, recursive=False)

    def test_raise_src_path_is_symlink(self, tmp_path: Path):
        sub = tmp_path / "sub"
        sub.mkdir(parents=True, exist_ok=True)
        lnk = tmp_path / "lnk"
        lnk.symlink_to(sub)
        with pytest.raises(ValueError, match="not a directory"):
            load_paths(lnk, recursive=False)
