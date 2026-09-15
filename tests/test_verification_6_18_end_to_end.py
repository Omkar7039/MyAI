from verification.mutation_gap import MutationGapAnalyzer
from verification.post_repair_loop import PostRepairVerificationLoop
from verification.property_expansion import PropertyExpansionEngine
from verification.regression_test_generator import RegressionTestGenerator
from verification.strategy_selector import VerificationStrategySelector
from verification.test_quality import TestQualityAssessor
from verification.test_strengthener import TestStrengthener
from verification.weak_test_detector import WeakTestDetector


SOURCE = """
def add(a, b):
    return a + b
"""


def test_complete_6_18_verification_flow():
    tests = """
assert add(2, 3) == 5
"""

    # 6.18.1 — Test quality
    quality = TestQualityAssessor().assess(tests)

    assert quality.valid is True
    assert quality.assertion_count == 1
    assert quality.strong is False

    # 6.18.2 — Weak-test detection
    weak = WeakTestDetector().detect(tests)

    assert weak.weak is True
    assert weak.assertion_count == 1

    # Simulate mutation results from the existing mutation infrastructure.
    mutation = MutationGapAnalyzer().assess(
        [True, True, False, True]
    )

    assert mutation.survived_mutations == 1
    assert mutation.gap_rate == 25.0

    # 6.18.3 — Mutation-gap analysis feeds strengthening.
    strengthening = TestStrengthener().strengthen(
        tests,
        weak_assessment=weak,
        mutation_assessment=mutation,
    )

    assert strengthening.changed is True
    assert strengthening.added_tests

    strengthened_tests = strengthening.strengthened_tests

    # 6.18.4 — Regression generation.
    regression = RegressionTestGenerator().generate(
        source_code=SOURCE,
        function_name="add",
        arguments=(2, 3),
        expected=5,
        description="preserve repaired addition behavior",
    )

    assert regression.test_code
    assert "assert add(2, 3) == 5" in regression.test_code

    # Ensure the generated regression case can be incorporated.
    combined_tests = (
        strengthened_tests.rstrip()
        + "\n"
        + regression.test_code
        + "\n"
    )

    combined_quality = TestQualityAssessor().assess(combined_tests)

    assert combined_quality.valid is True
    assert combined_quality.assertion_count >= 2

    # 6.18.6 — Property expansion.
    properties = PropertyExpansionEngine().expand(
        "add",
        "add",
    )

    assert len(properties) == 4
    assert any(
        case.name == "add_commutative"
        for case in properties
    )

    # 6.18.7 — Verification strategy selection.
    # Use a direct assertion suite for the property-verification path.
    property_ready_tests = """
assert add(2, 3) == 5
assert add(3, 2) == 5
assert add(-2, 2) == 0
assert add(0, 0) == 0
"""

    property_quality = TestQualityAssessor().assess(
        property_ready_tests
    )
    property_weak = WeakTestDetector().detect(
        property_ready_tests
    )

    decision = VerificationStrategySelector().select(
        quality=property_quality,
        weak=property_weak,
        mutation=MutationGapAnalyzer().assess(
            [True, True, True, True, True]
        ),
        operation="add",
    )

    assert decision.strategy.value == "property"

    # 6.18.8 — Post-repair verification loop.
    result = PostRepairVerificationLoop().verify(
        strategy=decision,
        run_standard=lambda: True,
        run_property=lambda: True,
    )

    assert result.passed is True
    assert result.attempts == 1
    assert result.mutation_gap == 0


def test_6_18_e2e_preserves_determinism():
    def run_flow():
        tests = """
assert add(2, 3) == 5
"""

        quality = TestQualityAssessor().assess(tests)
        weak = WeakTestDetector().detect(tests)
        mutation = MutationGapAnalyzer().assess(
            [True, False, True]
        )

        strengthened = TestStrengthener().strengthen(
            tests,
            weak_assessment=weak,
            mutation_assessment=mutation,
        )

        regression = RegressionTestGenerator().generate(
            source_code=SOURCE,
            function_name="add",
            arguments=(4, 5),
            expected=9,
        )

        properties = PropertyExpansionEngine().expand(
            "add",
            "add",
        )

        decision = VerificationStrategySelector().select(
            quality=quality,
            weak=weak,
            mutation=mutation,
            operation="add",
        )

        verification = PostRepairVerificationLoop(
            max_attempts=2
        ).verify(
            strategy=decision,
            run_standard=lambda: True,
            strengthen=lambda: strengthened.changed,
            run_mutation=lambda: MutationGapAnalyzer().assess(
                [True, True, True]
            ),
            run_property=lambda: True,
        )

        return (
            quality,
            weak,
            mutation,
            strengthened,
            regression,
            properties,
            decision,
            verification,
        )

    first = run_flow()
    second = run_flow()

    assert first == second


def test_6_18_components_remain_modular():
    quality = TestQualityAssessor().assess(
        "assert add(1, 2) == 3\n"
    )
    weak = WeakTestDetector().detect(
        "assert add(1, 2) == 3\n"
    )
    mutation = MutationGapAnalyzer().assess(
        [True, False]
    )
    properties = PropertyExpansionEngine().expand(
        "add",
        "add",
    )

    assert quality.valid is True
    assert weak.weak is True
    assert mutation.survived_mutations == 1
    assert len(properties) == 4
