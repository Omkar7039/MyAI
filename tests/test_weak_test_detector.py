from verification.weak_test_detector import WeakTestDetector


def test_strong_direct_assertions_are_not_weak():
    code = """
assert add(2, 3) == 5
assert add(3, 2) == 5
assert add(-2, 2) == 0
assert add(0, 0) == 0
"""

    result = WeakTestDetector().detect(code)

    assert result.weak is False
    assert result.assertion_count == 4
    assert result.duplicate_assertion_count == 0
    assert result.trivial_assertion_count == 0
    assert result.score >= 70.0


def test_single_assertion_is_weak():
    code = """
assert add(2, 3) == 5
"""

    result = WeakTestDetector().detect(code)

    assert result.weak is True
    assert result.assertion_count == 1
    assert "test contains fewer than two assertions" in result.reasons


def test_no_assertions_is_weak():
    code = """
value = add(2, 3)
print(value)
"""

    result = WeakTestDetector().detect(code)

    assert result.weak is True
    assert result.assertion_count == 0
    assert "test contains no assertions" in result.reasons


def test_duplicate_assertions_are_weak():
    code = """
assert add(2, 3) == 5
assert add(2, 3) == 5
assert add(-2, 2) == 0
"""

    result = WeakTestDetector().detect(code)

    assert result.weak is True
    assert result.duplicate_assertion_count == 1
    assert "test contains duplicate assertions" in result.reasons


def test_trivial_assertions_are_weak():
    code = """
assert True
assert 1 == 1
"""

    result = WeakTestDetector().detect(code)

    assert result.weak is True
    assert result.trivial_assertion_count == 2
    assert "test contains trivial assertions" in result.reasons


def test_invalid_syntax_is_weak():
    code = """
assert add(2, 3) ==
"""

    result = WeakTestDetector().detect(code)

    assert result.weak is True
    assert result.score == 0.0
    assert result.reasons == ("test code has invalid syntax",)


def test_detection_is_deterministic():
    code = """
assert add(2, 3) == 5
"""

    detector = WeakTestDetector()

    first = detector.detect(code)
    second = detector.detect(code)

    assert first == second
