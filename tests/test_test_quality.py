from verification.test_quality import TestQualityAssessor


def test_strong_direct_test_gets_good_score():
    code = """
assert add(2, 3) == 5
assert add(-2, 2) == 0
"""

    result = TestQualityAssessor().assess(code)

    assert result.valid is True
    assert result.assertion_count == 2
    assert result.import_count == 0
    assert result.function_count == 0
    assert result.score == 65.0
    assert result.strong is False


def test_multiple_direct_assertions_can_be_strong():
    code = """
assert add(2, 3) == 5
assert add(3, 2) == 5
assert add(-2, 2) == 0
assert add(0, 0) == 0
"""

    result = TestQualityAssessor().assess(code)

    assert result.valid is True
    assert result.assertion_count == 4
    assert result.score >= 70.0
    assert result.strong is True


def test_invalid_test_code_is_rejected():
    result = TestQualityAssessor().assess(
        "assert ("
    )

    assert result.valid is False
    assert result.score < 70.0
    assert result.assertion_count == 0


def test_test_without_assertions_is_rejected():
    result = TestQualityAssessor().assess(
        "x = add(2, 3)"
    )

    assert result.valid is False
    assert result.assertion_count == 0
    assert result.strong is False


def test_imports_and_functions_reduce_quality():
    code = """
import math

def test_value():
    assert math.sqrt(4) == 2
"""

    result = TestQualityAssessor().assess(code)

    assert result.valid is True
    assert result.assertion_count == 1
    assert result.import_count == 1
    assert result.function_count == 1
    assert result.score < 70.0


def test_quality_assessment_is_deterministic():
    code = """
assert add(2, 3) == 5
assert add(0, 0) == 0
"""

    assessor = TestQualityAssessor()

    first = assessor.assess(code)
    second = assessor.assess(code)

    assert first == second
