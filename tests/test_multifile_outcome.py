from experience.multifile_outcome import MultiFileRepairOutcomeRecorder


class FakeStored:
    def __init__(self, experience_id):
        self.experience_id = experience_id


class FakeRecorder:
    def __init__(self):
        self.calls = []

    def record_repair(self, **kwargs):
        self.calls.append(kwargs)
        return FakeStored("exp-recorded")


class FakeLinks:
    def __init__(self):
        self.links = []

    def save(self, link):
        self.links.append(link)


class Target:
    def __init__(self, symbol):
        self.symbol = symbol


class Plan:
    def __init__(self):
        self.targets = [
            Target("RepairAgent.repair_and_verify"),
            Target("ProjectAgent.analyze"),
        ]


def _component():
    recorder = FakeRecorder()
    links = FakeLinks()

    component = MultiFileRepairOutcomeRecorder(
        recorder=recorder,
        link_store=links,
    )

    return component, recorder, links


def test_multifile_outcome_records_verified_success():
    component, recorder, links = _component()

    stored = component.record(
        request="Fix parser validation across multiple files",
        plan=Plan(),
        result={
            "success": True,
            "stage": "complete",
            "errors": [],
            "applied_files": [
                "agents/repair.py",
                "project/project_agent.py",
            ],
            "rolled_back": False,
        },
        project_root="/Users/omkar/MyAI",
    )

    assert stored.experience_id == "exp-recorded"
    assert recorder.calls
    assert recorder.calls[0]["success"] is True

    provenance = recorder.calls[0]["provenance"]
    assert provenance.source == "multi_file_repair"
    assert provenance.workflow == "patch_apply"
    assert provenance.verified is True

    assert len(links.links) == 1
    assert links.links[0].experience_id == "exp-recorded"
    assert links.links[0].project_root == "/Users/omkar/MyAI"
    assert links.links[0].file_paths == (
        "agents/repair.py",
        "project/project_agent.py",
    )
    assert links.links[0].symbols == (
        "RepairAgent.repair_and_verify",
        "ProjectAgent.analyze",
    )


def test_multifile_outcome_records_rollback_as_failure():
    component, recorder, links = _component()

    stored = component.record(
        request="Fix parser validation across multiple files",
        plan=Plan(),
        result={
            "success": False,
            "stage": "post_apply_verification",
            "errors": [
                "Post-apply content mismatch: agents/repair.py"
            ],
            "applied_files": [
                "agents/repair.py",
            ],
            "rolled_back": True,
        },
        project_root="/Users/omkar/MyAI",
    )

    assert stored.experience_id == "exp-recorded"
    assert recorder.calls
    assert recorder.calls[0]["success"] is False

    provenance = recorder.calls[0]["provenance"]
    assert provenance.source == "multi_file_repair"
    assert provenance.workflow == "patch_apply"
    assert provenance.verified is False
    assert "rollback completed" in provenance.evidence

    assert len(links.links) == 1
    assert links.links[0].experience_id == "exp-recorded"
