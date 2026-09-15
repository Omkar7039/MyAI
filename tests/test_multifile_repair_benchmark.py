from agents.multifile_repair_benchmark import MultiFileRepairBenchmark


def test_autonomous_multifile_repair_benchmark():
    result = MultiFileRepairBenchmark().run()

    assert result.controller == 100.0
    assert result.retry_context == 100.0
    assert result.attempt_evaluation == 100.0
    assert result.improvement == 100.0
    assert result.reverification == 100.0
    assert result.regression == 100.0
    assert result.recovery == 100.0
    assert result.overall == 100.0
