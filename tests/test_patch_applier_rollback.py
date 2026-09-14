from pathlib import Path
from tempfile import TemporaryDirectory

from project.patch_applier import PatchApplier
from project.patch_set import PatchSet


def test_patch_applier_rolls_back_after_post_apply_failure():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        target = root / "example.py"

        original = "value = 1\n"
        target.write_text(original, encoding="utf-8")

        patch_set = PatchSet(
            request="Test rollback"
        )

        patch_set.add(
            file="example.py",
            original=original,
            updated="value = 2\n",
            reason="Intentional rollback test",
        )

        applier = PatchApplier(root)

        original_verify = applier._verify_applied

        def forced_failure(patch_set):
            errors = original_verify(patch_set)
            errors.append("Forced verification failure")
            return errors

        applier._verify_applied = forced_failure

        result = applier.apply(patch_set)

        assert result["success"] is False
        assert result["stage"] == "post_apply_verification"
        assert result["rolled_back"] is True
        assert "Forced verification failure" in result["errors"]

        assert target.read_text(encoding="utf-8") == original


def test_patch_applier_does_not_leave_partial_multi_file_changes():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)

        first = root / "first.py"
        second = root / "second.py"

        first_original = "first = 1\n"
        second_original = "second = 1\n"

        first.write_text(first_original, encoding="utf-8")
        second.write_text(second_original, encoding="utf-8")

        patch_set = PatchSet(
            request="Test multi-file rollback"
        )

        patch_set.add(
            file="first.py",
            original=first_original,
            updated="first = 2\n",
        )

        patch_set.add(
            file="second.py",
            original=second_original,
            updated="second = 2\n",
        )

        applier = PatchApplier(root)

        def forced_failure(patch_set):
            return ["Forced multi-file verification failure"]

        applier._verify_applied = forced_failure

        result = applier.apply(patch_set)

        assert result["success"] is False
        assert result["rolled_back"] is True
        assert result["applied_files"] == [
            "first.py",
            "second.py",
        ]

        assert first.read_text(encoding="utf-8") == first_original
        assert second.read_text(encoding="utf-8") == second_original
