"""Tests for io layer: path loading, trash management, and deduplication log"""

# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

from pathlib import Path

import pytest

from photon.io import load_files


class TestLoadFiles:
    """Test io.load_files(): generic directory walker with recursive/non-recursive modes"""

    @pytest.fixture
    def nested_files(self, tmp_path: Path):

        file_1 = tmp_path / "file_1.jpg"
        file_1.write_bytes(b"file_1")
        link_1 = tmp_path / "link_1.jpg"
        link_1.symlink_to(file_1)

        subdir = tmp_path / "sub"
        subdir.mkdir()

        file_2 = subdir / "file_2.jpg"
        file_2.write_bytes(b"file_2")
        link_2 = subdir / "link_2.jpg"
        link_2.symlink_to(file_2)

        return tmp_path, file_1, link_1, subdir, file_2, link_2

    ##############################################
    #### Valid inputs

    def test_load_src_recursively(self, nested_files: tuple[Path, ...]):
        src_dir, file_1, link_1, subdir, file_2, link_2 = nested_files

        result = set(load_files(src_dir, recursive=True))

        assert file_1 in result
        assert link_1 not in result

        assert subdir not in result
        assert file_2 in result
        assert link_2 not in result

    def test_load_src_non_recursively(self, nested_files: tuple[Path, ...]):
        src_dir, file_1, link_1, subdir, file_2, link_2 = nested_files

        result = set(load_files(src_dir, recursive=False))

        assert file_1 in result
        assert link_1 not in result

        assert subdir not in result
        assert file_2 not in result
        assert link_2 not in result

    def test_load_src_empty(self, tmp_path: Path):
        result = set(load_files(tmp_path, recursive=False))
        assert result == set()

    ##############################################
    #### Invalid inputs

    def test_raise_src_path_no_exists(self):
        with pytest.raises(ValueError, match="not a directory"):
            load_files(Path("/nonexistent"), recursive=False)

    def test_raise_src_path_is_file(self, tmp_path: Path):
        f = tmp_path / "file.txt"
        f.write_bytes(b"data")
        with pytest.raises(ValueError, match="not a directory"):
            load_files(f, recursive=False)

    def test_raise_src_path_is_symlink(self, tmp_path: Path):
        sub = tmp_path / "sub"
        sub.mkdir(parents=True, exist_ok=True)
        lnk = tmp_path / "lnk"
        lnk.symlink_to(sub)
        with pytest.raises(ValueError, match="not a directory"):
            load_files(lnk, recursive=False)
