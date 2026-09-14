from project.project_memory_benchmark import ProjectMemoryBenchmark


def test_advanced_project_memory_benchmark():
    result = ProjectMemoryBenchmark().run()

    assert result.snapshots == 100.0
    assert result.change_detection == 100.0
    assert result.file_tracking == 100.0
    assert result.history == 100.0
    assert result.deduplication == 100.0
    assert result.health == 100.0
    assert result.reconciliation == 100.0
    assert result.automatic_update == 100.0
    assert result.change_aware_context == 100.0
    assert result.project_agent == 100.0
    assert result.overall == 100.0
