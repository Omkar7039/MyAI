from pathlib import Path
from tempfile import TemporaryDirectory

from agents.multi_file_repair_executor import MultiFileRepairExecutor
from experience.multifile_outcome import MultiFileRepairOutcomeRecorder
from experience.project_link_store import ExperienceProjectLinkStore
from experience.recorder import ExperienceRecorder
from experience.store import ExperienceStore
from project.patch_applier import PatchApplier
from project.patch_set import PatchSet


class FakePlanner:
    def __init__(self, patch_set):
        self.patch_set = patch_set

    def build_patch_set(self, **kwargs):
        return {
            "success": True,
            "patch_set": self.patch_set,
            "errors": [],
            "warnings": [],
        }


class Plan:
    targets = []
    affected_files = ["example.py"]


def test_executor_records_rolled_back_repair_as_warning():
    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        db = root / "experience.db"
        target = root / "example.py"

        original = "value = 1\n"
        target.write_text(original, encoding="utf-8")

        patch_set = PatchSet(
            request="Test rollback learning"
        )

        patch_set.add(
            file="example.py",
            original=original,
            updated="value = 2\n",
            reason="Rollback learning test",
        )

        store = ExperienceStore(db)
        links = ExperienceProjectLinkStore(db)

        applier = PatchApplier(root)
        applier._verify_applied = (
            lambda patch_set: ["Forced verification failure"]
        )

        executor = MultiFileRepairExecutor(
            planner=FakePlanner(patch_set),
            applier=applier,
            outcome_recorder=MultiFileRepairOutcomeRecorder(
                recorder=ExperienceRecorder(store),
                link_store=links,
            ),
            root=root,
        )

        result = executor.execute(
            request="Test rollback learning",
            plan=Plan(),
            evidence="Current source evidence",
        )

        assert result["success"] is False
        assert result["stage"] == "post_apply_verification"
        assert result["rolled_back"] is True

        assert target.read_text(encoding="utf-8") == original

        recent = store.recent(limit=10)
        assert len(recent) == 1

        recorded = recent[0]

        assert recorded.success is False
        assert "Forced verification failure" in recorded.outcome
        assert "rollback completed" in recorded.metadata

        link = links.get(recorded.experience_id)

        assert link is not None
        assert link.project_root == str(root)
        assert link.file_paths == ("example.py",)
