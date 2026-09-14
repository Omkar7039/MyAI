from experience.consumer_benchmark import ConsumerBenchmark


def test_experience_consumer_benchmark():
    result = ConsumerBenchmark().run()

    assert result.project_agent_scoping == 100.0
    assert result.project_agent_symbol_linking == 100.0
    assert result.multifile_success_learning == 100.0
    assert result.multifile_failure_learning == 100.0
    assert result.overall == 100.0
