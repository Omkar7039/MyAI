from agents.debug_benchmark import DebugBenchmark


def test_autonomous_debugging_benchmark():
    result = DebugBenchmark().run()

    assert result.investigation == 100.0
    assert result.hypothesis_generation == 100.0
    assert result.hypothesis_ranking == 100.0
    assert result.hypothesis_verification == 100.0
    assert result.retry_loop == 100.0
    assert result.classification == 100.0
    assert result.repair_bridge == 100.0
    assert result.reinvestigation == 100.0
    assert result.stop_policy == 100.0
    assert result.overall == 100.0
