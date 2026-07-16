"""Test data model"""

# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

from pathlib import Path

import pytest

from photon.model import ImgGroup


class TestImgGroupCreate:
    """ImgGroup state machine initialization"""

    def test_minimal_init(self):
        """Without reference directory (protected images)"""
        grp = ImgGroup(signature=42)
        assert grp.signature == 42
        assert grp.ref_dir is None
        assert len(grp) == 0

    def test_with_reference_dir(self, ref_dir: Path):
        """With reference directory (photos from reference album protected from deletion)"""
        grp = ImgGroup(signature=42, ref_dir=ref_dir)
        assert grp.ref_dir == ref_dir

    def test_reject_invalid_reference_dir(self):
        """With non-existent path for reference directory"""
        with pytest.raises(ValueError, match="Reference"):
            ImgGroup(signature=42, ref_dir=Path("/nonexistent"))


class TestImgGroupAdd:
    """ImgGroup.add method to add new files to the image group"""

    def test_add_image_outside_ref_dir(self, img_file: Path):
        """
        Files outside ref_dir are not protected against deletion, therefore should be classified
        either as a 'survivor' (non-protected file that is not stated for removal) or as a 'file
        to remove'.
        """

        grp = ImgGroup(signature=42)
        grp.add(img_file, signature=42)

        assert grp.survivors == frozenset({img_file})
        assert grp.files_to_remove == frozenset()
        assert len(grp) == 1

    def test_add_image_inside_ref_dir(self, ref_dir: Path, ref_file: Path):
        """
        Files inside ref_dir are protected against deletion, therefore do not qualify either as
        'survivor' (non-protected file that is not stated for removal) or as a 'file to remove'.
        """

        grp = ImgGroup(signature=42, ref_dir=ref_dir)
        grp.add(ref_file, signature=42)

        assert ref_file not in grp.survivors
        assert ref_file not in grp.files_to_remove
        assert grp.signatures == frozenset({42})
        assert len(grp) == 1

    def test_reject_nonexistent_file(self):
        """ImgGroup.add method requires that path is an actual file"""
        grp = ImgGroup(signature=42)
        with pytest.raises(ValueError, match="Not a file"):
            grp.add(Path("/nonexistent.jpg"), signature=42)

    def test_reject_add_after_lock(self, img_file: Path):
        """
        ImgGroup is a two-phase state machine, forcing the separation between image detection
        (grouping) and image selection (e.g. for duplicate removal). Once selection starts
        (first time .stage_for_removal is called), no more files can be added to the group
        (.add method raises RuntimeError).
        """

        dup_file = img_file.with_stem("dup")
        dup_file.write_bytes(img_file.read_bytes())

        grp = ImgGroup(signature=42)
        grp.add(img_file, signature=42)
        grp.add(dup_file, signature=42)

        grp.stage_for_removal({dup_file})

        new = img_file.with_stem("new")
        new.write_bytes(img_file.read_bytes())
        with pytest.raises(RuntimeError, match="locked"):
            grp.add(new, signature=99)

    def test_reject_add_after_explicit_lock(self, img_file: Path):
        """Test that you cannot add extra files to Image group after locking"""

        grp = ImgGroup(signature=42)
        grp.lock()
        with pytest.raises(RuntimeError, match="locked"):
            grp.add(img_file, signature=42)


class TestImgGroupStageForRemoval:
    """
    Test ImgGroup.stage_for_removal method, which marks image files to be deleted (moved to trash)
    """

    def test_stage_selected_files(self, img_file: Path):
        """Stage one file for removal, while keeping a survivor (without a ref dir)"""
        keep = img_file
        dup = img_file.with_stem("duplicate")
        dup.write_bytes(keep.read_bytes())

        grp = ImgGroup(signature=42)
        grp.add(keep, signature=42)
        grp.add(dup, signature=42)

        grp.stage_for_removal({dup})

        assert grp.survivors == frozenset({keep})
        assert grp.files_to_remove == frozenset({dup})
        assert len(grp) == 2

    @pytest.mark.parametrize("img_keys", [("img", "ref"), ("img",), ("img", "dup"), ()])
    def test_stages_all_survivors_when_protected_exists(  # pylint: disable=R0917&R0913
        self,
        img_keys: tuple[str, ...],
        img_file: Path,
        ref_file: Path,
        dup_file: Path,
        ref_dir: Path,
    ):
        """
        When a protected image exists, all other non-protected images in the same ImgGroup
        are expected to be staged for removal (non-protected image duplicates) on the first
        call of .stage_for_removal, independently on the input paths.
        """

        grp = ImgGroup(signature=42, ref_dir=ref_dir)
        grp.add(ref_file, signature=42)
        grp.add(img_file, signature=42)
        grp.add(dup_file, signature=42)

        img_map = {"img": img_file, "ref": ref_file, "dup": dup_file}
        selected = {img_map[k] for k in img_keys}
        grp.stage_for_removal(selected)

        assert grp.files_to_remove == frozenset({img_file, dup_file})
        assert grp.survivors == frozenset()

    def test_preserves_last_survivor(self, img_file: Path, dup_file: Path):
        """Make sure the last survivor is not staged for removal, if no ref dir is defined"""
        grp = ImgGroup(signature=42)
        grp.add(img_file, signature=42)
        grp.add(dup_file, signature=42)

        assert grp.is_exhausted is False
        grp.stage_for_removal({dup_file})
        grp.stage_for_removal({img_file})

        assert grp.survivors == frozenset({img_file})
        assert grp.files_to_remove == frozenset({dup_file})

    def test_is_noop_when_exhausted(self, img_file: Path, dup_file: Path):

        grp = ImgGroup(signature=42)
        grp.add(img_file, signature=42)
        grp.add(dup_file, signature=42)
        grp.stage_for_removal({dup_file})

        assert grp.is_exhausted is True
        survivors = grp.survivors.copy()
        files_to_remove = grp.files_to_remove.copy()
        signatures = grp.signatures.copy()

        grp.stage_for_removal({img_file})
        assert grp.survivors == survivors
        assert grp.files_to_remove == files_to_remove
        assert grp.signatures == signatures


class TestIsExhausted:
    """
    Test ImgGroup.is_exhausted property, which returns True if no more survivors can be
    staged for removal without breaking ImgGroup validation rules
    """

    def test_false_when_multiple_survivors_without_protected(self, img_file: Path, dup_file: Path):

        grp = ImgGroup(signature=42)
        grp.add(img_file, signature=42)
        grp.add(dup_file, signature=42)

        assert grp.is_exhausted is False

    def test_true_when_one_survivor_without_protected(self, img_file: Path):

        grp = ImgGroup(signature=42)
        grp.add(img_file, signature=42)

        assert grp.is_exhausted is True

    def test_false_when_one_survivor_with_protected(
        self, img_file: Path, ref_file: Path, ref_dir: Path
    ):

        grp = ImgGroup(signature=42, ref_dir=ref_dir)
        grp.add(img_file, signature=42)
        grp.add(ref_file, signature=42)

        assert grp.is_exhausted is False

    def test_true_when_no_survivors_with_protected(
        self, img_file: Path, ref_dir: Path, ref_file: Path
    ):

        grp = ImgGroup(signature=42, ref_dir=ref_dir)
        grp.add(ref_file, signature=42)
        grp.add(img_file, signature=42)

        assert grp.is_exhausted is False

        grp.stage_for_removal({img_file})
        assert grp.is_exhausted is True


class TestSignatures:
    """Test view of all image signatures in the image group"""

    def test_returns_all_signatures(self, img_file: Path, dup_file: Path):
        """
        The group signature is an aggregate value of file signatures, which, in the simplest form,
        is the equal to the signatures of all images in the group (identical images). In the
        general case, image signatures can be different from group signatures.
        """

        grp = ImgGroup(signature=42)
        grp.add(img_file, signature=41)
        grp.add(dup_file, signature=43)

        assert grp.signatures == frozenset({41, 43})


class TestLenAndCounts:
    """
    Tests ImgGroup.__len__ which accounts for all images added to the image group, inrespectively
    of the container that holds the file path (survivors, staged for removal, or protected)
    """

    def test_len_includes_all_buckets(
        self, img_file: Path, dup_file: Path, ref_file: Path, ref_dir: Path
    ):

        grp = ImgGroup(signature=42, ref_dir=ref_dir)
        grp.add(img_file, signature=42)
        grp.add(dup_file, signature=42)
        grp.add(ref_file, signature=42)

        assert grp.survivors == frozenset({img_file, dup_file})
        assert len(grp) == 3

        grp.stage_for_removal({img_file, dup_file})
        assert grp.files_to_remove == frozenset({img_file, dup_file})
        assert len(grp) == 3


class TestReadOnlyProperties:

    def test_survivors_cannot_be_assigned(self, img_file: Path, dup_file: Path):

        grp = ImgGroup(signature=42)
        grp.add(img_file, signature=42)
        grp.add(dup_file, signature=42)

        with pytest.raises(AttributeError):
            grp.survivors = frozenset({img_file})

    def test_files_to_remove_cannot_be_assigned(self, img_file: Path, dup_file: Path):

        grp = ImgGroup(signature=42)
        grp.add(img_file, signature=42)
        grp.add(dup_file, signature=42)

        with pytest.raises(AttributeError):
            grp.files_to_remove = frozenset({dup_file})
