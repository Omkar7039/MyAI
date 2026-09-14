from experience.benchmark import ExperienceBenchmark


def test_experience_benchmark_report_is_deterministic():
    benchmark = ExperienceBenchmark()

    first = benchmark.run()
    second = benchmark.run()

    assert first == second
    assert first["benchmark"] == "experience-memory-baseline"
    assert first["metrics"]["overall"] == 100.0

    rendered = benchmark.render(first)

    assert "MYAI EXPERIENCE MEMORY BASELINE" in rendered
    assert "Retrieval:" in rendered
    assert "Overall:" in rendered

    payload = benchmark.to_json(first)

    assert "experience-memory-baseline" in payload
    assert '"overall": 100.0' in payload
